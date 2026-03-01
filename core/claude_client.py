"""Anthropic Claude API common client (text + vision).

Wraps the anthropic SDK with tenacity retry logic for rate limits and timeouts.
"""

import base64
from pathlib import Path

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings
from core.logger import setup_logger

logger = setup_logger("claude_client")


class ClaudeClient:
    """Shared Claude API client used by Module 2 and Module 3.

    Attributes:
        model: Claude model name loaded from config.
        client: anthropic.Anthropic SDK instance.
    """

    def __init__(self) -> None:
        """Initialize the Claude client with settings from config."""
        self.model = settings.claude_model
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def call_text(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 2000,
    ) -> str:
        """Send a text-only request to Claude.

        Args:
            prompt: User message content.
            system: Optional system prompt.
            max_tokens: Maximum tokens for the response.

        Returns:
            Claude's response as a plain string.

        Raises:
            anthropic.APIError: On non-retryable API errors.
        """
        logger.debug(f"call_text | model={self.model} | prompt_len={len(prompt)}")

        kwargs: dict = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        response = self.client.messages.create(**kwargs)
        return response.content[0].text

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def call_vision(
        self,
        prompt: str,
        image_b64_list: list[str],
        system: str = "",
        max_tokens: int = 2000,
        media_type: str = "image/jpeg",
    ) -> str:
        """Send a vision request with base64-encoded images to Claude.

        Args:
            prompt: User message describing what to analyze.
            image_b64_list: List of base64-encoded image strings.
            system: Optional system prompt.
            max_tokens: Maximum tokens for the response.
            media_type: MIME type for all images (e.g. "image/jpeg", "image/png").

        Returns:
            Claude's response as a plain string.

        Raises:
            anthropic.APIError: On non-retryable API errors.
        """
        logger.debug(
            f"call_vision | model={self.model} | images={len(image_b64_list)}"
        )

        content: list[dict] = []
        for b64 in image_b64_list:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": b64,
                },
            })
        content.append({"type": "text", "text": prompt})

        kwargs: dict = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": content}],
        }
        if system:
            kwargs["system"] = system

        response = self.client.messages.create(**kwargs)
        return response.content[0].text

    @staticmethod
    def encode_image_to_b64(image_path: Path) -> str:
        """Encode an image file to a base64 string.

        Args:
            image_path: Path to the image file.

        Returns:
            Base64-encoded string of the image bytes.
        """
        with open(image_path, "rb") as f:
            return base64.standard_b64encode(f.read()).decode("utf-8")
