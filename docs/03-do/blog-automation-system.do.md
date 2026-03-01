# 네이버 맛집 블로그 자동화 시스템 Implementation Guide

> **Summary**: 3모듈(이웃 신청 / 초안 생성 / 스타일 관리) Python 자동화 시스템 구현 가이드
>
> **Project**: blog-automation-system
> **Author**: yejun
> **Date**: 2026-02-20
> **Status**: In Progress
> **Design Doc**: [blog-automation-system.design.md](../02-design/features/blog-automation-system.design.md)

---

## 1. 사전 체크리스트

### 1.1 문서 확인

- [ ] Plan 문서 확인: `docs/01-plan/features/blog-automation-system.plan.md`
- [ ] Design 문서 확인: `docs/02-design/features/blog-automation-system.design.md`
- [ ] CLAUDE.md 규칙 숙지 (Python 3.11, PEP 8, type hints, Google docstring)

### 1.2 환경 준비

- [ ] Python 3.11 설치 확인 (`python3 --version`)
- [ ] 가상환경 생성 및 활성화
- [ ] `.env` 파일 생성 (`.env.example` 참고)
- [ ] 필수 환경변수 설정 완료

```bash
# 가상환경
python3.11 -m venv .venv
source .venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# Playwright 브라우저 설치
playwright install chromium
```

### 1.3 필수 환경변수 (.env)

```dotenv
ANTHROPIC_API_KEY=
CLAUDE_MODEL=claude-sonnet-4-6

NAVER_CLIENT_ID=
NAVER_CLIENT_SECRET=
NAVER_ID=
NAVER_PW=

NEIGHBOR_ADD_DAILY_LIMIT=20
NEIGHBOR_SEARCH_KEYWORD=맛집

INPUT_DIR=input
STYLE_GUIDE_PATH=data/style_guide.json
STYLE_HISTORY_PATH=data/style_guide_history.json
URL_ANALYSIS_SESSION_TTL=600

LOG_DIR=logs
```

---

## 2. 구현 순서

Design 문서 `9. 구현 순서`(Phase 1 → 6) 기준으로 진행합니다.

### Phase 1 — 공유 인프라 (core/)  `우선순위: P0`

| 순서 | 작업 | 파일 | 상태 |
|:---:|------|------|:---:|
| 1 | requirements.txt 정리 | `requirements.txt` | ☐ |
| 2 | 중앙 설정 | `config.py` | ☐ |
| 3 | Claude API 클라이언트 | `core/claude_client.py` | ☐ |
| 4 | 네이버 Open API 래퍼 | `core/naver_client.py` | ☐ |
| 5 | Playwright 브라우저 세션 | `core/browser.py` | ☐ |
| 6 | loguru 로거 | `core/logger.py` | ☐ |
| 7 | 스타일 가이드 초기값 | `data/style_guide.json` | ☐ |
| 8 | 디렉토리 생성 | `input/`, `logs/`, `data/` | ☐ |

### Phase 2 — Module 3: 스타일 가이드 웹 UI  `우선순위: P1`

| 순서 | 작업 | 파일 | 상태 |
|:---:|------|------|:---:|
| 9 | 스타일 가이드 CRUD | `modules/style/style_manager.py` | ☐ |
| 10 | FastAPI 앱 초기화 | `modules/style/app.py` | ☐ |
| 11 | API 라우트 (피드백/이력) | `modules/style/routes.py` | ☐ |
| 12 | 웹 UI | `templates/index.html` | ☐ |
| 13 | M3 실행 스크립트 | `run_module3.py` | ☐ |

### Phase 3 — Module 2: 초안 자동 생성  `우선순위: P0`

| 순서 | 작업 | 파일 | 상태 |
|:---:|------|------|:---:|
| 14 | input/ watchdog 감시 | `modules/draft/watcher.py` | ☐ |
| 15 | 이미지 로드 + vision 분석 | `modules/draft/image_processor.py` | ☐ |
| 16 | 초안 텍스트 생성 | `modules/draft/draft_generator.py` | ☐ |
| 17 | SmartEditor 포스팅 | `modules/draft/poster.py` | ☐ |
| 18 | M2 실행 스크립트 | `run_module2.py` | ☐ |

### Phase 4 — Module 1: 이웃 추가 자동화  `우선순위: P1`

| 순서 | 작업 | 파일 | 상태 |
|:---:|------|------|:---:|
| 19 | 이웃 블로거 검색 | `modules/neighbor/searcher.py` | ☐ |
| 20 | 조건 필터링 | `modules/neighbor/filter.py` | ☐ |
| 21 | 이웃 신청 실행 | `modules/neighbor/adder.py` | ☐ |
| 22 | M1 실행 스크립트 | `run_module1.py` | ☐ |

### Phase 5 — 스케줄러 + 테스트  `우선순위: P2`

| 순서 | 작업 | 파일 | 상태 |
|:---:|------|------|:---:|
| 23 | APScheduler M1 스케줄 | `scheduler.py` | ☐ |
| 24 | Unit 테스트 | `tests/test_filter.py`, `tests/test_style_manager.py` | ☐ |
| 25 | Integration 테스트 | `tests/test_routes.py` | ☐ |

### Phase 6 — Module 3 확장: URL 스타일 분석  `우선순위: P2`

| 순서 | 작업 | 파일 | 상태 |
|:---:|------|------|:---:|
| 26 | URL 크롤링 + 스타일 추출 | `modules/style/url_analyzer.py` | ☐ |
| 27 | URL 분석 라우트 3개 추가 | `modules/style/routes.py` (수정) | ☐ |
| 28 | 웹 UI URL 분석 섹션 추가 | `templates/index.html` (수정) | ☐ |

---

## 3. 생성할 파일 목록

```
blog_automation/
├── config.py
├── requirements.txt                  ← 수정
├── run_module1.py
├── run_module2.py
├── run_module3.py
├── scheduler.py
├── core/
│   ├── __init__.py
│   ├── claude_client.py
│   ├── naver_client.py
│   ├── browser.py
│   └── logger.py
├── modules/
│   ├── neighbor/
│   │   ├── __init__.py
│   │   ├── searcher.py
│   │   ├── filter.py
│   │   └── adder.py
│   ├── draft/
│   │   ├── __init__.py
│   │   ├── watcher.py
│   │   ├── image_processor.py
│   │   ├── draft_generator.py
│   │   └── poster.py
│   └── style/
│       ├── __init__.py
│       ├── app.py
│       ├── routes.py
│       ├── style_manager.py
│       └── url_analyzer.py           ← Phase 6
├── data/
│   ├── style_guide.json
│   └── style_guide_history.json
├── input/                            ← 빈 디렉토리 (gitkeep)
├── logs/                             ← 빈 디렉토리 (gitkeep)
├── templates/
│   └── index.html
└── tests/
    ├── __init__.py
    ├── test_filter.py
    ├── test_style_manager.py
    └── test_routes.py
```

---

## 4. 의존성 (requirements.txt)

```
# Anthropic
anthropic>=0.40.0

# 브라우저 자동화
playwright>=1.40.0

# 네이버 API / HTTP
httpx>=0.27.0
beautifulsoup4>=4.12.0

# FastAPI (M3)
fastapi>=0.115.0
uvicorn[standard]>=0.30.0

# 파일 감시 (M2)
watchdog>=4.0.0

# 스케줄러 (M1)
apscheduler>=3.10.0

# 유틸리티
python-dotenv>=1.0.0
tenacity>=8.2.0
loguru>=0.7.0
```

---

## 5. 구현 주의사항

### 5.1 핵심 설계 결정 준수

| 결정 | 내용 |
|------|------|
| 포스팅 공개 여부 | 항상 **나만보기** 저장 — 절대 자동 공개 금지 |
| 이웃 신청 한도 | 일 **20건** 초과 시 즉시 중단 |
| Claude 모델 | `config.py`의 `CLAUDE_MODEL`에서만 참조 — 코드에 하드코딩 금지 |
| 로깅 | `print()` 사용 금지 — `core/logger.py`의 loguru만 사용 |

### 5.2 Python 코딩 규칙 (CLAUDE.md 기준)

- [ ] 모든 함수/클래스에 **type hints** 필수
- [ ] **Google style docstring** 작성
- [ ] 최대 라인 길이 **100자**
- [ ] `bare except:` 금지 — 구체적 예외 타입 명시
- [ ] f-string 우선 사용

### 5.3 오류 처리 패턴

```python
# Claude API 재시도 예시
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def call_claude(self, prompt: str) -> str:
    ...
```

### 5.4 피해야 할 것

- [ ] API 키 하드코딩 — 반드시 `config.py` or 환경변수 사용
- [ ] 동기 Playwright 코드에서 async 혼용 주의
- [ ] `done.txt` 중복 처리 — `processed/` 이동 로직 필수
- [ ] SmartEditor selector 단일 의존 — 2단계 폴백 구현

---

## 6. 모듈별 실행 확인

```bash
# Module 3 (FastAPI 서버)
python run_module3.py
# → http://127.0.0.1:8000 에서 스타일 가이드 UI 확인

# Module 2 (watchdog 감시)
python run_module2.py
# → input/테스트게시글/ 폴더 생성 후 이미지 + done.txt 추가로 테스트

# Module 1 (이웃 신청 1회 실행)
python run_module1.py

# 스케줄러
python scheduler.py
```

---

## 7. 테스트 체크리스트

### 7.1 수동 E2E 테스트 (M2 핵심)

- [ ] `input/강남스시/` 폴더 생성 + 이미지 복사
- [ ] `done.txt` 파일 생성
- [ ] watcher가 감지 → draft_generator 실행 확인 (로그)
- [ ] 네이버 블로그 "나만보기" 포스팅 확인

### 7.2 pytest 자동 테스트

```bash
pytest tests/ -v
```

- [ ] `test_filter.py`: 이웃 신청 필터 조건 검증
- [ ] `test_style_manager.py`: 스타일 가이드 CRUD + 이력 저장
- [ ] `test_routes.py`: FastAPI 엔드포인트 응답 검증

---

## 8. 구현 완료 후

모든 Phase 구현 및 테스트 완료 시 Gap Analysis 실행:

```
/pdca analyze blog-automation-system
```

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-02-20 | Initial do guide | yejun |
