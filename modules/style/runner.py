"""Module 3 orchestrators for style update, URL analysis, and style merge."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from core.logger import setup_logger
from modules.style import history_manager, style_updater

logger = setup_logger("style")


@dataclass
class StyleUpdateResult:
    """Result of a style guide feedback update."""

    success: bool
    diff_summary: str
    updated_at: str
    updated_guide: dict = field(default_factory=dict)
    error: str = ""


@dataclass
class UrlAnalysisResult:
    """Result of a blog URL style analysis."""

    success: bool
    session_id: str
    post_title: str
    analysis_summary: str
    style_sections: dict
    error: str = ""


@dataclass
class StyleMergeResult:
    """Result of merging extracted style sections into the current guide."""

    success: bool
    applied_sections: list[str]
    diff_summary: str
    updated_at: str
    error: str = ""


def run_style_module(feedback: str) -> StyleUpdateResult:
    """Update the style guide based on user feedback.

    Args:
        feedback: Raw feedback text from the web UI.

    Returns:
        StyleUpdateResult with success status and diff summary.
    """
    try:
        current = style_updater.load_current_guide()
        new_guide = style_updater.update_style_guide(feedback, current)
        style_updater.save_guide(new_guide)
        history_manager.save_to_history(current, new_guide, feedback)

        return StyleUpdateResult(
            success=True,
            diff_summary=history_manager._build_diff_summary(current, new_guide),
            updated_at=new_guide.get("updated_at", ""),
            updated_guide=new_guide,
        )
    except Exception as exc:
        logger.error(f"run_style_module failed: {exc}")
        return StyleUpdateResult(success=False, diff_summary="", updated_at="", error=str(exc))


async def run_url_analysis_module(
    url: str,
    analysis_cache: dict,
    session_ttl: int = 600,
) -> UrlAnalysisResult:
    """Crawl a Naver blog post URL and extract style information.

    Args:
        url: Public Naver blog post URL to analyze.
        analysis_cache: Shared in-memory dict for caching analysis sessions.
        session_ttl: Cache TTL in seconds.

    Returns:
        UrlAnalysisResult with session_id and extracted style sections.
    """
    from modules.style.url_analyzer import fetch_post_content, analyze_style_from_post
    from core.claude_client import ClaudeClient

    try:
        post = await fetch_post_content(url)
        current_guide = style_updater.load_current_guide()
        client = ClaudeClient()
        extracted = analyze_style_from_post(post, current_guide, client)

        session_id = str(uuid.uuid4())
        analysis_cache[session_id] = {
            "extracted_style": extracted,
            "source_url": url,
            "post_title": post.title,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": datetime.now(timezone.utc).timestamp() + session_ttl,
        }

        return UrlAnalysisResult(
            success=True,
            session_id=session_id,
            post_title=post.title,
            analysis_summary=f"총 {len(extracted)} 섹션 추출 완료",
            style_sections=extracted,
        )
    except Exception as exc:
        logger.error(f"run_url_analysis_module failed: {exc}")
        return UrlAnalysisResult(
            success=False,
            session_id="",
            post_title="",
            analysis_summary="",
            style_sections={},
            error=str(exc),
        )


def run_style_merge_module(
    extracted_style: dict,
    selected_sections: list[str],
    source_url: str,
) -> StyleMergeResult:
    """Merge selected extracted style sections into the current guide.

    Args:
        extracted_style: Style dict returned from URL analysis.
        selected_sections: Keys of sections the user selected to apply.
        source_url: Source URL used for history logging.

    Returns:
        StyleMergeResult with applied sections and diff summary.
    """
    try:
        current = style_updater.load_current_guide()
        updated, diff = style_updater.merge_extracted_style(
            current, extracted_style, selected_sections
        )
        style_updater.save_guide(updated)
        feedback_label = f"URL 분석 적용: {source_url} → {', '.join(selected_sections)} 섹션"
        history_manager.save_to_history(current, updated, feedback_label)

        return StyleMergeResult(
            success=True,
            applied_sections=selected_sections,
            diff_summary=diff,
            updated_at=updated.get("updated_at", ""),
        )
    except Exception as exc:
        logger.error(f"run_style_merge_module failed: {exc}")
        return StyleMergeResult(
            success=False,
            applied_sections=[],
            diff_summary="",
            updated_at="",
            error=str(exc),
        )
