"""Style guide CRUD and Claude-powered update logic."""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from config import STYLE_GUIDE_PATH
from core.claude_client import ClaudeClient
from core.logger import setup_logger

logger = setup_logger("style")

_SYSTEM_PROMPT = (
    "당신은 네이버 맛집 블로그 작성 스타일 전문가입니다. "
    "사용자 피드백을 반영하여 스타일 가이드를 JSON 형식으로만 응답하세요. "
    "반드시 기존 JSON 구조를 유지하고 필요한 부분만 수정하세요."
)


def load_current_guide() -> dict:
    """Load the current style guide from disk.

    Returns:
        Parsed style guide as a dict. Returns empty dict if file is missing.
    """
    if not STYLE_GUIDE_PATH.exists():
        logger.warning("style_guide.json not found — returning empty dict")
        return {}
    return json.loads(STYLE_GUIDE_PATH.read_text(encoding="utf-8"))


def save_guide(new_guide: dict) -> None:
    """Atomically write the style guide to disk.

    Uses a temp file + rename to prevent partial writes.

    Args:
        new_guide: Updated style guide dict to persist.
    """
    new_guide["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    STYLE_GUIDE_PATH.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(dir=STYLE_GUIDE_PATH.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(new_guide, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, STYLE_GUIDE_PATH)
    except Exception:
        Path(tmp_path).unlink(missing_ok=True)
        raise
    logger.info("style_guide.json saved")


def build_update_prompt(feedback: str, current_guide: dict) -> str:
    """Build a Claude prompt for updating the style guide based on user feedback.

    Args:
        feedback: Raw user feedback text.
        current_guide: Current style guide dict.

    Returns:
        Formatted prompt string.
    """
    guide_str = json.dumps(current_guide, ensure_ascii=False, indent=2)
    return (
        f"현재 스타일 가이드:\n```json\n{guide_str}\n```\n\n"
        f"사용자 피드백: {feedback}\n\n"
        "위 피드백을 반영하여 스타일 가이드를 수정해주세요. "
        "반드시 전체 JSON만 응답하고 다른 텍스트는 포함하지 마세요."
    )


def update_style_guide(feedback: str, current_guide: dict) -> dict:
    """Call Claude to produce an updated style guide from user feedback.

    Args:
        feedback: User feedback text.
        current_guide: Current style guide dict.

    Returns:
        Updated style guide dict parsed from Claude's JSON response.

    Raises:
        json.JSONDecodeError: If Claude's response is not valid JSON.
    """
    client = ClaudeClient()
    prompt = build_update_prompt(feedback, current_guide)
    raw = client.call_text(prompt, system=_SYSTEM_PROMPT, max_tokens=3000)

    # Strip markdown fences if present
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    new_guide = json.loads(cleaned)
    logger.info("Style guide updated via Claude feedback")
    return new_guide


def merge_extracted_style(
    current_guide: dict,
    extracted_style: dict,
    selected_sections: list[str],
    merge_strategy: str = "selective",
) -> tuple[dict, str]:
    """Merge selected sections from an extracted style into the current guide.

    Args:
        current_guide: Current style guide dict.
        extracted_style: Style dict extracted from a blog URL analysis.
        selected_sections: List of top-level keys to apply from extracted_style.
        merge_strategy: Merge mode — currently only "selective" is supported.

    Returns:
        Tuple of (updated guide dict, diff summary string).
    """
    import copy

    updated = copy.deepcopy(current_guide)
    applied: list[str] = []

    for section in selected_sections:
        value = extracted_style.get(section)
        if value is None:
            continue
        # Remove confidence metadata before saving
        if isinstance(value, dict):
            value = {k: v for k, v in value.items() if not k.startswith("_")}
        updated[section] = value
        applied.append(section)

    diff = f"적용된 섹션: {', '.join(applied)}" if applied else "변경 없음"
    logger.info(diff)
    return updated, diff
