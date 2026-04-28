# disclosure-summary

한국 공시(DART) 정리 및 요약 프로젝트.
하루 동안 DART 전자공시시스템에 접수된 공시를 한 페이지로 정리해 주는 나만의 공시 리포트.

## Phase 1 (현재)

- DART OpenAPI로 일별 공시 목록 수집
- SQLite에 저장
- 표지 + 인덱스 형태의 HTML 리포트 생성

## 설치

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows (Git Bash: source .venv/Scripts/activate)
pip install -r requirements.txt
```

## 환경 변수

`.env.example` 을 복사해서 `.env` 만들고 DART API 키 입력:

```
DART_API_KEY=발급받은_키
```

DART API 키는 [opendart.fss.or.kr](https://opendart.fss.or.kr) 에서 무료 발급.

## 사용법

### 1) 오늘 공시 수집

```bash
python -m disclosure_summary.fetch
```

특정 일자:

```bash
python -m disclosure_summary.fetch --date 2026-04-28
```

시장 필터 (Y=유가증권, K=코스닥, N=코넥스, E=기타):

```bash
python -m disclosure_summary.fetch --corp-cls Y
```

### 2) HTML 리포트 생성

```bash
python -m disclosure_summary.render
```

생성물: `reports/YYYY-MM-DD/index.html` — 브라우저에서 바로 열어보면 됩니다.

## 디렉터리 구조

```
disclosure-summary/
├── disclosure_summary/    # 패키지
│   ├── config.py          # 경로/환경변수
│   ├── dart.py            # DART API 클라이언트
│   ├── db.py              # SQLite 스키마/IO
│   ├── fetch.py           # 수집 CLI
│   └── render.py          # 리포트 생성 CLI
├── templates/report.html  # Jinja2 템플릿
├── static/style.css       # 리포트 스타일
├── data/disclosures.db    # SQLite (gitignored)
└── reports/YYYY-MM-DD/    # 생성된 HTML
```

## 다음 단계 (Phase 2~)

- [ ] Phase 2: 공시 유형별 룰 기반 매매 시그널 분류 (매수/중립/매도)
- [ ] Phase 3: 종목별 1페이지 — 사업 BM, 매출 구성, 재무 한 줄 (DART 사업보고서 파싱)
- [ ] Phase 4: Claude API로 공시 해석/투자 인사이트 자동 생성
- [ ] Phase 5: 매일 20:00 자동 실행 스케줄링
