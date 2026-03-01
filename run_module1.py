"""Module 1 entry point — runs one neighbor addition cycle immediately."""

from modules.neighbor.runner import run_neighbor_module

if __name__ == "__main__":
    result = run_neighbor_module()
    print(f"Done: searched={result.total_searched}, requested={result.total_requested}")
    if result.log_path:
        print(f"Log: {result.log_path}")
