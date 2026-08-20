# ✒️ 자소서 스튜디오 (JASO STUDIO)

**읽는 순간, 뽑고 싶어지는 자기소개서.**
실시간 기업 분석 → 직무 적합도 진단 → 재료 인터뷰 → 합격 문체 자동 작성까지, 첨삭 전문가의 기준을 그대로 담은 자기소개서 작성 프로그램입니다.

## 핵심 기능

| 기능 | 설명 |
|---|---|
| 🔍 실시간 기업 분석 | Claude 웹 검색 + DART 전자공시 API로 최신 뉴스·실적·인재상을 조사해 지원동기의 '근거'를 만듭니다 |
| ⚖️ 직무 적합도 진단 | 스펙을 입력하면 서류 심사관 관점에서 적합/조건부/보완 판정 + 축별 점수 + 자소서 소재 추천 |
| 🎙 재료 인터뷰 | 질문에 답하기만 하면 경험이 자동으로 정리되어 자소서에 반영됩니다 |
| ✒️ 합격 문체 자동 작성 | 두괄식 · 문항당 1개의 자극적 소제목 · 상황→문제제기→원인→해결책→입사 후 활용 스토리텔링 · 기자식 가독성 |
| 📏 분량 제어 | 문항별 300~5000자, 공백 포함/제외 선택. 목표 분량에 자동 보정 |
| 📄 내보내기 | DOCX / TXT 다운로드, 진행 상황 저장·불러오기(.json) |

## 폴더 구조

```
jaso-studio/
├── app.py                  # 메인 앱 (Streamlit)
├── core/
│   ├── engine.py           # Claude API · DART 연동 · 분량 보정
│   ├── prompts.py          # 문체 헌법 · 합격 예문 · 프롬프트 빌더
│   ├── styles.py           # 아이보리+딥네이비 디자인
│   └── exporter.py         # DOCX/TXT 내보내기
├── .streamlit/config.toml  # 테마
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
3. **③ 재료 인터뷰** — 대표 경험 하나를 깊게, 메모하듯 답변
4. **④ 자소서 생성** — 공고 문항 붙여넣기 → 분량(300~5000자) 선택 → 생성 → 수정 지시로 다듬기
5. **⑤ 완성본** — 전체 검토 → DOCX/TXT 다운로드

## 문제 해결

| 증상 | 해결 |
|---|---|
| `API 키가 올바르지 않습니다` | 키 앞뒤 공백 제거, `sk-ant-`로 시작하는지 확인 |
| `선택한 모델을 찾을 수 없습니다` | 사이드바에서 다른 모델 선택. 모델 ID는 [docs.claude.com](https://docs.claude.com) 참고 |
| 웹 검색이 안 됨 | 키 권한에 따라 자동으로 검색 없이 작성됩니다(결과에 표시). Console에서 웹 검색 활성화 확인 |
| DART에서 기업을 못 찾음 | 정식 법인명으로 검색 (예: "삼성전자" O, "삼전" X). 비상장 중소기업은 없을 수 있음 |
| 배포 후 `ModuleNotFoundError` | `requirements.txt`가 저장소 최상단에 있는지 확인 |

---

© JASO STUDIO — 합격을 설계하는 자기소개서
