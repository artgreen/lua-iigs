"""Build orchestration: one directory per configuration, content-hashed
dependencies, configuration/toolchain fingerprints, and atomic products.

Directory layout (dev builds under build/dev, identified builds under
build/builds/<id>-<utc>):

  <config>/gen/parseconf.h    generated configuration header
  <config>/obj/               objects (+ .deps stamps)
  <config>/hostobj/           host/probe objects (lua configuration only)
  <config>/out/               executables, link maps, libraries, headers
  <config>/state.json         fingerprint of configuration + toolchain + recipe

An object is reused only if its source, every header it includes (found by
scanning quoted #include lines through the same search path ORCA uses),
and the configuration fingerprint are unchanged. A fingerprint change
discards the configuration's objects and outputs before rebuilding.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import re
from typing import Dict, Iterable, List, Optional, Sequence

from . import RECIPE_VERSION
from .common import (BuildError, copy_with_metadata, digest_json, read_json, rel, remove_tree,
                     say, sha256, sha256_file, write_atomic, write_json)
from .configs import (COMPILE_FLAGS, HOSTS, PARSER_SYMBOLS, Config)
from .orca import Orca, link_symbols

INCLUDE = re.compile(rb'^[ \t]*#[ \t]*include[ \t]*"([^"]+)"', re.M)
PUBLIC_HEADERS = ("lua.h", "luaconf.h", "lualib.h", "lauxlib.h", "lua.hpp")


def include_closure(source: Path, search: Sequence[Path]) -> List[Path]:
    """Every quoted include reachable from 'source' (over-approximate: ignores #if)."""
    found: Dict[Path, None] = {}
    pending = [source]
    while pending:
        current = pending.pop()
        for name in INCLUDE.findall(current.read_bytes()):
            name = name.decode()
            for directory in search:
                candidate = (directory / name).resolve()
                if candidate.is_file():
                    if candidate not in found and candidate != source:
                        found[candidate] = None
                        pending.append(candidate)
                    break
    return sorted(found)


class ConfigBuild:
    """Builds the products of one configuration from one source tree."""

    def __init__(self, orca: Orca, tree: Path, config: Config, out_root: Path,
                 build_id: Optional[str] = None, jobs: int = 1):
        self.orca = orca
        self.tree = Path(tree).resolve()
        self.src = self.tree / "src"
        self.config = config
        self.build_id = build_id
        self.jobs = max(1, jobs)
        self.dir = Path(out_root).resolve() / config.name
        self.gen, self.obj, self.out = self.dir / "gen", self.dir / "obj", self.dir / "out"
        self.hostobj, self.logs = self.dir / "hostobj", self.dir / "logs"
        self.compiled = self.reused = 0
        self.parseconf = config.parseconf(build_id)
        self.fingerprint = digest_json({
            "recipe": RECIPE_VERSION, "config": config.name, "flags": COMPILE_FLAGS,
            "parseconf": self.parseconf, "toolchain": orca.tc.fingerprint()})
        self._prepared = False

    # -- configuration state -------------------------------------------------
    def prepare(self) -> None:
        if self._prepared:
            return
        state = read_json(self.dir / "state.json")
        if state and state.get("fingerprint") != self.fingerprint:
            changed = [k for k in ("parseconf", "toolchain", "recipe")
                       if state.get(k) != self._state()[k]]
            say(f"  {self.config.name}: {', '.join(changed) or 'fingerprint'} changed; "
                "discarding this configuration's objects and outputs")
            for path in (self.obj, self.hostobj, self.out):
                remove_tree(path)
        for path in (self.gen, self.obj / ".deps", self.out / ".stamps", self.logs):
            path.mkdir(parents=True, exist_ok=True)
        header = self.gen / "parseconf.h"
        if not header.is_file() or header.read_text() != self.parseconf:
            write_atomic(header, self.parseconf.encode())
        write_json(self.dir / "state.json", {"fingerprint": self.fingerprint, **self._state()})
        self._prepared = True

    def _state(self) -> dict:
        return {"config": self.config.name, "recipe": RECIPE_VERSION,
                "parseconf": self.parseconf, "toolchain": self.orca.tc.fingerprint()}

    # -- compilation ---------------------------------------------------------
    def _search(self, host: bool) -> List[Path]:
        # Generated header first so no other parseconf.h can shadow it.
        dirs = [self.gen, self.src]
        return dirs + [self.tree, self.tree / "tests"] if host else dirs

    def _stamp(self, source: Path, search: Sequence[Path]) -> dict:
        inputs = {source.name: sha256_file(source)}
        for header in include_closure(source, search):
            try:
                key = str(header.relative_to(self.dir))
            except ValueError:
                key = str(header.relative_to(self.tree))
            inputs[key] = sha256_file(header)
        return {"fingerprint": self.fingerprint, "inputs": inputs}

    def _compile_all(self, jobs: Iterable[tuple]) -> None:
        """jobs: (name, source, obj_dir, host). Compile stale units, bounded parallel."""
        todo = []
        for name, source, obj_dir, host in jobs:
            if not source.is_file():
                raise BuildError(f"missing source: {rel(source)}")
            search = self._search(host)
            stamp = self._stamp(source, search)
            record = read_json(obj_dir / ".deps" / (name + ".json"))
            obj = obj_dir / (name + ".a")
            if (record and record.get("stamp") == stamp and obj.is_file()
                    and record.get("outputs_sha256") == {
                        p.name: sha256_file(p)
                        for p in (obj, obj_dir / (name + ".root")) if p.is_file()}):
                self.reused += 1
                continue
            todo.append((name, source, obj_dir, search, stamp))
        if not todo:
            return

        def work(item):
            name, source, obj_dir, search, stamp = item
            (obj_dir / ".deps" / (name + ".json")).unlink(missing_ok=True)
            outputs = self.orca.compile(source, obj_dir, name, search, self.logs / f"compile-{name}.log")
            write_json(obj_dir / ".deps" / (name + ".json"),
                       {"stamp": stamp, "outputs_sha256": {p.name: sha256_file(p) for p in outputs}})
            return name

        say(f"  {self.config.name}: compiling {len(todo)} unit(s)"
            + (f" with up to {self.jobs} concurrent compiler processes" if self.jobs > 1 and len(todo) > 1 else ""))
        failures = []
        with ThreadPoolExecutor(max_workers=self.jobs) as pool:
            for item, future in [(item, pool.submit(work, item)) for item in todo]:
                try:
                    future.result()
                    self.compiled += 1
                except BuildError as exc:
                    failures.append(str(exc))
        if failures:
            raise BuildError(f"{self.config.name}: {len(failures)} compile failure(s)\n" + "\n".join(failures))

    def _ensure_units(self, units: Sequence[str]) -> None:
        self.prepare()
        self._compile_all((u, self.src / (u + ".c"), self.obj, False) for u in units)

    # -- products --------------------------------------------------------------
    def _product(self, name: str, inputs: Sequence[Path], build) -> Path:
        """Rebuild out/<name> unless every input's hash matches its stamp.

        On failure the stale product and its stamp are removed, so an
        out-of-date file can never be mistaken for a current build.
        """
        target = self.out / name
        stamp_path = self.out / ".stamps" / (name + ".json")
        stamp = {"fingerprint": self.fingerprint,
                 "inputs": {rel(p): sha256_file(p) for p in inputs}}
        record = read_json(stamp_path)
        if record and record.get("stamp") == stamp and target.is_file() \
                and record.get("sha256") == sha256_file(target):
            return target
        stamp_path.unlink(missing_ok=True)
        try:
            build(target)
        except BaseException:
            target.unlink(missing_ok=True)
            raise
        write_json(stamp_path, {"stamp": stamp, "sha256": sha256_file(target),
                                "size": target.stat().st_size})
        return target

    def _objects(self, obj_dir: Path, names: Sequence[str]) -> List[Path]:
        paths = []
        for name in names:
            base = name[:-2] if name.endswith(".a") else name
            for suffix in (".a", ".root"):
                if (obj_dir / (base + suffix)).is_file():
                    paths.append(obj_dir / (base + suffix))
        return paths

    def _fail_product(self, name: str) -> None:
        for path in (self.out / name, self.out / ".stamps" / (name + ".json")):
            if path.exists():
                path.unlink()
                say(f"  removed stale {rel(path)} (its inputs did not build)")

    def executable(self) -> Path:
        cfg = self.config
        try:
            self._ensure_units([*cfg.core_units(), "lvm", cfg.main])
        except BuildError:
            self._fail_product(cfg.exe)
            raise
        inputs = cfg.link_inputs()

        def link(target: Path):
            mapfile = self.out / (cfg.exe + ".map")
            self.orca.link(self.obj, inputs, target, mapfile)
            self.check_parser_symbols(mapfile.read_text(errors="replace"), target)
        return self._product(cfg.exe, self._objects(self.obj, inputs), link)

    def check_parser_symbols(self, map_text: str, target: Path) -> dict:
        symbols = link_symbols(map_text)
        present = sorted(s for s in PARSER_SYMBOLS if s in symbols)
        if self.config.parser and len(present) != len(PARSER_SYMBOLS):
            raise BuildError(f"{target.name}: parser symbols missing from link map: "
                             f"{sorted(set(PARSER_SYMBOLS) - set(present))}")
        if not self.config.parser and present:
            raise BuildError(f"{target.name}: parser-free build still links {present}")
        return {"parser_symbols_present": present, "global_symbols": len(symbols)}

    def library(self) -> Path:
        cfg = self.config
        if not cfg.lib:
            raise BuildError(f"configuration {cfg.name} has no library product")
        try:
            self._ensure_units([*cfg.core_units(), "lvm"])
        except BuildError:
            self._fail_product(cfg.lib)
            raise
        members = cfg.lib_members()
        lib = self._product(cfg.lib, self._objects(self.obj, members),
                            lambda target: self.orca.makelib(self.obj, members, target,
                                                             self.logs / f"makelib-{cfg.lib}.log"))
        # The VM object is linked separately from the library (historical layout).
        vm = self.out / "lvm.a"
        if not vm.is_file() or sha256_file(vm) != sha256_file(self.obj / "lvm.a"):
            copy_with_metadata(self.obj / "lvm.a", vm)
        include = self.out / "include"
        include.mkdir(exist_ok=True)
        for header in PUBLIC_HEADERS:
            copy_with_metadata(self.src / header, include / header)
        copy_with_metadata(self.gen / "parseconf.h", include / "parseconf.h")
        return lib

    def host(self, name: str) -> Path:
        if self.config.name != "lua":
            raise BuildError("hosts link against the full 'lua' configuration library")
        spec = HOSTS[name]
        lib = vm = None
        try:
            if spec["lua"]:
                lib, vm = self.library(), self.out / "lvm.a"
            self.prepare()
            sources = [self.tree / s for s in spec["sources"]]
            (self.hostobj / ".deps").mkdir(parents=True, exist_ok=True)
            self._compile_all((s.stem, s, self.hostobj, True) for s in sources)
        except BuildError:
            self._fail_product(name)
            raise
        inputs = [s.stem for s in sources]
        if lib:
            inputs += [os.path.relpath(vm.with_suffix(""), self.hostobj), os.path.relpath(lib, self.hostobj)]
        deps = self._objects(self.hostobj, [s.stem for s in sources]) + ([vm, lib] if lib else [])
        return self._product(name, deps, lambda target: self.orca.link(
            self.hostobj, inputs, target, self.out / (name + ".map")))


def summarize(path: Path) -> str:
    size = path.stat().st_size
    return f"{rel(path)}  {size:,} bytes  sha256 {sha256_file(path)[:16]}"


def parser_evidence(build: ConfigBuild) -> dict:
    mapfile = build.out / (build.config.exe + ".map")
    return build.check_parser_symbols(mapfile.read_text(errors="replace"), build.out / build.config.exe)
