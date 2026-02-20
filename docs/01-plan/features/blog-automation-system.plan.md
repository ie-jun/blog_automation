# 네이버 맛집 블로그 자동화 시스템 Plan

> **Feature**: blog-automation-system
> **Level**: Dynamic
> **Date**: 2026-02-20
> **Status**: In Progress

---

## 1. Background

네이버 맛집 블로그를 운영하면서 발생하는 반복 작업 3가지를 자동화한다:
1. 이웃 블로거 탐색 및 이웃 신청 — 매일 수동으로 진행하던 작업
2. 맛집 방문 후 사진을 업로드하면 AI가 리뷰 초안을 자동 생성 및 포스팅
3. 블로그 글쓰기 스타일 일관성 유지 — 피드백을 통해 스타일 가이드를 점진적으로 개선

기존 `requirements.txt`와 `README.md`는 단순 이미지→포스팅 단일 기능 기준으로 작성되어 있었으며, 3모듈 시스템으로 설계가 확장됨에 따라 CLAUDE.md 기반으로 전체 재설계 완료.

---

## 2. Scope

### 2.1 모듈 구성 (3개 독립 모듈)

| 모듈 | Feature ID | 설명 | 트리거 | 우선순위 |
|:----:|-----------|------|--------|:--------:|
| Module 1 | M1-NEIGHBOR | 이웃 추가 자동화 | APScheduler 매일 1회 | P1 |
| Module 2 | M2-DRAFT | 블로그 초안 자동 작성 | input/ 서브폴더 done.txt watchdog | P0 |
| Module 3 | M3-STYLE | 스타일 가이드 웹 UI + URL 분석 | FastAPI tmux 백그라운드 | P1 |

### 2.2 핵심 공유 인프라 (core/)

| 컴포넌트 | 역할 | 사용 모듈 |
|---------|------|---------|
| `claude_client.py` | Anthropic SDK 공통 클라이언트 (text + vision) | M2, M3 |
| `naver_client.py` | 네이버 Open API 래퍼 | M1 |
| `browser.py` | Playwright 브라우저 세션 + 네이버 로그인 | M1, M2, M3(URL 분석 폴백) |
| `logger.py` | loguru 날짜별 로테이션 로거 | 전체 |

### 2.3 데이터 흐름

```
Module 3 → data/style_guide.json → Module 2
Module 1 ↔ Module 2, 3: 완전 독립
```

### 2.4 스코프 외 항목

- 네이버 공식 블로그 API 사용 (존재하지 않음 — Playwright로 대체)
- OpenAI / GPT 사용 (Anthropic Claude만 사용)
- 자동 포스팅 후 공개 발행 (초안은 항상 "나만보기"로 저장)

---

## 3. Goals

| ID | Goal | 우선순위 | 완료 조건 |
|:--:|------|:--------:|---------|
| G-01 | core/ 인프라 완성 (4개 파일) | P0 | 모든 모듈이 공유 클라이언트 정상 임포트 |
| G-02 | Module 2: input/ 서브폴더→초안→나만보기 포스팅 전체 파이프라인 동작 | P0 | 게시글 서브폴더에 이미지 업로드 후 done.txt 추가 시 블로그 초안 자동 생성 및 포스팅 확인 |
| G-03 | Module 3: 피드백 제출 → style_guide.json 업데이트 → 이력 저장 | P1 | 웹 UI에서 피드백 입력 후 가이드 변경 확인 |
| G-04 | Module 1: 조건 필터링 후 이웃 신청 일일 20건 이하 자동 처리 | P1 | 로그 파일에 이웃 신청 결과 기록 확인 |
| G-05 | scheduler.py: Module 1 매일 자동 실행 | P2 | APScheduler 정상 구동 및 스케줄 동작 확인 |
| G-06 | Module 3: URL 입력 → 크롤링 → 스타일 추출 → 항목 선택 → style_guide 반영 | P2 | 공개 포스팅 URL로 분석 후 선택 섹션만 가이드에 반영 확인 |

---

## 4. Implementation Phases

| Phase | 내용 | 산출물 | 선행 조건 |
|:-----:|------|--------|---------|
| 1 | `requirements.txt` 정리, `config.py`, `core/` 4개 파일, `data/style_guide.json` | 공유 인프라 | 없음 |
| 2 | Module 3 (`modules/style/`), `run_module3.py`, `templates/index.html` | 스타일 가이드 웹 UI | Phase 1 |
| 3 | Module 2 (`modules/draft/`), `run_module2.py` | 핵심 초안 생성 파이프라인 | Phase 1 |
| 4 | Module 1 (`modules/neighbor/`), `run_module1.py` | 이웃 추가 자동화 | Phase 1 |
| 5 | `scheduler.py`, 통합 테스트 (`tests/`) | 마무리 및 검증 | Phase 1-4 |
| 6 | URL 스타일 분석 (`url_analyzer.py`, 라우트 3개, UI 추가) | Module 3 확장 | Phase 2 |

---

## 5. Technical Constraints

| 항목 | 결정 사항 | 이유 |
|------|---------|------|
| AI | Anthropic Claude (`claude-sonnet-4-6`) only | 프로젝트 방향성 |
| 브라우저 자동화 | Playwright only (Selenium 제외) | 안정성, async 지원 |
| Python | 3.11 타겟 | 모노레포 공통 규칙 |
| 블로그 포스팅 | 항상 "나만보기" | 초안 검토 후 수동 공개 |
| 이웃 신청 상한 | 일 20건 | 계정 제재 방지 |
| Naver API 일일 한도 | 검색 1,000건 (실제 25,000건) | 보수적 운용 |
| URL 크롤링 전략 | httpx + BS4 (1차) → Playwright 폴백 (2차) | 속도 우선, 안정성 폴백 |
| URL 분석 세션 캐시 | 인메모리 dict, TTL 10분 | 단일 프로세스, Redis 불필요 |

---

## 6. Risk Assessment

| 위험 | 가능성 | 영향 | 대응 방안 |
|------|:------:|:----:|---------|
| 네이버 로그인 CAPTCHA 발생 | 중 | 높음 | 자동화 전용 서브 계정 사용, 2FA 비활성화 |
| 네이버 SmartEditor iframe 구조 변경 | 중 | 높음 | `page.frame_locator()` 사용, selector 추상화 |
| Claude API rate limit | 낮음 | 중 | tenacity @retry 적용 |
| done.txt 미생성으로 트리거 누락 | 낮음 | 낮음 | README에 사용법 명시, watcher 로그로 대기 중 폴더 안내 |
| 이웃 신청 계정 제재 | 낮음 | 높음 | `neighbor_add_daily_limit = 20` 제한 |
| 네이버 모바일 HTML 구조 변경 | 중 | 중 | `.se-main-container` → `#postViewArea` 순 시도, 폴백으로 Playwright |
| URL 분석 세션 만료 | 낮음 | 낮음 | TTL 10분, 만료 시 404 반환 후 재분석 유도 |

---

## 7. Success Criteria

- Module 2 E2E: 게시글 서브폴더에 이미지 + done.txt → 초안 생성 → 나만보기 포스팅까지 오류 없이 완료
- Module 3 피드백: 피드백 입력 → `style_guide.json` 변경 → `style_guide_history.json` 이력 1건 추가
- Module 3 URL 분석: 공개 포스팅 URL → 포스팅 제목 정상 추출 → 섹션 선택 후 가이드 반영 확인
- Module 1: 조건 필터링 후 지정 한도 이내 이웃 신청 + `logs/neighbor_YYYYMMDD.json` 생성
- 전체 gap analysis 90%+ 달성

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-20 | Initial plan — 3모듈 시스템 설계 확정 |
| 1.1 | 2026-02-20 | Module 3에 URL 기반 스타일 추출 기능 추가 (G-06, Phase 6) |
| 1.2 | 2026-02-20 | Module 2 input 방식 변경: 디바운스 타이머 → 게시글별 서브폴더 + done.txt 신호 방식 |
