# -*- coding: utf-8 -*-
"""
자소서 스튜디오 — 프리미엄 디자인 v2
비디오 배경 + 다크 글래스 (Apple 무드) · 딥네이비 × 아이보리 × 샴페인 골드
"""
import html as _html

# ── 브랜드 토큰 ──────────────────────────
BG = "#0A1120"                       # 최종 폴백 배경
GLASS = "rgba(14,22,40,.55)"         # 카드
GLASS_HARD = "rgba(12,20,37,.74)"    # 입력 필드
BORDER = "rgba(242,236,222,.14)"
INK = "#F2EDE0"                      # 본문 아이보리
MUTED = "#A7AFC2"
FAINT = "#7C869C"
GOLD = "#C9A96A"
GOLD_DIM = "rgba(201,169,106,.16)"
NAVY_TXT = "#101A2E"                 # 밝은 버튼 위 글자
GOOD = "#4CAF7D"
WARN = "#D9A441"
BAD = "#E07B5F"

GLOBAL_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;600;700;900&family=Noto+Sans+KR:wght@200;300;400;500;700&display=swap');

/* ── 배경 비디오 ─────────────────────── */
.js-bgvid {{
    position: fixed; inset: 0;
    width: 100vw; height: 100vh;
    object-fit: cover;
    z-index: -2;
    filter: saturate(112%) brightness(.9);
}}
.js-bgoverlay {{
    position: fixed; inset: 0; z-index: -1;
    background:
      radial-gradient(1100px 500px at 78% -10%, rgba(201,169,106,.10), transparent 60%),
      linear-gradient(180deg, rgba(7,12,24,.46) 0%, rgba(9,15,29,.74) 38vh,
                      rgba(10,17,32,.92) 78vh, {BG} 115vh);
}}

/* ── 기본 ───────────────────────────── */
html, body {{ background: {BG}; }}
.stApp {{
    background: transparent !important;
    color: {INK};
    font-family: 'Noto Sans KR', -apple-system, sans-serif;
}}
.block-container {{
    max-width: 1120px;
    padding-top: 1.8rem;
    padding-bottom: 6rem;
}}
h1, h2, h3 {{
    font-family: 'Noto Serif KR', serif !important;
    color: {INK} !important;
    letter-spacing: -0.01em;
}}
.stMarkdown p, .stMarkdown li, .stMarkdown td {{ color: #E7E2D4; }}
.stMarkdown strong {{ color: {INK}; }}
.stMarkdown a {{ color: {GOLD}; }}
[data-testid="stHeader"] {{ background: transparent; }}
#MainMenu, footer, [data-testid="stToolbar"] {{ visibility: hidden; }}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p,
.stCaption, small {{ color: {MUTED} !important; }}
[data-testid="stWidgetLabel"] p {{ color: #C9CFDC !important; font-size: .85rem; }}

/* ── 사이드바 ───────────────────────── */
[data-testid="stSidebar"] {{
    background: rgba(7,12,23,.82);
    backdrop-filter: blur(22px) saturate(130%);
    -webkit-backdrop-filter: blur(22px) saturate(130%);
    border-right: 1px solid {BORDER};
}}
[data-testid="stSidebar"] * {{ color: #E4E0D2; }}
[data-testid="stSidebar"] label, [data-testid="stSidebar"] p,
[data-testid="stSidebar"] span {{ color: #B9C0D0 !important; font-size: .85rem; }}
[data-testid="stSidebar"] hr {{ border-color: {BORDER}; }}
[data-testid="stSidebar"] .stButton > button,
[data-testid="stSidebar"] .stDownloadButton > button {{
    width: 100%;
    background: {GOLD_DIM} !important;
    color: {INK} !important;
    border: 1px solid rgba(201,169,106,.5) !important;
}}
[data-testid="stSidebar"] .stButton > button:hover,
[data-testid="stSidebar"] .stDownloadButton > button:hover {{
    background: rgba(201,169,106,.3) !important;
    color: #FFFFFF !important;
}}

/* ── 입력 위젯 (글래스 필드) ─────────── */
.stTextInput input, .stTextArea textarea, .stNumberInput input {{
    background: {GLASS_HARD} !important;
    color: {INK} !important;
    -webkit-text-fill-color: {INK} !important;
    caret-color: {GOLD} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 12px !important;
}}
.stTextInput input::placeholder, .stTextArea textarea::placeholder {{
    color: rgba(226,221,206,.34) !important;
    -webkit-text-fill-color: rgba(226,221,206,.34) !important;
}}
.stTextInput input:focus, .stTextArea textarea:focus {{
    border-color: rgba(201,169,106,.65) !important;
    box-shadow: 0 0 0 3px rgba(201,169,106,.16) !important;
}}
/* 텍스트 인풋 래퍼(베이스웹) 배경 제거 */
.stTextInput > div, .stTextArea > div,
.stTextInput div[data-baseweb="input"], .stTextInput div[data-baseweb="base-input"] {{
    background: transparent !important;
    border: none !important;
}}
/* selectbox — react-aria(신) + baseweb(구) */
.stSelectbox [role="group"], .stSelectbox .react-aria-ComboBox > div,
div[data-baseweb="select"] > div {{
    background: {GLASS_HARD} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 12px !important;
}}
.stSelectbox input, .stSelectbox [role="group"] *,
div[data-baseweb="select"] span, div[data-baseweb="select"] input {{
    color: {INK} !important;
    -webkit-text-fill-color: {INK} !important;
}}
.stSelectbox svg, div[data-baseweb="select"] svg {{ fill: {GOLD} !important; color: {GOLD} !important; }}

.stSlider [data-baseweb="slider"] div[role="slider"] {{
    background: {GOLD} !important;
    border: 2px solid #0B1322 !important;
    box-shadow: 0 0 0 4px rgba(201,169,106,.25) !important;
}}
.stCheckbox p, .stRadio p, [data-testid="stToggle"] p {{ color: #D6DBE6 !important; }}

/* ── 버튼 (애플식 필) ────────────────── */
.stButton > button, .stDownloadButton > button {{
    border-radius: 999px;
    border: 1px solid {BORDER};
    background: rgba(242,237,224,.07);
    color: {INK};
    font-weight: 600;
    letter-spacing: .02em;
    padding: .55rem 1.3rem;
    backdrop-filter: blur(8px);
    transition: all .2s cubic-bezier(.2,.7,.3,1);
}}
.stButton > button:hover, .stDownloadButton > button:hover {{
    border-color: rgba(201,169,106,.7);
    color: #FFFFFF;
    box-shadow: 0 4px 18px rgba(201,169,106,.22);
    transform: translateY(-1px);
}}
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {{
    background: linear-gradient(135deg, #F5F0E1 0%, #E9E1CC 100%);
    color: {NAVY_TXT};
    border: 1px solid rgba(255,255,255,.5);
    font-weight: 700;
}}
.stButton > button[kind="primary"]:hover, .stDownloadButton > button[kind="primary"]:hover {{
    box-shadow: 0 6px 26px rgba(233,225,204,.3);
    color: #000;
}}

/* ── 탭 (세그먼트 무드) ──────────────── */
.stTabs [data-baseweb="tab-list"] {{
    gap: .25rem;
    background: rgba(12,20,37,.5);
    border: 1px solid {BORDER};
    border-radius: 999px;
    padding: .3rem .35rem;
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
}}
.stTabs [data-baseweb="tab"] {{
    font-weight: 600;
    font-size: .92rem;
    color: {MUTED};
    padding: .5rem 1.05rem;
    border-radius: 999px;
    background: transparent;
}}
.stTabs [aria-selected="true"] {{
    color: {INK} !important;
    background: rgba(242,237,224,.12);
}}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {{
    background-color: transparent;
}}

/* ── 컨테이너·익스팬더 (글래스 카드) ──── */
div[data-testid="stVerticalBlockBorderWrapper"] {{
    background: {GLASS};
    border: 1px solid {BORDER} !important;
    border-radius: 18px;
    backdrop-filter: blur(18px) saturate(135%);
    -webkit-backdrop-filter: blur(18px) saturate(135%);
    box-shadow: 0 10px 34px rgba(3,7,16,.35);
}}
[data-testid="stExpander"] details, details[data-testid="stExpander"],
[data-testid="stExpander"] {{
    background: {GLASS} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 14px !important;
    backdrop-filter: blur(14px);
}}
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary span,
[data-testid="stExpander"] summary p {{ color: {INK} !important; font-weight: 600; }}

/* ── 알림·업로더 ─────────────────────── */
[data-testid="stAlert"] {{
    background: {GLASS_HARD} !important;
    border: 1px solid {BORDER};
    border-radius: 14px;
    backdrop-filter: blur(12px);
}}
[data-testid="stAlert"] p {{ color: {INK} !important; }}
[data-testid="stFileUploaderDropzone"] {{
    background: {GLASS_HARD} !important;
    border: 1px dashed {BORDER} !important;
    border-radius: 12px !important;
}}
[data-testid="stFileUploaderDropzone"] * {{ color: {MUTED} !important; }}
[data-testid="stFileUploaderDropzone"] button {{
    background: {GOLD_DIM} !important;
    color: {INK} !important;
    border: 1px solid rgba(201,169,106,.5) !important;
    border-radius: 999px !important;
}}
.stCode, pre {{ border-radius: 12px !important; }}

/* ── 커스텀 컴포넌트 ────────────────── */
.js-hero {{
    padding: 3.4rem 0 2.2rem;
    margin-bottom: .6rem;
}}
.js-hero .brand {{
    font-size: .74rem; font-weight: 700;
    letter-spacing: .5em; color: {GOLD};
    margin-bottom: 1.05rem;
}}
.js-hero h1 {{
    font-family: 'Noto Serif KR', serif;
    font-size: 2.85rem; font-weight: 900;
    color: {INK} !important;
    margin: 0 0 .7rem 0; line-height: 1.24;
    text-shadow: 0 2px 30px rgba(3,7,16,.55);
}}
.js-hero .tagline {{
    color: #C6CCDA; font-size: 1.02rem; font-weight: 300;
    letter-spacing: .03em;
    text-shadow: 0 1px 14px rgba(3,7,16,.6);
}}
.js-hero .rule {{
    width: 64px; height: 2px;
    background: linear-gradient(90deg, {GOLD}, transparent);
    margin-top: 1.3rem;
}}

.js-step {{ display: flex; gap: .5rem; flex-wrap: wrap; margin-bottom: 1.2rem; }}
.js-step .s {{
    font-size: .78rem; font-weight: 500; color: {MUTED};
    background: {GLASS}; border: 1px solid {BORDER};
    padding: .34rem .9rem; border-radius: 999px;
    backdrop-filter: blur(10px);
}}
.js-step .s b {{ color: {GOLD}; font-family: 'Noto Serif KR', serif; margin-right: .35rem; }}

.js-overline {{ display: flex; align-items: baseline; gap: .7rem; margin: 1.5rem 0 .35rem; }}
.js-overline .no {{
    font-family: 'Noto Serif KR', serif;
    font-size: .8rem; font-weight: 700; color: {GOLD}; letter-spacing: .2em;
}}
.js-overline .t {{
    font-family: 'Noto Serif KR', serif;
    font-size: 1.34rem; font-weight: 700; color: {INK};
}}
.js-overline .sub {{ font-size: .84rem; color: {MUTED}; }}

.js-divider {{
    height: 1px; border: 0;
    background: linear-gradient(90deg, {BORDER}, transparent);
    margin: 1.2rem 0;
}}

.js-stat-row {{ display: flex; gap: .8rem; flex-wrap: wrap; margin: .4rem 0 .9rem; }}
.js-stat {{
    flex: 1 1 150px;
    background: {GLASS}; border: 1px solid {BORDER};
    border-radius: 16px; padding: 1rem 1.15rem .9rem;
    backdrop-filter: blur(16px);
}}
.js-stat .l {{
    font-size: .7rem; font-weight: 700; color: {FAINT};
    letter-spacing: .14em; margin-bottom: .35rem; text-transform: uppercase;
}}
.js-stat .v {{
    font-family: 'Noto Serif KR', serif;
    font-size: 1.3rem; font-weight: 700; color: {INK}; line-height: 1.2;
}}
.js-stat .s {{ font-size: .76rem; color: {MUTED}; margin-top: .25rem; }}

.js-hero-score {{
    display: flex; align-items: center; gap: 1.7rem;
    background: {GLASS}; border: 1px solid {BORDER};
    border-radius: 18px; padding: 1.5rem 1.8rem; margin: .5rem 0 1rem;
    backdrop-filter: blur(18px);
}}
.js-hero-score .num {{
    font-family: 'Noto Serif KR', serif;
    font-size: 3.6rem; font-weight: 900; color: {INK}; line-height: 1;
}}
.js-hero-score .unit {{ font-size: 1.1rem; color: {FAINT}; font-weight: 400; }}
.js-hero-score .desc {{ font-size: .95rem; color: #DDD8C8; line-height: 1.6; }}

.js-badge {{
    display: inline-flex; align-items: center; gap: .4rem;
    font-size: .84rem; font-weight: 700;
    padding: .32rem .9rem; border-radius: 999px;
    border: 1px solid; letter-spacing: .02em;
    backdrop-filter: blur(8px);
}}
.js-badge.good {{ color: {GOOD}; border-color: rgba(76,175,125,.55); background: rgba(76,175,125,.1); }}
.js-badge.warn {{ color: {WARN}; border-color: rgba(217,164,65,.55); background: rgba(217,164,65,.1); }}
.js-badge.bad  {{ color: {BAD};  border-color: rgba(224,123,95,.55); background: rgba(224,123,95,.1); }}

.js-meter {{ margin: .55rem 0 .7rem; }}
.js-meter .head {{ display: flex; justify-content: space-between; align-items: baseline; margin-bottom: .32rem; }}
.js-meter .name {{ font-size: .87rem; font-weight: 500; color: #DCD7C8; }}
.js-meter .val {{
    font-family: 'Noto Serif KR', serif;
    font-size: .94rem; font-weight: 700; color: {GOLD};
}}
.js-meter .track {{
    height: 8px; background: rgba(242,236,222,.12);
    border-radius: 999px; overflow: hidden;
}}
.js-meter .fill {{
    height: 100%; border-radius: 999px;
    background: linear-gradient(90deg, #8F7440, {GOLD});
}}

.js-answer {{
    background: {GLASS};
    border: 1px solid {BORDER};
    border-left: 3px solid {GOLD};
    border-radius: 18px;
    padding: 1.6rem 1.8rem;
    margin: .6rem 0 .9rem;
    backdrop-filter: blur(18px) saturate(135%);
    box-shadow: 0 12px 36px rgba(3,7,16,.4);
}}
.js-answer .q {{
    font-size: .8rem; color: {MUTED}; margin-bottom: .85rem;
    padding-bottom: .75rem; border-bottom: 1px dashed {BORDER};
}}
.js-answer .sub {{
    font-family: 'Noto Serif KR', serif;
    font-size: 1.18rem; font-weight: 700; color: {INK};
    margin-bottom: .8rem;
}}
.js-answer .sub::before {{ content: "["; color: {GOLD}; margin-right: 2px; }}
.js-answer .sub::after  {{ content: "]"; color: {GOLD}; margin-left: 2px; }}
.js-answer .body {{ font-size: .96rem; line-height: 1.92; color: #EDE8DA; }}
.js-answer .meta {{
    margin-top: 1.05rem; padding-top: .75rem;
    border-top: 1px dashed {BORDER};
    font-size: .78rem; color: {MUTED};
    display: flex; gap: 1.1rem; flex-wrap: wrap;
}}
.js-answer .meta b {{ color: {GOLD}; }}

.js-note {{
    background: {GOLD_DIM};
    border: 1px solid rgba(201,169,106,.4);
    border-radius: 14px;
    padding: .9rem 1.15rem;
    font-size: .86rem; color: #EDE8DA; line-height: 1.7;
    margin-bottom: .8rem;
    backdrop-filter: blur(10px);
}}
.js-note .t {{ font-weight: 700; color: {GOLD}; margin-bottom: .25rem; }}

/* AI 감지 게이지 */
.js-ai {{
    display: flex; align-items: center; gap: 1.5rem;
    background: {GLASS}; border: 1px solid {BORDER};
    border-radius: 18px; padding: 1.25rem 1.6rem; margin: .5rem 0 .7rem;
    backdrop-filter: blur(16px);
}}
.js-ai .num {{
    font-family: 'Noto Serif KR', serif;
    font-size: 2.7rem; font-weight: 900; line-height: 1;
}}
.js-ai .num.good {{ color: {GOOD}; }}
.js-ai .num.warn {{ color: {WARN}; }}
.js-ai .num.bad  {{ color: {BAD}; }}
.js-ai .unit {{ font-size: 1rem; color: {FAINT}; }}
.js-ai .desc {{ font-size: .88rem; color: #DDD8C8; line-height: 1.6; }}
.js-chiprow {{ display: flex; gap: .45rem; flex-wrap: wrap; margin: .5rem 0 .8rem; }}
.js-chip {{
    font-size: .78rem; color: #E3DECE;
    background: rgba(224,123,95,.12);
    border: 1px solid rgba(224,123,95,.4);
    padding: .26rem .75rem; border-radius: 999px;
}}

.js-empty {{
    text-align: center; padding: 2.6rem 1rem;
    color: {MUTED}; font-size: .9rem; line-height: 1.8;
    background: {GLASS}; border: 1px dashed {BORDER}; border-radius: 18px;
    backdrop-filter: blur(14px);
}}
.js-empty .big {{
    font-family: 'Noto Serif KR', serif;
    font-size: 1.08rem; font-weight: 700; color: {INK};
}}
</style>
"""


def esc(text: str) -> str:
    return _html.escape(str(text or ""))


def nl2br(text: str) -> str:
    return esc(text).replace("\n\n", "<br><br>").replace("\n", "<br>")


def video_background(video_url: str = "app/static/bg.mp4",
                     poster_url: str = "app/static/bg_poster.jpg") -> str:
    return (f'<video class="js-bgvid" autoplay muted loop playsinline preload="auto" '
            f'poster="{poster_url}"><source src="{video_url}" type="video/mp4"></video>'
            f'<div class="js-bgoverlay"></div>')


def hero_html() -> str:
    return """
<div class="js-hero">
  <div class="brand">JASO STUDIO</div>
  <h1>읽는 순간, 뽑고 싶어지는<br>자기소개서를 만듭니다</h1>
  <div class="tagline">실시간 기업 분석 · 직무 적합도 진단 · AI 감지 방어 — 첨삭 전문가의 기준 그대로</div>
  <div class="rule"></div>
</div>"""


def steps_html() -> str:
    return """
<div class="js-step">
  <span class="s"><b>01</b> 기업 분석</span>
  <span class="s"><b>02</b> 적합도 진단</span>
  <span class="s"><b>03</b> 소재 발굴</span>
  <span class="s"><b>04</b> 자소서 생성</span>
  <span class="s"><b>05</b> 완성본 다운로드</span>
</div>"""


def overline(no: str, title: str, sub: str = "") -> str:
    sub_html = f'<span class="sub">{esc(sub)}</span>' if sub else ""
    return f'<div class="js-overline"><span class="no">{esc(no)}</span><span class="t">{esc(title)}</span>{sub_html}</div>'


def divider() -> str:
    return '<hr class="js-divider">'


def stat_tiles(items: list) -> str:
    tiles = "".join(
        f'<div class="js-stat"><div class="l">{esc(l)}</div>'
        f'<div class="v">{esc(v)}</div>'
        + (f'<div class="s">{esc(s)}</div>' if s else "")
        + "</div>"
        for l, v, s in items)
    return f'<div class="js-stat-row">{tiles}</div>'


def verdict_badge(verdict: str) -> str:
    v = (verdict or "").strip()
    if v.startswith("적합") or v == "안전":
        cls, icon = "good", "&#10003;"
    elif "조건부" in v or v == "주의":
        cls, icon = "warn", "&#9651;"
    else:
        cls, icon = "bad", "&#33;"
    return f'<span class="js-badge {cls}">{icon} {esc(v)}</span>'


def hero_score(score, verdict: str, one_line: str) -> str:
    return f"""
<div class="js-hero-score">
  <div><span class="num">{esc(score)}</span><span class="unit"> / 100</span></div>
  <div>
    <div style="margin-bottom:.45rem;">{verdict_badge(verdict)}</div>
    <div class="desc">{esc(one_line)}</div>
  </div>
</div>"""


def meter(label: str, score) -> str:
    try:
        pct = max(0, min(100, int(score)))
    except (ValueError, TypeError):
        pct = 0
    return f"""
<div class="js-meter">
  <div class="head"><span class="name">{esc(label)}</span><span class="val">{pct}</span></div>
  <div class="track"><div class="fill" style="width:{pct}%"></div></div>
</div>"""


def ai_gauge(percent, verdict: str, comment: str, heuristic=None, llm=None) -> str:
    try:
        p = max(0, min(100, int(percent)))
    except (ValueError, TypeError):
        p = 0
    cls = "good" if p <= 30 else ("warn" if p <= 60 else "bad")
    detail = ""
    if heuristic is not None and llm is not None:
        detail = f'<div style="font-size:.76rem;color:#7C869C;margin-top:.3rem;">문체 통계 {esc(heuristic)}% · AI 판독 {esc(llm)}% 결합 추정</div>'
    return f"""
<div class="js-ai">
  <div><span class="num {cls}">{p}</span><span class="unit"> %</span></div>
  <div>
    <div style="margin-bottom:.4rem;">{verdict_badge(verdict)}</div>
    <div class="desc">{esc(comment)}</div>
    {detail}
  </div>
</div>"""


def flag_chips(flags: list) -> str:
    if not flags:
        return ""
    chips = "".join(f'<span class="js-chip">{esc(f.get("pattern", ""))}</span>' for f in flags[:5])
    return f'<div class="js-chiprow">{chips}</div>'


def answer_card(question: str, subtitle: str, body: str, chars: dict,
                limit: int, count_mode: str, extra_meta: str = "",
                ai_percent=None) -> str:
    mode_txt = "공백 포함" if count_mode == "incl" else "공백 제외"
    sub_html = f'<div class="sub">{esc(subtitle)}</div>' if subtitle else ""
    n = chars.get("incl" if count_mode == "incl" else "excl", 0)
    meta = (f'<span>{mode_txt} <b>{n}</b>자 / 목표 {limit}자</span>'
            f'<span>공백 포함 {chars.get("incl", 0)}자 · 공백 제외 {chars.get("excl", 0)}자</span>')
    if ai_percent is not None:
        meta += f'<span>AI 감지 위험 <b>{esc(ai_percent)}%</b> (추정)</span>'
    if extra_meta:
        meta += f"<span>{esc(extra_meta)}</span>"
    return f"""
<div class="js-answer">
  <div class="q">Q. {esc(question)}</div>
  {sub_html}
  <div class="body">{nl2br(body)}</div>
  <div class="meta">{meta}</div>
</div>"""


def note_box(title: str, body: str) -> str:
    return f'<div class="js-note"><div class="t">{esc(title)}</div>{nl2br(body)}</div>'


def material_card(m: dict) -> str:
    best = " · ".join(m.get("best_for", [])[:3])
    return f"""
<div class="js-answer" style="border-left-color:rgba(201,169,106,.65);padding:1.15rem 1.4rem;">
  <div class="sub" style="font-size:1.02rem;">{esc(m.get('title', ''))}</div>
  <div class="body" style="font-size:.9rem;line-height:1.7;">{esc(m.get('summary', ''))}</div>
  <div class="meta">
    <span>핵심 숫자 <b>{esc(m.get('number_hook', ''))}</b></span>
    <span>적합 문항 · {esc(best)}</span>
  </div>
  {f'<div style="font-size:.82rem;color:#C9A96A;margin-top:.6rem;">✦ {esc(m.get("tip", ""))}</div>' if m.get("tip") else ''}
</div>"""


def empty_state(big: str, small: str) -> str:
    return f'<div class="js-empty"><div class="big">{esc(big)}</div>{esc(small)}</div>'
