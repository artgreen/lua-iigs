"""Release-style packages from an identified build ('make package').

Each kind becomes <name>.po + <NAME>.SHK, verified member by member.
Executable bytes are read from the identified build after its manifest
hashes are rechecked; nothing is rebuilt. Readme text is generated here,
so wording changes produce a new package identity while the build (and
its executables) stay the same.
"""
from __future__ import annotations

from pathlib import Path

from .testfiles import test_source
from .common import (PACKAGES, ROOT, BuildError, digest_json, new_unique_dir, read_json, rel, say, sha256,
                     sha256_file, utc_iso, utc_stamp, write_atomic, write_json)
from .contracts import TESTS
from .identified import resolve
from .packaging import Member, build_container, write_sums

KINDS = ("runtime", "small", "compiler", "trace", "library", "library-small", "host")
HEADERS = ("lua.h", "luaconf.h", "lualib.h", "lauxlib.h", "lua.hpp", "parseconf.h")


def _scripts():
    return [Member(t.upper() + ".LUA", test_source(t + ".lua").read_bytes(), "TXT")
            for t in (*TESTS, "tracegc")]


def _library(build, config: str, lib: str):
    include = f"{config}/out/include/"
    members = [Member(lib.upper(), build.path(f"{config}/out/{lib}").read_bytes(), "LIB"),
               Member("LVM.A", build.path(f"{config}/out/lvm.a").read_bytes(), "OBJ")]
    members += [Member(h.upper(), build.path(include + h).read_bytes(), "CSRC") for h in HEADERS]
    return members


def kinds(build) -> dict:
    m = build.manifest
    banner = m.get("banners", {})
    return {
        "runtime": ("lua", "LUA", lambda: [Member("LUA", build.path("lua/out/lua").read_bytes(), "EXE"),
                                           *_scripts()],
                    ["Full Lua interpreter with the source parser, plus the targeted test scripts.",
                     f"Expected banner: {banner.get('lua', '?')}",
                     "Run: lua -E -v   then   lua -E -v hwsmoke.lua"]),
        "small": ("luasmall", "LUASMALL", lambda: [Member("LUASMALL", build.path("lua-small/out/luasmall").read_bytes(), "EXE")],
                  ["Compact parser-free Lua (LUA_NO_PARSER). Runs precompiled bytecode only;",
                   "text chunks are rejected with a catchable error. Compile with LUAC.",
                   f"Expected banner: {banner.get('lua-small', '?')}"]),
        "compiler": ("luac", "LUAC", lambda: [Member("LUAC", build.path("luac/out/luac").read_bytes(), "EXE")],
                     ["LUAC bytecode compiler (always parser-enabled). luac -o out.luo in.lua",
                      "luac -s strips debug information."]),
        "trace": ("luatrace", "LUATRACE", lambda: [Member("LUATRACE", build.path("luatrace/out/luatrace").read_bytes(), "EXE"),
                                                   *_scripts()],
                  ["Diagnostic interpreter with Memory Manager tracing (LUA_IIGS_MMTRACE).",
                   f"Expected banner: {banner.get('luatrace', '?')}"]),
        "library": ("lualib", "LUALIB", lambda: _library(build, "lua", "lua.lib"),
                    ["Full embedding library: link your objects, then LVM.A, then LUA.LIB.",
                     "Headers include this build's PARSECONF.H. See docs/EMBEDDING.md."]),
        "library-small": ("luasmlib", "LUASMLIB", lambda: _library(build, "lua-small", "luasmall.lib"),
                          ["Parser-free embedding library (LUA_NO_PARSER): link LVM.A and LUASMALL.LIB.",
                           "lua_load accepts binary chunks only. Headers include this build's PARSECONF.H."]),
        "host": ("iigshost", "IIGSHOST", lambda: [Member("IIGSHOST", build.path("lua/out/iigshost").read_bytes(), "EXE")],
                 ["Native embedding / C-hook regression host. Run with the HOSTCHECK kit",
                  "(make hardware-suite KIT=host)."]),
    }


def check_report(path: str, build) -> dict:
    report = read_json(Path(path))
    if not report:
        raise BuildError(f"cannot read test report {path}")
    subject = report.get("subject", {})
    if subject.get("build_id") != build.id:
        raise BuildError(f"test report is for build {subject.get('build_id')}, not {build.id}")
    for name, digest in subject.get("executables_sha256", {}).items():
        from .runtests import EXECUTABLES
        if build.manifest["artifacts"].get(EXECUTABLES[name], {}).get("sha256") != digest:
            raise BuildError(f"test report executable {name} does not match build {build.id}")
    return {"file": rel(Path(path)), "sha256": sha256_file(Path(path)), "summary": report.get("summary"),
            "environment": report.get("environment"), "test_identity": report.get("test_identity")}


def package(args) -> int:
    from .toolchain import Toolchain
    tc = Toolchain.discover(args.sdk)
    tc.require_packaging()
    build = resolve(args.build)
    available = kinds(build)
    selected = args.kinds or [k for k in KINDS if k != "library-small" or build.has("lua-small/out/luasmall.lib")]
    for kind in selected:
        if kind not in available:
            raise BuildError(f"unknown package kind {kind!r}; choose from {', '.join(KINDS)}")
    tests = check_report(args.report, build) if args.report else None
    out = new_unique_dir(PACKAGES, f"{build.id}-{utc_stamp()}")
    say(f"Packaging build {build.id} ({build.dir.name}) into {rel(out)}")
    license_text = (ROOT / "LICENSE.txt").read_bytes()
    containers = {}
    for kind in selected:
        base, volume, members_fn, notes = available[kind]
        members = members_fn()
        readme = "\n".join([f"Lua 5.4.6 for Apple IIgs - {kind} package", *notes,
                            f"Build {build.id} ({build.manifest['git']['commit'][:12]}"
                            f"{'' if build.manifest['git']['inputs_match_commit'] else ', uncommitted inputs'}).",
                            "Extract with GS ShrinkIt to preserve ProDOS file types.",
                            "New executables need their own hardware validation."]) + "\n"
        members += [Member("README.TXT", readme.encode(), "TXT"), Member("LICENSE.TXT", license_text, "TXT")]
        say(f"  {kind:14} {len(members)} members -> {base}.po, {volume}.SHK")
        containers[kind] = build_container(tc, out, base, volume, members)
    write_atomic(out / "BUILD-MANIFEST.json", (build.dir / "BUILD-MANIFEST.json").read_bytes())
    manifest = {
        "schema": "lua-iigs-package/1", "utc": utc_iso(),
        "build_id": build.id, "build_dir": build.dir.name, "build_manifest_sha256": build.manifest_sha256,
        "package_identity": digest_json({k: v["members"] for k, v in containers.items()})[:12],
        "packaging_tools": tc.packaging_identity(),
        "tests": tests or "none referenced (pass REPORT=<report.json> to record one)",
        "containers": containers,
        "hardware_validation": "none recorded for these executables",
    }
    write_json(out / "PACKAGE-MANIFEST.json", manifest)
    names = [p.name for p in out.iterdir() if p.is_file() and p.name != "SHA256SUMS"]
    write_sums(out, names)
    say(f"Verified {len(containers)} packages. Manifest: {rel(out / 'PACKAGE-MANIFEST.json')}")
    args.package_path = out
    return 0
