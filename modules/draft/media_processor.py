"""Image preprocessing for Module 2 — resize and Base64 encoding.

Supported formats: JPEG, PNG, WEBP.
"""

import base64
import io
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from core.logger import setup_logger

logger = setup_logger("draft")

_SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
_MAX_DIMENSION = 1024  # pixels


@dataclass
class ProcessedMedia:
    """A preprocessed image ready for Claude Vision API.

    Attributes:
        path: Original file path.
        b64_data: Base64-encoded image bytes.
        media_type: MIME type string (e.g. "image/jpeg").
    """

    path: Path
    b64_data: str
    media_type: str


def process_images(file_paths: list[Path]) -> list[ProcessedMedia]:
    """Resize and encode all supported images in the given list.

    Args:
        file_paths: List of image file paths to process.

    Returns:
        List of ProcessedMedia for files that are supported and readable.
    """
    results: list[ProcessedMedia] = []
    for path in file_paths:
        if path.suffix.lower() not in _SUPPORTED_EXTENSIONS:
            logger.debug(f"Skipping unsupported file: {path.name}")
            continue
        try:
            image_bytes = resize_image(path)
            media_type = _media_type(path)
            b64 = encode_to_base64(image_bytes)
            results.append(ProcessedMedia(path=path, b64_data=b64, media_type=media_type))
            logger.debug(f"Processed image: {path.name}")
        except Exception as exc:
            logger.error(f"Failed to process {path.name}: {exc}")
    return results


def resize_image(path: Path, max_size: int = _MAX_DIMENSION) -> bytes:
    """Open an image and resize it so the longest side is at most max_size.

    Args:
        path: Path to the image file.
        max_size: Maximum pixel dimension for the longest side.

    Returns:
        JPEG-encoded image bytes after resizing.
    """
    with Image.open(path) as img:
        img = img.convert("RGB")
        w, h = img.size
        if max(w, h) > max_size:
            scale = max_size / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return buf.getvalue()


def encode_to_base64(image_bytes: bytes) -> str:
    """Encode raw image bytes to a Base64 string.

    Args:
        image_bytes: Raw bytes of the image.

    Returns:
        Base64-encoded string.
    """
    return base64.standard_b64encode(image_bytes).decode("utf-8")


def _media_type(path: Path) -> str:
    """Return the MIME type based on file extension.

    Args:
        path: Image file path.

    Returns:
        MIME type string. Defaults to "image/jpeg" for unknown extensions.
    """
    mapping = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    return mapping.get(path.suffix.lower(), "image/jpeg")
