"""Module 2 watchdog — monitors input/ for done.txt signals.

Directory structure expected:
    input/
    └── <게시글명>/
        ├── img1.jpg
        └── done.txt   ← triggers draft generation when created
"""

import asyncio
from pathlib import Path

from watchdog.events import FileSystemEventHandler, FileCreatedEvent
from watchdog.observers import Observer

from config import INPUT_DIR
from core.logger import setup_logger

logger = setup_logger("draft")


class InputFolderHandler(FileSystemEventHandler):
    """Watchdog event handler that reacts to done.txt file creation.

    Attributes:
        loop: Asyncio event loop used to schedule async draft jobs.
    """

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        """Initialize the handler.

        Args:
            loop: Running asyncio event loop.
        """
        super().__init__()
        self.loop = loop

    def on_created(self, event: FileCreatedEvent) -> None:
        """Called when a file is created inside input/.

        Triggers draft generation when done.txt appears inside a subfolder.

        Args:
            event: Watchdog file creation event.
        """
        if event.is_directory:
            return

        src_path = Path(event.src_path)
        if src_path.name != "done.txt":
            return

        folder_path = src_path.parent
        logger.info(f"done.txt detected in: {folder_path.name!r}")

        # Schedule async job on the running event loop
        asyncio.run_coroutine_threadsafe(
            _run_draft_job(folder_path), self.loop
        )


async def _run_draft_job(folder_path: Path) -> None:
    """Run the full draft generation pipeline for a given input subfolder.

    Args:
        folder_path: Path to the subfolder containing images and done.txt.
    """
    from modules.draft.runner import run_draft_module

    try:
        result = await run_draft_module(folder_path)
        if result.success:
            logger.info(f"Draft complete: {result.post_url}")
        else:
            logger.error(f"Draft failed: {result.error}")
    except Exception as exc:
        logger.error(f"Unhandled error in draft job: {exc}")


def start_watching(input_dir: Path = INPUT_DIR) -> None:
    """Start the blocking watchdog observer loop.

    Args:
        input_dir: Directory to monitor (default: INPUT_DIR from config).
    """
    input_dir.mkdir(parents=True, exist_ok=True)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    handler = InputFolderHandler(loop)
    observer = Observer()
    observer.schedule(handler, str(input_dir), recursive=True)
    observer.start()

    logger.info(f"Watching for done.txt in: {input_dir}")

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info("Watcher stopped by user")
    finally:
        observer.stop()
        observer.join()
        loop.close()
