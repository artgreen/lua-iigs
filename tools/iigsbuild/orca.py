"""ORCA/C compile, link, and makelib through GoldenGate, with atomic outputs.

Observed ORCA behavior this module defends against:
- A failed compile exits nonzero but can leave a partial .root file.
- An unresolved link exits nonzero but still writes a truncated executable.
- Quoted #include files are searched in the current directory first, then
  each cc=-i directory in order (ahead of any #pragma path).
Outputs are therefore produced in a private staging location and renamed
into place only after success (rename keeps the file-type metadata).
"""
from __future__ import annotations

import os
from pathlib import Path
import re
from typing import List, Sequence

from .common import BuildError, remove_tree, run_logged
from .configs import COMPILE_FLAGS
from .toolchain import Toolchain

LINK_ERRORS = re.compile(r"Unresolved reference|error(?:s)? found during link|Terminal error", re.I)
COMPILE_ERRORS = re.compile(r"^\d+ errors? found\.|Terminal error", re.M)
MAX_COMMAND = 240


class Orca:
    def __init__(self, toolchain: Toolchain):
        toolchain.require_compiler()
        self.tc = toolchain
        self.env = toolchain.env()

    def compile(self, source: Path, obj_dir: Path, name: str,
                include_dirs: Sequence[Path], log: Path) -> List[Path]:
        """Compile one unit to obj_dir/name.a (+ name.root for main units)."""
        stage = obj_dir / f".stage-{name}"
        remove_tree(stage)
        stage.mkdir(parents=True)
        for suffix in (".a", ".root"):
            (obj_dir / (name + suffix)).unlink(missing_ok=True)
        # ORCA rejects long command lines ("file name or command-line
        # parameter is too long"), so pass paths relative to the stage.
        argv = [self.tc.iix, "compile", *COMPILE_FLAGS, os.path.relpath(source, stage), f"keep={name}",
                *[f"cc=-i{os.path.relpath(d, stage)}" for d in include_dirs]]
        if len(" ".join(argv[1:])) > MAX_COMMAND:
            raise BuildError(f"ORCA command line for {source.name} exceeds {MAX_COMMAND} characters; "
                             "use a shorter build directory path")
        try:
            result = run_logged(argv, stage, self.env, log, check=False)
            text = result.stdout.decode(errors="replace")
            if result.returncode or COMPILE_ERRORS.search(text) or not (stage / (name + ".a")).is_file():
                tail = "\n".join("    " + line for line in text.strip().splitlines()[-10:])
                raise BuildError(f"compile failed: {source.name} (exit {result.returncode})\n{tail}")
            produced = []
            for suffix in (".a", ".root"):
                staged = stage / (name + suffix)
                if staged.is_file():
                    os.replace(staged, obj_dir / (name + suffix))
                    produced.append(obj_dir / (name + suffix))
            return produced
        finally:
            remove_tree(stage)

    def link(self, cwd: Path, inputs: Sequence[str], out: Path, log: Path) -> None:
        """Link to 'out'; the log keeps the +S global symbol table (link map)."""
        tmp = out.with_name("." + out.name + ".partial")
        tmp.unlink(missing_ok=True)
        out.unlink(missing_ok=True)
        argv = [self.tc.iix, "link", "+S", *inputs, f"KEEP={tmp}"]
        result = run_logged(argv, cwd, self.env, log, check=False)
        text = result.stdout.decode(errors="replace")
        if result.returncode or LINK_ERRORS.search(text) or not tmp.is_file():
            tmp.unlink(missing_ok=True)
            errors = [line for line in text.splitlines() if LINK_ERRORS.search(line)][:8]
            raise BuildError(f"link failed: {out.name} (exit {result.returncode}); incomplete output removed\n"
                             + "\n".join("    " + e.strip() for e in errors))
        os.replace(tmp, out)

    def makelib(self, cwd: Path, members: Sequence[str], out: Path, log: Path) -> None:
        # makelib appends to an existing library, so always start from nothing.
        tmp = out.with_name("." + out.name + ".partial")
        tmp.unlink(missing_ok=True)
        out.unlink(missing_ok=True)
        argv = [self.tc.iix, "makelib", str(tmp), *["+" + m for m in members]]
        result = run_logged(argv, cwd, self.env, log, check=False)
        text = result.stdout.decode(errors="replace")
        if result.returncode or "not an object module" in text or not tmp.is_file():
            tmp.unlink(missing_ok=True)
            raise BuildError(f"makelib failed: {out.name} (exit {result.returncode}); see {log}")
        os.replace(tmp, out)


def link_symbols(map_text: str) -> set:
    """Global symbol names from an 'iix link +S' symbol table."""
    return set(re.findall(r"[0-9A-F]{8} [PG] [0-9A-F]{2} [0-9A-F]{2} (\S+)", map_text))
