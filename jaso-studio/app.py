# -*- coding: utf-8 -*-
"""
자소서 스튜디오 (JASO STUDIO) v2
읽는 순간 뽑고 싶어지는 자기소개서 — 실시간 기업 분석 · 적합도 진단 · 소재 발굴 · AI 감지 방어
"""
import base64
import json
import datetime
import pathlib

import streamlit as st

from core import engine, styles, exporter, reader

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

# ──────────────────────────────────────────────
# 세션 상태 초기화
# ──────────────────────────────────────────────
_DEFAULTS = {
    "step": 1,                # 현재 단계 (1~5)
    "questions": [],          # [{id, is_freeform}]
    "q_seq": 0,
    "answers": {},            # id -> {question, answer, notes, chars, limit, count_mode, used_search, ai, sim}
    "materials": [],          # AI 발굴 소재
    "helper_qs": [],          # 기억 자극 질문 (소재 발굴 도우미)
    "uploaded_docs": [],      # [{name, text, chars, warn}]
    "doc_sigs": [],
    "research_md": "",
    "research_meta": "",
    "dart_snap": None,
    "fit": None,
    "_loaded_sig": "",
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

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
        },
        "spec": {k: st.session_state.get(f"sp_{k}", "") for k in SPEC_FIELDS},
        "questions": [_collect_question(q["id"]) for q in st.session_state.questions],
        "answers": st.session_state.answers,
        "materials": st.session_state.materials,
        "uploaded_docs": st.session_state.uploaded_docs,
        "research_md": st.session_state.research_md,
        "fit": st.session_state.fit,
    }
    return json.dumps(data, ensure_ascii=False, indent=1)


def _import_session(data: dict):
    basic = data.get("basic", {})
    st.session_state["in_company"] = basic.get("company", "")
    st.session_state["in_role"] = basic.get("role", "")
    st.session_state["in_posting"] = basic.get("posting", "")
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
    st.session_state.fit = data.get("fit", None)


@st.cache_data(show_spinner=False, ttl=86400)
def load_dart_corps(key: str):
    return engine.dart_load_corp_map(key)


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
                materials_text=mat_text)
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
    """④에서 발굴된 소재 선택 시 경험 5칸을 초안으로 자동 채움."""
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
    with st.spinner("AI 티를 지우고 사람의 문장으로 다시 쓰는 중… (재검사 포함)"):
        try:
            client = engine.get_client(api_key)
            r = engine.humanize_answer(
                client, model, question=ans["question"], prev_answer=ans["answer"],
                limit=ans["limit"], count_mode=ans["count_mode"], flags=flags)
            ans.update(answer=r["answer"], chars=r["chars"],
                       notes=r["notes"] or ans.get("notes", ""))
            ans["ai"] = engine.ai_scan(client, model, r["answer"])
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
    api_key = st.text_input("Anthropic API 키", type="password",
                            value=_secret("ANTHROPIC_API_KEY"),
                            help="키는 저장되지 않습니다")
    st.markdown('<div style="font-size:.78rem;margin:-.4rem 0 .6rem;">'
                '<a href="https://console.anthropic.com/settings/keys" target="_blank" '
                'style="color:#C9A96A;text-decoration:none;">→ Anthropic API 키 발급 바로가기</a></div>',
                unsafe_allow_html=True)
    model_label = st.selectbox("모델", list(engine.MODEL_CHOICES.keys()) + ["직접 입력"])
    if model_label == "직접 입력":
        model = st.text_input("모델 ID", value=engine.DEFAULT_MODEL)
    else:
        model = engine.MODEL_CHOICES[model_label]

    # DART 전자공시 키는 기본 내장 (secrets의 DART_API_KEY로 교체 가능)
    dart_key = _secret("DART_API_KEY") or engine.DEFAULT_DART_KEY
    st.caption("📊 DART 전자공시 연동: 기본 탑재 (상장사 재무·공시 자동 분석)")

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
            "1. **기업 분석** — 회사·직무 입력 후 실시간 분석\n"
            "2. **적합도 진단** — 스펙 입력, 합격 가능성 판별\n"
            "3. **소재 발굴** — 이력서 파일만 올리면 AI가 소재 발굴\n"
            "4. **자소서 생성** — 문항마다 소재 불러오기/경험 입력 후 생성,\n   AI 감지·유사도 검사\n"
            "5. **완성본** — 검토 후 DOCX/TXT 다운로드")

# ──────────────────────────────────────────────
# 헤더 + 단계 내비게이션
# ──────────────────────────────────────────────
st.markdown(styles.hero_html(), unsafe_allow_html=True)

STEP_TITLES = {
    1: "①  기업 분석",
    2: "②  적합도 진단",
    3: "③  소재 발굴",
    4: "④  자소서 생성",
    5: "⑤  완성본",
}


def _goto(n: int):
    st.session_state.step = n


_nav = st.columns(5)
for _i, (_n, _label) in enumerate(STEP_TITLES.items()):
    with _nav[_i]:
        st.button(_label, key=f"nav_{_n}", use_container_width=True,
                  type=("primary" if st.session_state.step == _n else "secondary"),
                  on_click=_goto, args=(_n,))

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

    run_research = st.button("🔍  실시간 기업 분석 시작", type="primary", use_container_width=True)

    if run_research:
        company = st.session_state.get("in_company", "").strip()
        if not company:
            st.warning("기업명을 입력해 주세요.")
        elif _require_key():
            dart_text = ""
            if dart_key.strip():
                with st.spinner("DART 전자공시에서 기업 정보를 가져오는 중…"):
                    try:
                        corps = load_dart_corps(dart_key)
                        snap = engine.dart_snapshot(dart_key, corps, company)
                        st.session_state.dart_snap = snap
                        dart_text = engine.dart_snapshot_to_text(snap)
                    except engine.EngineError as e:
                        st.warning(str(e))
            with st.spinner("웹에서 최신 뉴스·전략·인재상을 조사하는 중… (약 30초~1분)"):
                try:
                    result = engine.research_company(
                        engine.get_client(api_key), model, company,
                        st.session_state.get("in_role", ""),
                        st.session_state.get("in_posting", ""), dart_text)
                    st.session_state.research_md = result["markdown"]
                    st.session_state.research_meta = (
                        f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} 기준"
                        + (" · 웹 검색 사용" if result["used_search"] else " · ⚠ 웹 검색 미지원 키 — 일반 지식 기반"))
                except engine.EngineError as e:
                    st.error(str(e))

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
    elif snap and not snap.get("found"):
        st.info(snap.get("reason", ""))

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


# ══════════════════════════════════════════════
# ② 직무 적합도 진단
# ══════════════════════════════════════════════
if _step == 2:
    st.markdown(styles.overline("02", "직무 적합도 진단", "서류 심사관의 눈으로"), unsafe_allow_html=True)
    st.caption("스펙을 입력하면 지원 직무 기준으로 합격 가능성을 판별하고, 자소서에 쓸 소재까지 추천합니다.")

    cols = st.columns(3)
    keys = list(SPEC_FIELDS.items())
    for i, (k, label) in enumerate(keys):
        with cols[i % 3]:
            st.text_area(label, key=f"sp_{k}", height=88)

    use_fit_search = st.toggle("웹 검색으로 이 직무의 채용 요건까지 확인해서 평가 (기업 분석을 안 했을 때 권장)",
                               value=False)
    run_fit = st.button("⚖️  적합도 진단 실행", type="primary", use_container_width=True)

    if run_fit and _require_key():
        spec = {SPEC_FIELDS[k]: st.session_state.get(f"sp_{k}", "") for k in SPEC_FIELDS}
        if not any(str(v).strip() for v in spec.values()):
            st.warning("스펙을 한 항목 이상 입력해 주세요.")
        else:
            with st.spinner("서류 심사 기준으로 진단 중…"):
                try:
                    st.session_state.fit = engine.analyze_fit(
                        engine.get_client(api_key), model,
                        st.session_state.get("in_company", ""),
                        st.session_state.get("in_role", ""),
                        spec, st.session_state.research_md,
                        st.session_state.get("in_posting", ""),
                        use_search=use_fit_search)
                except engine.EngineError as e:
                    st.error(str(e))

    fit = st.session_state.fit
    if fit:
        st.markdown(styles.divider(), unsafe_allow_html=True)
        st.markdown(styles.hero_score(fit.get("overall", "?"), fit.get("verdict", ""),
                                      fit.get("one_line", "")), unsafe_allow_html=True)

        hard = str(fit.get("hard_check", "")).strip()
        if hard and "특이사항 없음" not in hard:
            st.error(f"**지원 자격 체크** — {hard}", icon="🚨")

        m1, m2 = st.columns([1.1, 1])
        with m1:
            st.markdown("**역량 축별 평가**")
            for name, score in (fit.get("scores") or {}).items():
                st.markdown(styles.meter(name, score), unsafe_allow_html=True)
        with m2:
            st.markdown("**강점 — 자소서에서 밀 것**")
            for s in fit.get("strengths", []):
                st.markdown(f"- **{s.get('title', '')}** — {s.get('why', '')}")
            st.markdown("**보완점 — 방어 전략**")
            for g in fit.get("gaps", []):
                st.markdown(f"- **{g.get('title', '')}** → {g.get('fix', '')}")

        if fit.get("materials"):
            st.markdown(styles.divider(), unsafe_allow_html=True)
            st.markdown("**이 스펙으로 쓸 수 있는 자소서 소재**")
            for mtr in fit["materials"]:
                st.markdown(styles.note_box(mtr.get("question_type", "소재"),
                                            mtr.get("story", "")), unsafe_allow_html=True)
    else:
        st.markdown(styles.empty_state(
            "아직 진단 결과가 없습니다",
            "스펙을 입력하고 '적합도 진단 실행'을 눌러 주세요. 진단 결과의 강점·보완점은 자소서 생성에 자동 반영됩니다."),
            unsafe_allow_html=True)


# ══════════════════════════════════════════════
# ③ 소재 발굴
# ══════════════════════════════════════════════
if _step == 3:
    st.markdown(styles.overline("03", "소재 발굴", "파일만 올리면 AI가 캐냅니다"), unsafe_allow_html=True)
    st.caption("여기서는 타이핑할 필요 없습니다. 파일을 올리고 발굴 버튼만 누르세요. 경험 입력은 ④단계에서 문항마다 한 번만 합니다.")

    with st.container(border=True):
        st.markdown("**STEP 1 · 재료 파일 올리기** — 이력서·경력기술서·기존 자소서 파일을 올리면 내용을 자동으로 추출해 소재 발굴과 작성에 씁니다.")
        ups = st.file_uploader("파일 업로드 (PDF · DOCX · TXT · HWP · HWPX)",
                               type=reader.SUPPORTED, accept_multiple_files=True,
                               key="doc_uploader")
        if ups:
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
                st.rerun()
        for i, d in enumerate(st.session_state.uploaded_docs):
            dc = st.columns([7, 1])
            with dc[0]:
                warn_txt = f"  ·  ⚠ {d['warn']}" if d.get("warn") else ""
                st.markdown(f"📄 **{d['name']}** — {d['chars']:,}자 추출됨{warn_txt}")
            with dc[1]:
                if st.button("삭제", key=f"deldoc_{i}", use_container_width=True):
                    st.session_state.uploaded_docs.pop(i)
                    st.rerun()
        if st.session_state.uploaded_docs:
            with st.expander("추출된 내용 미리보기"):
                for d in st.session_state.uploaded_docs:
                    st.markdown(f"**{d['name']}**")
                    st.text(d["text"][:1200] + ("…" if len(d["text"]) > 1200 else ""))

    with st.container(border=True):
        st.markdown("**STEP 2 · 뭘 써야 할지 막막하다면** — 파일도 경험도 없다고 느껴질 때, "
                    "기억을 끌어내는 질문을 만들어 드립니다. 질문을 읽다 떠오른 경험은 ④단계 문항 아래 '경험 입력'에 적으세요.")
        if st.button("🤔  기억 자극 질문 만들기", use_container_width=True) and _require_key():
            with st.spinner("이 직무에 맞는 기억 자극 질문을 만드는 중…"):
                try:
                    spec = {SPEC_FIELDS[k]: st.session_state.get(f"sp_{k}", "") for k in SPEC_FIELDS}
                    st.session_state.helper_qs = engine.memory_questions(
                        engine.get_client(api_key), model,
                        st.session_state.get("in_company", ""),
                        st.session_state.get("in_role", ""), spec)
                except engine.EngineError as e:
                    st.error(str(e))
        for g in st.session_state.helper_qs:
            st.markdown(f"**{g.get('area', '')}**")
            for qa in g.get("questions", []):
                st.markdown(styles.note_box("Q. " + qa.get("q", ""),
                                            "예: " + qa.get("example", "")), unsafe_allow_html=True)

    mine = st.button("⛏️  AI 소재 발굴 시작", type="primary", use_container_width=True)
    if mine and _require_key():
        spec = {SPEC_FIELDS[k]: st.session_state.get(f"sp_{k}", "") for k in SPEC_FIELDS}
        has_spec = any(str(v).strip() for v in spec.values())
        if not st.session_state.uploaded_docs and not has_spec:
            st.warning("파일을 올리거나 ②단계에서 스펙을 입력해 주세요. 그게 발굴 재료가 됩니다.")
        else:
            with st.spinner("업로드 파일과 스펙에서 자소서 소재를 캐내는 중…"):
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

    if st.session_state.materials:
        st.markdown(styles.divider(), unsafe_allow_html=True)
        st.markdown(styles.overline("—", "발굴된 소재", f"{len(st.session_state.materials)}개 — ④단계에서 '소재 불러오기'로 바로 채울 수 있습니다"),
                    unsafe_allow_html=True)
        for m in st.session_state.materials:
            st.markdown(styles.material_card(m), unsafe_allow_html=True)
    else:
        st.markdown(styles.empty_state(
            "아직 발굴된 소재가 없습니다",
            "파일을 올리고 'AI 소재 발굴 시작'을 누르면, 문항 유형별로 쓸 수 있는 경험 소재를 초안까지 만들어 드립니다."),
            unsafe_allow_html=True)


# ══════════════════════════════════════════════
# ④ 자소서 생성
# ══════════════════════════════════════════════
if _step == 4:
    st.markdown(styles.overline("04", "자소서 생성", "문항마다 경험을 넣고, 그 자리에서 생성"), unsafe_allow_html=True)
    st.caption("실제 공고의 문항을 붙여넣고 → 그 문항에 쓸 경험을 입력한 뒤 → 생성하세요. AI 감지 검사와 휴먼라이징까지 한 화면에서 끝납니다.")

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
            exp_label = f"🧩  이 문항에 쓸 경험 입력 — {filled}/{len(EXP_FIELDS)} 채움" if filled else "🧩  이 문항에 쓸 경험 입력 (③에서 발굴한 소재로 자동 채울 수 있어요)"
            with st.expander(exp_label, expanded=(filled == 0 and idx == 1)):
                if st.session_state.materials:
                    st.selectbox(
                        "⛏ 발굴된 소재 불러오기 — 선택하면 아래 5칸이 초안으로 채워집니다",
                        ["직접 입력"] + [m.get("title", "") for m in st.session_state.materials],
                        key=f"q_mat_{qid}", on_change=_fill_exp_from_material, args=(qid,))
                else:
                    st.caption("③단계에서 파일을 올려 소재를 발굴하면, 여기서 한 번에 불러올 수 있습니다.")
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
                    st.caption("※ 자체 문체 통계와 AI 판독을 결합한 추정치입니다. 실제 감지기(GPTZero·카피킬러 등)의 결과와 다를 수 있습니다. 30% 이하를 목표로 보정하세요.")

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
# ⑤ 완성본·다운로드
# ══════════════════════════════════════════════
if _step == 5:
    st.markdown(styles.overline("05", "완성본 검토와 다운로드"), unsafe_allow_html=True)

    ordered = [(q["id"], st.session_state.answers.get(q["id"]))
               for q in st.session_state.questions]
    done = [(qid, a) for qid, a in ordered if a]

    if not done:
        st.markdown(styles.empty_state(
            "완성된 답변이 아직 없습니다",
            "④ 탭에서 문항별 답변을 생성하면 이곳에서 전체를 검토하고 파일로 내려받을 수 있습니다."),
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
    if _step < 5:
        st.button(f"다음 · {STEP_TITLES[_step + 1]}  →", key="nav_next",
                  type="primary", use_container_width=True,
                  on_click=_goto, args=(_step + 1,))

st.markdown(
    '<div style="text-align:center;color:#7C869C;font-size:.75rem;margin-top:3rem;'
    'letter-spacing:.14em;">JASO STUDIO — 합격을 설계하는 자기소개서</div>',
    unsafe_allow_html=True)
