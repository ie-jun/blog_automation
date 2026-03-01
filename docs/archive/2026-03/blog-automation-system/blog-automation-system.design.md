# 네이버 맛집 블로그 자동화 시스템 Design Document

> **Summary**: 네이버 맛집 블로그 운영의 반복 작업(이웃 신청 / 초안 생성 / 스타일 관리)을 자동화하는 3모듈 Python 시스템
>
> **Project**: blog-automation-system
> **Version**: 0.2
> **Author**: yejun
> **Date**: 2026-02-20
> **Status**: Updated
> **Planning Doc**: [blog-automation-system.plan.md](../../01-plan/features/blog-automation-system.plan.md)

---

## 1. Overview

### 1.1 Design Goals

- 3개의 독립 모듈(이웃 신청 / 초안 생성 / 스타일 관리)이 공통 `core/` 인프라를 공유하는 모듈형 아키텍처 구성
- 각 모듈은 독립 실행 가능하며 상호 의존성 최소화
- Anthropic Claude API(vision + text)를 단일 클라이언트(`core/claude_client.py`)를 통해 사용
- Playwright 기반 브라우저 자동화로 네이버 SmartEditor 구조 변경에 유연하게 대응
- 모든 작업 결과는 JSON 로그로 기록하여 추적 가능

### 1.2 Design Principles

- **Single Responsibility**: 각 모듈은 하나의 자동화 작업만 담당
- **Shared Core**: 공통 기능(Claude, Naver API, Playwright, Logger)은 `core/`에서 중앙 관리
- **Fail-Safe**: 모든 네이버 API/Playwright 호출에 재시도 및 rate limit 대응
- **나만보기 원칙**: M2 자동 포스팅은 항상 "나만보기" 저장 — 수동 검토 후 공개
- **Config-driven**: 모델명, API 키, 한도 설정은 환경변수 + `config.py`(`pydantic-settings`)에서 관리

---

## 2. Architecture

### 2.1 전체 구조 다이어그램

```
blog_automation/
│
├── core/                          # 공유 인프라 (모든 모듈 공통)
│   ├── __init__.py
│   ├── claude_client.py           # Anthropic SDK 클라이언트 (text + vision)
│   ├── naver_client.py            # 네이버 Open API 래퍼
│   ├── browser.py                 # Playwright 브라우저 세션 + 네이버 로그인
│   └── logger.py                  # loguru 날짜별 로테이션 로거
│
├── modules/
│   ├── __init__.py
│   ├── neighbor/                  # M1: 이웃 추가 자동화
│   │   ├── __init__.py
│   │   ├── searcher.py            # 이웃 블로거 검색
│   │   ├── filter.py              # 조건 필터링
│   │   ├── automator.py           # 이웃 신청 실행 (Playwright)
│   │   └── runner.py              # M1 오케스트레이터
│   │
│   ├── draft/                     # M2: 블로그 초안 자동 작성
│   │   ├── __init__.py
│   │   ├── watcher.py             # input/ watchdog 감시
│   │   ├── media_processor.py     # Pillow 이미지 전처리 + Base64 인코딩
│   │   ├── draft_generator.py     # 초안 텍스트 생성
│   │   ├── poster.py              # 네이버 SmartEditor 포스팅
│   │   └── runner.py              # M2 오케스트레이터
│   │
│   └── style/                     # M3: 스타일 가이드 웹 UI + URL 분석
│       ├── __init__.py
│       ├── web_app.py             # FastAPI 앱 정의 + API 라우트
│       ├── style_updater.py       # style_guide.json 업데이트 + 병합
│       ├── history_manager.py     # style_guide_history.json 이력 관리
│       ├── url_analyzer.py        # URL 크롤링 + 스타일 추출
│       ├── runner.py              # M3 오케스트레이터
│       └── templates/
│           └── index.html         # 피드백 입력 + URL 분석 웹 UI (단일 페이지)
│
├── data/
│   ├── style_guide.json            # 현재 스타일 가이드 (M3 → M2 공유)
│   └── style_guide_history.json    # 스타일 변경 이력
│
├── input/                          # M2 트리거 디렉토리
│   └── {게시글명}/                  # 서브폴더 단위 게시글
│       ├── *.jpg / *.png           # 업로드 이미지
│       └── done.txt                # 처리 신호 파일
│
├── output/                         # M2 생성 초안 로컬 저장
│   └── .gitkeep
│
├── logs/
│   ├── neighbor_YYYYMMDD.json      # M1 이웃 신청 로그
│   ├── draft_YYYYMMDD.log          # M2 초안 생성 로그
│   └── style_YYYYMMDD.log          # M3 스타일 관리 로그
│
├── config.py                       # 중앙 설정 (pydantic-settings + pathlib)
├── run_module1.py                  # M1 단독 실행
├── run_module2.py                  # M2 단독 실행
├── run_module3.py                  # M3 단독 실행 (FastAPI uvicorn)
├── scheduler.py                    # APScheduler (M1 자동 스케줄)
└── requirements.txt
```

### 2.2 데이터 흐름

```
[Module 3 웹 UI]
  │ 피드백 / URL 분석
  ▼
data/style_guide.json ──────────────────────────────▶ [Module 2]
                                                          │
input/{게시글명}/done.txt ──▶ watcher.py ──▶ draft_generator.py
                                                          │
                                              claude_client.py (vision+text)
                                                          │
                                              poster.py (Playwright)
                                                          │
                                           네이버 블로그 (나만보기 저장)

[Module 1]  ◀── 완전 독립 ──▶  [Module 2 / 3]
APScheduler ──▶ searcher ──▶ filter ──▶ automator
                                          │
                                  logs/neighbor_YYYYMMDD.json
```

### 2.3 모듈 간 의존성

| 컴포넌트 | 의존 대상 | 방향 |
|---------|---------|------|
| M1 (neighbor/) | core/naver_client, core/browser, core/logger | M1 → core |
| M2 (draft/) | core/claude_client, core/browser, core/logger, data/style_guide.json | M2 → core, M3 산출물 |
| M3 (style/) | core/claude_client, core/logger | M3 → core |
| scheduler.py | M1 전체 | scheduler → M1 |

---

## 3. Data Model

### 3.1 style_guide.json 스키마

```json
{
  "version": "1.0",
  "created_at": "2026-02-20T00:00:00",
  "updated_at": "2026-02-20T00:00:00",
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

### 3.2 style_guide_history.json 스키마

```json
[
  {
    "timestamp": "2026-02-20T10:00:00Z",
    "feedback": "사용자 피드백 내용",
    "old_guide": { "...이전 가이드..." },
    "new_guide": { "...변경 후 가이드..." },
    "diff_summary": "변경 사항 요약"
  }
]
```

### 3.3 이웃 신청 로그 스키마 (logs/neighbor_YYYYMMDD.json)

```json
{
  "date": "2026-02-20",
  "total_searched": 50,
  "total_requested": 18,
  "daily_limit": 20,
  "entries": [
    {
      "blog_id": "blog123",
      "blog_name": "맛집탐방기",
      "status": "success",
      "reason": null,
      "timestamp": "2026-02-20T09:01:23Z"
    }
  ]
}
```

---

## 4. API Specification (Module 3 - FastAPI)

### 4.1 엔드포인트 목록

| Method | Path | 설명 | Auth |
|--------|------|------|------|
| GET | `/` | 스타일 가이드 웹 UI (피드백 입력 + URL 분석) | 없음 |
| GET | `/guide` | 현재 스타일 가이드 조회 | 없음 |
| POST | `/feedback` | 피드백 제출 → 가이드 업데이트 | 없음 |
| GET | `/history` | 스타일 변경 이력 조회 (최근 N건) | 없음 |
| POST | `/analyze-url` | URL 크롤링 + 스타일 분석 (동기 처리) | 없음 |
| GET | `/analyze-url/status/{session_id}` | 분석 세션 유효성 확인 | 없음 |
| POST | `/apply-style` | 선택 섹션 스타일 가이드 반영 | 없음 |

### 4.2 상세 스펙

#### `POST /feedback`

**Request:**
```json
{
  "feedback": "도입부가 너무 딱딱해요. 더 친근하게 써주세요."
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "diff_summary": "tone.overall 변경: '친근하고 솔직한 후기 스타일' → '편안한 대화체 후기'",
  "updated_at": "2026-02-20T10:00:00Z"
}
```

#### `POST /analyze-url`

**Request:**
```json
{
  "url": "https://blog.naver.com/some_blogger/123456789"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "post_title": "강남 스시 오마카세 방문기",
  "analysis_summary": "친근한 반말체, 섹션별 소제목 사용, 감성적 이미지 캡션",
  "style_sections": {
    "tone": {
      "overall": "솔직 담백한 후기체",
      "formality": "반말",
      "energy": "차분하고 정보 중심",
      "_confidence": 85
    },
    "hashtags": {
      "count": 12,
      "always_include": ["#강남맛집", "#오마카세"],
      "style": "한글 태그 위주",
      "_confidence": 72
    }
  },
  "session_id": "abc123-def456"
}
```

#### `GET /analyze-url/status/{session_id}`

**Response (200 OK):**
```json
{
  "valid": true,
  "expires_in_seconds": 480
}
```

**Error Responses:**
- `404 Not Found`: session_id 없음 또는 TTL(10분) 만료

#### `POST /apply-style`

**Request:**
```json
{
  "session_id": "abc123-def456",
  "selected_sections": ["tone", "hashtags"]
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "applied_sections": ["tone", "hashtags"],
  "diff_summary": "tone.overall 변경, hashtags.always_include 업데이트",
  "updated_at": "2026-02-20T10:05:00Z"
}
```

---

## 5. 핵심 클래스 / 함수 설계

### 5.1 core/claude_client.py

```python
class ClaudeClient:
    """Anthropic Claude API 공통 클라이언트."""

    def __init__(self, model: str = None) -> None: ...

    def call_text(
        self,
        prompt: str,
        system: str,
        max_tokens: int = 2000,
    ) -> str:
        """텍스트 프롬프트로 Claude API 호출. tenacity @retry 적용."""
        ...

    def call_vision(
        self,
        prompt: str,
        image_b64_list: list[str],
        system: str,
    ) -> str:
        """Base64 이미지 리스트를 vision API로 분석."""
        ...
```

### 5.2 core/browser.py

```python
class BrowserSession:
    """Playwright 기반 네이버 브라우저 세션 관리 (async context manager)."""

    async def __aenter__(self) -> Page: ...
    async def __aexit__(self, *args) -> None: ...

    async def naver_login(self, page: Page) -> None:
        """Settings.naver_id / Settings.naver_password로 로그인."""
        ...
```

### 5.3 modules/draft/watcher.py

```python
class InputFolderHandler(FileSystemEventHandler):
    """input/ 디렉토리의 done.txt 생성 이벤트 감시."""

    def on_created(self, event: FileSystemEvent) -> None:
        """done.txt 생성 감지 시 runner.run_draft_module(folder_path) 호출."""
        ...

def start_watching(input_dir: Path) -> None:
    """watchdog Observer 시작 (blocking)."""
    ...
```

### 5.4 modules/draft/draft_generator.py

```python
def load_style_guide() -> dict:
    """data/style_guide.json 로드."""
    ...

def build_vision_prompt(style_guide: dict) -> str:
    """스타일 가이드 기반 vision 프롬프트 구성."""
    ...

def generate_draft(
    media_list: list[ProcessedMedia],
    style_guide: dict,
) -> str:
    """Claude vision으로 이미지 분석 후 스타일 가이드 기반 초안 작성."""
    ...
```

### 5.5 modules/neighbor/filter.py

```python
def filter_bloggers(bloggers: list[BloggerInfo]) -> list[BloggerInfo]:
    """3가지 조건 순차 필터링. API 재호출 필요한 조건을 마지막에 배치."""
    ...

def check_food_content_ratio(blogger: BloggerInfo, threshold: float = 0.5) -> bool:
    """맛집 콘텐츠 비율 확인. 검색 결과 description 분석 (추가 API 호출 없음)."""
    ...

def check_sponsorship_experience(blogger: BloggerInfo) -> bool:
    """협찬 키워드 탐지. title/description 분석 (추가 API 호출 없음)."""
    ...

def check_recent_activity(blogger: BloggerInfo, days: int = 30, min_posts: int = 3) -> bool:
    """최근 활동 확인. 우선 기존 데이터 판단, 불가 시 API 1회 추가 호출."""
    ...
```

### 5.6 modules/neighbor/automator.py

```python
async def add_neighbor(page: Page, blog_id: str) -> bool:
    """Playwright로 개별 이웃 신청."""
    ...

async def add_neighbors_batch(bloggers: list[BloggerInfo]) -> list[NeighborResult]:
    """BrowserSession → naver_login() → 배치 이웃 신청."""
    ...
```

### 5.7 modules/style/style_updater.py

```python
def load_current_guide() -> dict:
    """현재 style_guide.json 로드."""
    ...

def update_style_guide(feedback: str, current_guide: dict) -> dict:
    """Claude API로 피드백 반영한 새 가이드 생성."""
    ...

def build_update_prompt(feedback: str, current_guide: dict) -> str:
    """피드백 업데이트용 프롬프트 구성."""
    ...

def save_guide(new_guide: dict) -> None:
    """tmp 파일 → rename (atomic write)."""
    ...

def merge_extracted_style(
    current_guide: dict,
    extracted_style: dict,
    selected_sections: list[str],
    merge_strategy: str = "selective",
) -> tuple[dict, str]:
    """URL 분석 결과에서 선택된 섹션만 현재 가이드에 병합."""
    ...
```

### 5.8 modules/style/history_manager.py

```python
def save_to_history(old_guide: dict, new_guide: dict, feedback: str) -> None:
    """style_guide_history.json에 변경 이력 추가."""
    ...

def load_history() -> list[HistoryEntry]:
    """전체 변경 이력 로드."""
    ...
```

### 5.9 modules/style/url_analyzer.py

```python
def normalize_naver_blog_url(url: str) -> tuple[str, str, str]:
    """네이버 블로그 URL 정규화 → (mobile_url, blog_id, log_no)."""
    ...

def fetch_post_content(url: str) -> CrawledPost:
    """httpx(1차) → Playwright 폴백(2차)으로 블로그 본문 크롤링."""
    ...

def analyze_style_from_post(
    post: CrawledPost,
    current_guide: dict,
    claude_client: ClaudeClient,
) -> ExtractedStyle:
    """본문(3000자 제한) + 현재 가이드 키 구조 → Claude 스타일 분석."""
    ...

def build_style_extraction_prompt(post: CrawledPost, current_guide: dict) -> str:
    """현재 style_guide 키 구조를 명시하여 동일 구조 + _confidence 포함 응답 유도."""
    ...
```

### 5.10 modules/*/runner.py (각 모듈 오케스트레이터)

```python
# modules/neighbor/runner.py
def run_neighbor_module() -> NeighborRunResult:
    """M1 전체 실행: 검색 → 필터 → 이웃 신청 → 로그 저장."""
    ...

def save_result(result: NeighborRunResult, date: str) -> Path:
    """logs/neighbor_YYYYMMDD.json으로 실행 결과 저장."""
    ...

# modules/draft/runner.py
def run_draft_module(folder_path: Path) -> DraftResult:
    """M2 전체 실행: 이미지 처리 → 초안 생성 → 네이버 포스팅(나만보기)."""
    ...

def save_draft_to_output(content: str, title: str) -> Path:
    """output/<폴더명>_draft_YYYYMMDD_HHMMSS.md로 초안 저장."""
    ...

# modules/style/runner.py
def run_style_module(feedback: str) -> StyleUpdateResult:
    """피드백 기반 스타일 가이드 업데이트."""
    ...

async def run_url_analysis_module(url: str) -> UrlAnalysisResult:
    """URL 크롤링 + 스타일 분석."""
    ...

def run_style_merge_module(
    extracted_style: dict,
    selected_sections: list[str],
    source_url: str,
) -> StyleMergeResult:
    """분석 결과에서 선택 섹션을 가이드에 반영."""
    ...
```

---

## 6. 오류 처리 전략

### 6.1 재시도 정책

| 대상 | 전략 | 설정 |
|------|------|------|
| Claude API 호출 | `tenacity` @retry | 최대 3회, wait_exponential(min=2, max=10) |
| 네이버 Open API | `tenacity` @retry | 최대 3회, wait_fixed(1) |
| Playwright 액션 | try/except + 폴백 selector | SmartEditor selector 2단계 폴백 |
| URL 크롤링 | httpx(1차) → Playwright(2차) | ConnectionError 시 자동 폴백 |

### 6.2 주요 예외 처리

| 예외 상황 | 처리 방법 |
|---------|---------|
| 네이버 로그인 CAPTCHA | `NaverLoginError` raise → 로그 기록 후 종료 |
| Claude rate limit | `anthropic.RateLimitError` → tenacity 재시도 |
| done.txt 중복 감지 | `processed/` 폴더로 이동 후 skip |
| 일일 이웃 신청 한도 초과 | `DailyLimitReachedError` → 로그 기록 후 중단 |
| URL 분석 세션 만료(TTL 10분) | 404 반환 + 재분석 유도 메시지 |

---

## 7. 보안 고려사항

- [ ] NAVER_ID, NAVER_PASSWORD, ANTHROPIC_API_KEY 환경변수로만 관리 (`pydantic-settings` + `python-dotenv`)
- [ ] `.env` `.gitignore` 등록 필수
- [ ] 이웃 신청 일일 상한 20건 기본값 + config 오버라이드 가능
- [ ] FastAPI 서버는 `0.0.0.0` 바인딩 (tmux 세션에서 백그라운드 실행)
- [ ] URL 분석 세션 인메모리 저장 (외부 노출 없음, TTL 10분)

---

## 8. 테스트 계획

### 8.1 테스트 범위

| 유형 | 대상 | 도구 |
|------|------|------|
| Unit | `filter.py`, `style_updater.py`, `history_manager.py`, `draft_generator.py` | pytest |
| Integration | FastAPI 라우트 (`/feedback`, `/analyze-url`, `/apply-style`) | pytest + httpx |
| E2E (수동) | M2 전체 파이프라인: done.txt → 초안 생성 → 나만보기 포스팅 | Playwright 브라우저 확인 |

### 8.2 핵심 테스트 케이스

- [ ] Happy path: `input/강남스시/done.txt` 생성 → 초안 생성 → 나만보기 포스팅 완료
- [ ] 피드백 제출 → `style_guide.json` 변경 + `style_guide_history.json` 이력 1건 추가
- [ ] URL 분석: 공개 블로그 URL → 섹션 추출 → 선택 적용 → 가이드 반영
- [ ] 이웃 신청 한도 도달 시 자동 중단 + 로그 기록
- [ ] Claude API 에러 → 재시도 3회 후 로그 기록

---

## 9. 구현 순서 (Plan 4. Implementation Phases 기반)

| Phase | 작업 | 파일 |
|:-----:|------|------|
| 1 | `requirements.txt` 정리, `config.py`, `core/` 4개 파일, `data/style_guide.json` 초기화 | core/ 전체 |
| 2 | Module 3: FastAPI 앱, 스타일 피드백 API, 웹 UI | modules/style/, run_module3.py |
| 3 | Module 2: watchdog, 초안 생성, Playwright 포스팅 | modules/draft/, run_module2.py |
| 4 | Module 1: 이웃 검색, 필터링, 신청 | modules/neighbor/, run_module1.py |
| 5 | scheduler.py (APScheduler M1 스케줄), tests/ 작성 | scheduler.py, tests/ |
| 6 | Module 3 확장: URL 스타일 분석 (url_analyzer.py, 라우트 추가, UI 추가) | modules/style/url_analyzer.py |

---

## 10. config.py 설계

```python
# config.py
from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).parent
INPUT_DIR = BASE_DIR / "input"
DATA_DIR  = BASE_DIR / "data"
LOGS_DIR  = BASE_DIR / "logs"
STYLE_GUIDE_PATH         = DATA_DIR / "style_guide.json"
STYLE_GUIDE_HISTORY_PATH = DATA_DIR / "style_guide_history.json"

class Settings(BaseSettings):
    """환경변수 기반 설정. .env 파일에서 자동 로드."""

    # Anthropic
    anthropic_api_key: str

    # Naver
    naver_client_id: str
    naver_client_secret: str
    naver_id: str
    naver_password: str

    # Model
    claude_model: str = "claude-sonnet-4-6"

    # Web Server (Module 3)
    web_host: str = "0.0.0.0"
    web_port: int = 8000

    # Module 1 Limits
    naver_search_daily_limit: int = 1000
    neighbor_add_daily_limit: int = 20

    class Config:
        env_file = ".env"
```

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-02-20 | Initial design — 3모듈 아키텍처, API 스펙, 데이터 모델 | yejun |
| 0.2 | 2026-02-28 | 실제 구현 반영 — 파일명, API 라우트, 데이터 모델, 클래스/함수 시그니처, config.py 전면 업데이트 | yejun |
