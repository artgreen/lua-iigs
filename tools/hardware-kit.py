#!/usr/bin/env python3
"""DEPRECATED: replaced by 'make kit' (identify + test + package).

The historical kit layout (build/hardware/<utc>/) is preserved for existing
evidence. New identified builds live in build/builds/, test reports in
build/test-reports/, and packages in build/packages/. See docs/BUILDING.md.
"""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from iigsbuild.cli import main  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--sdk")
parser.add_argument("--acx")
parser.add_argument("--plain-name", help="ignored: package executable names are now fixed (LUA, LUATRACE, ...)")
args = parser.parse_args()
print("tools/hardware-kit.py is deprecated; running 'make kit' equivalent.", file=sys.stderr)
if args.plain_name:
    print("note: --plain-name is ignored; rename a copy for comparisons instead.", file=sys.stderr)
if args.acx:
    import os
    os.environ["ACX"] = args.acx
raise SystemExit(main((["--sdk", args.sdk] if args.sdk else []) + ["kit"]))
