#!/usr/bin/env python3
"""DEPRECATED: use 'make suite' (local run) and 'make hardware-suite' (kit).

  run --lua EXE [--group G]   ->  make suite EXE=EXE GROUP=G
  package --lua EXE           ->  make hardware-suite KIT=suite EXES="lua=EXE"
"""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from iigsbuild.cli import main  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "package"))
    parser.add_argument("--lua", required=True)
    parser.add_argument("--group", default="full")
    parser.add_argument("--iix")
    parser.add_argument("--timeout", default="1800")
    parser.add_argument("--sdk")
    args = parser.parse_args()
    print(f"tools/test-suite.py is deprecated; forwarding '{args.action}'.", file=sys.stderr)
    if args.iix:
        import os
        os.environ["IIX"] = args.iix
    base = ["--sdk", args.sdk] if args.sdk else []
    if args.action == "run":
        raise SystemExit(main(base + ["suite", "--exe", args.lua, "--group", args.group, "--timeout", args.timeout]))
    raise SystemExit(main(base + ["hardware-suite", "--kit", "suite", "--group", args.group,
                                  "--exe", "lua=" + args.lua]))
