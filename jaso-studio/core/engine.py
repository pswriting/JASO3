# -*- coding: utf-8 -*-
"""
자소서 스튜디오 — Claude API + DART 전자공시 연동 엔진
"""
import io
import json
import re
import zipfile
import datetime
import xml.etree.ElementTree as ET

import requests
import anthropic

from . import prompts

# ──────────────────────────────────────────────
# 모델 / 공통
# ──────────────────────────────────────────────

MODEL_CHOICES = {
    "Claude Sonnet 5 — 권장 (품질·비용 균형)": "claude-sonnet-5",
    "Claude Opus 5 — 최고 품질": "claude-opus-5",
    "Claude Haiku 4.5 — 빠름·저비용": "claude-haiku-4-5",
}
DEFAULT_MODEL = "claude-sonnet-5"

# DART 전자공시 기본 인증키 (무료 · 운영자 내장 키)
# 교체하려면 Streamlit secrets에 DART_API_KEY를 넣으면 이 값 대신 사용된다.
DEFAULT_DART_KEY = "062436e4daf9f2a203dec2bf5f74a5e4990f6a94"

WEB_SEARCH_TOOL_TYPE = "web_search_20250305"


class EngineError(Exception):
    """사용자에게 그대로 보여줄 한국어 오류."""


def get_client(api_key: str) -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=api_key.strip(), max_retries=2)


def _extract_text(resp) -> str:
    out = []
    for block in resp.content:
        if getattr(block, "type", "") == "text":
            out.append(block.text)
    return "".join(out).strip()


def _friendly_api_error(e: Exception) -> EngineError:
    raw = str(getattr(e, "message", "") or e)
    body = getattr(e, "body", None)
    if isinstance(body, dict):
        raw = f"{raw} {body}".strip()
    low = raw.lower()
    # 가장 흔한 400: 크레딧 미충전
    if "credit balance" in low or "purchase credits" in low:
        return EngineError(
            "Anthropic 계정에 크레딧이 없습니다. console.anthropic.com → Billing에서 "
            "크레딧을 충전(최소 $5)한 뒤 다시 시도해 주세요. API는 구독(Claude Pro)과 별도로 충전해야 합니다.")
    if isinstance(e, anthropic.AuthenticationError):
        return EngineError("API 키가 올바르지 않습니다. 사이드바에서 Anthropic API 키를 다시 확인해 주세요.")
    if isinstance(e, anthropic.PermissionDeniedError):
        return EngineError("이 API 키에 해당 기능(모델 또는 웹 검색) 권한이 없습니다. console.anthropic.com에서 키 권한을 확인해 주세요.")
    if isinstance(e, anthropic.NotFoundError):
        return EngineError("선택한 모델을 찾을 수 없습니다. 사이드바에서 다른 모델을 선택하거나 모델 ID를 확인해 주세요.")
    if isinstance(e, anthropic.RateLimitError):
        return EngineError("요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요.")
    if isinstance(e, anthropic.APIConnectionError):
        return EngineError("Anthropic 서버에 연결하지 못했습니다. 네트워크 상태를 확인한 뒤 다시 시도해 주세요.")
    if isinstance(e, anthropic.BadRequestError):
        return EngineError(f"요청이 거부되었습니다 — {raw[:250]}")
    if isinstance(e, anthropic.APIStatusError):
        return EngineError(f"API 오류 (status {e.status_code}) — {raw[:250]}")
    return EngineError(f"알 수 없는 오류가 발생했습니다: {raw[:250]}")


def _continuable_content(content):
    """이어쓰기용 assistant 콘텐츠 — 마지막 thinking 블록은 API가 거부하므로 제거."""
    blocks = list(content or [])
    while blocks and getattr(blocks[-1], "type", "") in ("thinking", "redacted_thinking"):
        blocks.pop()
    return blocks


THINKING_OFF = {"type": "disabled"}  # Claude 5는 적응형 생각이 기본 ON — 끄면 빠르고 출력이 안정적


def _create_with_pause_loop(client, base_kwargs: dict, messages: list, max_rounds: int = 6):
    """pause_turn(검색만 하고 턴 일시정지)·max_tokens(중간 끊김)이면
    assistant 내용을 이어붙여 끝까지 완성한다. 전체 텍스트를 이어서 반환."""
    msgs = list(messages)
    out = ""
    for _ in range(max_rounds):
        resp = client.messages.create(**base_kwargs, messages=msgs)
        out += _extract_text(resp)
        reason = getattr(resp, "stop_reason", "")
        if reason in ("pause_turn", "max_tokens"):
            cont = _continuable_content(resp.content)
            if cont:
                msgs = msgs + [{"role": "assistant", "content": cont}]
            # cont가 비면(생각만 하다 끝남) 같은 요청을 그대로 재시도
            continue
        break
    return out.strip()


def call_claude(client, model: str, system: str, messages: list,
                max_tokens: int = 8000, web_search: bool = False,
                max_searches: int = 6, temperature: float = 0.7):
    """반환: (텍스트, 웹서치_실제사용여부)
    - temperature는 하위 호환용 인자일 뿐 API에는 보내지 않는다 (Claude 5가 거부)
    - thinking은 기본 비활성화, 미지원 모델이면 자동으로 파라미터 제거 후 재시도
    - 웹서치 미지원 키/모델이면 검색 없이 재시도"""
    tools = [{"type": WEB_SEARCH_TOOL_TYPE, "name": "web_search", "max_uses": max_searches}]
    attempts = [(web_search, True), (web_search, False), (False, True), (False, False)]
    tried, last_err = set(), None
    for use_tools, think_off in attempts:
        sig = (use_tools, think_off)
        if sig in tried:
            continue
        tried.add(sig)
        kwargs = dict(model=model, max_tokens=max_tokens, system=system)
        if use_tools:
            kwargs["tools"] = tools
        if think_off:
            kwargs["thinking"] = THINKING_OFF
        try:
            return _create_with_pause_loop(client, kwargs, messages), use_tools
        except anthropic.BadRequestError as e:
            last_err = e
            continue
        except Exception as e:
            raise _friendly_api_error(e)
    raise _friendly_api_error(last_err)


# ──────────────────────────────────────────────
# 글자수
# ──────────────────────────────────────────────

def count_chars(text: str, mode: str = "incl") -> int:
    """incl: 공백 포함(줄바꿈 제외) / excl: 공백 제외"""
    if mode == "excl":
        return len(re.sub(r"\s", "", text))
    return len(text.replace("\n", "").replace("\r", ""))


def char_report(text: str) -> dict:
    return {"incl": count_chars(text, "incl"), "excl": count_chars(text, "excl")}


# ──────────────────────────────────────────────
# 답변 파싱
# ──────────────────────────────────────────────

def split_answer(raw: str):
    """===ANSWER=== / ===NOTES=== 형식 파싱. 형식이 깨져도 안전하게 처리."""
    text = raw.strip()
    answer, notes = text, ""
    m = re.search(r"===ANSWER===\s*(.*?)\s*(?:===NOTES===\s*(.*))?$", text, re.S)
    if m:
        answer = m.group(1).strip()
        notes = (m.group(2) or "").strip()
    if notes in ("없음", "- 없음", "없음.", "-"):
        notes = ""
    answer = _enforce_single_subtitle(answer)
    return answer, notes


def _enforce_single_subtitle(answer: str) -> str:
    """소제목은 첫 줄 1개만 — 본문 중간의 [소제목] 단독 줄은 제거해 이어붙인다."""
    lines = answer.split("\n")
    cleaned, seen = [], False
    for i, line in enumerate(lines):
        stripped = line.strip()
        is_sub = bool(re.fullmatch(r"\[[^\[\]]{2,40}\]", stripped))
        if is_sub:
            if not seen and i <= 1:
                seen = True
                cleaned.append(stripped)
                continue
            continue  # 중간 소제목 제거
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def split_subtitle(answer: str):
    """첫 줄이 [소제목]이면 (소제목, 본문)으로 분리."""
    lines = answer.strip().split("\n", 1)
    first = lines[0].strip()
    if re.fullmatch(r"\[[^\[\]]{2,40}\]", first):
        body = lines[1].strip() if len(lines) > 1 else ""
        return first.strip("[]"), body
    return "", answer.strip()


# ──────────────────────────────────────────────
# 자소서 생성
# ──────────────────────────────────────────────

MOTIVATION_PAT = re.compile(
    r"지원\s*동기|지원\s*(한|하게\s*된|하신)\s*(이유|사유|동기|계기)|"
    r"왜\s*(우리|당사|저희|본사)|입사(를)?\s*(희망|결심|지원)|당사에\s*지원")
ASPIRATION_PAT = re.compile(r"입사\s*후|포부|커리어\s*(계획|목표)|10년|성장\s*비전|이루고\s*싶은")


def is_company_question(question: str) -> bool:
    """지원동기·포부 등 회사 맞춤 리서치가 필요한 문항인지."""
    q = question or ""
    return bool(MOTIVATION_PAT.search(q) or ASPIRATION_PAT.search(q))


def _system_for_writing() -> str:
    return prompts.STYLE_CONSTITUTION + "\n\n" + prompts.FEWSHOT_EXAMPLES


def _max_tokens_for(limit: int) -> int:
    return min(12000, max(1500, int(limit * 2) + 600))


def generate_answer(client, model: str, *, company: str, role: str, question: str,
                    limit: int, count_mode: str, interview: dict, hint: str = "",
                    research_md: str = "", fit_summary: str = "",
                    live_search: bool = False, is_freeform: bool = False,
                    materials_text: str = "", pass_analysis: str = ""):
    """
    반환 dict: answer, notes, used_search, chars(incl/excl), attempts
    live_search: 리서치 자료가 없을 때 생성 단계에서 직접 웹 검색을 수행할지
    """
    user = prompts.build_answer_prompt(
        company=company, role=role, question=question, limit=limit,
        count_mode=count_mode, interview=interview, hint=hint,
        research_md=research_md, fit_summary=fit_summary, is_freeform=is_freeform,
        materials_text=materials_text, pass_analysis=pass_analysis)
    if live_search and not research_md:
        user += ("\n\n추가 지시: 회사 리서치 자료가 없으므로, 웹 검색으로 "
                 f"'{company}'의 최신 사실(실적·신사업·전략) 2~3개를 확인해 지원동기 근거로 인용하라. "
                 "검색으로 확인되지 않은 수치는 쓰지 마라.")

    system = _system_for_writing()
    messages = [{"role": "user", "content": user}]
    use_search = live_search and not research_md and bool(company.strip())
    raw, used_search = call_claude(client, model, system, messages,
                                   max_tokens=_max_tokens_for(limit),
                                   web_search=use_search, max_searches=5)
    answer, notes = split_answer(raw)

    # 분량 자동 보정 (최대 2회)
    lo, hi = int(limit * 0.92), limit
    attempts = 1
    for _ in range(2):
        n = count_chars(answer, count_mode)
        if lo <= n <= hi:
            break
        messages = messages + [
            {"role": "assistant", "content": raw},
            {"role": "user", "content": prompts.build_length_fix_prompt(n, lo, hi, count_mode)},
        ]
        raw, _ = call_claude(client, model, system, messages,
                             max_tokens=_max_tokens_for(limit), web_search=False)
        new_answer, new_notes = split_answer(raw)
        if new_answer:
            answer = new_answer
            notes = new_notes or notes
        attempts += 1

    if not answer.strip():
        raise EngineError("답변 생성에 실패했습니다(빈 응답). 다시 한 번 눌러 주세요.")
    return {
        "answer": answer,
        "notes": notes,
        "used_search": used_search,
        "chars": char_report(answer),
        "attempts": attempts,
    }


def refine_answer(client, model: str, *, question: str, prev_answer: str,
                  instruction: str, limit: int, count_mode: str):
    system = _system_for_writing()
    user = prompts.build_refine_prompt(question, prev_answer, instruction, limit, count_mode)
    messages = [{"role": "user", "content": user}]
    raw, _ = call_claude(client, model, system, messages,
                         max_tokens=_max_tokens_for(limit), web_search=False)
    answer, notes = split_answer(raw)

    lo, hi = int(limit * 0.92), limit
    for _ in range(1):
        n = count_chars(answer, count_mode)
        if lo <= n <= hi:
            break
        messages = messages + [
            {"role": "assistant", "content": raw},
            {"role": "user", "content": prompts.build_length_fix_prompt(n, lo, hi, count_mode)},
        ]
        raw, _ = call_claude(client, model, system, messages,
                             max_tokens=_max_tokens_for(limit), web_search=False)
        new_answer, new_notes = split_answer(raw)
        if new_answer:
            answer, notes = new_answer, (new_notes or notes)

    if not answer.strip():
        raise EngineError("답변 생성에 실패했습니다(빈 응답). 다시 한 번 눌러 주세요.")
    return {"answer": answer, "notes": notes, "chars": char_report(answer)}


# ──────────────────────────────────────────────
# 기업 리서치 (Claude 웹서치)
# ──────────────────────────────────────────────

def _stream_with_search(client, model: str, system: str, user: str,
                        max_tokens: int, max_searches: int, status: dict):
    """웹서치 스트리밍 제너레이터.
    - 미지원 키/모델이면 검색 없이 폴백 (status['fallback']=True)
    - stop_reason=pause_turn(검색만 하고 턴 일시정지)이면 자동으로 이어받아 끝까지 작성
    """
    base = dict(model=model, max_tokens=max_tokens, system=system)
    tools = [{"type": WEB_SEARCH_TOOL_TYPE, "name": "web_search", "max_uses": max_searches}]
    msgs = [{"role": "user", "content": user}]
    use_tools = True
    think_off = True
    total = 0
    for _round in range(8):
        kwargs = dict(base, messages=msgs)
        if use_tools:
            kwargs["tools"] = tools
        if think_off:
            kwargs["thinking"] = THINKING_OFF
        try:
            with client.messages.stream(**kwargs) as s:
                for t in s.text_stream:
                    total += len(t)
                    yield t
                final = s.get_final_message()
        except anthropic.BadRequestError as e:
            if think_off and "thinking" in str(e).lower():
                think_off = False  # thinking 파라미터 미지원 모델
                continue
            if use_tools and total == 0:
                use_tools = False
                status["fallback"] = True
                continue
            raise _friendly_api_error(e)
        except Exception as e:
            raise _friendly_api_error(e)
        if getattr(final, "stop_reason", "") in ("pause_turn", "max_tokens"):
            # pause_turn: 검색만 하고 멈춤 / max_tokens: 쓰다가 중간 끊김
            # → 지금까지의 내용을 이어붙여 계속 쓰게 한다 (마지막 thinking 블록은 제거)
            cont = _continuable_content(final.content)
            if cont:
                msgs = msgs + [{"role": "assistant", "content": cont}]
            # cont가 비면(생각만 하다 끝남) 같은 요청을 그대로 재시도
            continue
        break
    if total == 0:
        raise EngineError("분석 본문을 받지 못했습니다. 잠시 후 한 번 더 시도해 주세요. "
                          "반복되면 '정밀 분석' 모드로 시도해 보세요.")


def research_company_stream(client, model: str, company: str, role: str,
                            posting: str = "", dart_text: str = "",
                            fast: bool = True, status: dict = None):
    """기업 분석 스트리밍 — st.write_stream에 바로 넣는다."""
    user = prompts.build_research_prompt(company, role, posting, dart_text, fast=fast)
    return _stream_with_search(client, model, prompts.RESEARCH_SYSTEM, user,
                               max_tokens=5000 if fast else 8000,
                               max_searches=3 if fast else 8,
                               status=status if status is not None else {})


def analyze_pass_essays_stream(client, model: str, company: str, role: str,
                               status: dict = None):
    """합격 자소서 패턴 분석 스트리밍."""
    user = prompts.build_pass_prompt(company, role)
    return _stream_with_search(client, model, prompts.PASS_SYSTEM, user,
                               max_tokens=5000, max_searches=5,
                               status=status if status is not None else {})


def research_company(client, model: str, company: str, role: str,
                     posting: str = "", dart_text: str = ""):
    user = prompts.build_research_prompt(company, role, posting, dart_text, fast=False)
    text, used_search = call_claude(
        client, model, prompts.RESEARCH_SYSTEM,
        [{"role": "user", "content": user}],
        max_tokens=7000, web_search=True, max_searches=8)
    return {"markdown": text, "used_search": used_search}


def analyze_pass_essays(client, model: str, company: str, role: str):
    """기업·직무별 공개 합격 자소서 패턴 분석 (실시간 웹 검색)."""
    user = prompts.build_pass_prompt(company, role)
    text, used_search = call_claude(
        client, model, prompts.PASS_SYSTEM,
        [{"role": "user", "content": user}],
        max_tokens=6000, web_search=True, max_searches=8)
    return {"markdown": text, "used_search": used_search}


# ──────────────────────────────────────────────
# 직무 적합도 진단
# ──────────────────────────────────────────────

def _parse_json_loose(text: str) -> dict:
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.S)
    try:
        return json.loads(t)
    except Exception:
        pass
    start, end = t.find("{"), t.rfind("}")
    if start != -1 and end > start:
        return json.loads(t[start:end + 1])
    raise EngineError("진단 결과를 해석하지 못했습니다. 다시 한번 시도해 주세요.")


def analyze_fit(client, model: str, company: str, role: str, spec: dict,
                research_md: str = "", posting: str = "", use_search: bool = False):
    user = prompts.build_fit_prompt(company, role, spec, research_md, posting)
    if use_search and not research_md:
        user += (f"\n\n추가 지시: 웹 검색으로 '{company}' '{role}' 채용 요건·우대사항을 확인한 뒤 평가에 반영하라.")
    text, used_search = call_claude(
        client, model, prompts.FIT_SYSTEM,
        [{"role": "user", "content": user}],
        max_tokens=4000, web_search=use_search and not research_md,
        max_searches=4, temperature=0.2)
    data = _parse_json_loose(text)
    data["used_search"] = used_search
    return data


def fit_summary_text(fit: dict) -> str:
    """생성 프롬프트에 넣을 진단 요약."""
    if not fit:
        return ""
    lines = [f"종합 {fit.get('overall', '?')}점 · {fit.get('verdict', '')} — {fit.get('one_line', '')}"]
    for s in fit.get("strengths", [])[:3]:
        lines.append(f"강점: {s.get('title', '')} ({s.get('why', '')})")
    for g in fit.get("gaps", [])[:3]:
        lines.append(f"보완: {g.get('title', '')} → {g.get('fix', '')}")
    return "\n".join(lines)


# ──────────────────────────────────────────────
# AI 소재 발굴
# ──────────────────────────────────────────────

def mine_materials(client, model: str, company: str, role: str, docs_text: str,
                   spec: dict, research_md: str = "", fit_summary: str = ""):
    user = prompts.build_mine_prompt(company, role, docs_text, spec, research_md, fit_summary)
    text, _ = call_claude(client, model, prompts.MINE_SYSTEM,
                          [{"role": "user", "content": user}],
                          max_tokens=5000, temperature=0.4)
    data = _parse_json_loose(text)
    return data.get("materials", [])


def memory_questions(client, model: str, company: str, role: str, spec: dict):
    """소재가 안 떠오르는 사용자를 위한 기억 자극 질문 생성."""
    user = prompts.build_helper_prompt(company, role, spec)
    text, _ = call_claude(client, model, prompts.HELPER_SYSTEM,
                          [{"role": "user", "content": user}],
                          max_tokens=3000, temperature=0.6)
    data = _parse_json_loose(text)
    return data.get("groups", [])


def materials_to_text(materials: list) -> str:
    """생성 프롬프트 주입용."""
    if not materials:
        return ""
    lines = []
    for m in materials:
        best = "·".join(m.get("best_for", []))
        lines.append(f"- [{m.get('title','')}] {m.get('summary','')} "
                     f"(핵심 숫자: {m.get('number_hook','')} / 적합 문항: {best})")
    return "\n".join(lines)


# ──────────────────────────────────────────────
# AI 감지 위험 진단 · 휴먼라이징
# ──────────────────────────────────────────────

_AI_CLICHES = ["이를 통해", "뿐만 아니라", "나아가", "라고 할 수 있습니다",
               "확인할 수 있었습니다", "다양한 노력", "적극적으로", "기반으로 한",
               "긍정적인 영향을 미칠 것입니다", "라고 생각합니다"]


def _stylometrics(text: str) -> dict:
    """로컬 문체 통계 → AI스러움 휴리스틱 점수(0~100)."""
    body = re.sub(r"^\[[^\[\]]{2,40}\]\s*", "", text.strip())  # 소제목 제외
    sents = [s.strip() for s in re.split(r"(?<=다\.)\s+|(?<=[.!?])\s+", body) if len(s.strip()) >= 4]
    if len(sents) < 3:
        return {"score": 50, "sent_cv": 0, "ending_ratio": 0, "cliche_per_k": 0, "n_sents": len(sents)}

    lens = [len(s) for s in sents]
    mean = sum(lens) / len(lens)
    var = sum((x - mean) ** 2 for x in lens) / len(lens)
    cv = (var ** 0.5) / mean if mean else 0  # 길이 변동계수: 낮을수록 기계적

    endings = {}
    for s in sents:
        e = s[-6:]
        e = re.sub(r"[^가-힣]", "", e)[-4:]
        endings[e] = endings.get(e, 0) + 1
    ending_ratio = max(endings.values()) / len(sents)  # 같은 종결 반복 비율

    n_chars = max(1, len(body))
    cliche_count = sum(body.count(c) for c in _AI_CLICHES)
    cliche_per_k = cliche_count * 1000 / n_chars

    # 점수 결합
    score = 0.0
    score += max(0.0, (0.55 - min(cv, 0.55))) / 0.55 * 40      # 균일한 문장 길이 (최대 40)
    score += max(0.0, ending_ratio - 0.55) / 0.45 * 25          # 종결 단조로움 (최대 25)
    score += min(cliche_per_k / 6.0, 1.0) * 35                  # 상투 표현 밀도 (최대 35)
    return {"score": round(min(100, score)), "sent_cv": round(cv, 2),
            "ending_ratio": round(ending_ratio, 2),
            "cliche_per_k": round(cliche_per_k, 1), "n_sents": len(sents)}


def ai_scan(client, model: str, text: str) -> dict:
    """AI 감지 위험(추정 %) = 로컬 휴리스틱 50% + Claude 포렌식 평가 50%."""
    heur = _stylometrics(text)
    raw, _ = call_claude(client, model, prompts.AISCAN_SYSTEM,
                         [{"role": "user", "content": prompts.build_aiscan_prompt(text)}],
                         max_tokens=2000, temperature=0.1)
    data = _parse_json_loose(raw)
    llm_p = int(data.get("probability", 50))
    percent = round(0.5 * heur["score"] + 0.5 * llm_p)
    if percent <= 30:
        verdict = "안전"
    elif percent <= 60:
        verdict = "주의"
    else:
        verdict = "위험"
    return {"percent": percent, "verdict": verdict,
            "llm": llm_p, "heuristic": heur["score"], "detail": heur,
            "flags": data.get("flags", []), "comment": data.get("comment", "")}


def humanize_answer(client, model: str, *, question: str, prev_answer: str,
                    limit: int, count_mode: str, flags: list):
    """AI 티 제거 재작성. 분량 유지 보정 포함."""
    system = _system_for_writing()
    user = prompts.build_humanize_prompt(question, prev_answer, limit, count_mode, flags)
    messages = [{"role": "user", "content": user}]
    raw, _ = call_claude(client, model, system, messages,
                         max_tokens=_max_tokens_for(limit), temperature=0.9)
    answer, notes = split_answer(raw)

    lo, hi = int(limit * 0.92), limit
    for _ in range(1):
        n = count_chars(answer, count_mode)
        if lo <= n <= hi:
            break
        messages = messages + [
            {"role": "assistant", "content": raw},
            {"role": "user", "content": prompts.build_length_fix_prompt(n, lo, hi, count_mode)},
        ]
        raw, _ = call_claude(client, model, system, messages,
                             max_tokens=_max_tokens_for(limit), temperature=0.9)
        new_answer, new_notes = split_answer(raw)
        if new_answer:
            answer, notes = new_answer, (new_notes or notes)

    if not answer.strip():
        raise EngineError("답변 생성에 실패했습니다(빈 응답). 다시 한 번 눌러 주세요.")
    return {"answer": answer, "notes": notes, "chars": char_report(answer)}


# ──────────────────────────────────────────────
# 유사도(다른 지원자와 겹침) 진단 · 고유화
# ──────────────────────────────────────────────

_TEMPLATE_PHRASES = [
    "기업 선택 시 가장 중요하게 생각하는 요인은", "가장 뛰어난 기업이라고 판단해 지원",
    "행보에 동참해", "제가 지닌 전문성을 발휘", "확인할 수 있었습니다",
    "다방면으로 노력한 결과", "문제를 해결하기 위해", "라는 사실을 발견했습니다",
    "긍정적인 영향을 미칠 것입니다", "기여하겠습니다", "이바지하겠습니다",
    "높은 인사고과를 받았습니다", "우수 직원으로", "직무에 적합하다고 생각합니다",
    "어린 시절부터", "가치관입니다", "역량을 강화했습니다", "전문성을 강화했습니다",
    "입사 후에도", "그 결과,",
]


def _similarity_heuristic(text: str) -> dict:
    """상투 문형 밀도 기반 유사도 위험(0~100)."""
    hits, found = 0.0, []
    for ph in _TEMPLATE_PHRASES:
        c = text.count(ph)
        if c:
            found.append(ph)
            hits += 8 + 4 * (c - 1)
    # 흔한 소제목 패턴
    m = re.match(r"\s*\[([^\[\]]{2,40})\]", text)
    if m and re.search(r"비결|이유|직무에 적합한", m.group(1)):
        hits += 8
    score = round(min(100, hits))
    return {"score": score, "found": found[:8]}


def similarity_scan(client, model: str, text: str) -> dict:
    """유사도 위험(추정 %) = 로컬 상투 문형 밀도 50% + Claude 평가 50%."""
    heur = _similarity_heuristic(text)
    raw, _ = call_claude(client, model, prompts.SIM_SYSTEM,
                         [{"role": "user", "content": prompts.build_simscan_prompt(text)}],
                         max_tokens=2000, temperature=0.1)
    data = _parse_json_loose(raw)
    llm_p = int(data.get("probability", 50))
    percent = round(0.5 * heur["score"] + 0.5 * llm_p)
    if percent <= 30:
        verdict = "낮음"
    elif percent <= 60:
        verdict = "주의"
    else:
        verdict = "높음"
    flags = data.get("flags", [])
    for ph in heur["found"]:
        if not any(ph in str(f.get("phrase", "")) for f in flags):
            flags.append({"phrase": ph, "why": "자소서에 매우 흔한 관용구",
                          "fix": "같은 뜻의 새 문장으로 교체"})
    return {"percent": percent, "verdict": verdict, "llm": llm_p,
            "heuristic": heur["score"], "flags": flags[:6],
            "comment": data.get("comment", "")}


def uniquify_answer(client, model: str, *, question: str, prev_answer: str,
                    limit: int, count_mode: str, flags: list):
    """유사도 낮추기 — 사실·구조 유지, 문장 틀만 고유하게 재작성. 분량 보정 포함."""
    system = _system_for_writing()
    user = prompts.build_uniquify_prompt(question, prev_answer, limit, count_mode, flags)
    messages = [{"role": "user", "content": user}]
    raw, _ = call_claude(client, model, system, messages,
                         max_tokens=_max_tokens_for(limit), temperature=0.9)
    answer, notes = split_answer(raw)

    lo, hi = int(limit * 0.92), limit
    for _ in range(1):
        n = count_chars(answer, count_mode)
        if lo <= n <= hi:
            break
        messages = messages + [
            {"role": "assistant", "content": raw},
            {"role": "user", "content": prompts.build_length_fix_prompt(n, lo, hi, count_mode)},
        ]
        raw, _ = call_claude(client, model, system, messages,
                             max_tokens=_max_tokens_for(limit), temperature=0.9)
        new_answer, new_notes = split_answer(raw)
        if new_answer:
            answer, notes = new_answer, (new_notes or notes)

    if not answer.strip():
        raise EngineError("답변 생성에 실패했습니다(빈 응답). 다시 한 번 눌러 주세요.")
    return {"answer": answer, "notes": notes, "chars": char_report(answer)}


# ──────────────────────────────────────────────
# DART 전자공시 API
# ──────────────────────────────────────────────

DART_BASE = "https://opendart.fss.or.kr/api"
# DART 방화벽이 python 기본 User-Agent를 거부하는 경우가 있어 브라우저 UA로 요청
DART_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
    "Accept": "*/*",
}


def dart_search_corps(name: str):
    """DART 웹 기업명 검색으로 고유번호 조회.
    대용량 corpCode.xml 다운로드(해외 서버에서 타임아웃)를 대체하는 가벼운 방식."""
    try:
        r = requests.get("https://dart.fss.or.kr/dsae001/search.ax",
                         params={"textCrpNm": name},
                         headers=DART_HEADERS, timeout=12)
        r.raise_for_status()
        html = r.text
        if "select(" not in html:
            try:
                html = r.content.decode("euc-kr", errors="replace")
            except Exception:
                pass
    except requests.RequestException:
        raise EngineError(
            "DART 기업 검색에 연결하지 못해 이번 분석에서는 건너뜁니다. "
            "웹 검색으로 재무·공시 정보를 대신 조사하므로 분석은 정상 진행됩니다.")
    corps, seen = [], set()
    for m in re.finditer(r"select\('(\d{8})'\)", html):
        code = m.group(1)
        if code in seen:
            continue
        window = html[m.start(): m.start() + 600]
        nm_m = re.search(r">\s*([^<>\n\r]{1,60}?)\s*</", window)
        nm = nm_m.group(1).strip() if nm_m else ""
        st_m = re.search(r">\s*(\d{6})\s*</", window)
        stock = st_m.group(1) if st_m else ""
        if nm:
            seen.add(code)
            corps.append({"name": nm, "code": code, "stock": stock})
    return corps


def dart_find_corp(corps: list, name: str):
    key = re.sub(r"\s+|\(주\)|주식회사", "", name)
    if not key:
        return None
    exact = [c for c in corps if re.sub(r"\s+", "", c["name"]) == key]
    partial = [c for c in corps if key in re.sub(r"\s+", "", c["name"])]
    pool = exact or partial
    if not pool:
        return None
    listed = [c for c in pool if c["stock"]]
    return (listed or pool)[0]


def _dart_get(dart_key: str, endpoint: str, **params):
    params["crtfc_key"] = dart_key.strip()
    try:
        return requests.get(f"{DART_BASE}/{endpoint}", params=params,
                            headers=DART_HEADERS, timeout=12).json()
    except requests.RequestException:
        return {"status": "err"}


def _fmt_krw(s):
    try:
        v = int(str(s).replace(",", ""))
    except (ValueError, TypeError):
        return str(s)
    sign = "-" if v < 0 else ""
    v = abs(v)
    if v >= 1_0000_0000_0000:
        return f"{sign}{v / 1_0000_0000_0000:.1f}조 원"
    if v >= 1_0000_0000:
        return f"{sign}{v / 1_0000_0000:,.0f}억 원"
    return f"{sign}{v:,}원"


def dart_snapshot(dart_key: str, company: str) -> dict:
    """기업개요 + 최근 재무 + 최근 공시를 한 번에. 실패해도 부분 결과 반환."""
    corps = dart_search_corps(company)
    corp = dart_find_corp(corps, company)
    if not corp:
        return {"found": False, "reason": "DART에서 해당 기업명을 찾지 못했습니다. 정식 법인명으로 다시 시도해 보세요."}

    snap = {"found": True, "corp_name": corp["name"],
            "listed": bool(corp["stock"]), "brief": {}, "fin": [], "fin_year": None,
            "disclosures": []}

    info = _dart_get(dart_key, "company.json", corp_code=corp["code"])
    if info.get("status") == "000":
        snap["brief"] = {
            "대표자": info.get("ceo_nm", ""),
            "설립일": _fmt_date(info.get("est_dt", "")),
            "상장 여부": "상장" if corp["stock"] else "비상장",
            "홈페이지": info.get("hm_url", ""),
        }

    # 최근 사업보고서 재무 (올해-1년부터 역순 탐색)
    this_year = datetime.date.today().year
    for year in (this_year - 1, this_year - 2):
        fin = _dart_get(dart_key, "fnlttSinglAcnt.json",
                        corp_code=corp["code"], bsns_year=str(year), reprt_code="11011")
        if fin.get("status") == "000" and fin.get("list"):
            rows = fin["list"]
            cfs = [r for r in rows if r.get("fs_div") == "CFS"] or rows
            wanted = ["매출액", "영업수익", "영업이익", "당기순이익", "자산총계"]
            picked, seen = [], set()
            for w in wanted:
                for r in cfs:
                    nm = (r.get("account_nm") or "").replace(" ", "")
                    if w in nm and w not in seen:
                        picked.append({
                            "항목": r.get("account_nm", "").strip(),
                            "당기": _fmt_krw(r.get("thstrm_amount", "")),
                            "전기": _fmt_krw(r.get("frmtrm_amount", "")),
                        })
                        seen.add(w)
                        break
            snap["fin"] = picked
            snap["fin_year"] = year
            break

    # 최근 6개월 공시
    bgn = (datetime.date.today() - datetime.timedelta(days=180)).strftime("%Y%m%d")
    dis = _dart_get(dart_key, "list.json", corp_code=corp["code"],
                    bgn_de=bgn, page_count="10")
    if dis.get("status") == "000":
        snap["disclosures"] = [
            {"일자": _fmt_date(d.get("rcept_dt", "")), "보고서": d.get("report_nm", "")}
            for d in dis.get("list", [])[:8]
        ]
    return snap


def _fmt_date(s: str) -> str:
    s = str(s).strip()
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}.{s[4:6]}.{s[6:]}"
    return s


def dart_snapshot_to_text(snap: dict) -> str:
    """리서치 프롬프트 주입용 텍스트."""
    if not snap or not snap.get("found"):
        return ""
    lines = [f"기업명: {snap['corp_name']} ({'상장' if snap.get('listed') else '비상장'})"]
    for k, v in snap.get("brief", {}).items():
        if v:
            lines.append(f"{k}: {v}")
    if snap.get("fin"):
        lines.append(f"{snap.get('fin_year')}년 사업보고서 기준 재무:")
        for f in snap["fin"]:
            lines.append(f"  - {f['항목']}: 당기 {f['당기']} / 전기 {f['전기']}")
    if snap.get("disclosures"):
        lines.append("최근 공시:")
        for d in snap["disclosures"]:
            lines.append(f"  - {d['일자']} {d['보고서']}")
    return "\n".join(lines)
