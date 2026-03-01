"""Blog draft generator using Claude Vision API.

Reads the current style guide and generates a draft based on uploaded images.
"""

import json

from config import STYLE_GUIDE_PATH
from core.claude_client import ClaudeClient
from core.logger import setup_logger
from modules.draft.media_processor import ProcessedMedia

logger = setup_logger("draft")

_SYSTEM_PROMPT = (
    "당신은 네이버 맛집 블로그 전문 작가입니다. "
    "제공된 음식 사진들을 분석하고, 스타일 가이드에 따라 맛집 리뷰 초안을 작성해주세요. "
    "반드시 스타일 가이드의 톤, 구조, 어휘를 따르세요."
)


def load_style_guide() -> dict:
    """Load the current style guide from disk.

    Returns:
        Parsed style guide dict. Empty dict if file is missing.
    """
    if not STYLE_GUIDE_PATH.exists():
        logger.warning("style_guide.json not found — using empty guide")
        return {}
    return json.loads(STYLE_GUIDE_PATH.read_text(encoding="utf-8"))


def build_vision_prompt(style_guide: dict, restaurant_name: str = "") -> str:
    """Build a Claude Vision prompt incorporating the style guide.

    Args:
        style_guide: Current style guide dict.
        restaurant_name: Optional restaurant name inferred from the folder name.

    Returns:
        Formatted prompt string.
    """
    guide_str = json.dumps(style_guide, ensure_ascii=False, indent=2)
    name_hint = f"가게 이름: {restaurant_name}\n" if restaurant_name else ""
    return (
        f"{name_hint}"
        f"위 사진들을 보고 아래 스타일 가이드에 맞춰 네이버 맛집 블로그 글을 작성해주세요.\n\n"
        f"스타일 가이드:\n```json\n{guide_str}\n```\n\n"
        "요구사항:\n"
        "1. 스타일 가이드의 구조(intro → body → conclusion)를 반드시 따르세요.\n"
        "2. 지정된 톤과 어휘를 사용하세요.\n"
        "3. 사진에서 보이는 메뉴, 분위기, 인테리어를 구체적으로 묘사하세요.\n"
        "4. 마지막에 해시태그를 추가하세요.\n"
        "5. 제목도 함께 작성해주세요 (첫 줄에 '제목:' 으로 시작)."
    )


def generate_draft(
    media_list: list[ProcessedMedia],
    style_guide: dict,
    restaurant_name: str = "",
) -> str:
    """Generate a blog draft from images using Claude Vision.

    Args:
        media_list: List of ProcessedMedia with base64-encoded images.
        style_guide: Current style guide dict.
        restaurant_name: Optional restaurant name for the prompt.

    Returns:
        Generated draft text from Claude.
    """
    if not media_list:
        raise ValueError("No images provided for draft generation")

    client = ClaudeClient()
    prompt = build_vision_prompt(style_guide, restaurant_name)
    image_b64_list = [m.b64_data for m in media_list]

    logger.info(f"Generating draft with {len(image_b64_list)} image(s)")
    draft = client.call_vision(
        prompt=prompt,
        image_b64_list=image_b64_list,
        system=_SYSTEM_PROMPT,
        max_tokens=3000,
    )
    logger.info(f"Draft generated ({len(draft)} chars)")
    return draft
