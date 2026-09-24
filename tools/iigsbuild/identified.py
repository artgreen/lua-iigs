"""Identified builds: immutable, provenance-recorded builds of every
configuration from a byte snapshot of the runtime and host sources.

Build identity covers only what can change executable bytes: runtime
sources (src/*.c, src/*.h), the compile/link recipe, configuration macros,
and the toolchain. Documentation, tests, and packaging code are excluded,
so a documentation-only or packaging-only change does not change the
runtime or its banner. Test and package identities are recorded separately.

Layout: build/builds/<build id>-<utc>/
  source/              exact bytes that were compiled
  <config>/...         per-configuration gen/obj/out (see builder.py)
  logs/                banner checks
  BUILD-MANIFEST.json  identities, hashes, parser-omission evidence
The finished directory is made read-only. It is never rebuilt in place;
packaging and tests read it and verify its hashes first.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
from typing import Dict, Optional

from . import RECIPE_VERSION
from .builder import ConfigBuild, parser_evidence
from .common import (IDENTIFIED, ROOT, TEST_RUNS, BuildError, DirLock, digest_json, make_read_only,
                     new_unique_dir, read_json, rel, remove_tree, say, sha256, sha256_file, utc_iso,
                     utc_stamp, write_atomic, write_json)
from .configs import COMPILE_FLAGS, CONFIGS, CORE_UNITS, HOSTS, PARSER_UNITS
from .orca import Orca
from .toolchain import Toolchain

HOST_HEADERS = ("testiface.h",)
MANIFEST = "BUILD-MANIFEST.json"
RELEASE_NAMES = {"LUA": "lua/out/lua", "LUAC": "luac/out/luac", "LUATRACE": "luatrace/out/luatrace",
                 "IIGSHOST": "lua/out/iigshost", "LUASMALL": "lua-small/out/luasmall"}


def runtime_inputs(tree: Path = ROOT) -> Dict[str, bytes]:
    if (tree / "src/parseconf.h").exists():
        raise BuildError("src/parseconf.h exists: it is generated per build now. Remove it (make clean) "
                         "so it cannot be mistaken for configuration input.")
    files = sorted(p for pattern in ("*.c", "*.h", "*.hpp") for p in tree.joinpath("src").glob(pattern))
    return {str(p.relative_to(tree)): p.read_bytes() for p in files}


def host_inputs(tree: Path = ROOT) -> Dict[str, bytes]:
    names = sorted({s for spec in HOSTS.values() for s in spec["sources"]} | set(HOST_HEADERS))
    return {name: (tree / name).read_bytes() for name in names}


def recipe(tc: Toolchain) -> dict:
    return {"recipe_version": RECIPE_VERSION, "compile_flags": list(COMPILE_FLAGS),
            "core_units": list(CORE_UNITS), "parser_units": list(PARSER_UNITS),
            "configurations": {n: {"macros": [m for m, _ in c.macros()], "link": c.link_inputs(),
                                   "library": c.lib} for n, c in CONFIGS.items()},
            "toolchain": tc.identity()}


def build_digest(tc: Toolchain, runtime: Dict[str, bytes]) -> str:
    return digest_json({"recipe": recipe(tc),
                        "sources": {k: sha256(v) for k, v in runtime.items()}})[:12]


def git_state(files: Dict[str, bytes]) -> dict:
    def git(*args):
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    tree = {}
    for line in git("ls-tree", "-r", "HEAD").splitlines():
        meta, path = line.split("\t", 1)
        tree[path] = meta.split()[2]
    differs = sorted(name for name, data in files.items()
                     if tree.get(name) != hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest())
    return {"commit": git("rev-parse", "HEAD"), "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
            "inputs_match_commit": not differs, "inputs_differing_from_commit": differs}


def artifact_kind(path: str) -> str:
    return "LIB" if path.endswith(".lib") else "OBJ" if path.endswith(".a") else \
        "TXT" if path.endswith((".h", ".hpp", ".map")) else "EXE"


def identify(args) -> Path:
    tc = Toolchain.discover(args.sdk)
    orca = Orca(tc)
    from .cli import jobs_for
    jobs = jobs_for(tc)
    runtime, hosts = runtime_inputs(), host_inputs()
    ident = build_digest(tc, runtime)
    label = args.label or f"IIgs {ident}"
    configs = [CONFIGS[n] for n in (args.configs or list(CONFIGS))]
    directory = IDENTIFIED / f"{ident}-{utc_stamp()}"
    if directory.exists():
        raise BuildError(f"{directory} already exists; wait a second and retry")
    with DirLock(IDENTIFIED, "identify"):
        say(f"Identified build {ident} -> {rel(directory)}")
        try:
            for name, data in {**runtime, **hosts}.items():
                write_atomic(directory / "source" / name, data)
            builds = {}
            for cfg in configs:
                banner = f"{label} {cfg.variant}" if cfg.variant else None
                build = ConfigBuild(orca, directory / "source", cfg, directory, build_id=banner, jobs=jobs)
                build.executable()
                if cfg.lib:
                    build.library()
                builds[cfg.name] = build
            if "lua" in builds and not args.no_hosts:
                for host in HOSTS:
                    builds["lua"].host(host)
            manifest = write_manifest(tc, directory, ident, label, runtime, hosts, builds)
        except BaseException:
            say(f"Identified build failed; removing incomplete {rel(directory)}")
            remove_tree(directory)
            raise
        make_read_only(directory)
    say(f"Build {ident} complete: {rel(directory / MANIFEST)}")
    for path, info in manifest["artifacts"].items():
        if info["kind"] in ("EXE", "LIB"):
            say(f"  {path:28} {info['size']:>9,} bytes  {info['sha256'][:16]}")
    if manifest["same_id_comparisons"]:
        for comp in manifest["same_id_comparisons"]:
            say(f"  vs {comp['build']}: {len(comp['identical'])} identical, {len(comp['different'])} different")
    return directory


def check_banner(tc: Toolchain, exe: Path, banner: str, log: Path) -> str:
    work = new_unique_dir(TEST_RUNS, "banner")
    try:
        result = subprocess.run([tc.iix, str(exe), "-E", "-v"], cwd=work, env=tc.env(),
                                stdin=subprocess.DEVNULL, capture_output=True, timeout=120)
    except subprocess.TimeoutExpired as exc:
        raise BuildError(f"{exe.name} -v did not finish within 120s under GoldenGate") from exc
    finally:
        remove_tree(work)
    text = (result.stdout + result.stderr).decode(errors="replace")
    write_atomic(log, text.encode())
    if result.returncode or banner not in text:
        raise BuildError(f"{exe.name} -v did not print banner {banner!r}; see {rel(log)}")
    return next(line.strip() for line in text.splitlines() if banner in line)


def write_manifest(tc, directory, ident, label, runtime, hosts, builds) -> dict:
    artifacts, configs, banners = {}, {}, {}
    for name, build in builds.items():
        cfg = build.config
        configs[name] = {"macros": [f"{m}={v}" if v else m for m, v in cfg.macros(build.build_id)],
                         "parseconf_sha256": sha256(build.parseconf.encode()),
                         "units_compiled": len(cfg.core_units()) + 2,
                         "link_inputs": cfg.link_inputs(),
                         "parser": parser_evidence(build) | {"units_omitted": [] if cfg.parser else list(PARSER_UNITS)}}
        if build.build_id:
            banners[name] = check_banner(tc, build.out / cfg.exe, build.build_id,
                                         directory / "logs" / f"banner-{name}.log")
        for path in sorted(build.out.rglob("*")):
            if path.is_file() and ".stamps" not in path.parts:
                key = str(path.relative_to(directory))
                artifacts[key] = {"kind": artifact_kind(key), "size": path.stat().st_size,
                                  "sha256": sha256_file(path)}
    git = git_state({**runtime, **hosts})
    manifest = {
        "schema": "lua-iigs-build/1",
        "build_id": ident,
        "banner_label": label,
        "created_utc": utc_iso(),
        "identity_scope": "runtime sources, recipe, configuration macros, toolchain; "
                          "excludes docs, tests, and packaging code",
        "git": git,
        "recipe": recipe(tc),
        "toolchain_selected_by": tc.sdk_source,
        "runtime_sources_sha256": {k: sha256(v) for k, v in runtime.items()},
        "host_sources_sha256": {k: sha256(v) for k, v in hosts.items()},
        "configurations": configs,
        "banners": banners,
        "artifacts": artifacts,
        "same_id_comparisons": compare_same_id(directory, ident, artifacts),
        "reproducibility": "not claimed; see same_id_comparisons and any release comparison",
        "tests": "none recorded here; test reports are separate (make test BUILD=...)",
        "hardware_validation": "none: newly built executables need their own hardware validation",
    }
    write_json(directory / MANIFEST, manifest)
    return manifest


def compare_same_id(directory: Path, ident: str, artifacts: dict) -> list:
    comparisons = []
    for other in sorted(IDENTIFIED.glob(ident + "-*")):
        if other == directory or not (other / MANIFEST).is_file():
            continue
        theirs = read_json(other / MANIFEST)["artifacts"]
        common = sorted(set(theirs) & set(artifacts))
        comparisons.append({
            "build": other.name,
            "identical": [k for k in common if theirs[k]["sha256"] == artifacts[k]["sha256"]],
            "different": [k for k in common if theirs[k]["sha256"] != artifacts[k]["sha256"]]})
    return comparisons


class IdentifiedBuild:
    """A finished identified build, verified against its manifest on load."""

    def __init__(self, directory: Path):
        self.dir = directory
        self.manifest = read_json(directory / MANIFEST)
        if not self.manifest:
            raise BuildError(f"{directory} has no {MANIFEST}; not an identified build")
        bad = [p for p, info in self.manifest["artifacts"].items()
               if not (directory / p).is_file() or sha256_file(directory / p) != info["sha256"]]
        if bad:
            raise BuildError(f"identified build {directory.name} was modified after it was built: {bad[:5]}")
        self.id = self.manifest["build_id"]

    def path(self, key: str) -> Path:
        if key not in self.manifest["artifacts"]:
            raise BuildError(f"build {self.dir.name} has no {key}")
        return self.dir / key

    def has(self, key: str) -> bool:
        return key in self.manifest["artifacts"]

    @property
    def manifest_sha256(self) -> str:
        return sha256_file(self.dir / MANIFEST)


def resolve(spec: Optional[str]) -> IdentifiedBuild:
    """BUILD= accepts a directory, a directory name, or a unique build-ID prefix."""
    if not spec:
        raise BuildError("select an identified build explicitly: BUILD=<build id|directory> "
                         "(create one with make identify)")
    candidate = Path(spec).expanduser()
    if candidate.is_dir():
        return IdentifiedBuild(candidate.resolve())
    matches = sorted(p for p in IDENTIFIED.glob(spec + "*") if (p / MANIFEST).is_file())
    if len(matches) == 1:
        return IdentifiedBuild(matches[0])
    if not matches:
        raise BuildError(f"no identified build matches {spec!r} under {rel(IDENTIFIED)}")
    raise BuildError(f"{spec!r} is ambiguous: " + ", ".join(p.name for p in matches))


def compare_release(build: IdentifiedBuild, release_dir: Path) -> dict:
    """Compare executables with a published release's recorded hashes."""
    release = read_json(release_dir / "RELEASE-MANIFEST.json")
    if not release:
        raise BuildError(f"{release_dir} has no RELEASE-MANIFEST.json")
    rows = {}
    for name, digest in release["executables_sha256"].items():
        key = RELEASE_NAMES.get(name)
        if key and build.has(key):
            ours = build.manifest["artifacts"][key]["sha256"]
            rows[name] = {"release": digest, "build": ours, "identical": ours == digest}
    return {"release": release.get("tag"), "release_build_id": release.get("build_id"), "executables": rows}
