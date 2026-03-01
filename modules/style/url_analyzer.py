"""Blog URL crawler and style extractor for Module 3.

Fetch strategy:
  1. httpx + BeautifulSoup4 (fast, lightweight)
  2. Playwright fallback (for JS-rendered pages)
"""

import json
import re
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup

from core.claude_client import ClaudeClient
from core.logger import setup_logger

logger = setup_logger("style")

_MOBILE_BASE = "https://m.blog.naver.com"
_POST_URL_RE = re.compile(r"blog\.naver\.com/([^/?#]+)/(\d+)")
_MAX_CONTENT_CHARS = 3000

# HTML selectors tried in order
_CONTENT_SELECTORS = [".se-main-container", "#postViewArea", ".post-view"]


@dataclass
class CrawledPost:
    """Represents a crawled Naver blog post."""

    url: str
    title: str
    content: str  # plain text, truncated to _MAX_CONTENT_CHARS


def normalize_naver_blog_url(url: str) -> tuple[str, str, str]:
    """Extract blog_id and log_no and build a mobile URL.

    Args:
        url: Any Naver blog post URL format.

    Returns:
        Tuple of (mobile_url, blog_id, log_no).

    Raises:
        ValueError: If the URL does not match Naver blog patterns.
    """
    match = _POST_URL_RE.search(url)
    if match:
        blog_id, log_no = match.group(1), match.group(2)
        return f"{_MOBILE_BASE}/{blog_id}/{log_no}", blog_id, log_no

    # PostView.naver?blogId=x&logNo=y format
    bid = re.search(r"blogId=([^&]+)", url)
    lno = re.search(r"logNo=(\d+)", url)
    if bid and lno:
        blog_id, log_no = bid.group(1), lno.group(1)
        return f"{_MOBILE_BASE}/{blog_id}/{log_no}", blog_id, log_no

    raise ValueError(f"Cannot parse Naver blog URL: {url!r}")


async def fetch_post_content(url: str) -> CrawledPost:
    """Fetch blog post content using httpx first, Playwright as fallback.

    Args:
        url: Public Naver blog post URL.

    Returns:
        CrawledPost with title and plain-text content.
    """
    mobile_url, _, _ = normalize_naver_blog_url(url)

    try:
        return await _fetch_via_httpx(mobile_url)
    except Exception as exc:
        logger.warning(f"httpx fetch failed ({exc}), falling back to Playwright")
        return await _fetch_via_playwright(url)


async def _fetch_via_httpx(mobile_url: str) -> CrawledPost:
    """Fetch and parse the mobile blog page with httpx + BeautifulSoup.

    Args:
        mobile_url: Mobile version of the blog post URL.

    Returns:
        CrawledPost parsed from the response HTML.

    Raises:
        httpx.HTTPError: On HTTP-level errors.
        ValueError: If no content selector matched.
    """
    headers = {"User-Agent": "Mozilla/5.0 (compatible; BlogAnalyzer/1.0)"}
    async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
        resp = await client.get(mobile_url, headers=headers)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")
    title = soup.find("title")
    title_text = title.get_text(strip=True) if title else "제목 없음"

    content_el = None
    for selector in _CONTENT_SELECTORS:
        content_el = soup.select_one(selector)
        if content_el:
            break

    if not content_el:
        raise ValueError(f"No content element found at {mobile_url}")

    content_text = content_el.get_text(separator="\n", strip=True)[:_MAX_CONTENT_CHARS]
    return CrawledPost(url=mobile_url, title=title_text, content=content_text)


async def _fetch_via_playwright(url: str) -> CrawledPost:
    """Fetch and parse the blog page using Playwright (JS-rendered fallback).

    Args:
        url: Original blog post URL.

    Returns:
        CrawledPost parsed from the rendered HTML.

    Raises:
        ValueError: If no content selector matched after rendering.
    """
    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle", timeout=30000)

        title_text = await page.title()
        content_text = ""

        for selector in _CONTENT_SELECTORS:
            el = page.locator(selector).first
            if await el.count() > 0:
                content_text = await el.inner_text()
                break

        await browser.close()

    if not content_text:
        raise ValueError(f"No content element found via Playwright at {url}")

    return CrawledPost(
        url=url,
        title=title_text,
        content=content_text[:_MAX_CONTENT_CHARS],
    )


def build_style_extraction_prompt(post: CrawledPost, current_guide: dict) -> str:
    """Build a Claude prompt to extract style information from a blog post.

    Args:
        post: Crawled blog post content.
        current_guide: Current style guide for structural reference.

    Returns:
        Formatted prompt string.
    """
    guide_keys = json.dumps(list(current_guide.keys()), ensure_ascii=False)
    return (
        f"다음은 네이버 블로그 포스팅입니다:\n\n"
        f"제목: {post.title}\n"
        f"내용:\n{post.content}\n\n"
        f"위 포스팅에서 스타일을 분석하여 아래 JSON 키 구조에 맞게 추출해주세요.\n"
        f"키 목록: {guide_keys}\n\n"
        "각 섹션에 '_confidence' 필드(0.0~1.0)를 추가하여 추출 신뢰도를 표시하세요. "
        "반드시 JSON만 응답하고 다른 텍스트는 포함하지 마세요."
    )


def analyze_style_from_post(
    post: CrawledPost,
    current_guide: dict,
    claude_client: ClaudeClient,
) -> dict:
    """Extract style information from a crawled post using Claude.

    Args:
        post: Crawled blog post.
        current_guide: Current style guide for structural reference.
        claude_client: Initialized ClaudeClient instance.

    Returns:
        Extracted style dict with _confidence fields.

    Raises:
        json.JSONDecodeError: If Claude returns invalid JSON.
    """
    prompt = build_style_extraction_prompt(post, current_guide)
    raw = claude_client.call_text(prompt, max_tokens=2000)

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    return json.loads(cleaned)
