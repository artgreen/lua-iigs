"""'make test-build': integration tests of the build system itself.

Runs real 'make' commands in a private copy of the working tree (under
build/test-runs/buildcheck-*), with GoldenGate and the selected SDK, and
checks:
  - independent library builds with no prior interpreter build
  - clean builds of every configuration; repeated builds compile nothing
  - incremental rebuilds after source, header, and toolchain changes
  - missing/corrupted .root companions are rebuilt, with a runnable result
  - switching between full, compact, compiler, and traced builds without
    contamination (outputs and objects stay per configuration)
  - make -j and two concurrent make processes
  - compile and link failures propagate and leave no stale/partial outputs
    (including hosts whose library failed to build)
  - LUAC debug/stripped bytecode on both runtimes; compact source rejection
  - identified build, packaging with byte/metadata verification, rejection
    of a tampered build and a corrupted container
  - make clean removes disposable outputs and preserves evidence
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

from .common import ROOT, TEST_RUNS, BuildError, new_unique_dir, say, sha256_file
from .concurrency import default_jobs
from .toolchain import Toolchain

PRODUCTS = {"lua": "lua/out/lua", "luasmall": "lua-small/out/luasmall", "luac": "luac/out/luac",
            "luatrace": "luatrace/out/luatrace", "lua.lib": "lua/out/lua.lib",
            "luasmall.lib": "lua-small/out/luasmall.lib"}


class Check:
    def __init__(self):
        self.failures, self.count = [], 0

    def __call__(self, cond, what):
        self.count += 1
        say(f"    [{'ok' if cond else 'FAIL'}] {what}")
        if not cond:
            self.failures.append(what)


class Tree:
    def __init__(self, work: Path, sdk: Path, jobs: int):
        self.root = work / "repo"
        self.dev = self.root / "build/dev"
        from .distribution import source_files
        files = source_files(ROOT)
        for name in files:
            source = ROOT / name
            if source.is_file():
                dest = self.root / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, dest)
        # A repository of its own, so provenance and tracked-file checks are real.
        git = ["git", "-c", "user.name=buildcheck", "-c", "user.email=buildcheck@invalid",
               "-c", "core.hooksPath=/dev/null"]
        subprocess.run(git + ["init", "-q"], cwd=self.root, check=True)
        subprocess.run(git + ["add", "-A"], cwd=self.root, check=True)
        subprocess.run(git + ["commit", "-q", "-m", "buildcheck snapshot"], cwd=self.root, check=True)
        self.env = dict(os.environ, GOLDEN_GATE=str(sdk), JOBS=str(jobs))
        self.env.pop("MAKEFLAGS", None)
        self.env.pop("MFLAGS", None)
        self.python = sys.executable

    def make(self, *targets, expect_ok=True, env=None):
        argv = ["make", f"PYTHON={self.python}", *targets]
        result = subprocess.run(argv, cwd=self.root, env=env or self.env, stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, timeout=3600)
        out = result.stdout + result.stderr
        if expect_ok and result.returncode:
            raise BuildError(f"make {' '.join(targets)} failed:\n{out[-2000:]}")
        return result.returncode, out

    def hashes(self):
        return {k: sha256_file(self.dev / v) for k, v in PRODUCTS.items() if (self.dev / v).is_file()}

    def edit(self, rel, append):
        path = self.root / rel
        original = path.read_bytes()
        path.write_bytes(original + append.encode())
        return lambda: path.write_bytes(original)


def compiled(out: str) -> int:
    return sum(int(n) for n in re.findall(r"Done in [\d.]+s: (\d+) compiled", out))


def main(args) -> int:
    tc = Toolchain.discover(args.sdk)
    tc.require_compiler()
    tc.require_packaging()
    jobs, _ = default_jobs(tc)
    work = new_unique_dir(TEST_RUNS, "buildcheck")
    say(f"Build-system integration tests in {work} (JOBS={jobs})")
    tree = Tree(work, tc.sdk, jobs)
    check = Check()
    started = time.monotonic()
    src_before = sorted(p.name for p in (tree.root / "src").iterdir())

    say("1. Libraries build independently, without an interpreter build")
    tree.make("liblua-small")
    check((tree.dev / "lua-small/out/luasmall.lib").is_file(), "liblua-small built first")
    check(not (tree.dev / "lua-small/obj/lua.a").exists(), "no interpreter main object compiled for the library")
    check(not any((tree.dev / "lua-small/obj").glob("lparser.*")), "parser units not compiled for the compact library")
    tree.make("liblua")
    check(not (tree.dev / "lua/out/lua").exists(), "liblua did not build the interpreter")
    check((tree.dev / "lua/out/include/parseconf.h").read_text().count("BUILD_IS_LUA") == 1,
          "library ships its own generated parseconf.h")

    say("2. Clean build of every configuration; repeated build compiles nothing")
    tree.make("everything")
    first = tree.hashes()
    check(len(first) == len(PRODUCTS), "all executables and libraries produced")
    check(len({first["lua"], first["luasmall"], first["luac"], first["luatrace"]}) == 4,
          "full, compact, compiler, and traced executables are distinct artifacts")
    _, out = tree.make("everything")
    check(compiled(out) == 0 and tree.hashes() == first, "second build reuses everything and changes nothing")
    check(sorted(p.name for p in (tree.root / "src").iterdir()) == src_before, "nothing written into src/")
    confs = {c: (tree.dev / c / "gen/parseconf.h").read_text() for c in ("lua", "lua-small", "luac", "luatrace")}
    check("LUA_NO_PARSER" in confs["lua-small"] and all("LUA_NO_PARSER" not in confs[c] for c in ("lua", "luac", "luatrace")),
          "each configuration has its own generated parseconf.h")
    check(sha256_file(tree.dev / "lua/obj/ldo.a") != sha256_file(tree.dev / "lua-small/obj/ldo.a"),
          "parser-dependent objects differ between full and compact")
    check(sha256_file(tree.dev / "lua/obj/lapi.a") == sha256_file(tree.dev / "lua-small/obj/lapi.a"),
          "parser-independent objects are identical, as expected")

    say("   compiler companion outputs are required for cache reuse")
    probe = tree.dev / "lua/out/mmtest"
    probe_hash = sha256_file(probe)
    root_object = tree.dev / "lua/hostobj/mmtest.root"
    for damage in ("missing", "corrupted"):
        if damage == "missing":
            root_object.unlink()
        else:
            root_object.write_bytes(b"corrupted root object")
        _, out = tree.make("mmtest")
        check(compiled(out) == 1 and root_object.is_file() and sha256_file(probe) == probe_hash,
              f"{damage} .root recompiles its unit and restores the correct executable")
    result = subprocess.run([tc.iix, str(probe)], env=tree.env, capture_output=True, timeout=60)
    check(result.returncode == 0 and b"MMTEST DONE errs=0" in result.stdout,
          "recovered probe executes its main function")

    say("3. Switching configurations does not contaminate outputs")
    for target in ("lua-small", "lua", "luac", "luatrace", "lua", "lua-small"):
        _, out = tree.make(target)
        check(compiled(out) == 0, f"make {target} after switching compiles nothing")
    check(tree.hashes() == first, "all outputs unchanged after switching")

    say("4. Incremental rebuilds")
    restore = tree.edit("src/lzio.c", "\n/* incremental test */\n")
    _, out = tree.make("lua")
    check(compiled(out) == 1, "source change recompiles exactly one unit")
    restore()
    tree.make("lua")
    from .builder import include_closure
    from .configs import get
    gen = tree.dev / "lua/gen"
    expect = sum(1 for u in [*get("lua").core_units(), "lvm", "lua"]
                 if (tree.root / "src/lzio.h").resolve() in include_closure(tree.root / "src" / (u + ".c"),
                                                                            [gen, tree.root / "src"]))
    restore = tree.edit("src/lzio.h", "\n/* header test */\n")
    _, out = tree.make("lua")
    check(compiled(out) == expect, f"header change recompiles exactly its {expect} dependents")
    restore()
    _, out = tree.make("lua")
    check(tree.hashes()["lua"] == first["lua"], "restored sources give the original executable")
    say("   toolchain change (modified copy of the SDK)")
    sdk_copy = work / "sdk-copy"
    subprocess.run(["cp", "-Rp", str(tc.sdk), str(sdk_copy)], check=True)
    header = sdk_copy / "Libraries/ORCACDefs/stdio.h"
    header.chmod(0o644)
    text = header.read_bytes()
    newline = b"\r" if b"\r" in text and b"\n" not in text else b"\n"
    header.write_bytes(text + newline + b"/* toolchain change test */" + newline)
    changed_env = dict(tree.env, GOLDEN_GATE=str(sdk_copy))
    _, out = tree.make("lua", env=changed_env)
    check("toolchain changed" in out and compiled(out) == 32, "toolchain change discards and rebuilds the configuration")
    _, out = tree.make("lua")
    check("toolchain changed" in out and tree.hashes()["lua"] == first["lua"], "switching back rebuilds again")

    say("5. make -j and concurrent invocations")
    shutil.rmtree(tree.dev)
    tree.make("-j8", "lua", "lua-small", "luac", "luatrace", "liblua", "liblua-small")
    check(tree.hashes() == first, "make -j8 from clean gives identical outputs")
    procs = [subprocess.Popen(["make", f"PYTHON={tree.python}", target], cwd=tree.root, env=tree.env,
                              stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
             for target in ("lua", "lua-small")]
    outs = [p.communicate(timeout=3600)[0] for p in procs]
    check(all(p.returncode == 0 for p in procs), "two concurrent make processes both succeed")
    check(tree.hashes() == first, "concurrent invocations leave identical outputs")

    say("6. Failure propagation and incomplete outputs")
    tree.make("iigshost")
    restore = tree.edit("src/lapi.c", "\nint broken_syntax( {\n")
    rc, out = tree.make("iigshost", expect_ok=False)
    check(rc != 0 and "compile failed: lapi.c" in out, "host build propagates its library compile failure")
    check(not (tree.dev / "lua/out/iigshost").exists()
          and not (tree.dev / "lua/out/.stamps/iigshost.json").exists(),
          "library failure removes the stale host and its success stamp")
    rc, out = tree.make("lua", expect_ok=False)
    check(rc != 0 and "compile failed: lapi.c" in out, "compile error fails make with the compiler message")
    check(not (tree.dev / "lua/obj/lapi.a").exists(), "failed object is not left behind")
    check(not (tree.dev / "lua/out/lua").exists(), "stale executable removed after its inputs failed")
    restore()
    restore = tree.edit("src/lzio.c", "\nvoid lua_iigs_missing_symbol(void);\n"
                                      "void lua_iigs_force_link_failure(void) { lua_iigs_missing_symbol(); }\n")
    rc, out = tree.make("lua", expect_ok=False)
    check(rc != 0 and "Unresolved reference" in out, "unresolved symbol fails the link")
    check(not (tree.dev / "lua/out/lua").exists(), "truncated executable from the failed link is removed")
    restore()
    leftovers = [p for p in tree.dev.rglob("*") if p.name.endswith(".partial") or p.name.startswith(".stage-")]
    check(not leftovers, "no partial files or staging directories remain")
    tree.make("lua")
    check(tree.hashes()["lua"] == first["lua"], "recovery build matches the original")

    say("7. Bytecode on both runtimes and compact source rejection")
    rc, out = tree.make("test", "CHECKS=luac compact", expect_ok=False)
    counts = re.search(r"(\d+)/(\d+) checks passed", out)
    check(rc == 0 and counts is not None and counts.group(1) == counts.group(2) and int(counts.group(2)) > 20,
          "make test CHECKS='luac compact' passes every check")

    say("8. Identified build, packages, and verification")
    _, out = tree.make("identify", "CONFIGS=lua lua-small luac")
    build_dir = sorted((tree.root / "build/builds").glob("*-*"))[-1]
    manifest = __import__("json").loads((build_dir / "BUILD-MANIFEST.json").read_text())
    check(manifest["configurations"]["lua-small"]["parser"]["parser_symbols_present"] == [],
          "manifest proves parser symbols absent from compact link")
    check(re.fullmatch(r"IIgs [0-9a-f]{12} small", manifest["banners"].get("lua-small", "")) is not None,
          "manifest records the build-ID banner printed by -v")
    shutil.rmtree(tree.dev)
    _, out = tree.make("package", f"BUILD={build_dir}", "KINDS=runtime small compiler library")
    check(not tree.dev.exists(), "packaging an identified build rebuilds nothing")
    package_dir = sorted((tree.root / "build/packages").glob("*"))[-1]
    check((package_dir / "LUASMALL.SHK").is_file() and (package_dir / "PACKAGE-MANIFEST.json").is_file(),
          "verified packages and manifest written")
    from .packaging import Member, verify_container
    corrupt = work / "corrupt.po"
    shutil.copyfile(package_dir / "luac.po", corrupt)
    data = bytearray(corrupt.read_bytes())
    exe = (build_dir / "luac/out/luac").read_bytes()
    offset = bytes(data).find(exe[4096:4160])
    check(offset > 0, "executable bytes located inside the image")
    data[offset] ^= 0xFF
    corrupt.write_bytes(bytes(data))
    try:
        verify_container(tc, corrupt, [Member("LUAC", exe, "EXE")])
        check(False, "corrupted image member detected")
    except BuildError:
        check(True, "corrupted image member detected")
    victim = build_dir / "luac/out/luac"
    victim.chmod(0o644)
    victim.write_bytes(victim.read_bytes() + b"\0")
    rc, out = tree.make("package", f"BUILD={build_dir}", "KINDS=compiler", expect_ok=False)
    check(rc != 0 and "modified after it was built" in out, "tampered identified build is refused")

    say("9. make clean preserves evidence")
    evidence = ["build/builds/keep/f", "build/packages/keep/f", "build/hardware/keep/f", "build/release-v9-download/f",
                "build/diagnostics/keep/f", "build/archive/keep/f", "build/worktrees/keep/f", "build/hardware-suites/k/f",
                "build/test-reports/r/f", "build/suites/s/f", "build/local/keep.json"]
    tree.make("test", "CHECKS=unit")  # creates build/test-runs
    for name in evidence:
        (tree.root / name).parent.mkdir(parents=True, exist_ok=True)
        (tree.root / name).write_text("x")
    tree.make("clean")
    check(not tree.dev.exists() and not (tree.root / "build/test-runs").exists(), "disposable outputs removed")
    check(all((tree.root / n).exists() for n in evidence), "identified builds, packages, kits, releases, evidence kept")
    check(all((tree.root / n).is_file() for n in ("src/lapi.c", "src/luaconf.h", "Makefile")), "tracked files untouched")

    say(f"{check.count - len(check.failures)}/{check.count} build-system checks passed "
        f"in {time.monotonic() - started:.0f}s. Work tree: {work}")
    if check.failures:
        say("FAILED: " + "; ".join(check.failures))
        return 1
    shutil.rmtree(work, ignore_errors=True)
    return 0
