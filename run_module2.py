"""Module 2 entry point — starts the watchdog file watcher."""

from config import INPUT_DIR
from modules.draft.watcher import start_watching

if __name__ == "__main__":
    start_watching(INPUT_DIR)
