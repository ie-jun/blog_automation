"""APScheduler entry point — runs Module 1 automatically every day at 09:00 KST."""

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from core.logger import setup_logger
from modules.neighbor.runner import run_neighbor_module

logger = setup_logger("scheduler")


def _job_neighbor() -> None:
    """Scheduled job that triggers the Module 1 neighbor addition pipeline."""
    logger.info("Scheduler: running Module 1 neighbor job")
    result = run_neighbor_module()
    logger.info(
        f"Scheduler: Module 1 done — "
        f"searched={result.total_searched}, requested={result.total_requested}"
    )


if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone="Asia/Seoul")
    scheduler.add_job(
        _job_neighbor,
        trigger=CronTrigger(hour=9, minute=0),
        id="neighbor_daily",
        name="Daily neighbor addition (Module 1)",
        replace_existing=True,
    )

    logger.info("Scheduler started — Module 1 runs daily at 09:00 KST")
    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
