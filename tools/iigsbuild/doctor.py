"""'make doctor': validate the SDK, compiler, emulator, and packaging tools
with live probes rather than presence checks alone."""
from __future__ import annotations

import os
from pathlib import Path
import platform
import subprocess
import sys

from .common import BUILD, ROOT, TEST_RUNS, BuildError, new_unique_dir, remove_tree, say
from .concurrency import RECORD, default_jobs
from .toolchain import Toolchain, orca_c_version

PROBE_C = b'#include <stdio.h>\nint main(void) { printf("DOCTOR %d\\n", 6 * 7); return 0; }\n'


class Report:
    def __init__(self):
        self.rows, self.failed = [], False

    def add(self, status: str, item: str, detail: str) -> None:
        self.rows.append((status, item, detail))
        self.failed |= status == "FAIL"
        say(f"  [{status:4}] {item:22} {detail}")


def run(argv, cwd, env=None, timeout=60):
    try:
        return subprocess.run([str(a) for a in argv], cwd=cwd, env=env, capture_output=True,
                              text=True, timeout=timeout, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(argv, 127, "", f"{Path(str(argv[0])).name}: {exc}")


def doctor(sdk_arg=None) -> int:
    rep = Report()
    say("Lua IIgs build doctor")
    ok = sys.version_info >= (3, 9)
    rep.add("OK" if ok else "FAIL", "python", f"{platform.python_version()} ({sys.executable})"
            + ("" if ok else "; 3.9 or later required"))
    make = run(["make", "--version"], ROOT)
    rep.add("OK" if make.returncode == 0 else "FAIL", "make", (make.stdout.splitlines() or ["missing"])[0])
    local = ROOT / "local.mk"
    rep.add("OK", "local.mk", "present (untracked machine settings)" if local.is_file()
            else "absent; defaults and environment are used (see local.mk.example)")
    try:
        tc = Toolchain.discover(sdk_arg)
    except BuildError as exc:
        rep.add("FAIL", "ORCA/C SDK", str(exc))
        return summary(rep)
    version = orca_c_version(tc.sdk)
    good = version is not None and version.startswith("2.2.")
    rep.add("OK" if good else "FAIL", "ORCA/C SDK",
            f"{tc.sdk} via {tc.sdk_source}; ORCA/C {version or 'not found'}"
            + ("" if good else " (2.2.x required)"))
    for sub in ("Languages/Linker", "Libraries/ORCACDefs", "Libraries/ORCALib"):
        exists = (tc.sdk / sub).exists()
        rep.add("OK" if exists else "FAIL", "  " + sub, "present" if exists else "missing from SDK")
    if tc.iix:
        rep.add("OK", "iix (GoldenGate)", f"{tc.iix}; {tc.identity()['iix']}")
    else:
        rep.add("FAIL", "iix (GoldenGate)", "not found (set IIX or PATH)")
    if tc.iix and good:
        probe = new_unique_dir(TEST_RUNS, "doctor")
        try:
            (probe / "probe.c").write_bytes(PROBE_C)
            env = tc.env()
            steps = [run([tc.iix, "compile", "-I", "-P", "-D", "+O", "probe.c", "keep=probe"], probe, env),
                     run([tc.iix, "link", "probe", "KEEP=probe"], probe, env),
                     run([tc.iix, "probe"], probe, env)]
            passed = all(s.returncode == 0 for s in steps) and "DOCTOR 42" in steps[-1].stdout
            rep.add("OK" if passed else "FAIL", "compile/link/run",
                    "probe compiled with the selected SDK and ran in GoldenGate" if passed
                    else "probe failed: " + " | ".join((s.stdout + s.stderr).strip()[-120:] for s in steps))
        finally:
            remove_tree(probe)
        jobs, why = default_jobs(tc)
        rep.add("OK", "compile concurrency", f"JOBS default {jobs} ({why})")
    for name, path in (("acx", tc.acx), ("cp2", tc.cp2), ("nulib2", tc.nulib2)):
        rep.add("OK" if path else "FAIL", name, path or "not found (needed for packaging)")
    if tc.acx and tc.cp2 and tc.nulib2:
        rep.add(*packaging_probe(tc))
    stale = [p for p in ("src/parseconf.h",) if (ROOT / p).exists()]
    stale += sorted(str(p.relative_to(ROOT)) for p in (ROOT / "src").glob("*.a"))[:3]
    rep.add("WARN" if stale else "OK", "source tree", "legacy generated files present: "
            + ", ".join(stale) + " (make clean removes them)" if stale else "no generated files in src/")
    nas = Path(os.environ.get("NAS", "/Volumes/nas"))
    rep.add("OK", "transfer volume", f"{nas} is mounted" if nas.is_dir() else f"{nas} not mounted (only needed for make stage)")
    return summary(rep)


def packaging_probe(tc: Toolchain):
    """Round-trip a tiny image and archive, checking bytes and ProDOS metadata."""
    from .packaging import Member, build_container
    work = new_unique_dir(TEST_RUNS, "doctor-pack")
    try:
        members = [Member("PROBE", b"\x01\x02\x03", "EXE"), Member("NOTE.TXT", b"line\n", "TXT"),
                   Member("TEST", b"echo probe\n", "EXEC")]
        build_container(tc, work, "PROBE", "PROBE", members)
        return ("OK", "packaging round trip", "acx image + cp2 archive verified by extraction and metadata")
    except BuildError as exc:
        return ("FAIL", "packaging round trip", str(exc).splitlines()[0])
    finally:
        remove_tree(work)


def summary(rep: Report) -> int:
    if rep.failed:
        say("doctor: FAILED checks above must be fixed (see docs/BUILDING.md#setup).")
        return 1
    say("doctor: all required checks passed.")
    return 0
