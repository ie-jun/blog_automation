# CLAUDE.md — blog_automation

네이버 맛집 블로그 반자동화 시스템 구현 지침.

---

## 프로젝트 개요

네이버 블로그 운영을 반자동화하는 시스템. 3개의 독립 모듈로 구성:

| 모듈 | 설명 | 트리거 |
|---|---|---|
| Module 1 | 이웃 추가 자동화 | 매일 1회 자동 (APScheduler) |
| Module 2 | 블로그 초안 자동 작성 | input/ 폴더 파일 감지 (watchdog) |
| Module 3 | 스타일 가이드 업데이트 | 웹 UI (FastAPI + tmux 백그라운드) |

---

## 기술 스택

- **Python**: 3.11
- **AI**: Anthropic Claude API (`claude-sonnet-4-6`) — OpenAI 사용 안 함
- **브라우저 자동화**: Playwright (Selenium 사용 안 함)
- **폴더 감시**: watchdog
- **스케줄러**: APScheduler
- **웹 서버 (Module 3 UI)**: FastAPI + Uvicorn (tmux 세션에서 백그라운드 실행)
- **설정**: pydantic-settings + python-dotenv
- **로깅**: loguru

---

## 폴더 및 파일 구조

```
blog_automation/
├── .env                              # API 키, 네이버 계정
├── .gitignore
├── requirements.txt
├── CLAUDE.md                         # 이 파일
├── config.py                         # 중앙 설정: Settings + 경로 상수
│
├── run_module1.py                    # Module 1 독립 실행 진입점
├── run_module2.py                    # Module 2 독립 실행 진입점 (watchdog 시작)
├── run_module3.py                    # Module 3 독립 실행 진입점 (FastAPI uvicorn 서버 시작)
├── scheduler.py                      # APScheduler: Module 1 매일 자동 실행
│
├── modules/
│   ├── __init__.py
│   ├── neighbor/                     # Module 1: 이웃 추가 자동화
│   │   ├── __init__.py
│   │   ├── searcher.py               # 네이버 검색 API로 맛집 블로거 수집
│   │   ├── filter.py                 # 3가지 조건 필터링 로직
│   │   ├── automator.py              # Playwright 이웃 신청 자동화
│   │   └── runner.py                 # Module 1 오케스트레이터
│   │
│   ├── draft/                        # Module 2: 블로그 초안 자동 작성
│   │   ├── __init__.py
│   │   ├── watcher.py                # watchdog으로 input/ 폴더 실시간 감시
│   │   ├── media_processor.py        # Pillow 이미지 전처리 + Base64 인코딩
│   │   ├── draft_generator.py        # Claude Vision API로 초안 생성
│   │   ├── poster.py                 # Playwright 네이버 블로그 포스팅 (나만보기)
│   │   └── runner.py                 # Module 2 오케스트레이터
│   │
│   └── style/                        # Module 3: 스타일 가이드 업데이트
│       ├── __init__.py
│       ├── web_app.py                # FastAPI 앱 정의 (GET /, POST /feedback)
│       ├── style_updater.py          # Claude API로 style_guide.json 업데이트
│       ├── history_manager.py        # style_guide_history.json 이력 관리
│       ├── runner.py                 # Module 3 오케스트레이터
│       └── templates/
│           └── index.html            # 피드백 입력 웹 UI (단일 페이지)
│
├── core/
│   ├── __init__.py
│   ├── claude_client.py              # Anthropic SDK 공통 클라이언트 (text + vision)
│   ├── naver_client.py               # 네이버 Open API 공통 클라이언트
│   ├── browser.py                    # Playwright 브라우저 세션 + 네이버 로그인
│   └── logger.py                     # loguru 로거 설정
│
├── data/
│   ├── style_guide.json              # 현재 스타일 가이드 (Module 2 읽기 / Module 3 쓰기)
│   └── style_guide_history.json      # 스타일 변경 이력 누적
│
├── input/                            # 사용자 미디어 업로드 폴더 (watchdog 감시 대상)
│   └── .gitkeep
│
├── logs/                             # 날짜별 로그 저장
│   └── .gitkeep
│
└── tests/
    ├── test_neighbor.py
    ├── test_draft.py
    └── test_style.py
```

---

## 모듈별 실행 흐름 및 주요 함수

### config.py (루트)

```python
from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).parent
INPUT_DIR = BASE_DIR / "input"
DATA_DIR  = BASE_DIR / "data"
LOGS_DIR  = BASE_DIR / "logs"
STYLE_GUIDE_PATH         = DATA_DIR / "style_guide.json"
STYLE_GUIDE_HISTORY_PATH = DATA_DIR / "style_guide_history.json"

class Settings(BaseSettings):
    anthropic_api_key: str
    naver_client_id: str
    naver_client_secret: str
    naver_id: str
    naver_password: str
    claude_model: str = "claude-sonnet-4-6"
    web_host: str = "0.0.0.0"
    web_port: int = 8000
    naver_search_daily_limit: int = 1000  # 보수적 상한 (네이버 API 25,000/일 제한 대비)
    class Config:
        env_file = ".env"
```

---

### core/

#### claude_client.py
```python
class ClaudeClient:
    def call_text(prompt: str, system: str, max_tokens: int) -> str
        # tenacity @retry: rate limit / timeout 자동 재시도
    def call_vision(prompt: str, image_b64_list: list[str], system: str) -> str
        # Base64 이미지 첨부 Claude API 호출
```

#### naver_client.py
```python
class NaverSearchClient:
    def search_blog(query: str, display: int = 100, start: int = 1) -> dict
        # GET https://openapi.naver.com/v1/search/blog.json
```

#### browser.py
```python
class BrowserSession:              # async context manager
    async def __aenter__() -> Page
    async def __aexit__()
    async def naver_login(page: Page) -> None   # Module 1, 2 공유
```

#### logger.py
```python
def setup_logger(module_name: str) -> Logger
    # logs/{module_name}_YYYYMMDD.log 날짜별 로테이션
```

---

### Module 1 — modules/neighbor/

**실행 흐름:**
```
run_module1.py
  └─ runner.run_neighbor_module()
       ├─ searcher.search_food_bloggers(keywords) → list[BloggerInfo]
       ├─ filter.filter_bloggers(bloggers)
       │    ├─ check_recent_activity()      # 최근 30일 포스팅 3개 이상
       │    ├─ check_food_content_ratio()   # 맛집 비중 50%+
       │    └─ check_sponsorship_experience() # 협찬 키워드 탐지
       ├─ automator.add_neighbors_batch(filtered)
       │    └─ BrowserSession → naver_login() → add_neighbor(page, blog_id)
       └─ runner.save_result() → logs/neighbor_YYYYMMDD.json
```

**주요 함수:**
- `searcher.search_food_bloggers(keywords: list[str], display: int) -> list[BloggerInfo]`
- `searcher.extract_blogger_info(items: list[dict]) -> list[BloggerInfo]`
- `filter.filter_bloggers(bloggers: list[BloggerInfo]) -> list[BloggerInfo]`
  - 실행 순서: food_ratio → sponsorship → recent_activity (API 재호출 필요한 조건을 마지막에)
  - 앞 조건 탈락 시 즉시 skip → 불필요한 API 호출 최소화
- `filter.check_food_content_ratio(blogger, threshold=0.5) -> bool`
  - 검색 결과 description 텍스트 분석 → 추가 API 호출 없음
- `filter.check_sponsorship_experience(blogger) -> bool`
  - 검색 결과 title/description 키워드 탐지 → 추가 API 호출 없음
- `filter.check_recent_activity(blogger, days=30, min_posts=3) -> bool`
  - 우선 초기 검색 결과 내 동일 블로거 pubDate로 판단 (재호출 없음)
  - 판단 불가 시에만 NaverSearchClient로 블로거 재검색 (API 1회 추가 소모)
  - 이미 이웃 신청 이력 있는 블로거(logs/ 참조)는 skip
- `automator.add_neighbor(page: Page, blog_id: str) -> bool`
- `automator.add_neighbors_batch(bloggers: list[BloggerInfo]) -> list[NeighborResult]`
- `runner.run_neighbor_module() -> NeighborRunResult`
- `runner.save_result(result, date: str) -> Path`

---

### Module 2 — modules/draft/

**실행 흐름:**
```
run_module2.py
  └─ watcher.start_watching(INPUT_DIR)   # blocking
       └─ InputFolderHandler.on_created(event)
            └─ runner.run_draft_module(file_paths)
                 ├─ media_processor.process_images() → list[ProcessedMedia]
                 │    ├─ resize_image()        # Pillow 1024px
                 │    └─ encode_to_base64()
                 ├─ draft_generator.generate_draft(media_list, style_guide)
                 │    ├─ load_style_guide()
                 │    ├─ build_vision_prompt(style_guide)
                 │    └─ ClaudeClient.call_vision() → 초안 텍스트
                 └─ poster.post_to_naver_blog(title, content, images)
                      ├─ BrowserSession → naver_login()
                      ├─ navigate_to_write_page()
                      ├─ fill_title_and_content()
                      ├─ upload_images()
                      └─ set_visibility_private()  # "나만보기"로 발행
```

**주요 함수:**
- `watcher.InputFolderHandler(FileSystemEventHandler).on_created(event)`
- `watcher.start_watching(input_dir: Path) -> None`
- `media_processor.process_images(file_paths: list[Path]) -> list[ProcessedMedia]`
- `media_processor.resize_image(path: Path, max_size=1024) -> bytes`
- `media_processor.encode_to_base64(image_bytes: bytes, media_type: str) -> str`
- `draft_generator.generate_draft(media_list, style_guide: dict) -> str`
- `draft_generator.load_style_guide() -> dict`
- `draft_generator.build_vision_prompt(style_guide: dict) -> str`
- `poster.post_to_naver_blog(title: str, content: str, image_paths: list[Path]) -> str`
- `poster.set_visibility_private(page: Page) -> None`
- `runner.run_draft_module(file_paths: list[Path]) -> DraftResult`

지원 확장자: `.jpg`, `.jpeg`, `.png`, `.webp`

---

### Module 3 — modules/style/

**실행 흐름:**
```
[tmux 세션에서 서버 상시 실행]
run_module3.py
  └─ uvicorn으로 web_app.py (FastAPI) 구동 → http://localhost:8000

[사용자가 브라우저에서 접속]
GET /
  └─ templates/index.html 반환 (피드백 textarea + 제출 버튼)

POST /feedback  {"feedback": "도입부가 너무 딱딱해"}
  └─ runner.run_style_module(feedback)
       ├─ style_updater.load_current_guide() → dict
       ├─ style_updater.update_style_guide(feedback, current_guide) → dict
       │    ├─ build_update_prompt(feedback, current_guide)
       │    └─ ClaudeClient.call_text() → JSON 파싱 → new_guide
       ├─ style_updater.save_guide(new_guide)   # atomic write
       └─ history_manager.save_to_history(old, new, feedback)
            └─ style_guide_history.json에 entry 추가
  └─ JSON 응답 반환: {success, diff_summary, updated_at}
```

**web_app.py 라우트:**
```python
GET  /            → index.html (피드백 입력 폼)
POST /feedback    → {"feedback": str} 수신 → run_style_module() 호출
GET  /history     → style_guide_history.json 목록 반환 (최근 N건)
GET  /guide       → 현재 style_guide.json 내용 반환
```

**index.html 구성 (단일 페이지):**
- 피드백 텍스트 입력 textarea
- 제출 버튼 → fetch POST /feedback
- 처리 결과 (diff_summary) 인라인 표시
- 현재 스타일 가이드 요약 표시 (GET /guide)

**주요 함수:**
- `web_app.py`: FastAPI 앱 인스턴스, Jinja2 템플릿 마운트
- `style_updater.load_current_guide() -> dict`
- `style_updater.update_style_guide(feedback: str, current_guide: dict) -> dict`
- `style_updater.build_update_prompt(feedback: str, current_guide: dict) -> str`
- `style_updater.save_guide(new_guide: dict) -> None`  — tmp 파일 → rename (atomic)
- `history_manager.save_to_history(old_guide, new_guide, feedback: str) -> None`
- `history_manager.load_history() -> list[HistoryEntry]`
- `runner.run_style_module(feedback: str) -> StyleUpdateResult`

**HistoryEntry 구조:** `{timestamp, feedback, old_guide, new_guide, diff_summary}`

**tmux 백그라운드 실행 방법:**
```bash
# 최초 실행: tmux 세션 생성 후 서버 시작
tmux new -s blog_style
python run_module3.py          # uvicorn 서버 시작 (http://localhost:8000)
Ctrl+b, d                      # 세션 분리 → 터미널 닫아도 서버 유지

# 재접속
tmux attach -t blog_style

# 세션 목록 확인
tmux ls
```

---

## data/style_guide.json 초기 구조

```json
{
  "version": "1.0",
  "created_at": "2026-02-19T00:00:00",
  "updated_at": "2026-02-19T00:00:00",
  "tone": {
    "overall": "친근하고 솔직한 후기 스타일",
    "formality": "반말 (해체형)",
    "energy": "활발하고 긍정적"
  },
  "structure": {
    "intro": {
      "style": "장소 방문 계기나 에피소드로 시작",
      "length": "2-3문장"
    },
    "body": {
      "sections": ["분위기/인테리어", "메뉴 소개", "맛 평가", "가격/가성비", "서비스"],
      "style": "각 섹션별 소제목 사용",
      "length_per_section": "3-5문장"
    },
    "conclusion": {
      "style": "재방문 의사 및 추천 대상 언급으로 마무리",
      "length": "2-3문장"
    }
  },
  "vocabulary": {
    "preferred_expressions": ["진짜 맛있어", "강추", "꼭 가봐"],
    "avoid_expressions": ["맛있었습니다", "좋았습니다", "방문했습니다"]
  },
  "hashtags": {
    "count": 10,
    "always_include": ["#맛집", "#서울맛집"],
    "style": "한글 태그 위주, 영어 태그 최소화"
  },
  "formatting": {
    "use_emoji": true,
    "emoji_frequency": "섹션당 1-2개",
    "line_breaks": "단락 사이 1줄 공백",
    "bold_usage": "메뉴명, 가격, 중요 포인트"
  },
  "image_placement": {
    "order": "분위기 → 메뉴 → 디저트/음료 → 영수증",
    "caption_style": "짧고 감성적인 한 줄 설명"
  },
  "metadata": {
    "target_length_chars": 800,
    "language": "한국어",
    "blog_category": "맛집리뷰"
  }
}
```

---

## 모듈 간 의존성

```
core/ (claude_client, naver_client, browser, logger)
  ├── Module 1 (neighbor)  →  naver_client + browser
  ├── Module 2 (draft)     →  claude_client + browser
  │                            읽기: data/style_guide.json
  └── Module 3 (style)     →  claude_client
                               읽기/쓰기: data/style_guide.json
                               누적 쓰기: data/style_guide_history.json

Module 1 ↔ Module 2,3: 완전 독립 (공유 데이터 없음)
Module 3 → Module 2: style_guide.json을 통한 단방향 흐름
```

---

## 구현 순서 (Phase)

| Phase | 내용 | 비고 |
|---|---|---|
| 1 | `requirements.txt`, `config.py`, `core/` 4개 파일, `data/style_guide.json` | 선행 필수 |
| 2 | Module 3 (`modules/style/`), `run_module3.py`, `templates/index.html` | FastAPI 웹 UI, tmux 백그라운드 실행 |
| 3 | Module 2 (`modules/draft/`), `run_module2.py` | 핵심 기능, Playwright 포스팅 난이도 최고 |
| 4 | Module 1 (`modules/neighbor/`), `run_module1.py` | 독립 기능 |
| 5 | `scheduler.py`, 통합 테스트 | 마무리 |

---

## requirements.txt 최종 구성

```
# AI
anthropic

# 이미지 처리
Pillow

# 브라우저 자동화
playwright

# HTTP / 네이버 API
requests
httpx

# 폴더 감시
watchdog

# 스케줄러
apscheduler

# 웹 서버 (Module 3 UI)
fastapi
uvicorn[standard]
jinja2
python-multipart

# 설정 관리
python-dotenv
pydantic
pydantic-settings

# 유틸리티
aiofiles
loguru
tenacity
```

제거 항목: `openai`, `selenium`, `webdriver-manager`

---

## 코딩 규칙

- Python 3.11 타겟
- PEP 8, 4-space 들여쓰기, 최대 100자
- 모든 public 함수에 type hint + Google style docstring
- f-string 우선 사용
- bare `except:` 금지 — 항상 구체적인 예외 타입 지정
- `print()` 대신 `logging` / `loguru` 사용
- API 키 하드코딩 금지 — 항상 `.env` + `config.py`에서 로드
- 각 모듈은 `run_moduleN.py`로 독립 실행 가능해야 함
