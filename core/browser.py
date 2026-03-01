"""Playwright browser session with Naver login support.

Usage (async context manager):
    async with BrowserSession() as page:
        await page.goto("https://blog.naver.com/write")
"""

from playwright.async_api import async_playwright, Browser, Page, Playwright

from config import settings
from core.logger import setup_logger

logger = setup_logger("browser")

_NAVER_LOGIN_URL = "https://nid.naver.com/nidlogin.login"


class BrowserSession:
    """Async context manager that manages a Playwright browser session.

    Logs in to Naver automatically on entry. Shared by Module 1 and Module 2.

    Attributes:
        headless: Whether to run the browser in headless mode.
    """

    def __init__(self, headless: bool = True) -> None:
        """Initialize the browser session.

        Args:
            headless: Run Chromium in headless mode if True.
        """
        self.headless = headless
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._page: Page | None = None

    async def __aenter__(self) -> Page:
        """Start the browser and log in to Naver.

        Returns:
            Authenticated Playwright Page instance.
        """
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.headless)
        context = await self._browser.new_context(
            locale="ko-KR",
            timezone_id="Asia/Seoul",
        )
        self._page = await context.new_page()
        await self.naver_login(self._page)
        return self._page

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Close the browser and stop Playwright."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def naver_login(self, page: Page) -> None:
        """Log in to Naver using credentials from config.

        Uses JavaScript injection to bypass Naver's keyboard security.

        Args:
            page: Playwright Page instance to perform login on.

        Raises:
            RuntimeError: If login fails after navigation.
        """
        logger.info(f"Logging in to Naver as {settings.naver_id!r}")
        await page.goto(_NAVER_LOGIN_URL, wait_until="domcontentloaded")

        # Inject credentials via JS to bypass Naver's key logger protection
        await page.evaluate(
            f"document.querySelector('#id').value = '{settings.naver_id}'"
        )
        await page.evaluate(
            f"document.querySelector('#pw').value = '{settings.naver_password}'"
        )
        await page.click(".btn_login")
        await page.wait_for_load_state("domcontentloaded")

        current_url = page.url
        if "nid.naver.com" in current_url and "login" in current_url:
            raise RuntimeError(
                f"Naver login failed — still on login page: {current_url}. "
                "Check NAVER_ID / NAVER_PASSWORD or CAPTCHA."
            )

        logger.info("Naver login successful")
