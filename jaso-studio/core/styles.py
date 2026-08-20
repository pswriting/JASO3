# -*- coding: utf-8 -*-
"""
자소서 스튜디오 — 프리미엄 디자인 (아이보리 + 딥네이비)
CSS와 HTML 컴포넌트 빌더.
"""
import html as _html

# 브랜드 토큰
IVORY = "#F7F3EA"
PAPER = "#FFFDF8"
INK = "#1B2233"
NAVY = "#1E3A5F"
NAVY_DEEP = "#14213A"
NAVY_SOFT = "#2C4A6E"
GOLD = "#B08D57"          # 장식 전용 (데이터·본문 텍스트에는 쓰지 않음)
LINE = "#E5DECB"
MUTED = "#6E6857"
GOOD = "#1F7A4D"
WARN = "#8A6100"
BAD = "#A23B2E"

GLOBAL_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;600;700;900&family=Noto+Sans+KR:wght@300;400;500;700&display=swap');

/* ── 기본 ───────────────────────────── */
html, body, .stApp {{
    background-color: {IVORY} !important;
    color: {INK};
    font-family: 'Noto Sans KR', -apple-system, sans-serif;
}}
.block-container {{
    max-width: 1120px;
    padding-top: 2.2rem;
    padding-bottom: 5rem;
}}
h1, h2, h3 {{
    font-family: 'Noto Serif KR', serif !important;
    color: {INK};
    letter-spacing: -0.01em;
}}
[data-testid="stHeader"] {{ background: transparent; }}
#MainMenu, footer, [data-testid="stToolbar"] {{ visibility: hidden; }}

/* ── 사이드바: 딥네이비 ─────────────── */
[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, {NAVY_DEEP} 0%, #0F1A2E 100%);
    border-right: 1px solid rgba(176,141,87,.25);
}}
[data-testid="stSidebar"] * {{ color: #EDE7D8; }}
[data-testid="stSidebar"] label, [data-testid="stSidebar"] p,
[data-testid="stSidebar"] span {{ color: #CFC8B4 !important; font-size: .86rem; }}
/* 사이드바 입력: 밝은 필드 + 진한 글자 (일관된 폼 스타일) */
[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] .stTextArea textarea,
[data-testid="stSidebar"] .stNumberInput input {{
    background: {PAPER} !important;
    color: {INK} !important;
    -webkit-text-fill-color: {INK} !important;
    border-radius: 10px !important;
}}
/* selectbox — Streamlit 신버전(react-aria)과 구버전(baseweb) 모두 대응 */
[data-testid="stSidebar"] .stSelectbox [role="group"],
[data-testid="stSidebar"] .stSelectbox .react-aria-ComboBox > div,
[data-testid="stSidebar"] div[data-baseweb="select"] > div {{
    background-color: {PAPER} !important;
    border: 1px solid rgba(237,231,216,.35) !important;
    border-radius: 10px !important;
}}
[data-testid="stSidebar"] .stSelectbox input,
[data-testid="stSidebar"] .stSelectbox [role="group"] *,
[data-testid="stSidebar"] div[data-baseweb="select"] span,
[data-testid="stSidebar"] div[data-baseweb="select"] input {{
    color: {INK} !important;
    -webkit-text-fill-color: {INK} !important;
}}
[data-testid="stSidebar"] .stSelectbox svg,
[data-testid="stSidebar"] div[data-baseweb="select"] svg {{
    fill: {NAVY} !important; color: {NAVY} !important;
}}
[data-testid="stSidebar"] hr {{ border-color: rgba(237,231,216,.15); }}
[data-testid="stSidebar"] .stButton > button,
[data-testid="stSidebar"] .stDownloadButton > button {{
    width: 100%;
    background: rgba(176,141,87,.18) !important;
    color: #F3EEDF !important;
    border: 1px solid rgba(176,141,87,.55) !important;
}}
[data-testid="stSidebar"] .stButton > button:hover,
[data-testid="stSidebar"] .stDownloadButton > button:hover {{
    background: rgba(176,141,87,.32) !important;
    color: #FFFFFF !important;
}}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {{
    background: rgba(247,243,234,.06) !important;
    border: 1px dashed rgba(237,231,216,.35) !important;
    border-radius: 10px !important;
}}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] * {{ color: #C9C2AE !important; }}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button {{
    background: rgba(176,141,87,.2) !important;
    color: #F3EEDF !important;
    border: 1px solid rgba(176,141,87,.5) !important;
    border-radius: 8px !important;
}}
[data-testid="stSidebar"] [data-testid="stExpander"] details,
[data-testid="stSidebar"] details[data-testid="stExpander"],
[data-testid="stSidebar"] [data-testid="stExpander"] {{
    background: rgba(247,243,234,.05) !important;
    border: 1px solid rgba(237,231,216,.22) !important;
    border-radius: 10px !important;
}}
[data-testid="stSidebar"] [data-testid="stExpander"] summary,
[data-testid="stSidebar"] [data-testid="stExpander"] summary span {{
    color: #EDE7D8 !important;
}}

/* ── 입력 위젯 ─────────────────────── */
.stTextInput input, .stTextArea textarea, .stNumberInput input {{
    background: {PAPER} !important;
    border: 1px solid {LINE} !important;
    border-radius: 10px !important;
    color: {INK} !important;
}}
.stTextInput input:focus, .stTextArea textarea:focus {{
    border-color: {NAVY} !important;
    box-shadow: 0 0 0 2px rgba(30,58,95,.14) !important;
}}
[data-baseweb="select"] > div {{
    background: {PAPER} !important;
    border: 1px solid {LINE} !important;
    border-radius: 10px !important;
}}
.stSlider [data-baseweb="slider"] div[role="slider"] {{
    background: {NAVY} !important;
    border: 2px solid {PAPER} !important;
    box-shadow: 0 1px 4px rgba(20,33,58,.4) !important;
}}

/* ── 버튼 ──────────────────────────── */
.stButton > button, .stDownloadButton > button {{
    border-radius: 10px;
    border: 1px solid {NAVY};
    background: {PAPER};
    color: {NAVY};
    font-weight: 600;
    letter-spacing: .02em;
    padding: .5rem 1.1rem;
    transition: all .18s ease;
}}
.stButton > button:hover, .stDownloadButton > button:hover {{
    border-color: {GOLD};
    color: {NAVY_DEEP};
    box-shadow: 0 2px 10px rgba(176,141,87,.28);
    transform: translateY(-1px);
}}
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {{
    background: linear-gradient(135deg, {NAVY_DEEP} 0%, {NAVY} 60%, {NAVY_SOFT} 100%);
    color: #F3EEDF;
    border: 1px solid {NAVY_DEEP};
}}
.stButton > button[kind="primary"]:hover {{
    box-shadow: 0 4px 16px rgba(20,33,58,.35);
    border-color: {GOLD};
    color: #FFF;
}}

/* ── 탭 ────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {{
    gap: .3rem;
    border-bottom: 1px solid {LINE};
}}
.stTabs [data-baseweb="tab"] {{
    font-family: 'Noto Sans KR', sans-serif;
    font-weight: 600;
    font-size: .95rem;
    color: {MUTED};
    padding: .65rem 1.05rem;
    border-radius: 10px 10px 0 0;
}}
.stTabs [aria-selected="true"] {{
    color: {NAVY_DEEP} !important;
    background: {PAPER};
}}
.stTabs [data-baseweb="tab-highlight"] {{ background-color: {GOLD}; height: 3px; }}
.stTabs [data-baseweb="tab-border"] {{ background-color: {LINE}; }}

/* ── 컨테이너·익스팬더 ─────────────── */
[data-testid="stVerticalBlockBorderWrapper"] > div {{ border-radius: 14px; }}
div[data-testid="stVerticalBlockBorderWrapper"] {{
    background: {PAPER};
    border: 1px solid {LINE} !important;
    border-radius: 14px;
    box-shadow: 0 1px 6px rgba(27,34,51,.05);
}}
details[data-testid="stExpander"], [data-testid="stExpander"] details {{
    background: {PAPER};
    border: 1px solid {LINE} !important;
    border-radius: 12px !important;
}}
[data-testid="stExpander"] summary {{ font-weight: 600; color: {NAVY_DEEP}; }}

/* ── 알림 ──────────────────────────── */
[data-testid="stAlert"] {{ border-radius: 12px; }}

/* ── 커스텀 컴포넌트 ────────────────── */
.js-hero {{
    padding: 2.6rem 2.4rem 2.2rem;
    background:
      radial-gradient(1200px 400px at 85% -20%, rgba(176,141,87,.16), transparent 60%),
      linear-gradient(135deg, {NAVY_DEEP} 0%, #1A2C4D 55%, {NAVY} 100%);
    border-radius: 18px;
    border: 1px solid rgba(176,141,87,.35);
    margin-bottom: 1.6rem;
    box-shadow: 0 8px 30px rgba(20,33,58,.22);
}}
.js-hero .brand {{
    font-family: 'Noto Sans KR', sans-serif;
    font-size: .72rem;
    font-weight: 700;
    letter-spacing: .42em;
    color: {GOLD};
    margin-bottom: .8rem;
}}
.js-hero h1 {{
    font-family: 'Noto Serif KR', serif;
    font-size: 2.05rem;
    font-weight: 900;
    color: #F5F1E4 !important;
    margin: 0 0 .55rem 0;
    line-height: 1.28;
}}
.js-hero .tagline {{
    color: #C9C2AE;
    font-size: .95rem;
    font-weight: 300;
    letter-spacing: .02em;
}}
.js-hero .rule {{
    width: 54px; height: 2px;
    background: linear-gradient(90deg, {GOLD}, transparent);
    margin-top: 1.15rem;
}}

.js-overline {{
    display: flex; align-items: baseline; gap: .7rem;
    margin: 1.4rem 0 .35rem;
}}
.js-overline .no {{
    font-family: 'Noto Serif KR', serif;
    font-size: .8rem; font-weight: 700;
    color: {GOLD}; letter-spacing: .18em;
}}
.js-overline .t {{
    font-family: 'Noto Serif KR', serif;
    font-size: 1.32rem; font-weight: 700; color: {INK};
}}
.js-overline .sub {{ font-size: .84rem; color: {MUTED}; }}

.js-divider {{
    height: 1px; border: 0;
    background: linear-gradient(90deg, {LINE}, transparent);
    margin: 1.1rem 0;
}}

.js-stat-row {{ display: flex; gap: .8rem; flex-wrap: wrap; margin: .4rem 0 .8rem; }}
.js-stat {{
    flex: 1 1 150px;
    background: {PAPER};
    border: 1px solid {LINE};
    border-radius: 14px;
    padding: .95rem 1.1rem .85rem;
}}
.js-stat .l {{
    font-size: .72rem; font-weight: 700; color: {MUTED};
    letter-spacing: .1em; margin-bottom: .3rem;
}}
.js-stat .v {{
    font-family: 'Noto Serif KR', serif;
    font-size: 1.28rem; font-weight: 700; color: {INK}; line-height: 1.2;
}}
.js-stat .s {{ font-size: .76rem; color: {MUTED}; margin-top: .25rem; }}

.js-hero-score {{
    display: flex; align-items: center; gap: 1.6rem;
    background: {PAPER}; border: 1px solid {LINE};
    border-radius: 16px; padding: 1.4rem 1.7rem; margin: .5rem 0 1rem;
}}
.js-hero-score .num {{
    font-family: 'Noto Serif KR', serif;
    font-size: 3.4rem; font-weight: 900; color: {NAVY_DEEP}; line-height: 1;
}}
.js-hero-score .unit {{ font-size: 1.1rem; color: {MUTED}; font-weight: 400; }}
.js-hero-score .desc {{ font-size: .95rem; color: {INK}; line-height: 1.55; }}

.js-badge {{
    display: inline-flex; align-items: center; gap: .4rem;
    font-size: .84rem; font-weight: 700;
    padding: .3rem .85rem; border-radius: 999px;
    border: 1px solid; letter-spacing: .02em;
}}
.js-badge.good {{ color: {GOOD}; border-color: {GOOD}; background: rgba(31,122,77,.07); }}
.js-badge.warn {{ color: {WARN}; border-color: {WARN}; background: rgba(138,97,0,.07); }}
.js-badge.bad  {{ color: {BAD};  border-color: {BAD};  background: rgba(162,59,46,.07); }}

.js-meter {{ margin: .5rem 0 .65rem; }}
.js-meter .head {{
    display: flex; justify-content: space-between; align-items: baseline;
    margin-bottom: .3rem;
}}
.js-meter .name {{ font-size: .86rem; font-weight: 600; color: {INK}; }}
.js-meter .val {{
    font-family: 'Noto Serif KR', serif;
    font-size: .92rem; font-weight: 700; color: {NAVY_DEEP};
}}
.js-meter .track {{
    height: 9px; background: #ECE6D5;
    border-radius: 999px; overflow: hidden;
}}
.js-meter .fill {{
    height: 100%; border-radius: 999px;
    background: linear-gradient(90deg, {NAVY_SOFT}, {NAVY_DEEP});
}}

.js-answer {{
    background: {PAPER};
    border: 1px solid {LINE};
    border-left: 3px solid {GOLD};
    border-radius: 14px;
    padding: 1.5rem 1.7rem;
    margin: .6rem 0 .9rem;
    box-shadow: 0 2px 12px rgba(27,34,51,.06);
}}
.js-answer .q {{
    font-size: .8rem; color: {MUTED}; margin-bottom: .8rem;
    padding-bottom: .7rem; border-bottom: 1px dashed {LINE};
}}
.js-answer .sub {{
    font-family: 'Noto Serif KR', serif;
    font-size: 1.14rem; font-weight: 700; color: {NAVY_DEEP};
    margin-bottom: .75rem;
}}
.js-answer .sub::before {{ content: "["; color: {GOLD}; margin-right: 2px; }}
.js-answer .sub::after  {{ content: "]"; color: {GOLD}; margin-left: 2px; }}
.js-answer .body {{
    font-size: .96rem; line-height: 1.85; color: {INK};
    white-space: normal;
}}
.js-answer .meta {{
    margin-top: 1rem; padding-top: .7rem;
    border-top: 1px dashed {LINE};
    font-size: .78rem; color: {MUTED};
    display: flex; gap: 1.1rem; flex-wrap: wrap;
}}

.js-note {{
    background: rgba(176,141,87,.08);
    border: 1px solid rgba(176,141,87,.35);
    border-radius: 12px;
    padding: .85rem 1.1rem;
    font-size: .86rem; color: {INK}; line-height: 1.65;
    margin-bottom: .8rem;
}}
.js-note .t {{ font-weight: 700; color: {NAVY_DEEP}; margin-bottom: .2rem; }}

.js-step {{
    display: flex; gap: .55rem; flex-wrap: wrap; margin-bottom: 1.1rem;
}}
.js-step .s {{
    font-size: .78rem; font-weight: 600; color: {MUTED};
    background: {PAPER}; border: 1px solid {LINE};
    padding: .32rem .8rem; border-radius: 999px;
}}
.js-step .s b {{ color: {GOLD}; font-family: 'Noto Serif KR', serif; margin-right: .3rem; }}

.js-empty {{
    text-align: center; padding: 2.4rem 1rem;
    color: {MUTED}; font-size: .9rem; line-height: 1.8;
    background: {PAPER}; border: 1px dashed {LINE}; border-radius: 14px;
}}
.js-empty .big {{
    font-family: 'Noto Serif KR', serif;
    font-size: 1.06rem; font-weight: 700; color: {NAVY_DEEP};
}}
</style>
"""


def esc(text: str) -> str:
    return _html.escape(str(text or ""))


def nl2br(text: str) -> str:
    return esc(text).replace("\n\n", "<br><br>").replace("\n", "<br>")


def hero_html() -> str:
    return """
<div class="js-hero">
  <div class="brand">JASO STUDIO</div>
  <h1>읽는 순간, 뽑고 싶어지는<br>자기소개서를 만듭니다</h1>
  <div class="tagline">실시간 기업 분석 · 직무 적합도 진단 · 합격 문체 자동 작성 — 첨삭 전문가의 기준 그대로</div>
  <div class="rule"></div>
</div>"""


def steps_html() -> str:
    return """
<div class="js-step">
  <span class="s"><b>01</b> 기업 분석</span>
  <span class="s"><b>02</b> 적합도 진단</span>
  <span class="s"><b>03</b> 재료 인터뷰</span>
  <span class="s"><b>04</b> 자소서 생성</span>
  <span class="s"><b>05</b> 완성본 다운로드</span>
</div>"""


def overline(no: str, title: str, sub: str = "") -> str:
    sub_html = f'<span class="sub">{esc(sub)}</span>' if sub else ""
    return f'<div class="js-overline"><span class="no">{esc(no)}</span><span class="t">{esc(title)}</span>{sub_html}</div>'


def divider() -> str:
    return '<hr class="js-divider">'


def stat_tiles(items: list) -> str:
    """items: [(label, value, sub), ...]"""
    tiles = "".join(
        f'<div class="js-stat"><div class="l">{esc(l)}</div>'
        f'<div class="v">{esc(v)}</div>'
        + (f'<div class="s">{esc(s)}</div>' if s else "")
        + "</div>"
        for l, v, s in items)
    return f'<div class="js-stat-row">{tiles}</div>'


def verdict_badge(verdict: str) -> str:
    v = (verdict or "").strip()
    if "적합" == v or v.startswith("적합"):
        cls, icon = "good", "&#10003;"
    elif "조건부" in v:
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


def answer_card(question: str, subtitle: str, body: str, chars: dict,
                limit: int, count_mode: str, extra_meta: str = "") -> str:
    mode_txt = "공백 포함" if count_mode == "incl" else "공백 제외"
    sub_html = f'<div class="sub">{esc(subtitle)}</div>' if subtitle else ""
    meta = (f'<span>{mode_txt} <b>{chars.get(count_mode == "incl" and "incl" or "excl", 0)}</b>자'
            f' / 목표 {limit}자</span>'
            f'<span>공백 포함 {chars.get("incl", 0)}자 · 공백 제외 {chars.get("excl", 0)}자</span>')
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


def empty_state(big: str, small: str) -> str:
    return f'<div class="js-empty"><div class="big">{esc(big)}</div>{esc(small)}</div>'
