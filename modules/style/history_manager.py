"""Style guide history manager.

Appends change entries to style_guide_history.json whenever the guide is updated.
"""

import json
from datetime import datetime, timezone

from config import STYLE_GUIDE_HISTORY_PATH
from core.logger import setup_logger

logger = setup_logger("style")


def save_to_history(old_guide: dict, new_guide: dict, feedback: str) -> None:
    """Append a change entry to the style guide history file.

    Args:
        old_guide: Style guide dict before the update.
        new_guide: Style guide dict after the update.
        feedback: User feedback text or a descriptive string for URL-based updates.
    """
    STYLE_GUIDE_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)

    history: list[dict] = []
    if STYLE_GUIDE_HISTORY_PATH.exists():
        try:
            history = json.loads(STYLE_GUIDE_HISTORY_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("history file corrupted — starting fresh")

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "feedback": feedback,
        "old_guide": old_guide,
        "new_guide": new_guide,
        "diff_summary": _build_diff_summary(old_guide, new_guide),
    }
    history.append(entry)

    STYLE_GUIDE_HISTORY_PATH.write_text(
        json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info(f"History saved ({len(history)} total entries)")


def load_history(limit: int = 20) -> list[dict]:
    """Load the most recent style guide history entries.

    Args:
        limit: Maximum number of entries to return (most recent first).

    Returns:
        List of history entry dicts, newest first.
    """
    if not STYLE_GUIDE_HISTORY_PATH.exists():
        return []

    try:
        history: list[dict] = json.loads(
            STYLE_GUIDE_HISTORY_PATH.read_text(encoding="utf-8")
        )
        return list(reversed(history))[:limit]
    except json.JSONDecodeError:
        logger.error("Failed to parse history file")
        return []


def _build_diff_summary(old: dict, new: dict) -> str:
    """Build a human-readable summary of top-level key changes.

    Args:
        old: Previous guide dict.
        new: Updated guide dict.

    Returns:
        Summary string listing changed top-level keys.
    """
    changed = [k for k in new if old.get(k) != new.get(k)]
    if not changed:
        return "변경 없음"
    return f"변경된 섹션: {', '.join(changed)}"
