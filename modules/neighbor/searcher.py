"""Naver blog searcher for Module 1.

Uses the Naver Open API to find food bloggers based on search keywords.
"""

import re
from dataclasses import dataclass, field

from core.logger import setup_logger
from core.naver_client import NaverSearchClient

logger = setup_logger("neighbor")

_BLOG_ID_RE = re.compile(r"blog\.naver\.com/([^/?#\"']+)")


@dataclass
class BloggerInfo:
    """Information about a candidate blogger extracted from search results.

    Attributes:
        blog_id: Naver blog ID (subdomain part of blog.naver.com/<blog_id>).
        blog_name: Display name of the blog.
        description: Snippet text from the search result.
        recent_pub_dates: Publication dates of this blogger found in the search batch.
    """

    blog_id: str
    blog_name: str
    description: str
    recent_pub_dates: list[str] = field(default_factory=list)


def search_food_bloggers(
    keywords: list[str],
    display: int = 100,
) -> list[BloggerInfo]:
    """Search Naver blogs for food-related posts and extract blogger info.

    Deduplicates by blog_id. Collects all pubDates per blogger for activity check.

    Args:
        keywords: List of search keyword strings (e.g. ["맛집", "서울 맛집"]).
        display: Number of results per keyword request (max 100).

    Returns:
        Deduplicated list of BloggerInfo objects.
    """
    client = NaverSearchClient()
    seen: dict[str, BloggerInfo] = {}

    for keyword in keywords:
        logger.info(f"Searching blogs for keyword: {keyword!r}")
        try:
            data = client.search_blog(query=keyword, display=display)
            items = data.get("items", [])
            for item in items:
                link = item.get("link", "")
                blog_id = _extract_blog_id(link)
                if not blog_id:
                    continue

                if blog_id in seen:
                    seen[blog_id].recent_pub_dates.append(item.get("pubDate", ""))
                else:
                    seen[blog_id] = BloggerInfo(
                        blog_id=blog_id,
                        blog_name=_strip_tags(item.get("bloggername", "")),
                        description=_strip_tags(item.get("description", "")),
                        recent_pub_dates=[item.get("pubDate", "")],
                    )
        except Exception as exc:
            logger.error(f"Search failed for keyword {keyword!r}: {exc}")

    logger.info(f"Found {len(seen)} unique bloggers")
    return list(seen.values())


def extract_blogger_info(items: list[dict]) -> list[BloggerInfo]:
    """Convert raw API items to BloggerInfo objects.

    Args:
        items: List of raw item dicts from Naver API response.

    Returns:
        List of BloggerInfo objects.
    """
    results: list[BloggerInfo] = []
    for item in items:
        blog_id = _extract_blog_id(item.get("link", ""))
        if blog_id:
            results.append(BloggerInfo(
                blog_id=blog_id,
                blog_name=_strip_tags(item.get("bloggername", "")),
                description=_strip_tags(item.get("description", "")),
                recent_pub_dates=[item.get("pubDate", "")],
            ))
    return results


def _extract_blog_id(link: str) -> str:
    """Extract the blog ID from a Naver blog URL.

    Args:
        link: URL string from the API response.

    Returns:
        Blog ID string, or empty string if not found.
    """
    match = _BLOG_ID_RE.search(link)
    return match.group(1) if match else ""


def _strip_tags(text: str) -> str:
    """Remove HTML tags from a string.

    Args:
        text: String potentially containing HTML tags.

    Returns:
        Plain text without HTML tags.
    """
    return re.sub(r"<[^>]+>", "", text).strip()
