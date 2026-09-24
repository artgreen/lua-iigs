"""Local regression checks ('make test') under GoldenGate memory checking.

Results are emulator results, never hardware results. Each check runs in
its own copy of the test files, with stdin closed, and must satisfy the
completion contracts in contracts.py. Intentional skips are reported.

Check groups:
  unit      Python contract/packaging/build-tool unit tests
  targeted  the 16 targeted regression scripts on full Lua
  luac      LUAC debug and stripped bytecode on both runtimes; clean
            rejection of syntax errors and excessive nesting; recovery
  compact   bytecode acceptance on parser-free Lua (tests/compact.json),
            plus source rejection from a script, stdin, and load()
  hosts     native embedding/C-hook host, allocator fault injection,
            bridge demo, and raw Memory Manager probe
  trace     the targeted scripts on the traced interpreter (trace contracts)
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Dict, List, Optional

from .common import (REPORTS, ROOT, TEST_RUNS, BuildError, digest_json, new_unique_dir, rel, say,
                     sha256_file, utc_iso, utc_stamp, write_json)
from .contracts import FAILURE, TESTS, compact_manifest, validate

DEFAULT_CHECKS = ("unit", "targeted", "luac", "compact", "hosts")
ALL_CHECKS = DEFAULT_CHECKS + ("trace",)
EXECUTABLES = {"lua": "lua/out/lua", "luasmall": "lua-small/out/luasmall", "luac": "luac/out/luac",
               "luatrace": "luatrace/out/luatrace", "iigshost": "lua/out/iigshost",
               "allocfail": "lua/out/allocfail", "bridge": "lua/out/bridge", "mmtest": "lua/out/mmtest",
               "memfree": "lua/out/memfree"}
NEEDS = {"targeted": ["lua"], "luac": ["luac", "lua", "luasmall"], "compact": ["luasmall", "luac"],
         "hosts": ["iigshost", "allocfail", "bridge", "mmtest", "memfree"], "trace": ["luatrace"],
         "unit": ["lua"]}
DEV_TARGETS = {"lua": "lua", "luasmall": "lua-small", "luac": "luac", "luatrace": "luatrace",
               "iigshost": "iigshost", "allocfail": "allocfail", "bridge": "bridge",
               "mmtest": "mmtest", "memfree": "memfree"}
CORRUPTION = re.compile(r"MemCheck:|\bBRK\b")


class Failed(Exception):
    pass


class Session:
    def __init__(self, tc, subject: dict, work: Path, timeout: int):
        self.tc, self.subject, self.work, self.timeout = tc, subject, work, timeout
        self.env = tc.env()
        self.results: List[dict] = []
        self.logs = work / "logs"
        self.logs.mkdir(parents=True, exist_ok=True)

    def exe(self, name: str) -> Path:
        return self.subject["paths"][name]

    def run(self, argv, cwd: Path, log: str, stdin: Optional[bytes] = None, memcheck=True):
        command = [self.tc.iix] + (["--memcheck"] if memcheck else []) + [str(a) for a in argv]
        try:
            result = subprocess.run(command, cwd=cwd, env=self.env, input=stdin if stdin is not None else b"",
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=self.timeout)
        except subprocess.TimeoutExpired as exc:
            (self.logs / log).write_bytes((exc.stdout or b"") + b"\n[local timeout]\n")
            raise Failed(f"local timeout after {self.timeout}s (not a hardware limit)") from exc
        (self.logs / log).write_bytes(result.stdout)
        return result.returncode, result.stdout.decode(errors="replace")

    def record(self, group: str, name: str, subject: str, fn) -> None:
        started = time.monotonic()
        entry = {"group": group, "name": name, "subject": subject}
        try:
            detail = fn() or {}
            entry.update(status=detail.pop("status", "passed"), **detail)
        except (Failed, ValueError, BuildError, OSError) as exc:
            entry.update(status="FAILED", error=str(exc))
        entry["seconds"] = round(time.monotonic() - started, 1)
        self.results.append(entry)
        extra = f" ({len(entry.get('skips', []))} skip lines)" if entry.get("skips") else ""
        say(f"  {group:8} {name:22} {entry['status']}{extra}" + (f": {entry['error']}" if "error" in entry else ""))

    def stage_tests(self, label: str) -> Path:
        stage = self.work / label
        shutil.copytree(ROOT / "tests", stage, ignore=shutil.ignore_patterns("*.py", "__pycache__", "libs"))
        (stage / "libs/P1").mkdir(parents=True, exist_ok=True)
        return stage

    # -- groups ----------------------------------------------------------------
    def script(self, group, exe_name, stage, test, traced=False, parser=None, args=(), label=None):
        def fn():
            rc, out = self.run([self.exe(exe_name), "-E", test + ".lua", *args], stage, f"{group}-{test}.log")
            if rc:
                raise Failed(f"exit status {rc}")
            check = validate(test, out, traced=traced, parser=parser)
            return {"status": check["status"], "skips": check["skips"]}
        self.record(group, label or test, exe_name, fn)

    def targeted(self, exe_name="lua", traced=False):
        group = "trace" if traced else "targeted"
        stage = self.stage_tests(group)
        for test in TESTS:
            self.script(group, exe_name, stage, test, traced=traced)

    def compile(self, stage: Path, source: str, output: str, strip: bool) -> None:
        argv = [self.exe("luac")] + (["-s"] if strip else []) + ["-o", output, source]
        rc, out = self.run(argv, stage, f"luac-{output}.log")
        if rc or CORRUPTION.search(out) or not (stage / output).is_file():
            raise Failed(f"luac failed on {source} (exit {rc})")

    def luac(self):
        stage = self.stage_tests("luac")
        for strip, form in ((False, "debug"), (True, "stripped")):
            for test, runtimes in (("hwsmoke", ["lua"]), ("numconv", ["lua", "luasmall"]),
                                   ("nosource", ["lua", "luasmall"])):
                chunk = f"{test}.{'lus' if strip else 'luo'}"

                def fn(test=test, chunk=chunk, strip=strip, runtimes=runtimes):
                    self.compile(stage, test + ".lua", chunk, strip)
                    for runtime in runtimes:
                        rc, out = self.run([self.exe(runtime), "-E", chunk], stage, f"luac-run-{runtime}-{chunk}.log")
                        if rc:
                            raise Failed(f"{runtime} exit status {rc}")
                        validate(test, out, parser=None if test != "nosource" else runtime == "lua")
                    return {"runtimes": runtimes}
                self.record("luac", f"{test} {form}", "luac+" + "+".join(runtimes), fn)
        (stage / "lcbad.lua").write_text("local x = = 1\n")
        (stage / "lcdeep.lua").write_text("return " + "(" * 500 + "1" + ")" * 500 + "\n")

        def rejected(source, pattern):
            def fn():
                rc, out = self.run([self.exe("luac"), "-p", source], stage, f"luac-reject-{source}.log")
                if rc == 0 or not re.search(pattern, out) or CORRUPTION.search(out):
                    raise Failed(f"expected clean rejection matching {pattern!r} (exit {rc})")
                return {"exit_code": rc}
            return fn
        self.record("luac", "syntax error rejected", "luac", rejected("lcbad.lua", r"unexpected symbol"))
        self.record("luac", "nesting rejected", "luac", rejected("lcdeep.lua", r"C stack overflow"))

        def recovery():
            self.compile(stage, "hwsmoke.lua", "again.luo", False)
            rc, out = self.run([self.exe("lua"), "-E", "again.luo"], stage, "luac-recovery.log")
            if rc:
                raise Failed(f"exit status {rc}")
            validate("hwsmoke", out)
        self.record("luac", "valid compile after errors", "luac+lua", recovery)

    def compact(self):
        plan = compact_manifest()
        for form, strip in (("debug", False), ("stripped", True)):
            stage = self.work / f"compact-{form}"
            stage.mkdir()
            (stage / "libs/P1").mkdir(parents=True)
            source_dir = self.work / f"compact-{form}-src"
            shutil.copytree(ROOT / "tests", source_dir, ignore=shutil.ignore_patterns("*.py", "__pycache__", "libs"))
            names = plan["groups"][form] + plan["helpers"]

            def build(names=names, source_dir=source_dir, stage=stage, strip=strip):
                for name in names:
                    self.compile(source_dir, name + ".lua", name + ".out", strip)
                    shutil.move(str(source_dir / (name + ".out")), str(stage / (name + ".lua")))
                return {"chunks": len(names)}
            self.record("compact", f"precompile {form}", "luac", build)
            for test in plan["groups"][form]:
                self.script("compact", "luasmall", stage, test, label=f"{test} {form}",
                            parser=False if test == "nosource" else None)
        stage = self.work / "compact-debug"
        (stage / "source.lua").write_text('print("SOURCE RAN")\n')

        def script_rejected():
            rc, out = self.run([self.exe("luasmall"), "-E", "source.lua"], stage, "compact-source-script.log")
            (stage / "source.log").write_text(out)
            if rc == 0 or CORRUPTION.search(out):
                raise Failed(f"source script not rejected cleanly (exit {rc})")
            rc2, out2 = self.run([self.exe("luasmall"), "-E", "nosource.lua", "cli", str(rc)], stage,
                                 "compact-source-verify.log")
            if rc2 or "NOSOURCE 1 CLI REJECTED" not in out2 or FAILURE.search(out2):
                raise Failed("rejection verifier failed")
            return {"exit_code": rc}
        self.record("compact", "source script rejected", "luasmall", script_rejected)

        def stdin_rejected():
            rc, out = self.run([self.exe("luasmall"), "-E", "-"], stage, "compact-source-stdin.log",
                               stdin=b'print("SOURCE RAN")\n')
            if rc == 0 or "SOURCE RAN" in out or "parser not included" not in out or CORRUPTION.search(out):
                raise Failed(f"stdin source not rejected cleanly (exit {rc})")
            return {"exit_code": rc}
        self.record("compact", "stdin source rejected", "luasmall", stdin_rejected)

        def continues():
            rc, out = self.run([self.exe("luasmall"), "-E", "numconv.lua"], stage, "compact-after-reject.log")
            if rc:
                raise Failed(f"exit status {rc}")
            validate("numconv", out)
        self.record("compact", "works after rejections", "luasmall", continues)

    def hosts(self):
        stage = self.stage_tests("hosts")
        shutil.copyfile(ROOT / "bridge.lua", stage / "bridge.lua")

        def native(name, marker, argv=(), cwd=None, allow_degraded=0):
            def fn():
                rc, out = self.run([self.exe(name), *argv], cwd or stage, f"hosts-{name}{'-' + argv[0] if argv else ''}.log")
                problems = bool(FAILURE.search(out))
                if allow_degraded:
                    problems = bool(re.search(r"MemCheck:|\bBRK\b|\bFAIL\b", out)) \
                        or out.count("Lua IIgs: mm=degraded") != allow_degraded
                if rc or problems or not re.search(marker, out, re.M):
                    raise Failed(f"exit {rc}; marker {marker!r} missing or failure output present")
                return {}
            return fn
        self.record("hosts", "iigshost", "iigshost", native("iigshost", r"^IIGSHOST PASSED yields=\d+$"))
        self.record("hosts", "allocfail", "allocfail", native("allocfail", r"ALLOCFAIL PASSED", allow_degraded=1))
        self.record("hosts", "bridge demo", "bridge", native("bridge", r"Closing LUA state"))

        def bridge_cstack():
            rc, out = self.run([self.exe("bridge"), "cstack.lua"], stage, "hosts-bridge-cstack.log")
            if rc:
                raise Failed(f"exit status {rc}")
            validate("cstack", out)
        self.record("hosts", "bridge cstack", "bridge", bridge_cstack)
        self.record("hosts", "mmtest", "mmtest", native("mmtest", r"MMTEST DONE errs=0"))
        self.results.append({"group": "hosts", "name": "memfree", "subject": "memfree",
                             "status": "built, not run", "reason": "needs real IIgs Memory Manager tools"})
        say("  hosts    memfree                built, not run (needs real hardware)")

    def unit(self):
        def fn():
            env = dict(os.environ, TEST_LUA=str(self.exe("lua")), GOLDEN_GATE=str(self.tc.sdk))
            if self.tc.iix:
                env["IIX"] = self.tc.iix
            result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tests"),
                                     "-p", "test_*.py"], cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=1800)
            (self.logs / "unit.log").write_bytes(result.stdout)
            text = result.stdout.decode(errors="replace")
            ran = re.search(r"Ran (\d+) tests?", text)
            if result.returncode:
                raise Failed("unit tests failed; see " + rel(self.logs / "unit.log"))
            skipped = re.search(r"skipped=(\d+)", text)
            return {"tests": int(ran.group(1)) if ran else 0,
                    "skips": [f"{skipped.group(1)} skipped (see log)"] if skipped else []}
        self.record("unit", "python unittest", "tools", fn)


def test_inputs() -> Dict[str, str]:
    files = sorted([*ROOT.joinpath("tests").glob("*.lua"), *ROOT.joinpath("tests").glob("*.json"),
                    *ROOT.joinpath("tests").glob("*.c"), ROOT / "bridge.lua",
                    ROOT / "tools/iigsbuild/contracts.py", ROOT / "tools/iigsbuild/runtests.py"])
    return {str(p.relative_to(ROOT)): sha256_file(p) for p in files}


def subject_for(args, tc, checks) -> dict:
    needed = sorted({n for c in checks for n in NEEDS[c]})
    if args.build:
        from .identified import resolve
        build = resolve(args.build)
        paths = {n: build.path(EXECUTABLES[n]) for n in needed}
        return {"kind": "identified", "build_id": build.id, "build_dir": build.dir.name,
                "build_manifest_sha256": build.manifest_sha256, "paths": paths}
    from .cli import cmd_build
    targets = sorted({DEV_TARGETS[n] for n in needed})
    say("Bringing dev builds up to date: " + " ".join(targets))
    ns = type("Args", (), {"targets": targets, "sdk": args.sdk})
    cmd_build(ns)
    from .common import DEV
    return {"kind": "dev", "build_id": None, "paths": {n: DEV / EXECUTABLES[n] for n in needed}}


def run_tests(args) -> int:
    from .toolchain import Toolchain
    tc = Toolchain.discover(args.sdk)
    tc.require_compiler()
    checks = list(args.checks or (["trace"] if args.config == "luatrace" else DEFAULT_CHECKS))
    if args.config == "lua-small" and not args.checks:
        checks = ["luac", "compact"]
    unknown = set(checks) - set(ALL_CHECKS)
    if unknown:
        raise BuildError(f"unknown checks {sorted(unknown)}; choose from {', '.join(ALL_CHECKS)}")
    subject = subject_for(args, tc, checks)
    if subject["kind"] == "identified":
        work = new_unique_dir(REPORTS, f"{subject['build_id']}-{utc_stamp()}")
    else:
        work = new_unique_dir(TEST_RUNS, f"test-{utc_stamp()}")
    say(f"Running checks {', '.join(checks)} in {rel(work)} (GoldenGate, not hardware)")
    session = Session(tc, subject, work, args.timeout)
    for check in checks:
        {"unit": session.unit, "targeted": session.targeted, "luac": session.luac,
         "compact": session.compact, "hosts": session.hosts,
         "trace": lambda: session.targeted("luatrace", traced=True)}[check]()
    inputs = test_inputs()
    failed = [r for r in session.results if r["status"] == "FAILED"]
    report = {
        "schema": "lua-iigs-test-report/1", "utc": utc_iso(),
        "environment": "GoldenGate emulator with --memcheck; not hardware",
        "emulator": {"iix": tc.identity()["iix"], "iix_sha256": tc.identity()["iix_sha256"]},
        "subject": {k: v for k, v in subject.items() if k != "paths"} | {
            "executables_sha256": {n: sha256_file(p) for n, p in subject["paths"].items()}},
        "test_identity": digest_json(inputs)[:12], "test_inputs_sha256": inputs,
        "checks": session.results,
        "summary": {"total": len(session.results), "failed": len(failed),
                    "with_skips": sum(1 for r in session.results if r.get("skips"))},
        "hardware_result": "not established by local tests",
    }
    write_json(work / "report.json", report)
    args.report_path = work / "report.json"
    say(f"{len(session.results) - len(failed)}/{len(session.results)} checks passed"
        f" ({report['summary']['with_skips']} with intentional skips). Report: {rel(work / 'report.json')}")
    return 1 if failed else 0
