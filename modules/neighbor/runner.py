"""Module 1 orchestrator — search, filter, add neighbors, save log."""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from config import LOGS_DIR, settings
from core.logger import setup_logger
from modules.neighbor.automator import add_neighbors_batch
from modules.neighbor.filter import filter_bloggers
from modules.neighbor.searcher import search_food_bloggers

logger = setup_logger("neighbor")

_SEARCH_KEYWORDS = ["맛집", "서울 맛집", "음식 리뷰"]


@dataclass
class NeighborRunResult:
    """Summary result of a single Module 1 run."""

    date: str
    total_searched: int
    total_requested: int
    daily_limit: int
    entries: list[dict] = field(default_factory=list)
    log_path: Path | None = None


def run_neighbor_module() -> NeighborRunResult:
    """Execute the full Module 1 pipeline synchronously.

    Wraps the async pipeline in asyncio.run() for use by the scheduler.

    Returns:
        NeighborRunResult with counts and log file path.
    """
    return asyncio.run(_async_run())


async def _async_run() -> NeighborRunResult:
    """Async pipeline: search → filter → add neighbors → save log."""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    limit = settings.neighbor_add_daily_limit

    # 1. Search
    bloggers = search_food_bloggers(_SEARCH_KEYWORDS)

    # 2. Filter
    eligible = filter_bloggers(bloggers)

    # 3. Add neighbors (respects daily limit)
    entries = await add_neighbors_batch(eligible, daily_limit=limit)

    # 4. Add timestamps
    now_iso = datetime.now(timezone.utc).isoformat()
    for entry in entries:
        entry["timestamp"] = now_iso

    result = NeighborRunResult(
        date=today,
        total_searched=len(bloggers),
        total_requested=len([e for e in entries if e["status"] == "success"]),
        daily_limit=limit,
        entries=entries,
    )

    result.log_path = save_result(result, today)
    logger.info(
        f"Module 1 done — searched={result.total_searched} "
        f"requested={result.total_requested}/{limit}"
    )
    return result


def save_result(result: NeighborRunResult, date: str) -> Path:
    """Persist the run result as a JSON log file.

    Args:
        result: NeighborRunResult to serialize.
        date: Date string (YYYYMMDD) for the filename.

    Returns:
        Path to the saved log file.
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / f"neighbor_{date}.json"

    payload = {
        "date": result.date,
        "total_searched": result.total_searched,
        "total_requested": result.total_requested,
        "daily_limit": result.daily_limit,
        "entries": result.entries,
    }
    log_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"Neighbor log saved: {log_path}")
    return log_path
