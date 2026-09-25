"""Concurrency policy for ORCA compiler processes.

GoldenGate/ORCA concurrency is not assumed. Compiles run serially unless
'make verify-concurrency' has shown, for the exact current toolchain
fingerprint, that parallel compiles produce objects byte-identical to a
serial build (and that no tool writes to the shared ORCA work prefix 14:,
which GoldenGate maps to the process temporary directory). Links and
library creation are always serial; separate make invocations on the same
build directory are serialized by a lock.
"""
from __future__ import annotations

import os
from pathlib import Path

from .common import (BUILD, TEST_RUNS, BuildError, new_unique_dir, read_json, say, sha256_file,
                     utc_iso, write_json)
from .configs import get
from .toolchain import Toolchain

RECORD = BUILD / "local" / "concurrency.json"  # machine-local; survives make clean
MAX_JOBS = 8


def default_jobs(tc: Toolchain):
    """(jobs, reason). An explicit JOBS always wins."""
    explicit = os.environ.get("JOBS", "").strip()
    if explicit:
        if not explicit.isdigit() or int(explicit) < 1:
            raise BuildError(f"JOBS must be a positive integer, not {explicit!r}")
        return int(explicit), "JOBS"
    record = read_json(RECORD, {})
    if record.get("toolchain") == tc.fingerprint() and record.get("result") == "identical":
        return min(MAX_JOBS, os.cpu_count() or 1), "verified " + record.get("utc", "")
    return 1, "parallel compiles not verified for this toolchain (make verify-concurrency)"


def verify(tc: Toolchain, rounds: int = 2) -> dict:
    from .builder import ConfigBuild
    from .common import ROOT
    from .orca import Orca

    orca = Orca(tc)
    jobs = min(MAX_JOBS, os.cpu_count() or 1)
    if jobs < 2:
        raise BuildError("only one CPU is available; nothing to verify")
    work = new_unique_dir(TEST_RUNS, "concurrency")
    readonly_tmp = work / "readonly-tmp"
    readonly_tmp.mkdir()
    readonly_tmp.chmod(0o555)
    # Any write to ORCA prefix 14: (the temp directory) now fails loudly.
    orca.env["TMPDIR"] = str(readonly_tmp) + "/"
    try:
        return _compare(orca, work, readonly_tmp, jobs, rounds, tc)
    finally:
        readonly_tmp.chmod(0o755)


def _compare(orca, work, readonly_tmp, jobs, rounds, tc) -> dict:
    from .builder import ConfigBuild
    from .common import ROOT
    config = get("lua")
    say(f"Serial reference build in {work}")
    serial = ConfigBuild(orca, ROOT, config, work / "serial", jobs=1)
    serial.executable()
    reference = {p.name: sha256_file(p) for p in sorted(serial.obj.glob("*.a"))}
    reference["<executable>"] = sha256_file(serial.out / config.exe)
    results = []
    for index in range(rounds):
        say(f"Parallel build {index + 1}/{rounds} with {jobs} concurrent compiles")
        build = ConfigBuild(orca, ROOT, config, work / f"parallel{index + 1}", jobs=jobs)
        build.executable()
        got = {p.name: sha256_file(p) for p in sorted(build.obj.glob("*.a"))}
        got["<executable>"] = sha256_file(build.out / config.exe)
        diffs = sorted(k for k in set(reference) | set(got) if reference.get(k) != got.get(k))
        results.append({"round": index + 1, "differences": diffs})
    leftover = sorted(os.listdir(readonly_tmp))
    identical = all(not r["differences"] for r in results) and not leftover
    record = {"utc": utc_iso(), "toolchain": tc.fingerprint(), "jobs": jobs,
              "objects_compared": len(reference), "rounds": results,
              "temp_prefix_writes": leftover,
              "result": "identical" if identical else "different", "work": str(work)}
    write_json(RECORD, record)
    if not identical:
        raise BuildError(f"parallel compiles differed from serial; builds stay serial. See {RECORD}")
    say(f"Verified: {len(reference)} outputs byte-identical across serial and {rounds} parallel builds; "
        f"no writes to the ORCA work prefix. Default JOBS is now {jobs} for this toolchain.")
    return record
