# -*- coding: utf-8 -*-
"""
자소서 스튜디오 (JASO STUDIO) v2
읽는 순간 뽑고 싶어지는 자기소개서 — 실시간 기업 분석 · 소재 발굴 · AI 감지 방어
"""
import base64
import json
import datetime
import pathlib

import streamlit as st

from core import engine, styles, exporter, reader, templates

# ──────────────────────────────────────────────
# 페이지 설정
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="자소서 스튜디오 — 합격 자기소개서 작성기",
    page_icon="✒️",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(styles.GLOBAL_CSS, unsafe_allow_html=True)

# 테마 설정(.streamlit/config.toml)이 없는 환경 → 기본 빨간 액센트를 골드 톤으로 보정
try:
    _theme_set = bool(st.get_option("theme.primaryColor"))
except Exception:
    _theme_set = False
if not _theme_set:
    st.markdown(styles.RED_FALLBACK_CSS, unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def _media_b64(relpath: str, max_mb: float = 15.0) -> str:
    """static 파일을 base64로 — 정적 서빙 설정 없이도 배경 영상이 나오게."""
    p = pathlib.Path(__file__).parent / relpath
    try:
        if p.exists() and p.stat().st_size <= max_mb * 1024 * 1024:
            return base64.b64encode(p.read_bytes()).decode()
    except Exception:
        pass
    return ""


_bg_mp4 = _media_b64("static/bg.mp4")
_bg_webm = _media_b64("static/bg.webm")
if _bg_mp4 or _bg_webm:
    import streamlit.components.v1 as _components
    _components.html(styles.video_iframe_html(_bg_mp4, _bg_webm), height=0)
else:
    st.markdown(styles.video_background("app/static/bg.mp4"), unsafe_allow_html=True)
st.markdown(styles.overlay_div(), unsafe_allow_html=True)
# core/styles.py가 구버전이어도 앱이 죽지 않게 방어적으로 호출
_menu_btn = getattr(styles, "menu_button_html", None)
if callable(_menu_btn):
    st.markdown(_menu_btn(), unsafe_allow_html=True)

# ──────────────────────────────────────────────
# 세션 상태 초기화
# ──────────────────────────────────────────────
_DEFAULTS = {
    "step": 1,                # 현재 단계 (1~5)
    "questions": [],          # [{id, is_freeform}]
    "q_seq": 0,
    "answers": {},            # id -> {question, answer, notes, chars, limit, count_mode, used_search, ai, sim}
    "materials": [],          # AI 발굴 소재
    "mat_recs": {},           # 문항별 AI 추천 소재 {qid: {title, reason}}
    "mat_rec_sig": "",        # 추천 재계산 방지용 서명
    "mat_rec_applied": {},    # 자동 적용된 추천 {qid: title}
    "helper_qs": [],          # 기억 자극 질문 (소재 발굴 도우미)
    "uploaded_docs": [],      # [{name, text, chars, warn}]
    "doc_sigs": [],
    "research_md": "",
    "research_meta": "",
    "pass_md": "",
    "pass_meta": "",
    "dart_snap": None,
    "fit": None,
    "_loaded_sig": "",
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── 입력값 고정 ──
# 단계형 화면에서는 현재 단계에 렌더되지 않은 위젯의 상태를 Streamlit이 지워버린다.
# 매 실행마다 값을 세션 키로 재할당해 단계를 오가도 입력값이 유지되게 한다.
_PERSIST_PREFIXES = ("in_", "sp_", "iv_", "q_text_", "q_limit_", "q_mode_",
                     "q_hint_", "q_research_", "q_exp_", "q_mat_")
for _k in list(st.session_state.keys()):
    if isinstance(_k, str) and _k.startswith(_PERSIST_PREFIXES):
        st.session_state[_k] = st.session_state[_k]

EXP_FIELDS = [
    ("situation", "상황 — 언제, 어디서, 무슨 역할이었나요?",
     "예: JW메리어트 호텔 멤버십 세일즈 담당, 2021~2023"),
    ("problem", "문제와 원인 — 무엇이 잘못되고 있었고, 진짜 원인은 무엇이었나요?",
     "예: 멤버십 가입률 매년 급감. 분석해 보니 선택지가 하나뿐이고 혜택이 약했음"),
    ("action", "해결 행동 — '내가' 한 행동을 순서대로 2~4개",
     "예: ① 고객 데이터로 이용 유형 3개 분류 ② 유형별 맞춤 멤버십 기획 ③ 총지배인 앞 PT"),
    ("result", "결과 — 가능하면 숫자로 (%, 금액, 건수, 수상, 채택)",
     "예: 월 매출 3,500만 원 → 8,000만 원. 최우수 직원 선정"),
    ("apply", "입사 후 활용 — 이 경험을 입사 후 어떻게 써먹을 수 있나요?",
     "예: 신규 멤버십을 주기적으로 제안해 영업 매출 극대화"),
]

SPEC_FIELDS = {
    "edu": "최종 학력·학교·전공",
    "gpa": "학점",
    "lang": "어학 성적 (토익·오픽 등)",
    "cert": "자격증",
    "career": "경력·인턴 (회사/기간/역할)",
    "project": "프로젝트·대외활동",
    "skill": "기술 스택·활용 도구",
    "award": "수상·성과",
    "etc": "기타 (블로그, 포트폴리오, 특이사항)",
}


import re as _re
_MD_HEAD_FIX = _re.compile(r"(?<![\n#])(#{2,4} )")


def _md_guard(gen):
    """스트리밍 마크다운 이중 방어 — 진행 멘트 제거 + 줄 중간 '##' 헤더 보정.
    engine 쪽 보정과 중복 적용돼도 결과가 같다(멱등)."""
    raw, sent = "", 0

    def _fix(txt):
        i = txt.find("## ")
        if i == -1:
            return ""
        return _MD_HEAD_FIX.sub(r"\n\n\1", txt[i:]).lstrip("\n")

    for t in gen:
        raw += t
        fixed = _fix(raw)
        safe = max(0, len(fixed) - 8)
        if safe > sent:
            yield fixed[sent:safe]
            sent = safe
    fixed = _fix(raw)
    if not fixed and raw.strip():
        fixed = raw
    if len(fixed) > sent:
        yield fixed[sent:]


def _secret(name: str) -> str:
    try:
        return st.secrets.get(name, "") or ""
    except Exception:
        return ""


def _docs_text(cap: int = 12000) -> str:
    """업로드된 이력서·자소서 파일에서 추출한 텍스트 (프롬프트 주입용)."""
    parts = []
    for d in st.session_state.uploaded_docs:
        parts.append(f"[파일: {d['name']}]\n{d['text']}")
    return "\n\n".join(parts)[:cap]


def _spec_dict() -> dict:
    """이력서 양식(직접 입력) + 추가 경험 메모 → 소재 발굴 재료."""
    spec = {SPEC_FIELDS[k]: st.session_state.get(f"sp_{k}", "") for k in SPEC_FIELDS}
    extra = str(st.session_state.get("in_extra_exp", "")).strip()
    if extra:
        spec["추가 경험·경력 메모"] = extra
    return spec


def _handle_uploads(ups) -> None:
    """이력서 파일 업로드 → 텍스트 추출. 새 파일이 추가되면 자동 소재 발굴 예약."""
    if not ups:
        return
    added = False
    for up in ups:
        sig = f"{up.name}-{up.size}"
        if sig in st.session_state.doc_sigs:
            continue
        with st.spinner(f"'{up.name}' 내용을 추출하는 중…"):
            text, warn = reader.extract_text(up.name, up.getvalue())
        st.session_state.doc_sigs.append(sig)
        if text.strip():
            st.session_state.uploaded_docs.append(
                {"name": up.name, "text": text[:8000],
                 "chars": len(text), "warn": warn})
            added = True
        else:
            st.warning(f"{up.name}: {warn or '텍스트를 추출하지 못했습니다.'}")
    if added:
        st.session_state["_auto_mine"] = True  # 기본 동작: 올리면 바로 발굴
        st.rerun()


def _mine_now(rerun: bool = True) -> bool:
    """업로드된 이력서 + 직접 입력 양식에서 소재 발굴 실행."""
    spec = _spec_dict()
    has_spec = any(str(v).strip() for v in spec.values())
    if not st.session_state.uploaded_docs and not has_spec:
        st.warning("이력서 파일을 올리거나, '이력서 양식으로 직접 입력'을 채워 주세요. 그게 발굴 재료가 됩니다.")
        return False
    with st.spinner("이력서에서 자소서 소재를 캐내는 중… (30초~1분)"):
        try:
            st.session_state.materials = engine.mine_materials(
                engine.get_client(api_key), model,
                st.session_state.get("in_company", ""),
                st.session_state.get("in_role", ""),
                _docs_text(), spec,
                st.session_state.research_md,
                engine.fit_summary_text(st.session_state.fit) if st.session_state.fit else "")
        except engine.EngineError as e:
            st.error(str(e))
            return False
    if rerun:
        st.rerun()
    return True


def _consume_auto_mine():
    """업로드 직후 자동 발굴 — API 키가 없으면 안내만."""
    if not st.session_state.pop("_auto_mine", False):
        return
    if api_key.strip():
        _mine_now()
    else:
        st.info("파일 추출 완료 — 사이드바에 Anthropic API 키를 입력하면, 다음부터는 올리는 즉시 소재 발굴까지 자동으로 진행됩니다.")


def _uploaded_docs_list(key_prefix: str = ""):
    """업로드된 파일 목록 + 삭제/미리보기."""
    for i, d in enumerate(st.session_state.uploaded_docs):
        dc = st.columns([7, 1])
        with dc[0]:
            warn_txt = f"  ·  ⚠ {d['warn']}" if d.get("warn") else ""
            st.markdown(f"📄 **{d['name']}** — {d['chars']:,}자 추출됨{warn_txt}")
        with dc[1]:
            if st.button("삭제", key=f"{key_prefix}deldoc_{i}", use_container_width=True):
                st.session_state.uploaded_docs.pop(i)
                st.rerun()
    if st.session_state.uploaded_docs:
        with st.expander("추출된 내용 미리보기"):
            for d in st.session_state.uploaded_docs:
                st.markdown(f"**{d['name']}**")
                st.text(d["text"][:1200] + ("…" if len(d["text"]) > 1200 else ""))


def _new_question(text: str = "", limit: int = 700, is_freeform: bool = False):
    st.session_state.q_seq += 1
    qid = st.session_state.q_seq
    st.session_state.questions.append({"id": qid, "is_freeform": is_freeform})
    st.session_state[f"q_text_{qid}"] = text
    st.session_state[f"q_limit_{qid}"] = limit
    st.session_state[f"q_mode_{qid}"] = "공백 포함"
    st.session_state[f"q_hint_{qid}"] = ""
    st.session_state[f"q_research_{qid}"] = True
    for f, _, _ in EXP_FIELDS:
        st.session_state.setdefault(f"q_exp_{qid}_{f}", "")
    return qid


def _collect_question(qid: int) -> dict:
    return {
        "id": qid,
        "text": st.session_state.get(f"q_text_{qid}", "").strip(),
        "limit": int(st.session_state.get(f"q_limit_{qid}", 700)),
        "count_mode": "incl" if st.session_state.get(f"q_mode_{qid}", "공백 포함") == "공백 포함" else "excl",
        "hint": st.session_state.get(f"q_hint_{qid}", ""),
        "use_research": bool(st.session_state.get(f"q_research_{qid}", True)),
        "exp": {f: st.session_state.get(f"q_exp_{qid}_{f}", "") for f, _, _ in EXP_FIELDS},
        "is_freeform": next((q.get("is_freeform", False) for q in st.session_state.questions if q["id"] == qid), False),
    }


def _exp_filled_count(qid: int) -> int:
    return sum(1 for f, _, _ in EXP_FIELDS if str(st.session_state.get(f"q_exp_{qid}_{f}", "")).strip())


def _export_session() -> str:
    data = {
        "meta": {"app": "jaso-studio", "version": 2,
                 "saved": datetime.datetime.now().isoformat(timespec="seconds")},
        "basic": {
            "company": st.session_state.get("in_company", ""),
            "role": st.session_state.get("in_role", ""),
            "posting": st.session_state.get("in_posting", ""),
            "extra_exp": st.session_state.get("in_extra_exp", ""),
        },
        "spec": {k: st.session_state.get(f"sp_{k}", "") for k in SPEC_FIELDS},
        "questions": [_collect_question(q["id"]) for q in st.session_state.questions],
        "answers": st.session_state.answers,
        "materials": st.session_state.materials,
        "uploaded_docs": st.session_state.uploaded_docs,
        "research_md": st.session_state.research_md,
        "pass_md": st.session_state.pass_md,
        "fit": st.session_state.fit,
    }
    return json.dumps(data, ensure_ascii=False, indent=1)


def _import_session(data: dict):
    basic = data.get("basic", {})
    st.session_state["in_company"] = basic.get("company", "")
    st.session_state["in_role"] = basic.get("role", "")
    st.session_state["in_posting"] = basic.get("posting", "")
    st.session_state["in_extra_exp"] = basic.get("extra_exp", "")
    for k, v in data.get("spec", {}).items():
        st.session_state[f"sp_{k}"] = v
    st.session_state.questions = []
    st.session_state.q_seq = 0
    for q in data.get("questions", []):
        qid = _new_question(q.get("text", ""), q.get("limit", 700), q.get("is_freeform", False))
        st.session_state[f"q_mode_{qid}"] = "공백 포함" if q.get("count_mode", "incl") == "incl" else "공백 제외"
        st.session_state[f"q_hint_{qid}"] = q.get("hint", "")
        st.session_state[f"q_research_{qid}"] = q.get("use_research", True)
        for f, val in (q.get("exp") or {}).items():
            st.session_state[f"q_exp_{qid}_{f}"] = val
    st.session_state.answers = {int(k): v for k, v in data.get("answers", {}).items()}
    st.session_state.materials = data.get("materials", [])
    st.session_state.uploaded_docs = data.get("uploaded_docs", [])
    st.session_state.research_md = data.get("research_md", "")
    st.session_state.pass_md = data.get("pass_md", "")
    st.session_state.fit = data.get("fit", None)


@st.cache_data(show_spinner=False)
def _cached_template(key: str) -> bytes:
    return templates.TEMPLATES[key][2]()


def _generate_one(qdata: dict, idx: int, quiet: bool = False):
    company = st.session_state.get("in_company", "")
    role = st.session_state.get("in_role", "")
    research = st.session_state.research_md if qdata["use_research"] else ""
    fit_sum = engine.fit_summary_text(st.session_state.fit) if st.session_state.fit else ""
    live = qdata["use_research"] and not st.session_state.research_md and engine.is_company_question(qdata["text"])
    interview = {f"exp_{f}": v for f, v in qdata["exp"].items()}
    interview["uploaded_docs"] = _docs_text()
    mat_text = engine.materials_to_text(st.session_state.materials)

    def _run():
        try:
            result = engine.generate_answer(
                engine.get_client(api_key), model,
                company=company, role=role, question=qdata["text"],
                limit=qdata["limit"], count_mode=qdata["count_mode"],
                interview=interview, hint=qdata["hint"],
                research_md=research, fit_summary=fit_sum,
                live_search=live, is_freeform=qdata["is_freeform"],
                materials_text=mat_text,
                pass_analysis=(st.session_state.pass_md if qdata["use_research"] else ""))
            st.session_state.answers[qdata["id"]] = {
                "question": qdata["text"], "answer": result["answer"],
                "notes": result["notes"], "chars": result["chars"],
                "limit": qdata["limit"], "count_mode": qdata["count_mode"],
                "used_search": result["used_search"], "ai": None, "sim": None,
            }
            return True
        except engine.EngineError as e:
            st.error(str(e))
            return False

    if quiet:
        return _run()
    with st.spinner(f"문항 {idx} 답변 작성 중… (두괄식·소제목·분량 자동 보정, 30초~1분)"):
        ok = _run()
    if ok:
        st.rerun()


def _fill_exp_from_material(qid: int):
    """③에서 발굴된 소재 선택 시 경험 5칸을 초안으로 자동 채움."""
    sel = st.session_state.get(f"q_mat_{qid}")
    if not sel or sel == "직접 입력":
        return
    for m in st.session_state.materials:
        if m.get("title") == sel:
            draft = m.get("draft") or {}
            for f, _, _ in EXP_FIELDS:
                val = str(draft.get(f, "")).strip()
                if val:
                    st.session_state[f"q_exp_{qid}_{f}"] = val
            if not draft and m.get("summary"):
                st.session_state[f"q_exp_{qid}_situation"] = m["summary"]
            break


def _run_ai_scan(qid: int):
    ans = st.session_state.answers.get(qid)
    if not ans:
        return
    with st.spinner("AI 감지 위험을 측정하는 중…"):
        try:
            scan = engine.ai_scan(engine.get_client(api_key), model, ans["answer"])
            ans["ai"] = scan
            st.session_state.answers[qid] = ans
            st.rerun()
        except engine.EngineError as e:
            st.error(str(e))


def _run_sim_scan(qid: int):
    ans = st.session_state.answers.get(qid)
    if not ans:
        return
    with st.spinner("다른 지원자와 겹칠 유사도 위험을 측정하는 중…"):
        try:
            scan = engine.similarity_scan(engine.get_client(api_key), model, ans["answer"])
            ans["sim"] = scan
            st.session_state.answers[qid] = ans
            st.rerun()
        except engine.EngineError as e:
            st.error(str(e))


def _run_humanize(qid: int):
    ans = st.session_state.answers.get(qid)
    if not ans:
        return
    flags = (ans.get("ai") or {}).get("flags", [])
    with st.spinner("AI 티를 지우고 사람의 문장으로 재작성 중… (10% 이하가 될 때까지 자동 반복, 최대 3회)"):
        try:
            client = engine.get_client(api_key)
            r = engine.humanize_answer(
                client, model, question=ans["question"], prev_answer=ans["answer"],
                limit=ans["limit"], count_mode=ans["count_mode"], flags=flags,
                target=10, max_rounds=3)
            ans.update(answer=r["answer"], chars=r["chars"],
                       notes=r["notes"] or ans.get("notes", ""))
            ans["ai"] = r["scan"]
            ans["sim"] = None  # 본문이 바뀌었으므로 유사도 재검사 필요
            st.session_state.answers[qid] = ans
            st.rerun()
        except engine.EngineError as e:
            st.error(str(e))


def _run_uniquify(qid: int):
    ans = st.session_state.answers.get(qid)
    if not ans:
        return
    flags = (ans.get("sim") or {}).get("flags", [])
    with st.spinner("겹치는 문장 틀을 이 지원자만의 표현으로 바꾸는 중… (재검사 포함)"):
        try:
            client = engine.get_client(api_key)
            r = engine.uniquify_answer(
                client, model, question=ans["question"], prev_answer=ans["answer"],
                limit=ans["limit"], count_mode=ans["count_mode"], flags=flags)
            ans.update(answer=r["answer"], chars=r["chars"],
                       notes=r["notes"] or ans.get("notes", ""))
            ans["sim"] = engine.similarity_scan(client, model, r["answer"])
            ans["ai"] = None  # 본문이 바뀌었으므로 AI 감지 재검사 필요
            st.session_state.answers[qid] = ans
            st.rerun()
        except engine.EngineError as e:
            st.error(str(e))


# ──────────────────────────────────────────────
# 사이드바
# ──────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div style="font-family:\'Noto Serif KR\',serif;font-size:1.25rem;font-weight:900;'
        'color:#F2EDE0;letter-spacing:.06em;margin-bottom:.1rem;">✒️ 자소서 스튜디오</div>'
        '<div style="font-size:.72rem;color:#C9A96A;letter-spacing:.3em;margin-bottom:1rem;">JASO STUDIO</div>',
        unsafe_allow_html=True)

    st.markdown("##### 연결 설정")

    # ── API 키 기억 (브라우저 쿠키, 30일) ──
    # 컴포넌트 값 보고로 인한 재실행(rerun)이 분석을 끊지 않도록,
    # 읽기는 st.context.cookies(요청 헤더), 쓰기는 순수 JS로 처리한다.
    def _saved_cookie_key() -> str:
        try:
            return st.context.cookies.get("jaso_api_key", "") or ""
        except Exception:
            return ""

    _saved_key = _saved_cookie_key()
    api_key = st.text_input("Anthropic API 키", type="password",
                            value=_secret("ANTHROPIC_API_KEY") or _saved_key,
                            help="키는 이 브라우저에만 저장됩니다")
    st.markdown('<div style="font-size:.78rem;margin:-.4rem 0 .6rem;">'
                '<a href="https://console.anthropic.com/settings/keys" target="_blank" '
                'style="color:#C9A96A;text-decoration:none;">→ Anthropic API 키 발급 바로가기</a></div>',
                unsafe_allow_html=True)
    remember = st.checkbox("이 브라우저에 키 기억하기 (30일)", value=True, key="remember_key")
    try:
        import streamlit.components.v1 as _cmp
        _k = api_key.strip()
        if remember and _k:
            # 저장: 쿠키(HTTPS면 Secure 포함) + localStorage 이중 저장.
            # 매 실행 재저장해 만료 연장·저장 실패를 자가 복구한다 (순수 JS라 rerun 유발 없음).
            _cmp.html(f"""<script>
try {{
  var v = {json.dumps(_k)};
  var sec = (parent.location.protocol === 'https:') ? '; Secure' : '';
  parent.document.cookie = 'jaso_api_key=' + encodeURIComponent(v)
    + '; max-age=2592000; path=/; SameSite=Lax' + sec;
  parent.localStorage.setItem('jaso_api_key', v);
}} catch (e) {{}}
</script>""", height=0)
        elif not remember:
            _cmp.html("""<script>
try {
  parent.document.cookie = 'jaso_api_key=; max-age=0; path=/';
  parent.document.cookie = 'jaso_api_key=; max-age=0; path=/; Secure';
  parent.localStorage.removeItem('jaso_api_key');
  parent.sessionStorage.removeItem('jaso_ck_restored');
} catch (e) {}
</script>""", height=0)
        if not _k and not _saved_key:
            # 복원: 서버가 키를 못 받았는데 브라우저에 저장본이 있으면
            # 쿠키를 다시 심고 한 번만 새로고침해 입력란을 자동으로 채운다.
            _cmp.html("""<script>
try {
  var d = parent.document, ls = parent.localStorage, ss = parent.sessionStorage;
  var v = ls.getItem('jaso_api_key');
  var hasCookie = d.cookie.indexOf('jaso_api_key=') !== -1;
  if ((v || hasCookie) && !ss.getItem('jaso_ck_restored')) {
    if (v && !hasCookie) {
      var sec = (parent.location.protocol === 'https:') ? '; Secure' : '';
      d.cookie = 'jaso_api_key=' + encodeURIComponent(v)
        + '; max-age=2592000; path=/; SameSite=Lax' + sec;
    }
    ss.setItem('jaso_ck_restored', '1');   // 새로고침 무한 반복 방지
    parent.location.reload();
  }
} catch (e) {}
</script>""", height=0)
    except Exception:
        pass
    model_label = st.selectbox("모델", list(engine.MODEL_CHOICES.keys()) + ["직접 입력"])
    if model_label == "직접 입력":
        model = st.text_input("모델 ID", value=engine.DEFAULT_MODEL)
    else:
        model = engine.MODEL_CHOICES[model_label]

    # DART 전자공시 키는 기본 내장 (secrets의 DART_API_KEY로 교체 가능)
    dart_key = _secret("DART_API_KEY") or engine.DEFAULT_DART_KEY
    st.caption("📊 DART 전자공시 연동: 기본 탑재")

    st.markdown("---")
    st.markdown("##### 작업 저장 / 불러오기")
    st.download_button("💾 진행 상황 저장 (.json)", _export_session(),
                       file_name=f"jaso_session_{datetime.date.today()}.json",
                       mime="application/json", use_container_width=True)
    up = st.file_uploader("저장 파일 불러오기", type=["json"], label_visibility="collapsed")
    if up is not None:
        sig = f"{up.name}-{up.size}"
        if st.session_state._loaded_sig != sig:
            try:
                _import_session(json.loads(up.getvalue().decode("utf-8")))
                st.session_state._loaded_sig = sig
                st.rerun()
            except Exception:
                st.error("파일을 읽지 못했습니다. 이 앱에서 저장한 .json 파일인지 확인해 주세요.")

    st.markdown("---")
    with st.expander("ℹ️ 사용 순서"):
        st.markdown(
            "1. **기업 분석** — 회사·직무 실시간 분석 (지원동기의 근거)\n"
            "2. **이력서·소재 발굴** — 이력서 파일만 올리면 소재 자동 발굴\n   (파일이 없으면 이력서 양식으로 직접 입력)\n"
            "3. **자소서 생성** — 문항마다 소재 불러와 생성,\n   AI 감지·유사도 검사 (소재 발굴도 이 안에서 가능)\n"
            "4. **완성본** — 검토 후 DOCX/TXT 다운로드")

# ──────────────────────────────────────────────
# 헤더 + 단계 내비게이션
# ──────────────────────────────────────────────
st.markdown(styles.hero_html(), unsafe_allow_html=True)

STEP_TITLES = {
    1: "①  기업 분석",
    2: "②  이력서·소재 발굴",
    3: "③  자소서 생성",
    4: "④  완성본",
}


def _goto(n: int):
    st.session_state.step = n


_nav = st.columns(len(STEP_TITLES))
for _i, (_n, _label) in enumerate(STEP_TITLES.items()):
    with _nav[_i]:
        st.button(_label, key=f"nav_{_n}", use_container_width=True,
                  type=("primary" if st.session_state.step == _n else "secondary"),
                  on_click=_goto, args=(_n,))

if st.session_state.step not in STEP_TITLES:   # 구버전 저장 파일(5단계) 호환
    st.session_state.step = 1
_step = st.session_state.step


def _require_key() -> bool:
    if not api_key.strip():
        st.warning("사이드바에 Anthropic API 키를 먼저 입력해 주세요.", icon="🔑")
        return False
    return True


# ══════════════════════════════════════════════
# ① 기업 분석
# ══════════════════════════════════════════════
if _step == 1:
    st.markdown(styles.overline("01", "기업 실시간 분석", "웹 검색 + DART 전자공시"), unsafe_allow_html=True)
    st.caption("지원할 회사의 최신 뉴스·실적·인재상을 실시간으로 조사해 지원동기의 '근거'를 만듭니다.")

    c1, c2 = st.columns(2)
    with c1:
        st.text_input("지원 기업명", key="in_company", placeholder="예: 한화갤러리아, Applied Materials Korea")
    with c2:
        st.text_input("지원 직무", key="in_role", placeholder="예: 영업관리, Customer Support Technician")
    st.text_area("채용공고 붙여넣기 (선택 — 자격요건·우대사항이 있으면 분석 정확도가 올라갑니다)",
                 key="in_posting", height=110)

    speed = st.radio("분석 모드", ["⚡ 빠른 분석 (권장 · 약 20~40초)", "🔬 정밀 분석 (검색 많음 · 1~2분)"],
                     horizontal=True, label_visibility="collapsed")
    run_research = st.button("🔍  실시간 기업 분석 시작", type="primary", use_container_width=True)

    if run_research:
        company = st.session_state.get("in_company", "").strip()
        if not company:
            st.warning("기업명을 입력해 주세요.")
        elif _require_key():
            # DART 공시는 조용히 시도 — 실패해도 아무 문구 없이 웹 검색만으로 진행
            dart_text = ""
            if dart_key.strip() and not st.session_state.get("dart_disabled"):
                try:
                    snap = engine.dart_snapshot(dart_key, company)
                    st.session_state.dart_snap = snap
                    dart_text = engine.dart_snapshot_to_text(snap)
                except Exception:
                    st.session_state.dart_snap = None
                    st.session_state.dart_disabled = True  # 이 세션에서는 재시도 안 함
            try:
                status = {}
                with st.container(border=True):
                    st.caption("실시간으로 조사하며 작성 중… (아래에 바로 표시됩니다)")
                    md = st.write_stream(_md_guard(engine.research_company_stream(
                        engine.get_client(api_key), model, company,
                        st.session_state.get("in_role", ""),
                        st.session_state.get("in_posting", ""), dart_text,
                        fast=speed.startswith("⚡"), status=status)))
                st.session_state.research_md = md or ""
                st.session_state.research_meta = (
                    f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} 기준"
                    + (" · ⚠ 웹 검색 미지원 키 — 일반 지식 기반" if status.get("fallback") else " · 웹 검색 사용"))
                _done = True
            except engine.EngineError as e:
                _done = False
                st.error(str(e))
            except Exception as e:  # 어떤 오류든 조용히 사라지지 않게
                _done = False
                st.error(f"예상치 못한 오류가 발생했습니다: {type(e).__name__} — {e}")
            if _done:
                st.rerun()

    snap = st.session_state.dart_snap
    if snap and snap.get("found"):
        st.markdown(styles.divider(), unsafe_allow_html=True)
        st.markdown(styles.overline("—", "DART 공시 스냅샷", snap.get("corp_name", "")), unsafe_allow_html=True)
        tiles = []
        for f in snap.get("fin", [])[:4]:
            tiles.append((f["항목"], f["당기"], f"전기 {f['전기']}"))
        if not tiles and snap.get("brief"):
            tiles = [(k, v, "") for k, v in list(snap["brief"].items())[:4] if v]
        if tiles:
            if snap.get("fin_year"):
                st.caption(f"{snap['fin_year']}년 사업보고서 (연결 기준)")
            st.markdown(styles.stat_tiles(tiles), unsafe_allow_html=True)
        if snap.get("disclosures"):
            with st.expander("최근 6개월 주요 공시"):
                for d in snap["disclosures"]:
                    st.markdown(f"- `{d['일자']}` {d['보고서']}")

    if st.session_state.research_md:
        st.markdown(styles.divider(), unsafe_allow_html=True)
        st.caption(st.session_state.research_meta)
        with st.container(border=True):
            st.markdown(st.session_state.research_md)
    else:
        st.markdown(styles.empty_state(
            "아직 분석 결과가 없습니다",
            "기업명과 직무를 입력하고 '실시간 기업 분석 시작'을 눌러 주세요. 분석 결과는 지원동기 작성에 자동으로 반영됩니다."),
            unsafe_allow_html=True)

    # ── 합격 자소서 패턴 분석 ──
    st.markdown(styles.divider(), unsafe_allow_html=True)
    st.markdown(styles.overline("—", "합격 자소서 패턴 분석", "이 기업·직무 합격자들은 어떻게 썼나"), unsafe_allow_html=True)
    st.caption("웹에 공개된 합격 자소서·후기를 실시간으로 찾아 공통 소재·구조·키워드를 추출합니다. 분석 결과는 자소서 생성에 자동 반영됩니다.")
    if st.button("🏆  합격 자소서 패턴 분석 시작", use_container_width=True):
        company = st.session_state.get("in_company", "").strip()
        if not company:
            st.warning("기업명을 먼저 입력해 주세요.")
        elif _require_key():
            try:
                status = {}
                with st.container(border=True):
                    st.caption("공개 합격 자소서를 검색·분석 중… (아래에 바로 표시됩니다)")
                    md = st.write_stream(_md_guard(engine.analyze_pass_essays_stream(
                        engine.get_client(api_key), model, company,
                        st.session_state.get("in_role", ""), status=status)))
                st.session_state.pass_md = md or ""
                st.session_state.pass_meta = (
                    f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} 기준"
                    + (" · ⚠ 웹 검색 미지원 키 — 일반 지식 기반" if status.get("fallback") else " · 웹 검색 사용"))
                _pdone = True
            except engine.EngineError as e:
                _pdone = False
                st.error(str(e))
            except Exception as e:
                _pdone = False
                st.error(f"예상치 못한 오류가 발생했습니다: {type(e).__name__} — {e}")
            if _pdone:
                st.rerun()
    if st.session_state.pass_md:
        st.caption(st.session_state.pass_meta + " · 합격자 문장은 베끼지 않고 패턴만 반영합니다")
        with st.container(border=True):
            st.markdown(st.session_state.pass_md)


# ══════════════════════════════════════════════
# ② 이력서·소재 발굴 (메인)
# ══════════════════════════════════════════════
if _step == 2:
    st.markdown(styles.overline("02", "이력서·소재 발굴", "이력서만 올리면, 자소서 소재가 나옵니다"), unsafe_allow_html=True)
    st.caption("이 프로그램의 핵심 기능입니다. 아래 두 방법 중 **하나만** 하면 됩니다. 경험 입력은 ③단계에서 문항마다 한 번만 합니다.")

    # ── 이력서 넣는 방법 선택 — 둘 중 하나만 ──
    _mode = st.radio("이력서를 어떻게 넣을까요? (둘 중 하나만 선택)",
                     ["📄 이력서 파일이 있어요 — 올리기만 하면 끝", "📝 파일이 없어요 — 양식에 직접 입력"],
                     key="in_resume_mode", horizontal=True)

    if _mode.startswith("📄"):
        with st.container(border=True):
            st.markdown("**이력서 파일 올리기** — 이력서·경력기술서·기존 자소서 파일을 올리면 내용을 추출하고, "
                        "바로 소재 발굴까지 자동으로 이어집니다. 아래 양식은 채울 필요 없습니다.")
            ups = st.file_uploader("파일 업로드 (PDF · DOCX · TXT · HWP · HWPX)",
                                   type=reader.SUPPORTED, accept_multiple_files=True,
                                   key="doc_uploader")
            _handle_uploads(ups)
            _uploaded_docs_list()
    else:
        with st.container(border=True):
            st.markdown("**이력서 양식으로 직접 입력** — 파일 업로드는 필요 없습니다. "
                        "아는 항목만 채워도 됩니다. 이 내용이 그대로 소재 발굴 재료가 됩니다.")
            cols = st.columns(3)
            for i, (k, label) in enumerate(SPEC_FIELDS.items()):
                with cols[i % 3]:
                    st.text_area(label, key=f"sp_{k}", height=88)
        if st.session_state.uploaded_docs:
            st.caption(f"ℹ️ 이미 올려둔 파일 {len(st.session_state.uploaded_docs)}개도 발굴에 함께 쓰입니다.")

    # ── 선택: 추가 경험·경력 메모 ──
    with st.expander("➕  이력서에 없는 경험·경력을 더 넣고 싶다면 (선택)"):
        st.text_area("자유롭게 적어 주세요 — 아르바이트, 동아리, 실패담, 사이드 프로젝트 등 이력서에 못 넣은 이야기일수록 좋은 소재가 됩니다.",
                     key="in_extra_exp", height=110,
                     placeholder="예: 편의점 야간 알바 2년 — 발주 데이터를 엑셀로 정리해 폐기율을 절반으로 줄임")

    # ── 도우미: 기억 자극 질문 ──
    with st.expander("🤔  뭘 써야 할지 막막하다면 — 기억 자극 질문 받기 (선택)"):
        st.caption("파일도 경험도 없다고 느껴질 때, 기억을 끌어내는 질문을 만들어 드립니다. "
                   "떠오른 경험은 위 '추가 경험 메모'나 ③단계 문항 아래 '경험 입력'에 적으세요.")
        if st.button("기억 자극 질문 만들기", use_container_width=True) and _require_key():
            with st.spinner("이 직무에 맞는 기억 자극 질문을 만드는 중…"):
                try:
                    st.session_state.helper_qs = engine.memory_questions(
                        engine.get_client(api_key), model,
                        st.session_state.get("in_company", ""),
                        st.session_state.get("in_role", ""), _spec_dict())
                except engine.EngineError as e:
                    st.error(str(e))
        for g in st.session_state.helper_qs:
            st.markdown(f"**{g.get('area', '')}**")
            for qa in g.get("questions", []):
                st.markdown(styles.note_box("Q. " + qa.get("q", ""),
                                            "예: " + qa.get("example", "")), unsafe_allow_html=True)

    _consume_auto_mine()

    mine_label = "🔄  소재 다시 발굴하기" if st.session_state.materials else "⛏️  AI 소재 발굴 시작"
    if st.button(mine_label, type="primary", use_container_width=True) and _require_key():
        _mine_now()

    if st.session_state.materials:
        st.markdown(styles.divider(), unsafe_allow_html=True)
        st.markdown(styles.overline("—", "발굴된 소재", f"{len(st.session_state.materials)}개 — ③단계에서 '소재 불러오기'로 바로 채울 수 있습니다"),
                    unsafe_allow_html=True)
        for m in st.session_state.materials:
            st.markdown(styles.material_card(m), unsafe_allow_html=True)
    else:
        st.markdown(styles.empty_state(
            "아직 발굴된 소재가 없습니다",
            "이력서 파일을 올리면 자동으로 발굴됩니다. 파일이 없다면 이력서 양식을 채우고 'AI 소재 발굴 시작'을 눌러 주세요. "
            "문항 유형별로 쓸 수 있는 경험 소재를 초안까지 만들어 드립니다."),
            unsafe_allow_html=True)


# ══════════════════════════════════════════════
# ③ 자소서 생성
# ══════════════════════════════════════════════
if _step == 3:
    st.markdown(styles.overline("03", "자소서 생성", "문항마다 경험을 넣고, 그 자리에서 생성"), unsafe_allow_html=True)
    st.caption("실제 공고의 문항을 붙여넣고 → 그 문항에 쓸 경험을 입력한 뒤 → 생성하세요. AI 감지 검사와 휴먼라이징까지 한 화면에서 끝납니다.")

    # ── 이 단계 안에서도 소재 발굴 가능 ──
    _mat_n = len(st.session_state.materials)
    _mine_label = (f"⛏  소재 발굴 — 현재 {_mat_n}개 발굴됨 (이력서 추가·재발굴 가능)"
                   if _mat_n else "⛏  소재 발굴 — 이력서를 올리면 여기서 바로 발굴됩니다")
    with st.expander(_mine_label, expanded=False):
        st.caption("②단계로 돌아갈 필요 없습니다. 여기서 이력서를 올리거나 발굴을 다시 돌리면, 아래 문항의 '소재 불러오기'에 바로 반영됩니다.")
        ups_q = st.file_uploader("이력서 파일 추가 (PDF · DOCX · TXT · HWP · HWPX)",
                                 type=reader.SUPPORTED, accept_multiple_files=True,
                                 key="doc_uploader_q")
        _handle_uploads(ups_q)
        _uploaded_docs_list(key_prefix="q_")
        _consume_auto_mine()
        if st.button("🔄  소재 다시 발굴하기" if _mat_n else "⛏️  AI 소재 발굴 시작",
                     key="mine_in_q", use_container_width=True) and _require_key():
            _mine_now()
        if st.session_state.materials:
            st.markdown("**발굴된 소재** — 각 문항의 '소재 불러오기'에서 선택하세요.")
            for m in st.session_state.materials:
                st.markdown(f"- **{m.get('title', '')}** — {m.get('summary', '')[:80]}")

    # ── 문항별 소재 자동 추천 (합격 패턴·기업 분석 근거) ──
    # 사용자가 소재를 고르지 않아도, 프로그램이 문항마다 최적 소재를 골라 미리 채워 둔다.
    _q_texts = [(q["id"], st.session_state.get(f"q_text_{q['id']}", "").strip())
                for q in st.session_state.questions]
    _q_texts = [(i, t) for i, t in _q_texts if t]
    if st.session_state.materials and _q_texts and api_key.strip():
        import hashlib as _hl
        _sig = _hl.md5(("|".join(t for _, t in _q_texts) + "§"
                        + "|".join(m.get("title", "") for m in st.session_state.materials)
                        ).encode()).hexdigest()
        if st.session_state.mat_rec_sig != _sig:
            with st.spinner("합격 패턴·기업 분석을 근거로 문항별 추천 소재를 고르는 중…"):
                try:
                    st.session_state.mat_recs = engine.recommend_materials(
                        engine.get_client(api_key), model,
                        [{"id": i, "text": t} for i, t in _q_texts],
                        st.session_state.materials,
                        st.session_state.research_md, st.session_state.pass_md,
                        st.session_state.get("in_role", ""))
                except engine.EngineError:
                    pass  # 추천 실패는 조용히 넘어감 — 직접 선택 경로는 그대로 동작
            st.session_state.mat_rec_sig = _sig
        # 추천을 자동 적용 — 단, 사용자가 이미 경험을 쓰거나 소재를 고른 문항은 건드리지 않는다
        for _qid, _rec in st.session_state.mat_recs.items():
            _title = _rec.get("title", "")
            if not _title or st.session_state.mat_rec_applied.get(_qid) == _title:
                continue
            _cur = st.session_state.get(f"q_mat_{_qid}", "직접 입력")
            if _exp_filled_count(_qid) == 0 and _cur in ("직접 입력", None, ""):
                st.session_state[f"q_mat_{_qid}"] = _title
                _fill_exp_from_material(_qid)
                st.session_state.mat_rec_applied[_qid] = _title

    st.markdown("**문항 빠른 추가**")
    pc = st.columns(6)
    presets = [
        ("지원동기", "당사에 지원한 동기를 기술해 주십시오.", 700),
        ("성장과정", "본인의 성장과정을 기술해 주십시오.", 800),
        ("성격 장단점", "본인 성격의 장단점을 기술해 주십시오.", 700),
        ("직무 역량", "지원 직무에 본인이 적합하다고 생각하는 이유를 기술해 주십시오.", 1000),
        ("입사 후 포부", "입사 후 포부와 커리어 계획을 기술해 주십시오.", 800),
        ("경력직 자율형", "자유 양식 (경력 중심 자기소개서)", 1500),
    ]
    for i, (name, text, limit) in enumerate(presets):
        with pc[i]:
            if st.button(name, key=f"preset_{i}", use_container_width=True):
                _new_question(text, limit, is_freeform=(name == "경력직 자율형"))
                st.rerun()
    if st.button("＋ 빈 문항 직접 추가", use_container_width=True):
        _new_question()
        st.rerun()

    if not st.session_state.questions:
        st.markdown(styles.empty_state(
            "문항을 추가해 주세요",
            "위 버튼으로 자주 나오는 문항을 넣거나, '빈 문항 직접 추가'로 실제 공고 문항을 붙여넣으세요."),
            unsafe_allow_html=True)

    for idx, q in enumerate(list(st.session_state.questions), 1):
        qid = q["id"]
        with st.container(border=True):
            top = st.columns([8, 1])
            with top[0]:
                st.markdown(f"**문항 {idx}**" + ("  ·  자율 양식" if q.get("is_freeform") else ""))
            with top[1]:
                if st.button("🗑", key=f"del_{qid}", help="이 문항 삭제"):
                    st.session_state.questions = [x for x in st.session_state.questions if x["id"] != qid]
                    st.session_state.answers.pop(qid, None)
                    st.rerun()

            st.text_area("문항 (공고 원문 그대로)", key=f"q_text_{qid}", height=72,
                         placeholder="예: 예상치 못한 문제를 해결한 경험을 구체적으로 기술해 주십시오. (1,000자)")

            # ── 이 문항 전용 경험 입력 (유일한 경험 입력 창구) ──
            filled = _exp_filled_count(qid)
            _rec = st.session_state.mat_recs.get(qid) or {}
            _rec_on = bool(_rec) and st.session_state.mat_rec_applied.get(qid) == _rec.get("title") \
                and st.session_state.get(f"q_mat_{qid}") == _rec.get("title")
            if _rec_on:
                exp_label = f"✨  AI 추천 소재 적용됨 — {_rec['title']} (다른 경험 선택은 자유)"
            elif filled:
                exp_label = f"🧩  이 문항에 쓸 경험 입력 — {filled}/{len(EXP_FIELDS)} 채움"
            else:
                exp_label = "🧩  이 문항에 쓸 경험 입력 (②에서 발굴한 소재로 자동 채울 수 있어요)"
            with st.expander(exp_label, expanded=(filled == 0 and idx == 1)):
                if st.session_state.materials:
                    if _rec:
                        st.markdown(styles.note_box(
                            "✨ AI 추천 — " + _rec.get("title", ""),
                            (_rec.get("reason", "") or "합격 패턴·기업 분석 기준으로 이 문항에 가장 적합한 소재입니다.")
                            + " (다른 경험을 쓰고 싶다면 아래에서 자유롭게 바꾸세요.)"), unsafe_allow_html=True)
                    _opts = ["직접 입력"] + [m.get("title", "") for m in st.session_state.materials]
                    if st.session_state.get(f"q_mat_{qid}") not in _opts:
                        st.session_state[f"q_mat_{qid}"] = "직접 입력"  # 재발굴로 소재가 바뀐 경우 안전 처리
                    st.selectbox(
                        "⛏ 소재 선택 — 바꾸면 아래 5칸이 그 소재의 초안으로 채워집니다 (선택 사항)",
                        _opts, key=f"q_mat_{qid}", on_change=_fill_exp_from_material, args=(qid,))
                else:
                    st.caption("위의 '⛏ 소재 발굴'에서 이력서를 올려 소재를 발굴하면, 여기서 한 번에 불러올 수 있습니다.")
                for f, label, ph in EXP_FIELDS:
                    st.text_area(label, key=f"q_exp_{qid}_{f}", height=72, placeholder=ph)

            oc = st.columns([3, 1.4, 2.6])
            with oc[0]:
                st.slider("분량 (자)", 300, 5000, key=f"q_limit_{qid}", step=50)
            with oc[1]:
                st.radio("글자수 기준", ["공백 포함", "공백 제외"], key=f"q_mode_{qid}", horizontal=False)
            with oc[2]:
                st.text_input("작성 방향 지정 (선택)", key=f"q_hint_{qid}",
                              placeholder="예: 소제목에 숫자를 꼭 넣어줘")

            st.checkbox("이 문항에 기업 분석 자료 반영 (지원동기·포부는 꼭 켜 두세요)",
                        key=f"q_research_{qid}")

            gen = st.button(f"✒️  문항 {idx} 답변 생성", key=f"gen_{qid}",
                            type="primary", use_container_width=True)
            if gen and _require_key():
                qdata = _collect_question(qid)
                if not qdata["text"]:
                    st.warning("문항 내용을 입력해 주세요.")
                else:
                    _generate_one(qdata, idx)

            # ── 결과 ──
            ans = st.session_state.answers.get(qid)
            if ans:
                subtitle, body = engine.split_subtitle(ans["answer"])
                ai = ans.get("ai")
                sim = ans.get("sim")
                st.markdown(styles.answer_card(
                    ans["question"], subtitle, body, ans["chars"],
                    ans["limit"], ans["count_mode"],
                    extra_meta=("실시간 웹 검색 반영" if ans.get("used_search") else ""),
                    ai_percent=(ai or {}).get("percent"),
                    sim_percent=(sim or {}).get("percent")),
                    unsafe_allow_html=True)
                if ans.get("notes"):
                    st.markdown(styles.note_box("✍ 더 좋아지려면", ans["notes"]), unsafe_allow_html=True)

                # 검사·보정 도구
                bc = st.columns(2)
                with bc[0]:
                    if st.button("🕵️  AI 감지 검사", key=f"scan_{qid}", use_container_width=True) and _require_key():
                        _run_ai_scan(qid)
                with bc[1]:
                    if st.button("📑  유사도 검사 (다른 지원자와 겹침)", key=f"simscan_{qid}", use_container_width=True) and _require_key():
                        _run_sim_scan(qid)
                bc2 = st.columns(2)
                with bc2[0]:
                    if st.button("🧬  AI 티 제거 (휴먼라이징)", key=f"hum_{qid}", use_container_width=True) and _require_key():
                        _run_humanize(qid)
                with bc2[1]:
                    if st.button("♻️  유사도 낮추기 (표현 고유화)", key=f"uniq_{qid}", use_container_width=True) and _require_key():
                        _run_uniquify(qid)

                if ai or sim:
                    gc = st.columns(2)
                    with gc[0]:
                        if ai:
                            st.markdown("**AI 감지 위험**")
                            st.markdown(styles.ai_gauge(ai.get("percent"), ai.get("verdict", ""),
                                                        ai.get("comment", ""),
                                                        heuristic=ai.get("heuristic"), llm=ai.get("llm")),
                                        unsafe_allow_html=True)
                            if ai.get("flags"):
                                st.markdown(styles.flag_chips(ai["flags"]), unsafe_allow_html=True)
                    with gc[1]:
                        if sim:
                            st.markdown("**유사도 위험 (다른 지원자와 겹침)**")
                            st.markdown(styles.ai_gauge(sim.get("percent"), sim.get("verdict", ""),
                                                        sim.get("comment", ""),
                                                        heuristic=sim.get("heuristic"), llm=sim.get("llm")),
                                        unsafe_allow_html=True)
                            if sim.get("flags"):
                                st.markdown(styles.flag_chips(sim["flags"]), unsafe_allow_html=True)
                    details = []
                    for fl in (ai or {}).get("flags", []):
                        details.append(f"- **[AI 감지] {fl.get('pattern', '')}** — \"{fl.get('example', '')}\" → {fl.get('fix', '')}")
                    for fl in (sim or {}).get("flags", []):
                        details.append(f"- **[유사도] {fl.get('phrase', '')}** — {fl.get('why', '')} → {fl.get('fix', '')}")
                    if details:
                        with st.expander("감지된 패턴 자세히"):
                            st.markdown("\n".join(details))
                    st.caption("※ 자체 문체 통계와 AI 판독을 결합한 추정치입니다. 실제 감지기(GPTZero·카피킬러 등)의 결과와 다를 수 있습니다. 'AI 티 제거'는 10% 이하가 될 때까지 자동 반복합니다.")

                rc = st.columns([3, 1.2])
                with rc[0]:
                    st.text_input("수정 지시 (예: 결과 수치를 더 강조하고, 소제목을 더 도발적으로)",
                                  key=f"ref_{qid}")
                with rc[1]:
                    st.write("")
                    if st.button("지시대로 다듬기", key=f"refbtn_{qid}", use_container_width=True):
                        instr = st.session_state.get(f"ref_{qid}", "").strip()
                        if not instr:
                            st.warning("수정 지시를 입력해 주세요.")
                        elif _require_key():
                            with st.spinner("답변을 다듬는 중…"):
                                try:
                                    r = engine.refine_answer(
                                        engine.get_client(api_key), model,
                                        question=ans["question"], prev_answer=ans["answer"],
                                        instruction=instr, limit=ans["limit"],
                                        count_mode=ans["count_mode"])
                                    ans.update(answer=r["answer"], chars=r["chars"],
                                               notes=r["notes"] or ans.get("notes", ""),
                                               ai=None, sim=None)
                                    st.session_state.answers[qid] = ans
                                    st.rerun()
                                except engine.EngineError as e:
                                    st.error(str(e))
                with st.expander("📋 복사용 텍스트"):
                    st.code(ans["answer"], language=None)

    if st.session_state.questions:
        st.markdown(styles.divider(), unsafe_allow_html=True)
        if st.button("⚡  모든 문항 한 번에 생성", use_container_width=True) and _require_key():
            qlist = [_collect_question(q["id"]) for q in st.session_state.questions]
            qlist = [q for q in qlist if q["text"]]
            if not qlist:
                st.warning("내용이 입력된 문항이 없습니다.")
            else:
                prog = st.progress(0.0, text="작성 준비 중…")
                for i, qdata in enumerate(qlist, 1):
                    prog.progress((i - 1) / len(qlist),
                                  text=f"문항 {i}/{len(qlist)} 작성 중 — 두괄식·소제목·분량 보정 포함")
                    _generate_one(qdata, i, quiet=True)
                prog.progress(1.0, text="완료")
                st.rerun()


# ══════════════════════════════════════════════
# ④ 완성본·다운로드
# ══════════════════════════════════════════════
if _step == 4:
    st.markdown(styles.overline("04", "완성본 검토와 다운로드"), unsafe_allow_html=True)

    ordered = [(q["id"], st.session_state.answers.get(q["id"]))
               for q in st.session_state.questions]
    done = [(qid, a) for qid, a in ordered if a]

    if not done:
        st.markdown(styles.empty_state(
            "완성된 답변이 아직 없습니다",
            "③단계에서 문항별 답변을 생성하면 이곳에서 전체를 검토하고 파일로 내려받을 수 있습니다."),
            unsafe_allow_html=True)
    else:
        total_incl = sum(a["chars"]["incl"] for _, a in done)
        total_excl = sum(a["chars"]["excl"] for _, a in done)
        scanned = [a for _, a in done if a.get("ai")]
        avg_ai = round(sum(a["ai"]["percent"] for a in scanned) / len(scanned)) if scanned else None
        sim_scanned = [a for _, a in done if a.get("sim")]
        avg_sim = round(sum(a["sim"]["percent"] for a in sim_scanned) / len(sim_scanned)) if sim_scanned else None
        tiles = [
            ("완성 문항", f"{len(done)}개", f"전체 {len(st.session_state.questions)}개 중"),
            ("총 분량 · 공백 포함", f"{total_incl:,}자", ""),
            ("총 분량 · 공백 제외", f"{total_excl:,}자", ""),
        ]
        if avg_ai is not None:
            tiles.append(("평균 AI 감지 위험", f"{avg_ai}%", "추정치"))
        if avg_sim is not None:
            tiles.append(("평균 유사도 위험", f"{avg_sim}%", "추정치"))
        st.markdown(styles.stat_tiles(tiles), unsafe_allow_html=True)

        items = []
        for qid, a in done:
            subtitle, body = engine.split_subtitle(a["answer"])
            items.append({
                "question": a["question"], "subtitle": subtitle, "body": body,
                "chars_incl": a["chars"]["incl"], "chars_excl": a["chars"]["excl"],
                "limit": a["limit"], "count_mode": a["count_mode"],
            })
            st.markdown(styles.answer_card(a["question"], subtitle, body, a["chars"],
                                           a["limit"], a["count_mode"],
                                           ai_percent=(a.get("ai") or {}).get("percent"),
                                           sim_percent=(a.get("sim") or {}).get("percent")),
                        unsafe_allow_html=True)

        company = st.session_state.get("in_company", "")
        role = st.session_state.get("in_role", "")
        fname = f"자기소개서_{company or '지원기업'}_{datetime.date.today()}".replace(" ", "")

        d1, d2 = st.columns(2)
        with d1:
            st.download_button("⬇️  DOCX로 다운로드", exporter.build_docx(company, role, items),
                               file_name=f"{fname}.docx",
                               mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                               type="primary", use_container_width=True)
        with d2:
            st.download_button("⬇️  TXT로 다운로드", exporter.build_txt(company, role, items),
                               file_name=f"{fname}.txt", mime="text/plain",
                               use_container_width=True)

    # ── 합격 이력서·경력기술서 양식 ──
    st.markdown(styles.divider(), unsafe_allow_html=True)
    st.markdown(styles.overline("—", "합격 이력서·경력기술서 양식",
                                "워드(.docx) 파일 — 한글(HWP)에서도 그대로 열립니다"),
                unsafe_allow_html=True)
    st.caption("회색 예시 문구를 본인 내용으로 바꿔 쓰면 됩니다. 모든 성과는 숫자로 끝내는 것이 원칙입니다.")
    _tcols = st.columns(len(templates.TEMPLATES))
    _DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    for _i, (_key, (_title, _desc, _)) in enumerate(templates.TEMPLATES.items()):
        with _tcols[_i]:
            st.markdown(f"**{_title}**")
            st.caption(_desc)
            st.download_button("⬇️  다운로드", _cached_template(_key),
                               file_name=f"{_title.replace(' ', '')}.docx",
                               mime=_DOCX_MIME, key=f"tpl_{_key}",
                               use_container_width=True)

# ──────────────────────────────────────────────
# 하단 이전/다음 내비게이션
# ──────────────────────────────────────────────
st.markdown(styles.divider(), unsafe_allow_html=True)
_bn = st.columns(2)
with _bn[0]:
    if _step > 1:
        st.button(f"←  이전 · {STEP_TITLES[_step - 1]}", key="nav_prev",
                  use_container_width=True, on_click=_goto, args=(_step - 1,))
with _bn[1]:
    if _step < 4:
        st.button(f"다음 · {STEP_TITLES[_step + 1]}  →", key="nav_next",
                  type="primary", use_container_width=True,
                  on_click=_goto, args=(_step + 1,))

st.markdown(
    '<div style="text-align:center;color:#7C869C;font-size:.75rem;margin-top:3rem;'
    'letter-spacing:.14em;">JASO STUDIO — 합격을 설계하는 자기소개서</div>',
    unsafe_allow_html=True)
