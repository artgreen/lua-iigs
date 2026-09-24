"""Run the reusable Lua suite (tests/suite.json + tests/suite.lua) locally
against an explicitly selected executable. The executable is copied, never
rebuilt. Stock GoldenGate cannot pass the complete I/O group (repeated-EOF
abort, text translation); use GROUP=runtime for the supported subset.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import time

from .common import TEST_RUNS, ROOT, BuildError, new_unique_dir, rel, say, sha256, sha256_file, utc_iso, write_json
from .contracts import lua_value, suite_manifest, validate_suite


def prepare(work: Path, exe: Path, data: dict) -> Path:
    stage = work / "tests"
    stage.mkdir()
    shutil.copyfile(exe, stage / "luatest")
    (stage / "suitecfg.lua").write_text("return " + lua_value(data) + "\n")
    shutil.copyfile(ROOT / "tests/suite.lua", stage / "test.lua")
    for name in [*data["tests"], "tracegc"]:
        shutil.copyfile(ROOT / "tests" / (name + ".lua"), stage / (name + ".lua"))
    return stage


def run_suite(args) -> int:
    from .runtests import EXECUTABLES
    from .toolchain import Toolchain
    data = suite_manifest()
    if args.group not in data["groups"]:
        raise BuildError(f"unknown group {args.group!r}: {', '.join(data['groups'])}")
    tc = Toolchain.discover(args.sdk)
    tc.require_compiler()
    if args.exe:
        exe, subject = args.exe.resolve(), {"kind": "explicit executable"}
    elif args.build:
        from .identified import resolve
        build = resolve(args.build)
        key = EXECUTABLES["luatrace" if args.config == "luatrace" else "lua"]
        exe, subject = build.path(key), {"kind": "identified", "build_id": build.id}
    else:
        from .cli import cmd_build
        target = "luatrace" if args.config == "luatrace" else "lua"
        cmd_build(type("Args", (), {"targets": [target], "sdk": args.sdk}))
        from .common import DEV
        exe, subject = DEV / EXECUTABLES[target], {"kind": "dev", "config": target}
    if not exe.is_file():
        raise BuildError(f"no executable at {exe}")
    work = new_unique_dir(TEST_RUNS, "suite-" + args.group)
    stage = prepare(work, exe, data)
    report = {"schema": "lua-iigs-suite-run/1", "utc": utc_iso(), "group": args.group, "subject": subject,
              "executable_sha256": sha256_file(exe), "suite_version": data["version"],
              "manifest_sha256": sha256((ROOT / "tests/suite.json").read_bytes()),
              "environment": "GoldenGate with --memcheck; not hardware",
              "emulator": tc.identity()["iix"]}
    say(f"Running suite group {args.group}; live log: {rel(work / 'suite.log')}")
    started = time.monotonic()
    failed = False
    try:
        with (work / "suite.log").open("wb") as log:
            result = subprocess.run([tc.iix, "--memcheck", str(stage / "luatest"), "-E", "-v", "test.lua", args.group],
                                    cwd=stage, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                    timeout=args.timeout, env=tc.env())
        report.update(exit_code=result.returncode, elapsed_seconds=round(time.monotonic() - started, 1))
        if result.returncode:
            raise ValueError(f"exit status {result.returncode}")
        report.update(validate_suite((work / "suite.log").read_text(errors="replace"), args.group, data["groups"]))
    except (ValueError, subprocess.TimeoutExpired) as exc:
        failed = True
        report.update(status="failed", error=str(exc))
        say(f"FAILED: {exc}")
    write_json(work / "report.json", report)
    if not failed:
        say(f"Suite {args.group}: {report['status']} ({len(report['tests'])} tests). Report: {rel(work / 'report.json')}")
    return int(failed)
