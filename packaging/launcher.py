"""Frozen executable entry point; application behavior stays in app.startup."""
import multiprocessing
import sys

from app.startup import main


if __name__ == "__main__":
    multiprocessing.freeze_support()
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FontFinderLocal could not start: {exc}", file=sys.stderr)
        raise SystemExit(1)
