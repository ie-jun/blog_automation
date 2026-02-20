# 블로그 자동화 (Blog Automation)

네이버 맛집 블로그 운영을 반자동화하는 시스템. 3개의 독립 모듈로 구성됩니다.

---

## 프로젝트 개요

| 모듈 | 설명 | 트리거 |
|---|---|---|
| Module 1 | 이웃 추가 자동화 | 매일 1회 자동 (APScheduler) |
| Module 2 | 블로그 초안 자동 작성 | `input/` 폴더 파일 감지 (watchdog) |
| Module 3 | 스타일 가이드 업데이트 | 웹 UI (FastAPI + tmux 백그라운드) |

---

## 기술 스택

| 분류 | 기술 |
|---|---|
| AI / LLM | Anthropic Claude Vision (`claude-sonnet-4-6`) |
| 브라우저 자동화 | Playwright |
| 폴더 감시 | watchdog |
| 스케줄러 | APScheduler |
| 웹 서버 | FastAPI + Uvicorn |
| 설정 관리 | pydantic-settings + python-dotenv |
| 로깅 | loguru |
| 크롤링 (Module 3 URL 분석) | httpx + BeautifulSoup4 (1차) → Playwright 폴백 (2차) |

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

### 3. 환경변수 설정

루트 디렉토리에 `.env` 파일 생성:

```env
ANTHROPIC_API_KEY=sk-ant-...
NAVER_CLIENT_ID=...
NAVER_CLIENT_SECRET=...
NAVER_ID=your_naver_id
NAVER_PASSWORD=your_naver_password
```

> `.env` 파일은 `.gitignore`에 등록되어 있어 git에 커밋되지 않습니다.

---

## 실행 방법

### Module 1 — 이웃 추가 (수동 1회 실행)

```bash
python run_module1.py
```

### Module 2 — 블로그 초안 작성 (폴더 감시 시작)

```bash
python run_module2.py
# 사용법: input/ 하위에 게시글별 서브폴더를 생성하고 이미지(.jpg/.jpeg/.png/.webp)를 넣은 뒤,
#         done.txt 파일을 추가하면 초안이 자동 생성되어 '나만보기'로 포스팅됩니다.
# 예시:
#   mkdir input/을지로_카페_250220
#   cp *.jpg input/을지로_카페_250220/
#   touch input/을지로_카페_250220/done.txt
```

### Module 3 — 스타일 가이드 웹 UI (tmux 백그라운드 실행)

```bash
tmux new -s blog_style
python run_module3.py    # http://localhost:8000 접속
# Ctrl+b, d 로 세션 분리 (서버 유지)
```

### 자동 스케줄러 (Module 1 매일 자동 실행)

```bash
python scheduler.py
```

---

## 주의사항

- 네이버 자동 로그인 시 **2차 인증(OTP)은 비활성화** 하거나 자동화 전용 서브 계정 사용 권장
- 네이버 보안 정책에 따라 간헐적으로 **CAPTCHA** 가 발생할 수 있음
- 이웃 신청은 일일 상한 20건으로 제한 (계정 제재 방지)
- API 키는 절대 git에 커밋하지 않도록 주의
