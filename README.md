# 블로그 자동화 (Blog Automation)

네이버 맛집 블로그 운영을 반자동화하는 Python 시스템.
3개의 독립 모듈이 이웃 신청, 초안 생성, 스타일 관리를 자동화합니다.

```
[Plan] ✅ → [Design] ✅ → [Do] ✅ → [Check] ✅ → [Act] ✅ → [Report] ✅
Match Rate: 93% | Tests: 47/47 (100%)
```

---

## 모듈 구성

| 모듈 | 설명 | 트리거 | 핵심 기술 |
|------|------|--------|----------|
| **Module 1** | 이웃 추가 자동화 | 매일 09:00 자동 (APScheduler) | 네이버 검색 API + Playwright |
| **Module 2** | 블로그 초안 자동 작성 | `input/` 폴더 `done.txt` 감지 (watchdog) | Claude Vision API + Playwright |
| **Module 3** | 스타일 가이드 관리 | 웹 UI (FastAPI) | Claude API + httpx/BeautifulSoup4 |

---

## 기술 스택

| 분류 | 기술 |
|------|------|
| Python | 3.11 |
| AI / LLM | Anthropic Claude (`claude-sonnet-4-6`) — Vision + Text |
| 브라우저 자동화 | Playwright (Chromium) |
| 폴더 감시 | watchdog |
| 스케줄러 | APScheduler |
| 웹 서버 | FastAPI + Uvicorn + Jinja2 |
| 설정 관리 | pydantic-settings + python-dotenv |
| 로깅 | loguru (날짜별 로테이션) |
| 크롤링 | httpx + BeautifulSoup4 (1차) → Playwright 폴백 (2차) |
| 이미지 처리 | Pillow |
| API 재시도 | tenacity (Claude/Naver API) + 자체 `_retry_async` (Playwright) |

---

## 프로젝트 구조

```
blog_automation/
├── config.py                      # pydantic-settings 중앙 설정
├── core/
│   ├── claude_client.py           # Anthropic SDK (text + vision + retry)
│   ├── naver_client.py            # 네이버 검색 API + retry
│   ├── browser.py                 # Playwright BrowserSession + 네이버 로그인
│   └── logger.py                  # loguru 모듈별 로거
│
├── modules/
│   ├── neighbor/                  # Module 1: 이웃 추가
│   │   ├── searcher.py            #   키워드 검색 + 블로거 수집
│   │   ├── filter.py              #   3단계 필터링 (API 절약 순)
│   │   ├── automator.py           #   Playwright 이웃 신청
│   │   └── runner.py              #   오케스트레이터
│   │
│   ├── draft/                     # Module 2: 초안 생성 (핵심)
│   │   ├── watcher.py             #   watchdog done.txt 감시
│   │   ├── media_processor.py     #   Pillow 리사이즈 + Base64
│   │   ├── draft_generator.py     #   Claude Vision → 초안
│   │   ├── poster.py              #   Playwright 네이버 포스팅 + retry
│   │   └── runner.py              #   오케스트레이터
│   │
│   └── style/                     # Module 3: 스타일 관리
│       ├── web_app.py             #   FastAPI 앱 (7개 라우트)
│       ├── style_updater.py       #   가이드 CRUD + Claude 반영
│       ├── history_manager.py     #   변경 이력 누적
│       ├── url_analyzer.py        #   URL 크롤링 + 스타일 추출
│       ├── runner.py              #   오케스트레이터
│       └── templates/index.html   #   웹 UI
│
├── data/
│   ├── style_guide.json           # 현재 스타일 가이드 (M3→M2 공유)
│   └── style_guide_history.json   # 변경 이력
│
├── input/                         # M2 트리거 (서브폴더/done.txt)
├── output/                        # M2 생성 초안
├── logs/                          # 날짜별 로그
│
├── run_module1.py                 # M1 독립 실행
├── run_module2.py                 # M2 독립 실행 (watchdog)
├── run_module3.py                 # M3 독립 실행 (FastAPI)
├── scheduler.py                   # APScheduler M1 자동화
│
└── tests/                         # pytest (47개)
    ├── conftest.py
    ├── test_draft.py              # 29개
    ├── test_neighbor.py           # 10개
    └── test_style.py              # 8개
```

---

## 환경 설정

### 1. 가상환경 생성

```bash
conda create -n blog_automation python=3.11
conda activate blog_automation
```

### 2. 패키지 설치

```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. `.env` 파일 생성

루트 디렉토리에 `.env` 파일 생성:

```env
# === 필수 ===
ANTHROPIC_API_KEY=sk-ant-...
NAVER_CLIENT_ID=...              # 네이버 개발자센터 > Open API
NAVER_CLIENT_SECRET=...
NAVER_ID=your_naver_id
NAVER_PASSWORD=your_naver_password

# === 선택 (기본값 있음) ===
CLAUDE_MODEL=claude-sonnet-4-6
NEIGHBOR_ADD_DAILY_LIMIT=20
NAVER_SEARCH_DAILY_LIMIT=1000
WEB_HOST=127.0.0.1
WEB_PORT=8000
```

> `.env` 파일은 `.gitignore`에 등록되어 있어 git에 커밋되지 않습니다.

### 4. 네이버 API 키 발급

1. [네이버 개발자센터](https://developers.naver.com) 접속
2. Application 등록 → "검색" API 사용 선택
3. Client ID / Client Secret 복사 → `.env`에 입력

---

## 테스트 실행

```bash
conda activate blog_automation

# 전체 테스트 (47개)
python -m pytest tests/ -v

# 모듈별 실행
python -m pytest tests/test_draft.py -v      # Module 2 (29개)
python -m pytest tests/test_neighbor.py -v   # Module 1 (10개)
python -m pytest tests/test_style.py -v      # Module 3 (8개)
```

---

## 실행 방법

### Module 2 — 블로그 초안 자동 생성 (핵심 기능)

```bash
# 터미널 1: watchdog 서비스 시작
python run_module2.py
```

```bash
# 터미널 2: 게시글 준비
mkdir -p input/강남_스시_오마카세
cp ~/사진/*.jpg input/강남_스시_오마카세/

# done.txt 생성 → 자동 트리거
touch input/강남_스시_오마카세/done.txt
```

**자동 실행 흐름:**
```
done.txt 감지 → 이미지 전처리 (1024px + Base64) → Claude Vision 초안 생성
→ 네이버 블로그 "나만보기" 포스팅 → output/ 초안 저장
```

### Module 3 — 스타일 가이드 웹 UI

```bash
# tmux 백그라운드 실행 (권장)
tmux new -s blog_style
python run_module3.py    # http://127.0.0.1:8000 접속
# Ctrl+b, d (세션 분리)
```

**웹 UI 기능:**
- 피드백 텍스트 입력 → Claude가 `style_guide.json` 자동 업데이트
- 네이버 블로그 URL → 스타일 추출 → 선택적 적용
- 변경 이력 타임라인 조회

**API 엔드포인트:**

| Method | Path | 설명 |
|--------|------|------|
| `GET` | `/` | 웹 UI |
| `GET` | `/guide` | 현재 스타일 가이드 조회 |
| `POST` | `/feedback` | 피드백 → 가이드 업데이트 |
| `GET` | `/history` | 변경 이력 (최근 20건) |
| `POST` | `/analyze-url` | URL 크롤링 + 스타일 분석 |
| `POST` | `/apply-style` | 분석된 스타일 선택 적용 |

### Module 1 — 이웃 추가 자동화

```bash
# 수동 1회 실행
python run_module1.py
```

### 스케줄러 — Module 1 매일 자동 실행

```bash
tmux new -s blog_scheduler
python scheduler.py    # 매일 09:00 KST Module 1 자동 실행
# Ctrl+b, d
```

---

## 모듈 간 의존성

```
core/ (claude_client, naver_client, browser, logger)
  ├── Module 1 → naver_client + browser
  ├── Module 2 → claude_client + browser + style_guide.json (읽기)
  └── Module 3 → claude_client + style_guide.json (읽기/쓰기)

Module 1 ↔ Module 2, 3: 완전 독립
Module 3 → Module 2: style_guide.json 단방향 공유
```

---

## 주의사항

- 네이버 자동 로그인 시 **2차 인증(OTP)은 비활성화** 하거나 자동화 전용 서브 계정 사용 권장
- 네이버 보안 정책에 따라 간헐적으로 **CAPTCHA** 가 발생할 수 있음 (RuntimeError → 수동 개입 필요)
- 이웃 신청은 일일 상한 **20건**으로 제한 (계정 제재 방지)
- API 키는 절대 git에 커밋하지 않도록 주의
- 지원 이미지 형식: `.jpg`, `.jpeg`, `.png`, `.webp`

---

## License

Private project. Not for redistribution.
