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
    if isinstance(e, anthropic.APIStatusError):
        return EngineError(f"API 오류가 발생했습니다 (status {e.status_code}). 잠시 후 다시 시도해 주세요.")
    return EngineError(f"알 수 없는 오류가 발생했습니다: {e}")


def call_claude(client, model: str, system: str, messages: list,
                max_tokens: int = 8000, web_search: bool = False,
                max_searches: int = 6, temperature: float = 0.7):
    """반환: (텍스트, 웹서치_실제사용여부)"""
    kwargs = dict(model=model, max_tokens=max_tokens, system=system,
                  messages=messages, temperature=temperature)
    if web_search:
        kwargs["tools"] = [{"type": WEB_SEARCH_TOOL_TYPE, "name": "web_search",
                            "max_uses": max_searches}]
    try:
        resp = client.messages.create(**kwargs)
        return _extract_text(resp), web_search
    except anthropic.BadRequestError:
        if web_search:
            # 웹서치 도구를 지원하지 않는 키/모델 → 검색 없이 폴백
            kwargs.pop("tools", None)
            try:
                resp = client.messages.create(**kwargs)
                return _extract_text(resp), False
            except Exception as e2:
                raise _friendly_api_error(e2)
        raise
    except Exception as e:
        raise _friendly_api_error(e)


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
                    materials_text: str = ""):
    """
    반환 dict: answer, notes, used_search, chars(incl/excl), attempts
    live_search: 리서치 자료가 없을 때 생성 단계에서 직접 웹 검색을 수행할지
    """
    user = prompts.build_answer_prompt(
        company=company, role=role, question=question, limit=limit,
        count_mode=count_mode, interview=interview, hint=hint,
        research_md=research_md, fit_summary=fit_summary, is_freeform=is_freeform,
        materials_text=materials_text)
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

    return {"answer": answer, "notes": notes, "chars": char_report(answer)}


# ──────────────────────────────────────────────
# 기업 리서치 (Claude 웹서치)
# ──────────────────────────────────────────────

def research_company(client, model: str, company: str, role: str,
                     posting: str = "", dart_text: str = ""):
    user = prompts.build_research_prompt(company, role, posting, dart_text)
    text, used_search = call_claude(
        client, model, prompts.RESEARCH_SYSTEM,
        [{"role": "user", "content": user}],
        max_tokens=7000, web_search=True, max_searches=8, temperature=0.3)
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

def mine_materials(client, model: str, company: str, role: str, profile: dict,
                   spec: dict, research_md: str = "", fit_summary: str = ""):
    user = prompts.build_mine_prompt(company, role, profile, spec, research_md, fit_summary)
    text, _ = call_claude(client, model, prompts.MINE_SYSTEM,
                          [{"role": "user", "content": user}],
                          max_tokens=3500, temperature=0.4)
    data = _parse_json_loose(text)
    return data.get("materials", [])


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

    return {"answer": answer, "notes": notes, "chars": char_report(answer)}


# ──────────────────────────────────────────────
# DART 전자공시 API
# ──────────────────────────────────────────────

DART_BASE = "https://opendart.fss.or.kr/api"


def dart_load_corp_map(dart_key: str):
    """전체 기업 코드 목록 다운로드 (호출측에서 캐시 권장)."""
    try:
        r = requests.get(f"{DART_BASE}/corpCode.xml",
                         params={"crtfc_key": dart_key.strip()}, timeout=40)
        r.raise_for_status()
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        xml_data = zf.read(zf.namelist()[0])
    except zipfile.BadZipFile:
        raise EngineError("DART API 키가 올바르지 않습니다. opendart.fss.or.kr에서 발급한 키인지 확인해 주세요.")
    except requests.RequestException:
        raise EngineError("DART 서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.")
    root = ET.fromstring(xml_data)
    corps = []
    for el in root.iter("list"):
        corps.append({
            "name": (el.findtext("corp_name") or "").strip(),
            "code": (el.findtext("corp_code") or "").strip(),
            "stock": (el.findtext("stock_code") or "").strip(),
        })
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
        return requests.get(f"{DART_BASE}/{endpoint}", params=params, timeout=20).json()
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


def dart_snapshot(dart_key: str, corps: list, company: str) -> dict:
    """기업개요 + 최근 재무 + 최근 공시를 한 번에. 실패해도 부분 결과 반환."""
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
