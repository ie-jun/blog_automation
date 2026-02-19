# 📸 블로그 자동화 (Blog Automation)

이미지를 업로드하면 **AI가 자동으로 맛집 리뷰 게시글을 작성**하고 **네이버 블로그에 포스팅**해주는 자동화 프로젝트입니다.

---

## 🧭 프로젝트 개요

```
이미지 업로드 → AI 이미지 분석 → 리뷰 텍스트 생성 → 네이버 블로그 자동 포스팅
```

1. 사용자가 음식/맛집 이미지를 FastAPI 서버에 업로드
2. Claude Vision (또는 GPT-4o) 이 이미지를 분석해 맛집 리뷰 글 자동 생성
3. Selenium / Playwright 가 네이버 블로그에 자동 로그인 후 게시글 업로드

---

## 🛠 기술 스택

| 분류 | 기술 |
|------|------|
| **AI / LLM** | Anthropic Claude Vision, OpenAI GPT-4o |
| **이미지 처리** | Pillow, python-multipart |
| **블로그 자동화** | Selenium, Playwright, WebDriver Manager |
| **웹 서버** | FastAPI, Uvicorn |
| **HTTP 클라이언트** | requests, httpx |
| **설정 관리** | python-dotenv, pydantic-settings |
| **유틸리티** | aiofiles, loguru, tenacity |

---

## ⚙️ 환경 설정

### 1. 가상환경 생성 및 활성화

```bash
conda create -n blog_automation python=3.11
conda activate blog_automation
```

### 2. 패키지 설치

```bash
pip install -r requirements.txt
```

### 3. 환경변수 설정

`.env` 파일을 루트 디렉토리에 생성하고 아래 값을 채워넣습니다.

```env
# LLM API Keys
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# 네이버 Open API
NAVER_CLIENT_ID=your_naver_client_id_here
NAVER_CLIENT_SECRET=your_naver_client_secret_here

# 네이버 블로그 로그인 (Selenium 자동화용)
NAVER_ID=your_naver_id_here
NAVER_PASSWORD=your_naver_password_here
```

> ⚠️ `.env` 파일은 `.gitignore`에 등록되어 있어 git에 커밋되지 않습니다.

---

## 🔑 API 키 발급 방법

### Anthropic (Claude)
1. [https://console.anthropic.com](https://console.anthropic.com) 접속
2. API Keys 메뉴에서 키 발급

### OpenAI
1. [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys) 접속
2. `Create new secret key`로 발급

### 네이버 Open API
1. [https://developers.naver.com/apps/#/register](https://developers.naver.com/apps/#/register) 접속
2. 애플리케이션 등록 → 사용 API 선택 (검색, 로그인 등)
3. 환경 WEB 설정 → `http://localhost:8000` 등록
4. Client ID / Client Secret 발급

> 📌 네이버는 **블로그 글쓰기 공식 API를 제공하지 않으므로** Selenium으로 브라우저를 자동 조작해 포스팅합니다.

---

## 📁 프로젝트 구조

```
blog_automation/
├── .env                  # 환경변수 (git 제외)
├── .gitignore
├── requirements.txt      # 패키지 목록
├── README.md
└── CLAUDE.md             # Claude Code 프로젝트 설정
```

---

## 🚀 실행 방법

```bash
conda activate blog_automation
uvicorn main:app --reload
```

브라우저에서 `http://localhost:8000` 접속 후 이미지 업로드

---

## ⚠️ 주의사항

- 네이버 자동 로그인 시 **2차 인증(OTP)은 비활성화** 하거나, 자동화 전용 서브 계정 사용 권장
- 네이버 보안 정책에 따라 간헐적으로 **보안문자(CAPTCHA)** 가 발생할 수 있음
- API 키는 절대 git에 커밋하지 않도록 주의
