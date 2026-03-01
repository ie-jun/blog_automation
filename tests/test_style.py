"""Unit tests for Module 3 — style guide manager."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from modules.style import history_manager, style_updater
from modules.style.history_manager import _build_diff_summary


# ---------------------------------------------------------------------------
# style_updater
# ---------------------------------------------------------------------------

class TestStyleUpdater:
    def test_load_current_guide_missing_file(self, tmp_path: Path) -> None:
        with patch("modules.style.style_updater.STYLE_GUIDE_PATH", tmp_path / "missing.json"):
            result = style_updater.load_current_guide()
        assert result == {}

    def test_save_and_load_guide(self, tmp_path: Path) -> None:
        guide_path = tmp_path / "style_guide.json"
        guide = {"tone": {"overall": "친근한 스타일"}, "version": "1.0"}

        with patch("modules.style.style_updater.STYLE_GUIDE_PATH", guide_path):
            style_updater.save_guide(guide)
            loaded = style_updater.load_current_guide()

        assert loaded["tone"]["overall"] == "친근한 스타일"
        assert "updated_at" in loaded

    def test_merge_extracted_style_selective(self) -> None:
        current = {"tone": "old", "hashtags": {"count": 5}, "structure": "old_struct"}
        extracted = {
            "tone": "new_tone",
            "hashtags": {"count": 10, "_confidence": 0.9},
            "structure": "new_struct",
        }
        updated, diff = style_updater.merge_extracted_style(
            current, extracted, selected_sections=["tone", "hashtags"]
        )
        assert updated["tone"] == "new_tone"
        assert updated["hashtags"]["count"] == 10
        assert "_confidence" not in updated["hashtags"]
        assert updated["structure"] == "old_struct"  # not selected
        assert "tone" in diff
        assert "hashtags" in diff

    def test_merge_empty_selection_returns_no_change(self) -> None:
        current = {"tone": "old"}
        extracted = {"tone": "new"}
        updated, diff = style_updater.merge_extracted_style(current, extracted, [])
        assert updated["tone"] == "old"
        assert diff == "변경 없음"


# ---------------------------------------------------------------------------
# history_manager
# ---------------------------------------------------------------------------

class TestHistoryManager:
    def test_save_and_load_history(self, tmp_path: Path) -> None:
        history_path = tmp_path / "history.json"
        old = {"tone": "old"}
        new = {"tone": "new"}

        with patch("modules.style.history_manager.STYLE_GUIDE_HISTORY_PATH", history_path):
            history_manager.save_to_history(old, new, "테스트 피드백")
            entries = history_manager.load_history()

        assert len(entries) == 1
        assert entries[0]["feedback"] == "테스트 피드백"
        assert entries[0]["diff_summary"] == "변경된 섹션: tone"

    def test_build_diff_summary_no_change(self) -> None:
        guide = {"a": 1, "b": 2}
        assert _build_diff_summary(guide, guide) == "변경 없음"

    def test_build_diff_summary_changed_keys(self) -> None:
        old = {"tone": "a", "hashtags": {"count": 5}}
        new = {"tone": "b", "hashtags": {"count": 5}}
        summary = _build_diff_summary(old, new)
        assert "tone" in summary

    def test_load_history_empty_file(self, tmp_path: Path) -> None:
        with patch("modules.style.history_manager.STYLE_GUIDE_HISTORY_PATH",
                   tmp_path / "missing.json"):
            assert history_manager.load_history() == []
