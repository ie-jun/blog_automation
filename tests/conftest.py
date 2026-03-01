"""Pytest configuration for blog_automation tests.

Sets dummy environment variables before any module is imported so that
Settings() validation succeeds even without a real .env file.
"""

import os

import pytest


def pytest_configure(config: object) -> None:  # noqa: ANN001
    """Inject minimal dummy env vars required by Settings before collection."""
    _dummy: dict[str, str] = {
        "ANTHROPIC_API_KEY": "test-anthropic-key",
        "NAVER_CLIENT_ID": "test-naver-id",
        "NAVER_CLIENT_SECRET": "test-naver-secret",
        "NAVER_ID": "test-user",
        "NAVER_PASSWORD": "test-pass",
    }
    for key, value in _dummy.items():
        os.environ.setdefault(key, value)

    # Register asyncio marker for pytest-asyncio
    config.addinivalue_line("markers", "asyncio: mark test as async")
