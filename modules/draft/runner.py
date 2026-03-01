"""Module 2 orchestrator — coordinates image processing, draft generation, and posting."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from config import OUTPUT_DIR
from core.logger import setup_logger
from modules.draft.draft_generator import generate_draft, load_style_guide
from modules.draft.media_processor import process_images
from modules.draft.poster import post_to_naver_blog

logger = setup_logger("draft")

_SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


@dataclass
class DraftResult:
    """Result of a single draft generation run."""

    success: bool
    folder_name: str
    draft_path: Path | None = None
    post_url: str = ""
    error: str = ""


async def run_draft_module(folder_path: Path) -> DraftResult:
    """Full pipeline: images → draft text → Naver blog post (private).

    Args:
        folder_path: Subfolder under input/ containing images and done.txt.

    Returns:
        DraftResult with success status, saved draft path, and post URL.
    """
    folder_name = folder_path.name
    logger.info(f"Starting draft pipeline for: {folder_name!r}")

    try:
        # Collect image files
        image_paths = sorted(
            p for p in folder_path.iterdir()
            if p.suffix.lower() in _SUPPORTED_EXTENSIONS
        )
        if not image_paths:
            return DraftResult(success=False, folder_name=folder_name,
                               error="No images found in folder")

        # Process images
        media_list = process_images(image_paths)
        if not media_list:
            return DraftResult(success=False, folder_name=folder_name,
                               error="All images failed preprocessing")

        # Generate draft
        style_guide = load_style_guide()
        restaurant_name = folder_name.replace("_", " ")
        draft_text = generate_draft(media_list, style_guide, restaurant_name)

        # Parse title from draft (first line starting with "제목:")
        title, body = _split_title_and_body(draft_text, folder_name)

        # Save draft locally
        draft_path = save_draft_to_output(draft_text, folder_name)

        # Post to Naver blog (private)
        post_url = await post_to_naver_blog(title, body, image_paths)

        # Move done.txt to processed to prevent re-triggering
        done_txt = folder_path / "done.txt"
        processed_dir = folder_path / "processed"
        processed_dir.mkdir(exist_ok=True)
        if done_txt.exists():
            done_txt.rename(processed_dir / "done.txt")

        return DraftResult(
            success=True,
            folder_name=folder_name,
            draft_path=draft_path,
            post_url=post_url,
        )

    except Exception as exc:
        logger.error(f"Draft pipeline failed for {folder_name!r}: {exc}")
        return DraftResult(success=False, folder_name=folder_name, error=str(exc))


def save_draft_to_output(content: str, folder_name: str) -> Path:
    """Save the generated draft text to the output directory.

    Args:
        content: Draft text content.
        folder_name: Input subfolder name used as the base filename.

    Returns:
        Path to the saved draft file.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{folder_name}_draft_{timestamp}.md"
    path = OUTPUT_DIR / filename
    path.write_text(content, encoding="utf-8")
    logger.info(f"Draft saved: {path}")
    return path


def _split_title_and_body(draft_text: str, fallback_title: str) -> tuple[str, str]:
    """Extract the title and body from the generated draft.

    Expects the first line to be "제목: <title>".

    Args:
        draft_text: Full draft text from Claude.
        fallback_title: Title to use if no "제목:" line is found.

    Returns:
        Tuple of (title, body).
    """
    lines = draft_text.strip().split("\n")
    if lines and lines[0].startswith("제목:"):
        title = lines[0].replace("제목:", "").strip()
        body = "\n".join(lines[1:]).strip()
        return title, body
    return fallback_title, draft_text
