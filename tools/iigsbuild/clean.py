"""Cleanup with an allow-list: only known disposable outputs are removed.

'make clean' removes:
  build/dev/            per-configuration development builds
  build/test-runs/      local test scratch directories
  legacy in-tree outputs of the old Makefiles, only when Git does not
  track them: src/*.a *.root *.sym *.lib, src/lua, src/luac,
  src/parseconf.h, root/tests objects, bridge/mmtest/memfree/luac.out
It never touches identified builds (build/builds), packages, hardware
kits, test reports, release directories, hardware/diagnostic evidence,
archives, worktrees, dist/, or docs/validation.

'make clean-legacy' moves loose outputs of the old workflow (build/lua,
build/luac, build/lua.lib, ...) into build/archive/legacy-<utc>/ instead
of deleting them: some were used as evidence.
"""
from __future__ import annotations

import subprocess
from typing import List
from pathlib import Path

from .common import BUILD, DEV, ROOT, TEST_RUNS, DirLock, rel, remove_tree, say, utc_stamp

PRESERVED = ("builds", "packages", "hardware-suites", "test-reports", "hardware", "diagnostics",
             "archive", "worktrees", "suites", "local", "release-*", "doc-checks", "review-checks",
             "examples")
LEGACY_IN_TREE = ["src/*.a", "src/*.root", "src/*.sym", "src/*.lib", "src/lua", "src/luac",
                  "src/parseconf.h", "*.a", "*.root", "*.sym", "tests/*.a", "tests/*.root",
                  "tests/iigshost", "tests/allocfail", "bridge", "mmtest", "memfree", "luac.out"]
LEGACY_LOOSE = ["build/lua", "build/luac", "build/luatrace", "build/lua.lib", "build/luac.lib",
                "build/lvm.a", "build/mmtest", "build/memfree"]


def tracked() -> set:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout
    return set(out.splitlines())


def legacy_in_tree() -> List[Path]:
    keep = tracked()
    found = []
    for pattern in LEGACY_IN_TREE:
        for path in sorted(ROOT.glob(pattern)):
            if path.is_file() and str(path.relative_to(ROOT)) not in keep:
                found.append(path)
    return found


def clean(args) -> int:
    with DirLock(BUILD, "clean"):
        targets = [p for p in (DEV, TEST_RUNS) if p.exists()] + legacy_in_tree()
        if not targets:
            say("Nothing to clean.")
        for path in targets:
            say(("would remove " if args.dry_run else "removing ") + rel(path))
            if not args.dry_run:
                remove_tree(path)
    kept = sorted(p.name for p in BUILD.iterdir() if p.is_dir() and p.name not in ("dev", "test-runs")) \
        if BUILD.is_dir() else []
    if kept:
        say("Preserved: build/" + ", build/".join(kept))
    loose = [p for p in LEGACY_LOOSE if (ROOT / p).exists()]
    if loose:
        say("Legacy loose outputs left in place (make clean-legacy archives them): " + ", ".join(loose))
    return 0


def clean_legacy(args) -> int:
    with DirLock(BUILD, "clean-legacy"):
        loose = [ROOT / p for p in LEGACY_LOOSE if (ROOT / p).exists()]
        if not loose:
            say("No legacy loose outputs.")
            return 0
        dest = BUILD / "archive" / f"legacy-{utc_stamp()}"
        for path in loose:
            say(("would move " if args.dry_run else "moving ") + f"{rel(path)} -> {rel(dest)}/")
            if not args.dry_run:
                dest.mkdir(parents=True, exist_ok=True)
                path.rename(dest / path.name)  # rename keeps file-type metadata
    return 0
