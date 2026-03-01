"""Central configuration for blog_automation.

Loads all settings from environment variables via pydantic-settings.
"""

from pathlib import Path

from pydantic import ConfigDict
from pydantic_settings import BaseSettings

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
STYLE_GUIDE_PATH = DATA_DIR / "style_guide.json"
STYLE_GUIDE_HISTORY_PATH = DATA_DIR / "style_guide_history.json"


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
class Settings(BaseSettings):
    """Application settings loaded from .env file."""

    # Anthropic
    anthropic_api_key: str
    claude_model: str = "claude-sonnet-4-6"

    # Naver Open API
    naver_client_id: str
    naver_client_secret: str

    # Naver login
    naver_id: str
    naver_password: str

    # Module 1
    neighbor_add_daily_limit: int = 20
    naver_search_daily_limit: int = 1000

    # Web server (Module 3)
    web_host: str = "127.0.0.1"
    web_port: int = 8000

    # URL analysis session TTL (seconds)
    url_analysis_session_ttl: int = 600

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
