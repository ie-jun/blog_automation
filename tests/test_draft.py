"""Unit tests for Module 2 — media processor, draft generator, poster, and runner."""

import asyncio
import io
import json
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

from modules.draft.media_processor import (
    ProcessedMedia,
    _media_type,
    encode_to_base64,
    process_images,
    resize_image,
)
from modules.draft.runner import _split_title_and_body


# ---------------------------------------------------------------------------
# media_processor
# ---------------------------------------------------------------------------

class TestMediaType:
    def test_jpeg(self) -> None:
        assert _media_type(Path("photo.jpg")) == "image/jpeg"
        assert _media_type(Path("photo.JPEG")) == "image/jpeg"

    def test_png(self) -> None:
        assert _media_type(Path("img.png")) == "image/png"

    def test_webp(self) -> None:
        assert _media_type(Path("img.webp")) == "image/webp"

    def test_unknown_defaults_to_jpeg(self) -> None:
        assert _media_type(Path("img.bmp")) == "image/jpeg"


class TestResizeImage:
    def _create_temp_image(self, tmp_path: Path, size: tuple[int, int]) -> Path:
        img_path = tmp_path / "test.jpg"
        img = Image.new("RGB", size, color=(255, 0, 0))
        img.save(str(img_path), "JPEG")
        return img_path

    def test_small_image_unchanged_dimensions(self, tmp_path: Path) -> None:
        path = self._create_temp_image(tmp_path, (100, 100))
        result = resize_image(path, max_size=1024)
        img = Image.open(io.BytesIO(result))
        assert max(img.size) <= 1024

    def test_large_image_resized(self, tmp_path: Path) -> None:
        path = self._create_temp_image(tmp_path, (2000, 1500))
        result = resize_image(path, max_size=1024)
        img = Image.open(io.BytesIO(result))
        assert max(img.size) <= 1024

    def test_returns_bytes(self, tmp_path: Path) -> None:
        path = self._create_temp_image(tmp_path, (200, 200))
        result = resize_image(path)
        assert isinstance(result, bytes)


class TestEncodeToBase64:
    def test_encodes_correctly(self) -> None:
        import base64
        data = b"test data"
        encoded = encode_to_base64(data)
        assert base64.standard_b64decode(encoded) == data


class TestProcessImages:
    def test_skips_unsupported_extension(self, tmp_path: Path) -> None:
        txt_file = tmp_path / "readme.txt"
        txt_file.write_text("not an image")
        result = process_images([txt_file])
        assert result == []

    def test_processes_valid_image(self, tmp_path: Path) -> None:
        img_path = tmp_path / "food.jpg"
        img = Image.new("RGB", (100, 100), color=(0, 255, 0))
        img.save(str(img_path))
        result = process_images([img_path])
        assert len(result) == 1
        assert isinstance(result[0], ProcessedMedia)
        assert result[0].media_type == "image/jpeg"


# ---------------------------------------------------------------------------
# runner helpers
# ---------------------------------------------------------------------------

class TestSplitTitleAndBody:
    def test_extracts_title_line(self) -> None:
        draft = "제목: 강남 스시 맛집\n\n본문 내용입니다."
        title, body = _split_title_and_body(draft, "fallback")
        assert title == "강남 스시 맛집"
        assert "본문 내용입니다." in body

    def test_fallback_when_no_title_line(self) -> None:
        draft = "그냥 본문만 있는 경우입니다."
        title, body = _split_title_and_body(draft, "fallback_title")
        assert title == "fallback_title"
        assert body == draft


# ---------------------------------------------------------------------------
# draft_generator — Claude Vision mock tests
# ---------------------------------------------------------------------------

class TestBuildVisionPrompt:
    def test_includes_style_guide(self) -> None:
        from modules.draft.draft_generator import build_vision_prompt

        guide = {"tone": {"overall": "친근한 스타일"}, "hashtags": {"count": 10}}
        prompt = build_vision_prompt(guide, "강남 스시")
        assert "스타일 가이드" in prompt
        assert "친근한 스타일" in prompt
        assert "강남 스시" in prompt

    def test_no_restaurant_name(self) -> None:
        from modules.draft.draft_generator import build_vision_prompt

        prompt = build_vision_prompt({}, "")
        assert "가게 이름" not in prompt
        assert "스타일 가이드" in prompt

    def test_includes_requirements(self) -> None:
        from modules.draft.draft_generator import build_vision_prompt

        prompt = build_vision_prompt({}, "테스트")
        assert "해시태그" in prompt
        assert "제목:" in prompt


class TestGenerateDraft:
    def test_calls_claude_vision_with_correct_args(self) -> None:
        from modules.draft.draft_generator import generate_draft

        mock_client = MagicMock()
        mock_client.call_vision.return_value = "제목: 맛집 리뷰\n\n맛있었다."

        media = [
            ProcessedMedia(path=Path("a.jpg"), b64_data="base64a", media_type="image/jpeg"),
            ProcessedMedia(path=Path("b.png"), b64_data="base64b", media_type="image/png"),
        ]
        guide = {"tone": {"overall": "친근"}}

        with patch("modules.draft.draft_generator.ClaudeClient", return_value=mock_client):
            result = generate_draft(media, guide, "강남카페")

        assert result == "제목: 맛집 리뷰\n\n맛있었다."
        mock_client.call_vision.assert_called_once()
        call_kwargs = mock_client.call_vision.call_args
        assert call_kwargs.kwargs["max_tokens"] == 3000
        assert len(call_kwargs.kwargs["image_b64_list"]) == 2
        assert call_kwargs.kwargs["image_b64_list"] == ["base64a", "base64b"]

    def test_raises_on_empty_media(self) -> None:
        from modules.draft.draft_generator import generate_draft

        with pytest.raises(ValueError, match="No images"):
            generate_draft([], {}, "test")


# ---------------------------------------------------------------------------
# poster — Playwright mock tests
# ---------------------------------------------------------------------------

def _make_mock_page():
    """Create a mock Playwright Page with configurable locator responses."""
    page = AsyncMock()
    page.url = "https://blog.naver.com/testuser/12345"
    page.frames = []

    def make_locator(found: bool = True):
        loc = AsyncMock()
        loc.count = AsyncMock(return_value=1 if found else 0)
        loc.click = AsyncMock()
        loc.fill = AsyncMock()
        return loc

    # Default: first selector always found
    first_locator = make_locator(found=True)
    chain_mock = MagicMock()
    chain_mock.first = first_locator
    page.locator = MagicMock(return_value=chain_mock)

    page.keyboard = AsyncMock()
    page.keyboard.type = AsyncMock()
    page.set_input_files = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    page.goto = AsyncMock()

    return page


class TestFillTitle:
    @pytest.mark.asyncio
    async def test_fills_first_matching_selector(self) -> None:
        from modules.draft.poster import _fill_title

        page = _make_mock_page()
        await _fill_title(page, "테스트 제목")

        first_loc = page.locator.return_value.first
        first_loc.click.assert_called_once()
        first_loc.fill.assert_called_once_with("테스트 제목")

    @pytest.mark.asyncio
    async def test_raises_when_no_selector_found(self) -> None:
        from modules.draft.poster import _fill_title

        page = _make_mock_page()
        not_found = AsyncMock()
        not_found.count = AsyncMock(return_value=0)
        chain = MagicMock()
        chain.first = not_found
        page.locator = MagicMock(return_value=chain)

        with pytest.raises(RuntimeError, match="title input"):
            await _fill_title(page, "제목")


class TestFillContent:
    @pytest.mark.asyncio
    async def test_fills_via_selector(self) -> None:
        from modules.draft.poster import _fill_content

        page = _make_mock_page()
        await _fill_content(page, "본문 내용")

        first_loc = page.locator.return_value.first
        first_loc.click.assert_called_once()
        page.keyboard.type.assert_called_once_with("본문 내용", delay=10)

    @pytest.mark.asyncio
    async def test_raises_when_no_editor_found(self) -> None:
        from modules.draft.poster import _fill_content

        page = _make_mock_page()
        not_found = AsyncMock()
        not_found.count = AsyncMock(return_value=0)
        chain = MagicMock()
        chain.first = not_found
        page.locator = MagicMock(return_value=chain)
        page.frames = []

        with pytest.raises(RuntimeError, match="content editor"):
            await _fill_content(page, "본문")


class TestSetVisibilityPrivate:
    @pytest.mark.asyncio
    async def test_clicks_private_button(self) -> None:
        from modules.draft.poster import _set_visibility_private

        page = _make_mock_page()
        await _set_visibility_private(page)

        first_loc = page.locator.return_value.first
        first_loc.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_warns_when_no_selector(self) -> None:
        from modules.draft.poster import _set_visibility_private

        page = _make_mock_page()
        not_found = AsyncMock()
        not_found.count = AsyncMock(return_value=0)
        chain = MagicMock()
        chain.first = not_found
        page.locator = MagicMock(return_value=chain)

        # Should not raise, just log warning
        await _set_visibility_private(page)


class TestPublishAndGetUrl:
    @pytest.mark.asyncio
    async def test_returns_page_url(self) -> None:
        from modules.draft.poster import _publish_and_get_url

        page = _make_mock_page()
        page.url = "https://blog.naver.com/myid/99999"

        url = await _publish_and_get_url(page)
        assert url == "https://blog.naver.com/myid/99999"

    @pytest.mark.asyncio
    async def test_raises_when_no_publish_button(self) -> None:
        from modules.draft.poster import _publish_and_get_url

        page = _make_mock_page()
        not_found = AsyncMock()
        not_found.count = AsyncMock(return_value=0)
        chain = MagicMock()
        chain.first = not_found
        page.locator = MagicMock(return_value=chain)

        with pytest.raises(RuntimeError, match="publish button"):
            await _publish_and_get_url(page)


class TestRetryAsync:
    @pytest.mark.asyncio
    async def test_succeeds_on_first_try(self) -> None:
        from modules.draft.poster import _retry_async

        call_count = 0

        async def factory():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await _retry_async(factory, "test op", max_retries=3, delay=0.01)
        assert result == "ok"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_failure_then_succeeds(self) -> None:
        from modules.draft.poster import _retry_async

        call_count = 0

        async def factory():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("transient error")
            return "recovered"

        result = await _retry_async(factory, "test op", max_retries=3, delay=0.01)
        assert result == "recovered"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self) -> None:
        from modules.draft.poster import _retry_async

        async def factory():
            raise RuntimeError("persistent error")

        with pytest.raises(RuntimeError, match="persistent error"):
            await _retry_async(factory, "test op", max_retries=2, delay=0.01)


class TestPostToNaverBlogIntegration:
    @pytest.mark.asyncio
    async def test_full_posting_pipeline_mock(self) -> None:
        """Integration test: mocks BrowserSession and verifies full flow."""
        from modules.draft.poster import post_to_naver_blog

        mock_page = _make_mock_page()

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_page)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "modules.draft.poster.BrowserSession",
            return_value=mock_session,
        ):
            url = await post_to_naver_blog(
                title="테스트 제목",
                content="테스트 본문",
                image_paths=[Path("img1.jpg")],
            )

        assert "blog.naver.com" in url
        mock_page.goto.assert_called_once()
        mock_page.set_input_files.assert_called_once()
