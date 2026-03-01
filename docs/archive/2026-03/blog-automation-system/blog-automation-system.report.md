# 네이버 맛집 블로그 자동화 시스템 — 완료 보고서

> **Feature**: blog-automation-system
> **Report Date**: 2026-03-01
> **Match Rate**: 93% (PASSED, threshold 90%)
> **Test Result**: 47/47 PASSED (100%)
> **PDCA Phase**: Completed
> **Iteration Count**: 1

---

## 1. 요약

네이버 맛집 블로그 운영의 3대 반복 작업(이웃 신청 / 초안 생성 / 스타일 관리)을 자동화하는
Python 시스템을 완성했다. PDCA Check에서 발견된 3가지 핵심 이슈를 Iteration 1에서 모두 해결하여
Match Rate 74% → 93%로 개선, 90% 기준을 통과했다.

| 항목 | 결과 |
|------|------|
| 총 테스트 수 | **47개** |
| 통과 | **47개 (100%)** |
| 실패 | 0개 |
| Match Rate | **93%** (74% → 93%, +19pp) |
| Iteration | 1회 (최대 5회 중) |
| 총 코드 라인 | ~2,250줄 (production) |
| 핵심 기능 구현율 | **19/19 (100%)** |

---

## 2. PDCA Cycle 요약

```
[Plan] ✅ → [Design] ✅ → [Do] ✅ → [Check] ✅ → [Act] ✅ → [Report] ✅
```

| Phase | 날짜 | 산출물 | 핵심 내용 |
|-------|------|--------|---------|
| Plan | 2026-02-20 | `blog-automation-system.plan.md` | 3모듈 시스템 설계, 6단계 구현 로드맵, 7대 리스크 식별 |
| Design | 2026-02-20 | `blog-automation-system.design.md` v0.1 | 아키텍처, API 스펙, 데이터 모델, 클래스 설계 |
| Do | 2026-02-20~28 | 전체 구현 코드 | core/ 4파일 + 3모듈 15파일 + 진입점 4파일 |
| Check | 2026-02-28 | `blog-automation-system.analysis.md` v0.1 | Match Rate 74%, 3가지 Critical/Major 이슈 식별 |
| Act | 2026-02-28~03-01 | poster.py retry + 17 tests + design v0.2 | Match Rate 93% 달성 |
| Report | 2026-03-01 | 이 문서 | 완료 보고서 |

---

## 3. 구현 완료 항목

### 3.1 공유 인프라 (`core/`)

| 파일 | 역할 | 상태 |
|------|------|:----:|
| `config.py` | pydantic-settings 중앙 설정 (25개 파라미터) | ✅ |
| `core/claude_client.py` | Anthropic SDK 클라이언트 (text + vision, tenacity retry) | ✅ |
| `core/naver_client.py` | 네이버 Open API 래퍼 (search_blog, retry) | ✅ |
| `core/browser.py` | Playwright BrowserSession + 네이버 JS 로그인 | ✅ |
| `core/logger.py` | loguru 날짜별 로테이션 (모듈별 독립 파일 핸들러) | ✅ |

### 3.2 Module 1 — 이웃 추가 자동화 (`modules/neighbor/`)

| 파일 | 역할 | 테스트 |
|------|------|:------:|
| `searcher.py` | 네이버 맛집 블로거 검색 + 중복 제거 + pubDate 수집 | 4개 |
| `filter.py` | 음식 비율/협찬 키워드/최근 활동 3단계 필터링 (API 절약 순) | 6개 |
| `automator.py` | Playwright 이웃 신청 (3-selector fallback, 일일 20건 제한) | - |
| `runner.py` | M1 오케스트레이터 + JSON 로그 저장 | - |

### 3.3 Module 2 — 초안 자동 생성 (`modules/draft/`)

| 파일 | 역할 | 테스트 |
|------|------|:------:|
| `watcher.py` | input/ watchdog 감시 (done.txt 신호 → asyncio 브릿지) | - |
| `media_processor.py` | Pillow 리사이즈(1024px) + Base64 인코딩 | 10개 |
| `draft_generator.py` | Claude Vision API → 스타일 가이드 기반 초안 | 5개 |
| `poster.py` | Playwright SmartEditor 포스팅 (나만보기) + `_retry_async()` | 12개 |
| `runner.py` | M2 오케스트레이터 (이미지 → 초안 → 포스팅 → done.txt 이동) | 2개 |

### 3.4 Module 3 — 스타일 가이드 웹 UI (`modules/style/`)

| 파일 | 역할 | 테스트 |
|------|------|:------:|
| `web_app.py` | FastAPI 앱 + 7개 라우트 + 세션 캐시 | - |
| `style_updater.py` | style_guide.json CRUD + Claude 피드백 반영 + atomic write | 4개 |
| `history_manager.py` | 스타일 변경 이력 JSON 배열 누적 | 4개 |
| `url_analyzer.py` | httpx(1차) + Playwright(2차) 크롤링 + Claude 스타일 추출 | - |
| `runner.py` | M3 오케스트레이터 (피드백/URL분석/스타일병합) | - |
| `templates/index.html` | 단일 페이지 웹 UI (피드백 + URL 분석 3단계 상태머신) | - |

---

## 4. Iteration 1 수정 사항

### 4.1 poster.py Playwright 재시도 로직 추가 (Critical)

**문제**: Playwright 액션에 재시도 로직이 없어 네이버 페이지 로딩 불안정 시 전체 파이프라인 실패.

**해결**: `_retry_async()` 헬퍼 함수 추가.

```python
async def _retry_async(coro_factory, description, max_retries=3, delay=2):
    """Exponential backoff (delay * attempt) 재시도."""
    for attempt in range(1, max_retries + 1):
        try:
            return await coro_factory()
        except Exception as exc:
            if attempt < max_retries:
                await asyncio.sleep(delay * attempt)
            else:
                raise
```

적용 대상: `_fill_title`, `_fill_content`, `_set_visibility_private`, `_publish_and_get_url`

### 4.2 테스트 17개 추가 (Major)

**문제**: poster.py, draft_generator.py에 테스트가 전무하여 Critical Path 검증 불가.

**해결**: Mock Playwright + Mock Claude 기반 테스트 17개 추가 (총 29개 → 47개).

| 테스트 클래스 | 테스트 수 | 대상 |
|-------------|:--------:|------|
| `TestBuildVisionPrompt` | 3 | 프롬프트 구성 검증 |
| `TestGenerateDraft` | 2 | Claude Vision mock 호출 + 빈 미디어 에러 |
| `TestFillTitle` | 2 | selector 매칭 + 실패 RuntimeError |
| `TestFillContent` | 2 | selector 매칭 + 에디터 미발견 |
| `TestSetVisibilityPrivate` | 2 | 클릭 + selector 미발견 시 warning |
| `TestPublishAndGetUrl` | 2 | URL 반환 + 버튼 미발견 |
| `TestRetryAsync` | 3 | 즉시 성공 / 재시도 후 성공 / 최대 재시도 초과 |
| `TestPostToNaverBlogIntegration` | 1 | BrowserSession mock 전체 파이프라인 |

### 4.3 설계 문서 v0.2 동기화 (Major)

**문제**: design.md가 CLAUDE.md 확정 전에 작성되어 API 경로, 파일명, 데이터 모델이 구현과 불일치.

**해결**: 설계 문서 전면 업데이트.

| 항목 | Before (v0.1) | After (v0.2) |
|------|--------------|-------------|
| API 경로 | `/api/style/feedback` 등 | `/feedback` 등 (CLAUDE.md 일치) |
| 파일명 | `adder.py`, `image_processor.py` | `automator.py`, `media_processor.py` |
| 클래스명 | `NaverBrowser` | `BrowserSession` |
| 데이터 모델 | 간소한 style_guide.json | 풍부한 10-section 스키마 |
| config | `os.environ` | `pydantic-settings BaseSettings` |

---

## 5. Match Rate 변화

```
┌──────────────────────────┬────────┬────────┬────────┐
│ Category                 │ Before │ After  │ Delta  │
├──────────────────────────┼────────┼────────┼────────┤
│ Core Functionality       │   88%  │  100%  │  +12   │
│ API Route Match          │   43%  │  100%  │  +57   │
│ Data Model Match         │   60%  │   95%  │  +35   │
│ Design Match (naming)    │   68%  │   95%  │  +27   │
│ Error Handling           │   80%  │   90%  │  +10   │
│ Test Coverage            │   45%  │   78%  │  +33   │
│ Critical Path Readiness  │   75%  │   90%  │  +15   │
│ Architecture Compliance  │   92%  │   92%  │    0   │
│ Convention Compliance    │   90%  │   95%  │   +5   │
├──────────────────────────┼────────┼────────┼────────┤
│ Overall (Weighted)       │   74%  │   93%  │  +19   │
└──────────────────────────┴────────┴────────┴────────┘
```

---

## 6. 프로젝트 실행 가이드

### 6.1 환경 설정

#### Step 1 — Python 환경 생성

```bash
conda create -n blog_automation python=3.11
conda activate blog_automation
```

#### Step 2 — 의존성 설치

```bash
cd /Users/hwangyj9/develop_yejun/projects/blog_automation
pip install -r requirements.txt
```

#### Step 3 — Playwright 브라우저 설치 (최초 1회)

```bash
playwright install chromium
```

#### Step 4 — `.env` 파일 생성

```bash
cat > .env << 'EOF'
# === 필수 ===
ANTHROPIC_API_KEY=sk-ant-...          # Anthropic API 키
NAVER_CLIENT_ID=...                    # 네이버 개발자센터 > Open API > Client ID
NAVER_CLIENT_SECRET=...               # 네이버 개발자센터 > Open API > Client Secret
NAVER_ID=your_naver_id                # 네이버 블로그 계정 ID
NAVER_PASSWORD=your_naver_password    # 네이버 블로그 계정 비밀번호

# === 선택 (기본값 있음) ===
CLAUDE_MODEL=claude-sonnet-4-6        # Claude 모델명
NEIGHBOR_ADD_DAILY_LIMIT=20           # 이웃 신청 일일 상한
NAVER_SEARCH_DAILY_LIMIT=1000         # Naver API 검색 일일 한도
WEB_HOST=127.0.0.1                    # Module 3 서버 바인딩 주소
WEB_PORT=8000                         # Module 3 서버 포트
URL_ANALYSIS_SESSION_TTL=600          # URL 분석 세션 TTL (초)
EOF
```

> `.env` 파일은 `.gitignore`에 등록되어 있으며 절대 커밋하지 않는다.

#### Step 5 — 네이버 API 키 발급

1. [네이버 개발자센터](https://developers.naver.com) 접속
2. Application 등록 → "검색" API 사용 선택
3. Client ID / Client Secret 복사 → `.env`에 입력

---

### 6.2 테스트 실행

```bash
conda activate blog_automation
cd /Users/hwangyj9/develop_yejun/projects/blog_automation

# 전체 테스트 (47개)
python -m pytest tests/ -v

# 모듈별 실행
python -m pytest tests/test_draft.py -v      # Module 2 (29개)
python -m pytest tests/test_neighbor.py -v   # Module 1 (10개)
python -m pytest tests/test_style.py -v      # Module 3 (8개)

# 특정 테스트 클래스만
python -m pytest tests/test_draft.py::TestRetryAsync -v
```

**예상 결과:**
```
========================= 47 passed in 6.70s =========================
```

---

### 6.3 Module 2 — 블로그 초안 자동 생성 (핵심 기능)

```bash
# 1. watchdog 서비스 시작 (터미널 1)
python run_module2.py
# → "Watching input/ for done.txt..." 메시지 확인
```

```bash
# 2. 게시글 서브폴더 생성 + 이미지 복사 (터미널 2)
mkdir -p input/강남_스시_오마카세
cp ~/사진/food_*.jpg input/강남_스시_오마카세/

# 3. done.txt 생성 → 자동 트리거
touch input/강남_스시_오마카세/done.txt
```

**자동 실행 흐름:**
```
done.txt 감지
  → 이미지 전처리 (Pillow 1024px + Base64)
  → Claude Vision API로 초안 생성 (style_guide.json 참조)
  → 네이버 블로그 "나만보기" 포스팅
  → output/강남_스시_오마카세_draft_20260301_143000.md 저장
  → done.txt → processed/done.txt 이동 (재처리 방지)
```

**확인:**
```bash
# 생성된 초안 확인
cat output/강남_스시_오마카세_draft_*.md

# 로그 확인
tail -f logs/draft_$(date +%Y%m%d).log
```

---

### 6.4 Module 3 — 스타일 가이드 웹 UI

```bash
# 방법 1: 포그라운드 실행
python run_module3.py
# → http://127.0.0.1:8000 접속

# 방법 2: tmux 백그라운드 실행 (권장)
tmux new -s blog_style
python run_module3.py
# Ctrl+b, d  (세션 분리 → 터미널 닫아도 서버 유지)

# 재접속
tmux attach -t blog_style
```

**웹 UI 기능 (http://127.0.0.1:8000):**

| 섹션 | 기능 | 사용법 |
|------|------|--------|
| 피드백 입력 | 텍스트 피드백 → Claude가 style_guide.json 업데이트 | "도입부가 딱딱해요" 입력 후 제출 |
| URL 분석 | 네이버 블로그 URL → 스타일 추출 → 선택 적용 | URL 붙여넣기 → 분석 → 체크박스 선택 → 적용 |
| 변경 이력 | style_guide.json 변경 타임라인 | 자동 표시 |

**API 엔드포인트:**

| Method | Path | 설명 |
|--------|------|------|
| `GET` | `/` | 웹 UI (index.html) |
| `GET` | `/guide` | 현재 스타일 가이드 JSON 조회 |
| `POST` | `/feedback` | `{"feedback": "..."}` → 가이드 업데이트 |
| `GET` | `/history` | 변경 이력 목록 (최근 20건) |
| `POST` | `/analyze-url` | `{"url": "..."}` → 크롤링 + 스타일 분석 |
| `GET` | `/analyze-url/status/{session_id}` | 세션 유효성 확인 |
| `POST` | `/apply-style` | `{"session_id": "...", "selected_sections": [...]}` → 적용 |

**curl 테스트 예시:**
```bash
# 피드백 제출
curl -X POST http://127.0.0.1:8000/feedback \
  -H "Content-Type: application/json" \
  -d '{"feedback": "도입부를 더 친근하게 써주세요"}'

# 현재 가이드 조회
curl http://127.0.0.1:8000/guide | python -m json.tool

# URL 분석
curl -X POST http://127.0.0.1:8000/analyze-url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://blog.naver.com/example/123456"}'
```

---

### 6.5 Module 1 — 이웃 추가 자동화

```bash
# 1회 수동 실행
python run_module1.py
```

**동작 흐름:**
```
키워드 검색 ("맛집", "서울 맛집", "음식 리뷰")
  → 블로거 목록 수집 (중복 제거)
  → 3단계 필터링 (음식비율 ≥50% → 협찬키워드 없음 → 최근30일 3건+)
  → 이전 신청 이력 확인 (logs/ 참조)
  → Playwright 이웃 신청 (일일 최대 20건)
  → logs/neighbor_YYYYMMDD.json 결과 저장
```

```bash
# 결과 확인
cat logs/neighbor_$(date +%Y%m%d).json | python -m json.tool
```

---

### 6.6 자동 스케줄러 (Module 1 매일 실행)

```bash
# tmux에서 백그라운드 실행 권장
tmux new -s blog_scheduler
python scheduler.py
# → APScheduler가 매일 09:00 KST에 Module 1 자동 실행
# Ctrl+b, d
```

---

### 6.7 데이터 파일 위치

```bash
# 현재 스타일 가이드
cat data/style_guide.json | python -m json.tool

# 스타일 변경 이력
cat data/style_guide_history.json | python -m json.tool

# 생성된 초안 목록
ls -la output/

# 이웃 신청 로그
ls -la logs/neighbor_*.json

# 모듈별 로그
ls -la logs/*.log
```

---

## 7. 아키텍처 최종 구조

```
blog_automation/
├── .env                           # API 키, 계정 정보 (gitignore)
├── config.py                      # pydantic-settings 중앙 설정
│
├── core/                          # 공유 인프라
│   ├── claude_client.py           # Anthropic SDK (text + vision + retry)
│   ├── naver_client.py            # 네이버 검색 API (retry)
│   ├── browser.py                 # Playwright BrowserSession + 네이버 로그인
│   └── logger.py                  # loguru 모듈별 로거
│
├── modules/
│   ├── neighbor/                  # M1: 이웃 추가 자동화
│   │   ├── searcher.py            #   키워드 검색 + 블로거 수집
│   │   ├── filter.py              #   3단계 필터링 (API 절약 순)
│   │   ├── automator.py           #   Playwright 이웃 신청
│   │   └── runner.py              #   M1 오케스트레이터
│   │
│   ├── draft/                     # M2: 초안 자동 생성 (핵심)
│   │   ├── watcher.py             #   watchdog done.txt 감시
│   │   ├── media_processor.py     #   Pillow 리사이즈 + Base64
│   │   ├── draft_generator.py     #   Claude Vision → 초안 텍스트
│   │   ├── poster.py              #   Playwright 네이버 포스팅 + retry
│   │   └── runner.py              #   M2 오케스트레이터
│   │
│   └── style/                     # M3: 스타일 가이드 관리
│       ├── web_app.py             #   FastAPI 앱 + 7개 라우트
│       ├── style_updater.py       #   가이드 CRUD + Claude 반영
│       ├── history_manager.py     #   변경 이력 누적
│       ├── url_analyzer.py        #   URL 크롤링 + 스타일 추출
│       ├── runner.py              #   M3 오케스트레이터
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
├── tests/
│   ├── conftest.py                # 더미 env 주입 + asyncio 설정
│   ├── test_draft.py              # 29개 테스트
│   ├── test_neighbor.py           # 10개 테스트
│   └── test_style.py              # 8개 테스트
│
└── requirements.txt               # 의존성 (20개 패키지)
```

**의존성 방향:**
```
modules/* → core/*    (단방향)
M2 → data/style_guide.json ← M3   (파일 기반 공유)
M1 ↔ M2, M3: 완전 독립
```

---

## 8. 알려진 제약사항 및 향후 개선

| 항목 | 현황 | 우선순위 | 개선 방향 |
|------|------|:--------:|---------|
| 네이버 CAPTCHA | RuntimeError 발생 후 종료 | Medium | 수동 개입 알림 (Slack/Telegram) |
| SmartEditor selector | 3-tier fallback + retry | Low | selector 추상화 레이어 |
| FastAPI 통합 테스트 | 미작성 | Medium | TestClient 기반 라우트 테스트 |
| watcher.py 테스트 | 미작성 | Medium | 이벤트 시뮬레이션 테스트 |
| E2E 테스트 | 수동 검증만 가능 | Low | Playwright test mode E2E |
| 세션 캐시 정리 | 접근 시에만 만료 세션 제거 | Low | FastAPI lifespan 주기적 정리 |

---

## 9. Plan 목표 달성 현황

| ID | Goal | 달성 | 검증 방법 |
|:--:|------|:----:|---------|
| G-01 | core/ 인프라 완성 (4개 파일) | ✅ | 모든 모듈에서 정상 import 확인 |
| G-02 | M2: input/ → 초안 → 나만보기 포스팅 | ✅ | run_module2.py + poster.py 통합 테스트 |
| G-03 | M3: 피드백 → guide 업데이트 → 이력 저장 | ✅ | web_app.py /feedback 라우트 + test_style.py |
| G-04 | M1: 필터링 후 이웃 신청 ≤ 20건 | ✅ | test_neighbor.py 필터 로직 검증 |
| G-05 | scheduler.py: M1 매일 자동 실행 | ✅ | scheduler.py APScheduler 09:00 KST |
| G-06 | M3: URL 분석 → 스타일 추출 → 선택 반영 | ✅ | url_analyzer.py + /analyze-url + /apply-style |

**전체 gap analysis 90%+ 달성: ✅ (93%)**

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-28 | 초기 완료 보고서 — 버그 2건 수정, 30/30 테스트 통과 |
| 2.0 | 2026-03-01 | Iteration 1 반영 — poster retry, 47/47 테스트, design v0.2 동기화, Match Rate 93% |
