#!/usr/bin/env python3
"""Run Lua scripts in an isolated scratch directory; never swallow failures."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from test_support import FAILURE, TESTS, validate

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lua", type=Path, default=ROOT / "build/lua")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--expect-failure", action="store_true")
    parser.add_argument("tests", nargs="*", default=list(TESTS))
    args = parser.parse_args()
    parent = ROOT / "build/test-runs"
    parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(dir=parent))
    shutil.copytree(ROOT / "tests", work / "tests")
    (work / "tests/libs/P1").mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, GOLDEN_GATE=os.environ.get("GOLDEN_GATE", str(ROOT / ".orca-sdk-2.2.1")))
    failed = False
    for test in args.tests:
        if not (work / "tests" / (test + ".lua")).is_file():
            parser.error(f"No test script: {test}")
        try:
            result = subprocess.run(["iix", "--memcheck", str(args.lua.resolve()), "-E", test + ".lua"],
                                    cwd=work / "tests", env=env, stdin=subprocess.DEVNULL,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    timeout=args.timeout)
            output = result.stdout.decode(errors="replace")
            (work / (test + ".log")).write_text(output)
            if args.expect_failure:
                # Expected Lua error is not permission to ignore memory corruption.
                if FAILURE.search(output) or result.returncode == 0:
                    raise ValueError("corruption or unexpected pass; update expected-failure list")
                print(f"{test}: expected failure (see log)")
                continue
            if result.returncode:
                raise ValueError(f"exit status {result.returncode}")
            if test in TESTS:
                check = validate(test, output)
                print(f"{test}: {check['status']}")
                for skip in check["skips"]:
                    print(f"  {skip}")
            elif FAILURE.search(output):
                raise ValueError("diagnostic failure")
            else:
                print(f"{test}: completed (exit/memory checks only)")
        except (ValueError, subprocess.TimeoutExpired) as exc:
            failed = True
            print(f"{test}: FAILED: {exc}")
    print(f"Logs: {work}")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
