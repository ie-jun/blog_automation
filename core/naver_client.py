"""Naver Open API wrapper for blog search.

Reference: https://developers.naver.com/docs/search/blog/
"""

import requests
from tenacity import retry, stop_after_attempt, wait_fixed

from config import settings
from core.logger import setup_logger

logger = setup_logger("naver_client")

_BLOG_SEARCH_URL = "https://openapi.naver.com/v1/search/blog.json"


class NaverSearchClient:
    """Naver Open API client for blog search.

    Attributes:
        headers: Common request headers with client credentials.
    """

    def __init__(self) -> None:
        """Initialize with Naver API credentials from config."""
        self.headers = {
            "X-Naver-Client-Id": settings.naver_client_id,
            "X-Naver-Client-Secret": settings.naver_client_secret,
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        reraise=True,
    )
    def search_blog(
        self,
        query: str,
        display: int = 100,
        start: int = 1,
        sort: str = "sim",
    ) -> dict:
        """Search Naver blogs with the given query.

        Args:
            query: Search keyword string.
            display: Number of results to return (max 100 per request).
            start: Start index for pagination (1-based).
            sort: Sort order — "sim" (relevance) or "date" (newest first).

        Returns:
            Parsed JSON response dict from the Naver API.

        Raises:
            requests.HTTPError: On non-2xx responses after retries.
        """
        params = {
            "query": query,
            "display": display,
            "start": start,
            "sort": sort,
        }
        logger.debug(f"search_blog | query={query!r} display={display} start={start}")

        response = requests.get(_BLOG_SEARCH_URL, headers=self.headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
