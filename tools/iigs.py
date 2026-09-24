#!/usr/bin/env python3
"""Launcher for the shared build tooling; run 'make help' for commands."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from iigsbuild.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
