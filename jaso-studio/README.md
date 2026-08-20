# ✒️ 자소서 스튜디오 (JASO STUDIO)

**읽는 순간, 뽑고 싶어지는 자기소개서.**
실시간 기업 분석 → 직무 적합도 진단 → 재료 인터뷰 → 합격 문체 자동 작성까지, 첨삭 전문가의 기준을 그대로 담은 자기소개서 작성 프로그램입니다.

## 핵심 기능

| 기능 | 설명 |
|---|---|
| 🔍 실시간 기업 분석 | Claude 웹 검색 + DART 전자공시 API로 최신 뉴스·실적·인재상을 조사해 지원동기의 '근거'를 만듭니다 |
| ⚖️ 직무 적합도 진단 | 스펙을 입력하면 서류 심사관 관점에서 적합/조건부/보완 판정 + 축별 점수 + 자소서 소재 추천 |
| ⛏️ 소재 발굴 | 메모하듯 적은 이력·경험에서 AI가 문항 유형별 자소서 소재를 캐냅니다 |
| ✒️ 문항별 경험 → 생성 | 문항마다 그 문항에 쓸 경험을 입력하고 바로 생성. 두괄식 · 문항당 1개의 자극적 소제목 · 상황→문제제기→원인→해결책→입사 후 활용 스토리텔링 |
| 🕵️ AI 감지 방어 | 문체 통계 + AI 판독을 결합해 감지 위험 %(추정)를 표시하고, 휴먼라이징으로 AI 티를 제거 |
| 📏 분량 제어 | 문항별 300~5000자, 공백 포함/제외 선택. 목표 분량에 자동 보정 |
| 📄 내보내기 | DOCX / TXT 다운로드, 진행 상황 저장·불러오기(.json) |
| 🎬 프리미엄 디자인 | 배경 비디오 + 다크 글래스 UI (배경 영상은 `static/bg.mp4` 교체로 변경 가능) |

## 폴더 구조

```
jaso-studio/
├── app.py                  # 메인 앱 (Streamlit)
├── core/
│   ├── engine.py           # Claude API · DART 연동 · 분량 보정 · AI 감지
│   ├── prompts.py          # 문체 헌법 · 합격 예문 · 프롬프트 빌더
│   ├── styles.py           # 비디오 배경 + 다크 글래스 디자인
│   └── exporter.py         # DOCX/TXT 내보내기
├── static/
│   ├── bg.mp4              # 배경 영상 (교체 가능, 10MB 이하 권장)
│   └── bg_poster.jpg       # 영상 로딩 전 표시 이미지
├── .streamlit/config.toml  # 테마 + 정적 파일 서빙 설정
├── requirements.txt
└── README.md
```

## 1) API 키 준비

1. **Anthropic API 키 (필수)** — <https://console.anthropic.com> → *API Keys* → *Create Key*
   - 결제 수단 등록 후 사용량만큼 과금됩니다. 웹 검색은 1,000회당 $10 + 토큰 비용이 추가됩니다.
2. **DART 전자공시 API 키 (선택, 무료)** — <https://opendart.fss.or.kr> → 인증키 신청
   - 상장사 재무제표·공시를 함께 분석해 지원동기의 숫자 근거가 좋아집니다.

## 2) 로컬에서 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

브라우저가 열리면 사이드바에 API 키를 넣고 사용하세요.

## 3) GitHub에 올리기

1. <https://github.com>에서 **New repository** → 이름 예: `jaso-studio` → *Create*
2. **Add file → Upload files** 로 이 폴더의 파일 전체를 업로드
   (폴더 구조 그대로: `core/` 폴더와 `.streamlit/` 폴더 포함)
3. **Commit changes** 클릭

> Git에 익숙하다면: `git init` → `git add .` → `git commit -m "init"` → `git push`

## 4) Streamlit Community Cloud 배포 (무료)

1. <https://share.streamlit.io> 접속 → GitHub 계정으로 로그인
2. **Create app** → 방금 만든 저장소 선택 → Main file path: `app.py` → **Deploy**
3. 2~3분 후 나만의 URL(`https://아이디-jaso-studio.streamlit.app`)이 생깁니다

### (선택) 키를 서버에 심어두기 — 사용자가 키를 입력하지 않게 하려면

앱 관리 화면 → **Settings → Secrets** 에 아래처럼 입력:

```toml
ANTHROPIC_API_KEY = "sk-ant-..."
DART_API_KEY = "발급받은키"
```

> ⚠️ 이 경우 앱 사용자들의 모든 호출 비용이 이 키로 청구됩니다. 판매용이라면 비공개 배포 또는 사용자 본인 키 입력(BYOK) 방식을 권장합니다.

## 5) 사용 흐름

1. **① 기업 분석** — 회사·직무 입력 → 실시간 분석 (지원동기에 자동 인용)
2. **② 적합도 진단** — 스펙 입력 → 판정·점수·소재 추천
3. **③ 소재 발굴** — 프로필·자유 재료 입력 → AI가 문항 유형별 소재 발굴
4. **④ 자소서 생성** — 문항 붙여넣기 → **그 문항에 쓸 경험 입력** → 분량(300~5000자) 선택 → 생성 → AI 감지 검사 → 휴먼라이징
5. **⑤ 완성본** — 전체 검토 → DOCX/TXT 다운로드

## AI 감지 기능에 대해

- 표시되는 %는 **자체 문체 통계(문장 길이 균일도·종결 단조로움·상투 표현 밀도) 50% + Claude 포렌식 평가 50%**를 결합한 추정치입니다.
- GPTZero 등 실제 상용 감지기와 결과가 다를 수 있습니다. 30% 이하(안전)를 목표로 휴먼라이징을 활용하세요.
- 휴먼라이징은 사실·숫자·경험 내용을 바꾸지 않고 문장 리듬과 표현만 사람답게 고칩니다.

## 배경 영상 바꾸기

`static/bg.mp4`를 원하는 영상으로 교체하면 됩니다. 10MB 이하(1280px, 무음) 권장 — 용량이 크면 첫 로딩이 느려집니다. `static/bg.webm`은 같은 영상의 보조 포맷(선택)으로, 없어도 동작합니다. 영상은 앱이 직접 읽어 내장하므로 별도 서버 설정 없이도 재생됩니다.

## 문제 해결

| 증상 | 해결 |
|---|---|
| `API 키가 올바르지 않습니다` | 키 앞뒤 공백 제거, `sk-ant-`로 시작하는지 확인 |
| `선택한 모델을 찾을 수 없습니다` | 사이드바에서 다른 모델 선택. 모델 ID는 [docs.claude.com](https://docs.claude.com) 참고 |
| 웹 검색이 안 됨 | 키 권한에 따라 자동으로 검색 없이 작성됩니다(결과에 표시). Console에서 웹 검색 활성화 확인 |
| DART에서 기업을 못 찾음 | 정식 법인명으로 검색 (예: "삼성전자" O, "삼전" X). 비상장 중소기업은 없을 수 있음 |
| 배포 후 `ModuleNotFoundError` | `requirements.txt`가 저장소 최상단에 있는지 확인 |
| 배경 영상이 안 보임 | `.streamlit/config.toml`의 `enableStaticServing = true` 유지, `static/bg.mp4` 경로 확인 |

---

© JASO STUDIO — 합격을 설계하는 자기소개서
