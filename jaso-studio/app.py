# -*- coding: utf-8 -*-
"""
자소서 스튜디오 (JASO STUDIO)
읽는 순간 뽑고 싶어지는 자기소개서 — 실시간 기업 분석 · 직무 적합도 진단 · 합격 문체 자동 작성
"""
import json
import datetime

import streamlit as st

from core import engine, styles, exporter

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

# ──────────────────────────────────────────────
# 세션 상태 초기화
# ──────────────────────────────────────────────
_DEFAULTS = {
    "questions": [],          # [{id, is_freeform}]
    "q_seq": 0,
    "answers": {},            # id -> {question, answer, subtitle, notes, chars, limit, count_mode}
    "research_md": "",
    "research_meta": "",
    "dart_snap": None,
    "fit": None,
    "_loaded_sig": "",
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

IV_KEYS = [
    "exp1_situation", "exp1_problem", "exp1_cause", "exp1_action", "exp1_result", "exp1_apply",
    "exp2_free",
    "me_strength", "me_weakness", "me_value", "me_reputation",
    "co_reason", "co_goal", "co_spec",
    "extra_free",
]


def _secret(name: str) -> str:
    try:
        return st.secrets.get(name, "") or ""
    except Exception:
        return ""


def _interview_dict() -> dict:
    return {k: st.session_state.get(f"iv_{k}", "") for k in IV_KEYS}


def _new_question(text: str = "", limit: int = 700, is_freeform: bool = False):
    st.session_state.q_seq += 1
    qid = st.session_state.q_seq
    st.session_state.questions.append({"id": qid, "is_freeform": is_freeform})
    st.session_state[f"q_text_{qid}"] = text
    st.session_state[f"q_limit_{qid}"] = limit
    st.session_state[f"q_mode_{qid}"] = "공백 포함"
    st.session_state[f"q_hint_{qid}"] = ""
    st.session_state[f"q_research_{qid}"] = True
    return qid


def _collect_question(qid: int) -> dict:
    return {
        "id": qid,
        "text": st.session_state.get(f"q_text_{qid}", "").strip(),
        "limit": int(st.session_state.get(f"q_limit_{qid}", 700)),
        "count_mode": "incl" if st.session_state.get(f"q_mode_{qid}", "공백 포함") == "공백 포함" else "excl",
        "hint": st.session_state.get(f"q_hint_{qid}", ""),
        "use_research": bool(st.session_state.get(f"q_research_{qid}", True)),
        "is_freeform": next((q.get("is_freeform", False) for q in st.session_state.questions if q["id"] == qid), False),
    }


def _export_session() -> str:
    data = {
        "meta": {"app": "jaso-studio", "saved": datetime.datetime.now().isoformat(timespec="seconds")},
        "basic": {
            "company": st.session_state.get("in_company", ""),
            "role": st.session_state.get("in_role", ""),
            "posting": st.session_state.get("in_posting", ""),
        },
        "interview": _interview_dict(),
        "spec": {k: st.session_state.get(f"sp_{k}", "") for k in SPEC_FIELDS},
        "questions": [_collect_question(q["id"]) for q in st.session_state.questions],
        "answers": st.session_state.answers,
        "research_md": st.session_state.research_md,
        "fit": st.session_state.fit,
    }
    return json.dumps(data, ensure_ascii=False, indent=1)


def _import_session(data: dict):
    basic = data.get("basic", {})
    st.session_state["in_company"] = basic.get("company", "")
    st.session_state["in_role"] = basic.get("role", "")
    st.session_state["in_posting"] = basic.get("posting", "")
    for k, v in data.get("interview", {}).items():
        st.session_state[f"iv_{k}"] = v
    for k, v in data.get("spec", {}).items():
        st.session_state[f"sp_{k}"] = v
    st.session_state.questions = []
    st.session_state.q_seq = 0
    for q in data.get("questions", []):
        qid = _new_question(q.get("text", ""), q.get("limit", 700), q.get("is_freeform", False))
        st.session_state[f"q_mode_{qid}"] = "공백 포함" if q.get("count_mode", "incl") == "incl" else "공백 제외"
        st.session_state[f"q_hint_{qid}"] = q.get("hint", "")
        st.session_state[f"q_research_{qid}"] = q.get("use_research", True)
    st.session_state.answers = {int(k): v for k, v in data.get("answers", {}).items()}
    st.session_state.research_md = data.get("research_md", "")
    st.session_state.fit = data.get("fit", None)


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


@st.cache_data(show_spinner=False, ttl=86400)
def load_dart_corps(key: str):
    return engine.dart_load_corp_map(key)


def _generate_one(qdata: dict, idx: int, quiet: bool = False):
    company = st.session_state.get("in_company", "")
    role = st.session_state.get("in_role", "")
    research = st.session_state.research_md if qdata["use_research"] else ""
    fit_sum = engine.fit_summary_text(st.session_state.fit) if st.session_state.fit else ""
    live = qdata["use_research"] and not st.session_state.research_md and engine.is_company_question(qdata["text"])

    def _run():
        try:
            result = engine.generate_answer(
                engine.get_client(api_key), model,
                company=company, role=role, question=qdata["text"],
                limit=qdata["limit"], count_mode=qdata["count_mode"],
                interview=_interview_dict(), hint=qdata["hint"],
                research_md=research, fit_summary=fit_sum,
                live_search=live, is_freeform=qdata["is_freeform"])
            st.session_state.answers[qdata["id"]] = {
                "question": qdata["text"], "answer": result["answer"],
                "notes": result["notes"], "chars": result["chars"],
                "limit": qdata["limit"], "count_mode": qdata["count_mode"],
                "used_search": result["used_search"],
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


# ──────────────────────────────────────────────
# 사이드바
# ──────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div style="font-family:\'Noto Serif KR\',serif;font-size:1.25rem;font-weight:900;'
        'color:#F5F1E4;letter-spacing:.06em;margin-bottom:.1rem;">✒️ 자소서 스튜디오</div>'
        '<div style="font-size:.72rem;color:#B08D57;letter-spacing:.3em;margin-bottom:1rem;">JASO STUDIO</div>',
        unsafe_allow_html=True)

    st.markdown("##### 연결 설정")
    api_key = st.text_input("Anthropic API 키", type="password",
                            value=_secret("ANTHROPIC_API_KEY"),
                            help="console.anthropic.com에서 발급 · 키는 저장되지 않습니다")
    model_label = st.selectbox("모델", list(engine.MODEL_CHOICES.keys()) + ["직접 입력"])
    if model_label == "직접 입력":
        model = st.text_input("모델 ID", value=engine.DEFAULT_MODEL)
    else:
        model = engine.MODEL_CHOICES[model_label]

    dart_key = st.text_input("DART 전자공시 API 키 (선택)", type="password",
                             value=_secret("DART_API_KEY"),
                             help="opendart.fss.or.kr에서 무료 발급 · 재무제표를 함께 분석합니다")

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
            "3. **재료 인터뷰** — 질문에 답하며 경험 정리\n"
            "4. **자소서 생성** — 문항 입력, 분량 선택, 생성\n"
            "5. **완성본** — 검토 후 DOCX/TXT 다운로드")

# ──────────────────────────────────────────────
# 헤더
# ──────────────────────────────────────────────
st.markdown(styles.hero_html(), unsafe_allow_html=True)
st.markdown(styles.steps_html(), unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["①  기업 분석", "②  직무 적합도 진단", "③  재료 인터뷰", "④  자소서 생성", "⑤  완성본·다운로드"])


def _require_key() -> bool:
    if not api_key.strip():
        st.warning("사이드바에 Anthropic API 키를 먼저 입력해 주세요.", icon="🔑")
        return False
    return True


# ══════════════════════════════════════════════
# ① 기업 분석
# ══════════════════════════════════════════════
with tab1:
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
            snap = None
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
with tab2:
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
# ③ 재료 인터뷰
# ══════════════════════════════════════════════
with tab3:
    st.markdown(styles.overline("03", "답변 재료 인터뷰", "질문에 답하면 자소서에 반영됩니다"), unsafe_allow_html=True)
    answered = sum(1 for k in IV_KEYS if str(st.session_state.get(f"iv_{k}", "")).strip())
    st.caption(f"완벽한 문장이 아니어도 됩니다. 메모하듯 사실만 적어 주세요. — 현재 {answered}/{len(IV_KEYS)}개 답변됨")

    with st.container(border=True):
        st.markdown("**STEP 1 · 대표 경험 하나를 깊게** — 자소서의 승부는 경험 하나를 얼마나 깊게 쓰느냐로 갈립니다.")
        st.text_area("1-1. 언제, 어디서, 무슨 역할이었나요?",
                     key="iv_exp1_situation", height=76,
                     placeholder="예: JW메리어트 호텔 멤버십 세일즈 담당, 2021~2023")
        st.text_area("1-2. 무엇이 잘못되고 있었나요? 그대로 두면 어떻게 됐나요?",
                     key="iv_exp1_problem", height=76,
                     placeholder="예: 멤버십 가입률이 매년 급감. 홍보를 늘려도 판매가 안 됨")
        st.text_area("1-3. 파고들어 보니 진짜 원인은 무엇이었나요? 어떻게 알아냈나요?",
                     key="iv_exp1_cause", height=76,
                     placeholder="예: 기존 상품을 분석해 보니 선택지가 하나뿐이고 혜택이 약했음")
        st.text_area("1-4. 해결을 위해 '내가' 한 행동을 순서대로 2~4개 적어 주세요.",
                     key="iv_exp1_action", height=96,
                     placeholder="예: ① 고객 데이터로 이용 유형 3개 분류 ② 유형별 맞춤 멤버십 기획 ③ 총지배인 앞 PT")
        st.text_area("1-5. 결과는? 가능하면 숫자로. (%, 금액, 건수, 수상, 채택 등)",
                     key="iv_exp1_result", height=76,
                     placeholder="예: 월 매출 3,500만 원 → 8,000만 원. 최우수 직원 선정")
        st.text_area("1-6. 이 경험을 입사 후 어떻게 써먹을 수 있나요?",
                     key="iv_exp1_apply", height=76,
                     placeholder="예: 신규 멤버십을 주기적으로 제안해 영업 매출 극대화")

    with st.container(border=True):
        st.markdown("**STEP 2 · 보조 경험 (선택)** — 문항이 여러 개라면 두 번째 경험이 필요합니다.")
        st.text_area("2-1. 다른 경험 하나를 자유롭게. (상황→문제→해결→결과 순서로 메모)",
                     key="iv_exp2_free", height=120)

    with st.container(border=True):
        st.markdown("**STEP 3 · 나라는 사람**")
        c1, c2 = st.columns(2)
        with c1:
            st.text_area("3-1. 강점 + 그렇게 말할 근거", key="iv_me_strength", height=88)
            st.text_area("3-2. 약점 + 극복하려는 노력", key="iv_me_weakness", height=88)
        with c2:
            st.text_area("3-3. 가치관·일하는 원칙 (생긴 계기)", key="iv_me_value", height=88)
            st.text_area("3-4. 동료·상사가 나를 뭐라고 평가하나요?", key="iv_me_reputation", height=88)

    with st.container(border=True):
        st.markdown("**STEP 4 · 회사와 나**")
        st.text_area("4-1. 이 회사에 끌린 '개인적' 계기가 있나요?", key="iv_co_reason", height=76)
        c1, c2 = st.columns(2)
        with c1:
            st.text_area("4-2. 입사 후 목표 (1년 / 10년)", key="iv_co_goal", height=88)
        with c2:
            st.text_area("4-3. 지원 직무 관련 핵심 스펙 요약", key="iv_co_spec", height=88,
                         placeholder="②탭에 입력했다면 비워 두어도 됩니다")

    with st.container(border=True):
        st.markdown("**STEP 5 · 추가 재료 (선택)** — 이력서, 경력기술서, 예전 자소서를 통째로 붙여넣어도 됩니다.")
        st.text_area("추가 재료", key="iv_extra_free", height=140, label_visibility="collapsed")


# ══════════════════════════════════════════════
# ④ 자소서 생성
# ══════════════════════════════════════════════
with tab4:
    st.markdown(styles.overline("04", "자소서 생성", "두괄식 · 소제목 · 스토리텔링 자동 적용"), unsafe_allow_html=True)
    st.caption("실제 공고의 문항을 그대로 붙여넣고, 글자수 제한을 설정하세요. 문항별로 따로 생성할 수 있습니다.")

    # 문항 프리셋
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

    # 문항 목록
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

            oc = st.columns([3, 1.4, 2.6])
            with oc[0]:
                st.slider("분량 (자)", 300, 5000, key=f"q_limit_{qid}", step=50)
            with oc[1]:
                st.radio("글자수 기준", ["공백 포함", "공백 제외"], key=f"q_mode_{qid}", horizontal=False)
            with oc[2]:
                st.text_input("이 문항에 쓸 소재·방향 (선택)", key=f"q_hint_{qid}",
                              placeholder="예: 대표 경험① 대신 보조 경험②를 써줘")

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

            # 결과 표시
            ans = st.session_state.answers.get(qid)
            if ans:
                subtitle, body = engine.split_subtitle(ans["answer"])
                st.markdown(styles.answer_card(
                    ans["question"], subtitle, body, ans["chars"],
                    ans["limit"], ans["count_mode"],
                    extra_meta=("실시간 웹 검색 반영" if ans.get("used_search") else "")),
                    unsafe_allow_html=True)
                if ans.get("notes"):
                    st.markdown(styles.note_box("✍ 더 좋아지려면", ans["notes"]), unsafe_allow_html=True)

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
                                               notes=r["notes"] or ans.get("notes", ""))
                                    st.session_state.answers[qid] = ans
                                    st.rerun()
                                except engine.EngineError as e:
                                    st.error(str(e))
                with st.expander("📋 복사용 텍스트"):
                    st.code(ans["answer"], language=None)

    # 전체 생성
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
with tab5:
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
        st.markdown(styles.stat_tiles([
            ("완성 문항", f"{len(done)}개", f"전체 {len(st.session_state.questions)}개 중"),
            ("총 분량 · 공백 포함", f"{total_incl:,}자", ""),
            ("총 분량 · 공백 제외", f"{total_excl:,}자", ""),
        ]), unsafe_allow_html=True)

        items = []
        for qid, a in done:
            subtitle, body = engine.split_subtitle(a["answer"])
            items.append({
                "question": a["question"], "subtitle": subtitle, "body": body,
                "chars_incl": a["chars"]["incl"], "chars_excl": a["chars"]["excl"],
                "limit": a["limit"], "count_mode": a["count_mode"],
            })
            st.markdown(styles.answer_card(a["question"], subtitle, body, a["chars"],
                                           a["limit"], a["count_mode"]),
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

st.markdown(
    '<div style="text-align:center;color:#A39B85;font-size:.75rem;margin-top:3rem;'
    'letter-spacing:.14em;">JASO STUDIO — 합격을 설계하는 자기소개서</div>',
    unsafe_allow_html=True)
