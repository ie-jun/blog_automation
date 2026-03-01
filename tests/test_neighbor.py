"""Unit tests for Module 1 — neighbor filter logic."""

import pytest

from modules.neighbor.filter import (
    check_food_content_ratio,
    check_sponsorship_experience,
    is_eligible,
)
from modules.neighbor.searcher import BloggerInfo, _extract_blog_id, _strip_tags


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_blogger(
    blog_id: str = "testblog",
    name: str = "맛집 블로거",
    description: str = "서울 맛집 리뷰 전문 블로그",
    pub_dates: list[str] | None = None,
) -> BloggerInfo:
    return BloggerInfo(
        blog_id=blog_id,
        blog_name=name,
        description=description,
        recent_pub_dates=pub_dates or [],
    )


# ---------------------------------------------------------------------------
# check_food_content_ratio
# ---------------------------------------------------------------------------

class TestFoodContentRatio:
    def test_passes_food_heavy_description(self) -> None:
        blogger = _make_blogger(
            description="맛집 리뷰 전문 블로그. 서울 맛있는 음식 식당 카페 디저트"
        )
        assert check_food_content_ratio(blogger) is True

    def test_fails_non_food_description(self) -> None:
        blogger = _make_blogger(
            name="여행 블로거",
            description="해외 여행, 항공권 정보, 호텔 후기 전문 블로그",
        )
        assert check_food_content_ratio(blogger) is False

    def test_empty_description_fails(self) -> None:
        blogger = _make_blogger(name="", description="")
        assert check_food_content_ratio(blogger) is False


# ---------------------------------------------------------------------------
# check_sponsorship_experience
# ---------------------------------------------------------------------------

class TestSponsorshipCheck:
    def test_clean_blogger_passes(self) -> None:
        blogger = _make_blogger(description="진짜 맛집 후기만 씁니다")
        assert check_sponsorship_experience(blogger) is True

    def test_sponsored_blogger_fails(self) -> None:
        blogger = _make_blogger(description="협찬받은 제품 리뷰도 함께 작성")
        assert check_sponsorship_experience(blogger) is False

    def test_ad_keyword_fails(self) -> None:
        blogger = _make_blogger(description="광고 포함 맛집 리뷰")
        assert check_sponsorship_experience(blogger) is False


# ---------------------------------------------------------------------------
# Searcher helpers
# ---------------------------------------------------------------------------

class TestSearcherHelpers:
    def test_extract_blog_id_standard(self) -> None:
        assert _extract_blog_id("https://blog.naver.com/myfoodblog/123456") == "myfoodblog"

    def test_extract_blog_id_no_match(self) -> None:
        assert _extract_blog_id("https://naver.com") == ""

    def test_strip_tags(self) -> None:
        assert _strip_tags("<b>맛집</b> 리뷰") == "맛집 리뷰"

    def test_strip_tags_clean(self) -> None:
        assert _strip_tags("태그 없음") == "태그 없음"
