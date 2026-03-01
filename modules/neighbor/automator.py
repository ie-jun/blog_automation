"""Playwright automator for Naver neighbor (이웃) requests — Module 1."""

import asyncio

from playwright.async_api import Page

from config import settings
from core.browser import BrowserSession
from core.logger import setup_logger
from modules.neighbor.searcher import BloggerInfo

logger = setup_logger("neighbor")

_BLOG_BASE = "https://blog.naver.com"
_NEIGHBOR_BTN_SELECTORS = [
    "button:has-text('이웃추가')",
    ".btn_neighbor_add",
    "[class*='neighborAdd']",
]
_CONFIRM_BTN_SELECTORS = [
    "button:has-text('확인')",
    ".btn_confirm",
    ".modal button.ok",
]


async def add_neighbor(page: Page, blog_id: str) -> bool:
    """Request to add a Naver blog as an 이웃 (neighbor).

    Args:
        page: Authenticated Playwright Page instance.
        blog_id: Target blog ID.

    Returns:
        True if the request was sent successfully, False otherwise.
    """
    try:
        await page.goto(f"{_BLOG_BASE}/{blog_id}", wait_until="domcontentloaded", timeout=15000)
        await asyncio.sleep(1)

        for selector in _NEIGHBOR_BTN_SELECTORS:
            btn = page.locator(selector).first
            if await btn.count() > 0:
                await btn.click()
                await asyncio.sleep(1)
                # Confirm dialog if present
                for confirm_sel in _CONFIRM_BTN_SELECTORS:
                    confirm = page.locator(confirm_sel).first
                    if await confirm.count() > 0:
                        await confirm.click()
                        await asyncio.sleep(0.5)
                        break
                logger.info(f"Neighbor request sent: {blog_id!r}")
                return True

        logger.warning(f"Neighbor button not found for: {blog_id!r}")
        return False

    except Exception as exc:
        logger.error(f"add_neighbor failed for {blog_id!r}: {exc}")
        return False


async def add_neighbors_batch(
    bloggers: list[BloggerInfo],
    daily_limit: int | None = None,
) -> list[dict]:
    """Send neighbor requests to a batch of bloggers within the daily limit.

    Args:
        bloggers: List of filtered BloggerInfo candidates.
        daily_limit: Max requests per run. Defaults to settings.neighbor_add_daily_limit.

    Returns:
        List of result dicts with blog_id, status, and reason.
    """
    limit = daily_limit if daily_limit is not None else settings.neighbor_add_daily_limit
    results: list[dict] = []

    async with BrowserSession(headless=True) as page:
        for i, blogger in enumerate(bloggers):
            if i >= limit:
                logger.info(f"Daily limit ({limit}) reached — stopping")
                break

            success = await add_neighbor(page, blogger.blog_id)
            results.append({
                "blog_id": blogger.blog_id,
                "blog_name": blogger.blog_name,
                "status": "success" if success else "failed",
                "reason": None if success else "button not found or error",
            })
            await asyncio.sleep(2)  # polite delay between requests

    return results
