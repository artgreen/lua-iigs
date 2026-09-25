#!/usr/bin/env python3
"""DEPRECATED: use 'make hardware-suite KIT=luac RELEASE=<dir>' (or BUILD=<id>).

The LUACPROBE 1 batch and preflight now come from tools/iigsbuild/kits.py;
the generated batch commands are unchanged.
"""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from iigsbuild.cli import main  # noqa: E402
from iigsbuild.kits import luac_batch as batch  # noqa: E402,F401  (compatibility)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-dir", required=True)
    parser.add_argument("--sdk")
    parser.add_argument("--iix")
    parser.add_argument("--prefix", default="20:")
    args = parser.parse_args()
    print("tools/luac-test-kit.py is deprecated; forwarding to make hardware-suite KIT=luac.", file=sys.stderr)
    if args.iix:
        import os
        os.environ["IIX"] = args.iix
    raise SystemExit(main((["--sdk", args.sdk] if args.sdk else []) +
                          ["hardware-suite", "--kit", "luac", "--release", args.release_dir,
                           "--prefix", args.prefix or "none"]))
