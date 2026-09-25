"""Command-line entry point used by the Makefile (python3 tools/iigs.py ...)."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from typing import List

from .common import DEV, ROOT, BuildError, DirLock, say

BUILD_TARGETS = {
    "lua": ("lua", "executable"),
    "lua-small": ("lua-small", "executable"),
    "luac": ("luac", "executable"),
    "luatrace": ("luatrace", "executable"),
    "liblua": ("lua", "library"),
    "liblua-small": ("lua-small", "library"),
    "iigshost": ("lua", "host"), "allocfail": ("lua", "host"), "bridge": ("lua", "host"),
    "mmtest": ("lua", "host"), "memfree": ("lua", "host"),
}
ALIASES = {"all": ["lua", "luac", "liblua"],
           "hosts": ["iigshost", "allocfail", "bridge", "mmtest", "memfree"],
           "everything": ["lua", "lua-small", "luac", "luatrace", "liblua", "liblua-small",
                          "iigshost", "allocfail", "bridge", "mmtest", "memfree"]}

HELP = """\
Lua 5.4.6 for the Apple IIgs - build, test, and packaging commands

Build (outputs under build/dev/<configuration>/out; incremental):
  make / make all       full Lua, LUAC, and the full embedding library
  make lua              interpreter with the source parser        (configuration lua)
  make lua-small        compact bytecode-only interpreter         (configuration lua-small)
  make luac             bytecode compiler, always parser-enabled  (configuration luac)
  make luatrace         full interpreter with Memory Manager tracing
  make liblua           full embedding library (lua.lib + lvm.a + include/)
  make liblua-small     parser-free embedding library (luasmall.lib + lvm.a + include/)
  make hosts            native hosts/probes: iigshost allocfail bridge mmtest memfree
  make everything       every configuration, library, and host

Check and test:
  make doctor           validate SDK, compiler, emulator, and packaging tools
  make test             default local regression checks (GoldenGate, not hardware)
  make test-build       build-system integration tests (clean/incremental/-j/failures)
  make suite GROUP=..   run the reusable Lua suite locally against a selected build
  make verify-concurrency  prove parallel ORCA compiles match serial ones

Identified builds, packages, hardware kits (preserved; never rebuilt):
  make identify         build every configuration from an immutable source
                        snapshot with a build ID, under build/builds/<id>-<utc>
  make package BUILD=<id|dir>          verified .po/.SHK packages of that build
  make hardware-suite BUILD=<id|dir>   TEST.SHK kit for the real IIgs
      (or RELEASE=<dir> containing RELEASE-MANIFEST.json)
      KIT=suite|lua|small|luac|host   GROUP=full|runtime|...   PREFIX=20:
  make stage FROM=<kit/package dir> DEST=/Volumes/nas/<dir>   copy containers to the NAS
  make kit              identify + test + package (replaces tools/hardware-kit.py)

Cleanup:
  make clean            remove disposable outputs (build/dev, build/test-runs, legacy
                        in-tree objects); keeps identified builds, packages, kits,
                        releases, hardware/diagnostic evidence, and worktrees
  make clean-legacy     move legacy loose outputs (build/lua, ...) into build/archive

Options (make VAR=value or local.mk):
  GOLDEN_GATE=<sdk>  IIX= ACX= CP2= NULIB2=   tool locations (see make doctor)
  JOBS=N         concurrent compiler processes (default 1 until verify-concurrency)
  CONFIG=name    configuration for make test / suite (lua, lua-small, luatrace)
  BUILD=id|dir   identified build for test/package/hardware-suite (no rebuild)
  BUILD_LABEL=   banner prefix for make identify (default: IIgs <build id>)
  PYTHON=python3
"""


def jobs_for(tc) -> int:
    from .concurrency import default_jobs
    jobs, why = default_jobs(tc)
    if jobs == 1 and why != "JOBS":
        say(f"Compiling serially: {why}")
    return jobs


def expand(targets: List[str]) -> List[str]:
    out: List[str] = []
    for target in targets:
        for name in ALIASES.get(target, [target]):
            if name not in BUILD_TARGETS:
                raise BuildError(f"unknown build target {name!r}")
            if name not in out:
                out.append(name)
    return out


def cmd_build(args) -> int:
    from .builder import ConfigBuild, summarize
    from .configs import get
    from .orca import Orca
    from .toolchain import Toolchain

    targets = expand(args.targets or ["all"])
    tc = Toolchain.discover(args.sdk)
    orca = Orca(tc)
    jobs = jobs_for(tc)
    started = time.monotonic()
    builds = {}
    with DirLock(DEV, "make " + " ".join(targets)):
        for target in targets:
            config_name, product = BUILD_TARGETS[target]
            build = builds.setdefault(config_name, ConfigBuild(orca, ROOT, get(config_name), DEV, jobs=jobs))
            if product == "executable":
                path = build.executable()
            elif product == "library":
                path = build.library()
            else:
                path = build.host(target)
            say(f"{target:13} {summarize(path)}")
    compiled = sum(b.compiled for b in builds.values())
    reused = sum(b.reused for b in builds.values())
    say(f"Done in {time.monotonic() - started:.1f}s: {compiled} compiled, {reused} up to date.")
    return 0


def cmd_doctor(args) -> int:
    from .doctor import doctor
    return doctor(args.sdk)


def cmd_verify_concurrency(args) -> int:
    from .concurrency import verify
    from .toolchain import Toolchain
    with DirLock(DEV, "verify-concurrency"):
        verify(Toolchain.discover(args.sdk))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="iigs", description="Lua IIgs build tooling")
    parser.add_argument("--sdk", default=None, help="ORCA/C SDK root (default: GOLDEN_GATE, then local SDK)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("help")
    sub.add_parser("doctor")
    sub.add_parser("verify-concurrency")
    p = sub.add_parser("build")
    p.add_argument("targets", nargs="*")
    from . import commands
    commands.register(sub)
    args = parser.parse_args(argv)
    handlers = {"help": lambda a: (sys.stdout.write(HELP), 0)[1], "doctor": cmd_doctor,
                "verify-concurrency": cmd_verify_concurrency, "build": cmd_build}
    handlers.update(commands.HANDLERS)
    try:
        return handlers[args.command](args)
    except BuildError as exc:
        print(f"error: {exc}", file=sys.stderr, flush=True)
        return 1
    except subprocess.TimeoutExpired as exc:
        print(f"error: a tool did not finish within {exc.timeout}s: {exc.cmd}", file=sys.stderr, flush=True)
        return 1
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130
