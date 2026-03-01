"""Blogger eligibility filter for Module 1.

Applies three conditions in order (cheapest first):
  1. Food content ratio >= 50% (description text analysis — no extra API call)
  2. No sponsorship keywords detected (title/description — no extra API call)
  3. Recent activity: >= 3 posts in last 30 days (uses pubDates from search batch;
     falls back to one extra NaverSearchClient call only if needed)
"""

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from config import LOGS_DIR
from core.logger import setup_logger
from core.naver_client import NaverSearchClient
from modules.neighbor.searcher import BloggerInfo

logger = setup_logger("neighbor")

_FOOD_KEYWORDS = [
    "맛집", "음식", "식당", "카페", "레스토랑", "밥", "먹", "요리", "반찬",
    "디저트", "맛있", "메뉴", "라멘", "스시", "파스타", "피자", "치킨",
]
_SPONSORSHIP_KEYWORDS = [
    "협찬", "광고", "유료광고", "제품제공", "서비스제공", "paid", "sponsored",
    "PR", "파트너십", "원고료",
]
_FOOD_RATIO_THRESHOLD = 0.5
_MIN_RECENT_POSTS = 3
_RECENT_DAYS = 30


def filter_bloggers(bloggers: list[BloggerInfo]) -> list[BloggerInfo]:
    """Filter a list of bloggers by eligibility conditions.

    Applies conditions in cost order — early exits on failure to minimize API calls.
    Skips bloggers already in the neighbor log history.

    Args:
        bloggers: Candidate bloggers from the search step.

    Returns:
        List of eligible BloggerInfo objects.
    """
    past_ids = _load_past_neighbor_ids()
    eligible: list[BloggerInfo] = []

    for blogger in bloggers:
        if blogger.blog_id in past_ids:
            logger.debug(f"Skip {blogger.blog_id!r} — already requested")
            continue

        ok, reason = is_eligible(blogger)
        if ok:
            eligible.append(blogger)
        else:
            logger.debug(f"Filtered out {blogger.blog_id!r}: {reason}")

    logger.info(f"Eligible bloggers after filtering: {len(eligible)}/{len(bloggers)}")
    return eligible


def is_eligible(blogger: BloggerInfo) -> tuple[bool, str]:
    """Check whether a blogger passes all eligibility conditions.

    Args:
        blogger: BloggerInfo to evaluate.

    Returns:
        Tuple of (is_eligible, reason_if_not).
    """
    if not check_food_content_ratio(blogger):
        return False, "low food content ratio"

    if not check_sponsorship_experience(blogger):
        return False, "sponsorship keywords detected"

    if not check_recent_activity(blogger):
        return False, "insufficient recent activity"

    return True, ""


def check_food_content_ratio(
    blogger: BloggerInfo,
    threshold: float = _FOOD_RATIO_THRESHOLD,
) -> bool:
    """Estimate whether the blogger focuses on food content.

    Based on keyword density in the description — no extra API call.

    Args:
        blogger: BloggerInfo to check.
        threshold: Minimum required food keyword density (0.0–1.0).

    Returns:
        True if food keyword ratio meets the threshold.
    """
    text = (blogger.blog_name + " " + blogger.description).lower()
    words = text.split()
    if not words:
        return False
    food_count = sum(1 for w in words if any(k in w for k in _FOOD_KEYWORDS))
    ratio = food_count / len(words)
    return ratio >= threshold


def check_sponsorship_experience(blogger: BloggerInfo) -> bool:
    """Detect sponsorship-related keywords in the blogger's content.

    Args:
        blogger: BloggerInfo to check.

    Returns:
        True if NO sponsorship keywords are detected.
    """
    text = (blogger.blog_name + " " + blogger.description).lower()
    for keyword in _SPONSORSHIP_KEYWORDS:
        if keyword.lower() in text:
            return False
    return True


def check_recent_activity(
    blogger: BloggerInfo,
    days: int = _RECENT_DAYS,
    min_posts: int = _MIN_RECENT_POSTS,
) -> bool:
    """Check whether the blogger has been active recently.

    First tries to use pubDates already collected in the search batch.
    Falls back to one extra NaverSearchClient search if pubDates are insufficient.

    Args:
        blogger: BloggerInfo to check.
        days: Activity window in days.
        min_posts: Minimum number of posts within the window.

    Returns:
        True if the blogger meets the activity requirement.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    recent_count = sum(
        1 for d in blogger.recent_pub_dates if _parse_pub_date(d) >= cutoff
    )

    if recent_count >= min_posts:
        return True

    # Fallback: re-query Naver API with the blog_id
    try:
        client = NaverSearchClient()
        data = client.search_blog(query=blogger.blog_id, display=10, sort="date")
        extra_dates = [item.get("pubDate", "") for item in data.get("items", [])]
        extra_recent = sum(
            1 for d in extra_dates if _parse_pub_date(d) >= cutoff
        )
        return extra_recent >= min_posts
    except Exception as exc:
        logger.warning(f"Activity re-check failed for {blogger.blog_id!r}: {exc}")
        return False


def _parse_pub_date(date_str: str) -> datetime:
    """Parse a Naver API pubDate string to a timezone-aware datetime.

    Args:
        date_str: Date string from the API (e.g. "Mon, 20 Feb 2026 10:00:00 +0900").

    Returns:
        Parsed datetime (UTC). Returns epoch on parse failure.
    """
    try:
        return datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z").astimezone(
            timezone.utc
        )
    except ValueError:
        return datetime.fromtimestamp(0, tz=timezone.utc)


def _load_past_neighbor_ids() -> set[str]:
    """Load all previously requested blog IDs from log files.

    Returns:
        Set of blog_id strings that have already been requested.
    """
    ids: list[str] = []
    for log_file in LOGS_DIR.glob("neighbor_*.json"):
        try:
            data = json.loads(log_file.read_text(encoding="utf-8"))
            for entry in data.get("entries", []):
                ids.append(entry.get("blog_id", ""))
        except Exception:
            pass
    return set(ids)
