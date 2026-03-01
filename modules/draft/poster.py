"""Naver blog poster using Playwright.

Posts the generated draft as a private ("나만보기") blog entry.
Handles the SmartEditor ONE iframe structure with retry logic.
"""

import asyncio
from pathlib import Path

from playwright.async_api import Page, TimeoutError as PwTimeoutError

from core.browser import BrowserSession
from core.logger import setup_logger

logger = setup_logger("draft")

_WRITE_URL = "https://blog.naver.com/BlogPost.nhn"
_SMART_EDITOR_SELECTORS = [
    ".se-content",                # SmartEditor ONE (현행)
    "#postViewArea",              # 구형 에디터 fallback
]
_MAX_RETRIES = 3
_RETRY_DELAY_SEC = 2


async def _retry_async(
    coro_factory,
    description: str,
    max_retries: int = _MAX_RETRIES,
    delay: float = _RETRY_DELAY_SEC,
):
    """Retry an async operation with exponential backoff.

    Args:
        coro_factory: Callable returning a coroutine to retry.
        description: Human-readable label for log messages.
        max_retries: Maximum number of attempts.
        delay: Base delay between retries in seconds.

    Returns:
        The return value of the coroutine on success.

    Raises:
        The last exception if all retries are exhausted.
    """
    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            return await coro_factory()
        except Exception as exc:
            last_exc = exc
            if attempt < max_retries:
                wait = delay * attempt
                logger.warning(
                    f"{description} failed (attempt {attempt}/{max_retries}): "
                    f"{exc} — retrying in {wait:.1f}s"
                )
                await asyncio.sleep(wait)
            else:
                logger.error(
                    f"{description} failed after {max_retries} attempts: {exc}"
                )
    raise last_exc  # type: ignore[misc]


async def post_to_naver_blog(
    title: str,
    content: str,
    image_paths: list[Path],
) -> str:
    """Post a draft to Naver blog as a private entry.

    Args:
        title: Blog post title.
        content: Blog post body text (markdown-style).
        image_paths: List of image file paths to upload.

    Returns:
        URL of the created private blog post.

    Raises:
        RuntimeError: If posting fails at any step after retries.
    """
    async with BrowserSession(headless=True) as page:
        await _navigate_to_write_page(page)
        await _retry_async(
            lambda: _fill_title(page, title),
            "Fill title",
        )
        await _retry_async(
            lambda: _fill_content(page, content),
            "Fill content",
        )
        if image_paths:
            await _upload_images(page, image_paths)
        await _retry_async(
            lambda: _set_visibility_private(page),
            "Set visibility private",
        )
        post_url = await _retry_async(
            lambda: _publish_and_get_url(page),
            "Publish post",
        )

    logger.info(f"Posted to Naver blog (private): {post_url}")
    return post_url


async def _navigate_to_write_page(page: Page) -> None:
    """Navigate to the Naver blog write page."""
    await page.goto(_WRITE_URL, wait_until="networkidle", timeout=30000)
    await asyncio.sleep(2)


async def _fill_title(page: Page, title: str) -> None:
    """Fill in the blog post title field.

    Args:
        page: Playwright Page instance.
        title: Title string to input.
    """
    title_selectors = [".se-title-text", "#subject", "input[name='title']"]
    for selector in title_selectors:
        el = page.locator(selector).first
        if await el.count() > 0:
            await el.click()
            await el.fill(title)
            logger.debug(f"Title filled via selector: {selector!r}")
            return
    raise RuntimeError("Could not find title input field")


async def _fill_content(page: Page, content: str) -> None:
    """Fill in the blog post body.

    Tries SmartEditor ONE content area first, then legacy editor.

    Args:
        page: Playwright Page instance.
        content: Body text to input.
    """
    for selector in _SMART_EDITOR_SELECTORS:
        el = page.locator(selector).first
        if await el.count() > 0:
            await el.click()
            await page.keyboard.type(content, delay=10)
            logger.debug(f"Content filled via selector: {selector!r}")
            return

    # iframe fallback
    frames = page.frames
    for frame in frames:
        try:
            el = frame.locator(".se-content").first
            if await el.count() > 0:
                await el.click()
                await frame.keyboard.type(content, delay=10)
                logger.debug("Content filled via iframe")
                return
        except Exception:
            continue

    raise RuntimeError("Could not find content editor")


async def _upload_images(page: Page, image_paths: list[Path]) -> None:
    """Upload images to the blog post via file input.

    Args:
        page: Playwright Page instance.
        image_paths: List of image file paths to upload.
    """
    file_input_selector = "input[type='file']"
    try:
        await page.set_input_files(
            file_input_selector,
            [str(p) for p in image_paths],
        )
        await asyncio.sleep(2)
        logger.debug(f"Uploaded {len(image_paths)} image(s)")
    except Exception as exc:
        logger.warning(f"Image upload failed (non-fatal): {exc}")


async def _set_visibility_private(page: Page) -> None:
    """Set the post visibility to private ("나만보기").

    Args:
        page: Playwright Page instance.
    """
    private_selectors = [
        "button:has-text('나만보기')",
        "[data-visibility='private']",
        ".se-toolbar-visibility",
    ]
    for selector in private_selectors:
        el = page.locator(selector).first
        if await el.count() > 0:
            await el.click()
            await asyncio.sleep(1)
            logger.debug(f"Visibility set to private via: {selector!r}")
            return
    logger.warning("Could not set private visibility — check selector")


async def _publish_and_get_url(page: Page) -> str:
    """Click the publish button and return the post URL.

    Args:
        page: Playwright Page instance.

    Returns:
        URL of the newly created blog post.
    """
    publish_selectors = [
        "button:has-text('발행')",
        "#publishBtn",
        ".btn_publish",
    ]
    for selector in publish_selectors:
        el = page.locator(selector).first
        if await el.count() > 0:
            await el.click()
            await page.wait_for_load_state("networkidle", timeout=15000)
            return page.url

    raise RuntimeError("Could not find publish button")
