"""Assemble a complete local release candidate from committed, tested inputs.

Never rebuilds runtime executables, tags, uploads, or overwrites a candidate.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
import posixpath
import re
import shutil
import subprocess
from types import SimpleNamespace
import zipfile

from .common import (ROOT, BuildError, digest_json, new_unique_dir, read_json, rel,
                     say, sha256_file, utc_iso, utc_stamp, write_json)
from .distribution import source_files
from .identified import resolve, runtime_inputs, host_inputs
from .packaging import Member, build_container, write_sums
from .runtests import ALL_CHECKS, EXECUTABLES, NEEDS, expected_checks, test_inputs
from .toolchain import Toolchain


def approved_report(path, build):
    report = read_json(Path(path), {})
    if report.get("schema") != "lua-iigs-test-report/1":
        raise BuildError("release requires a current test report")
    subject = report.get("subject", {})
    if (subject.get("build_id") != build.id or
            subject.get("build_manifest_sha256") != build.manifest_sha256):
        raise BuildError("report does not identify this exact build manifest")
    checks = report.get("checks", [])
    def accepted(check):
        if check.get("status") in ("passed", "passed with skips"):
            return True
        # The ORCA memory-report tool needs real hardware and is intentionally build-only.
        return (check.get("group"), check.get("name"), check.get("subject"), check.get("status")) == (
            "hosts", "memfree", "memfree", "built, not run")
    if not checks or not all(accepted(c) for c in checks):
        raise BuildError("release requires a successful report")
    if Counter((c.get("group"), c.get("name"), c.get("subject")) for c in checks) != Counter(expected_checks()):
        raise BuildError("release requires every check exactly once in all groups: " + " ".join(ALL_CHECKS))
    if any(not isinstance(c.get("tests"), int) or c["tests"] <= 0 for c in checks if c["group"] == "unit"):
        raise BuildError("report must include executed tooling tests")
    summary = report.get("summary", {})
    if summary != {"failed": 0, "total": len(checks),
                   "built_only": sum(c["status"] == "built, not run" for c in checks),
                   "with_skips": sum(bool(c.get("skips")) for c in checks)}:
        raise BuildError("report summary does not match its successful checks")
    expected = {name for group in ALL_CHECKS for name in NEEDS[group]}
    for name in expected:
        expected_hash = build.manifest["artifacts"].get(EXECUTABLES[name], {}).get("sha256")
        if not expected_hash or subject.get("executables_sha256", {}).get(name) != expected_hash:
            raise BuildError(f"report executable {name} does not match this build")
    inputs = test_inputs()
    if report.get("test_inputs_sha256") != inputs or report.get("test_identity") != digest_json(inputs)[:12]:
        raise BuildError("test inputs changed since the report; rerun all checks")
    return report


def committed_sources(build):
    """Use an exact committed tree, not an accidental export of local artifacts."""
    def git(*args):
        p = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
        if p.returncode:
            raise BuildError("release assembly requires a committed Git checkout")
        return p.stdout.strip()
    if Path(git("rev-parse", "--show-toplevel")).resolve() != ROOT.resolve():
        raise BuildError("release assembly requires this project's own Git checkout")
    commit = git("rev-parse", "HEAD")
    if git("status", "--porcelain", "--untracked-files=all"):
        raise BuildError("commit source changes before assembling a release")
    names = git("ls-files").splitlines()
    if set(names) != set(source_files(ROOT)):
        raise BuildError("tracked files differ from the source distribution inventory")
    for actual, key in ((runtime_inputs(), "runtime_sources_sha256"), (host_inputs(), "host_sources_sha256")):
        from .common import sha256
        if {name: sha256(data) for name, data in actual.items()} != build.manifest[key]:
            raise BuildError("committed runtime/host sources differ from the selected build")
    return commit, names


def zip_files(path, files):
    """files maps safe archive names to source paths; also verifies ZIP integrity."""
    with zipfile.ZipFile(path, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, source in sorted(files.items()):
            archive.write(source, name)
    with zipfile.ZipFile(path) as archive:
        if archive.testzip():
            raise BuildError(f"ZIP integrity check failed: {path.name}")


def render_guide(name, local, commit):
    """Keep bundled links local; pin all other repository links to this commit."""
    from urllib.parse import urlsplit
    def link(match):
        target = match[1]
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc or not parsed.path:
            return match[0]
        path = posixpath.normpath(posixpath.join(posixpath.dirname(name), parsed.path))
        suffix = ("?" + parsed.query if parsed.query else "") + ("#" + parsed.fragment if parsed.fragment else "")
        if path in local:
            dest = posixpath.relpath(local[path], posixpath.dirname(local[name]) or ".")
        else:
            dest = f"https://github.com/artgreen/lua-iigs/blob/{commit}/{path}"
        return "](" + dest + suffix + ")"
    return re.sub(r"\]\(([^)]+)\)", link, (ROOT / name).read_text())


def bundle_guides(out, commit):
    names = [str(p.relative_to(ROOT)) for tree in ("docs", "tests", "examples")
             for p in (ROOT / tree).rglob("*.md")]
    local = {name: name for name in names}
    result = {}
    for name in names:
        path = out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_guide(name, local, commit))
        result[name] = path
    result["docs/BASELINE.json"] = ROOT / "docs/BASELINE.json"
    return result


def product_members(build, compact, commit):
    main = "LUASMALL" if compact else "LUA"
    key = "lua-small/out/luasmall" if compact else "lua/out/lua"
    members = [Member(main, build.path(key).read_bytes(), "EXE"),
               Member("LUAC", build.path("luac/out/luac").read_bytes(), "EXE")]
    examples = [ROOT / "examples/hello.lua"] if compact else sorted((ROOT / "examples").glob("*.lua"))
    members += [Member(p.name.upper(), p.read_bytes(), "TXT") for p in examples]
    if not compact:
        members.append(Member("HWSMOKE.LUA", (ROOT / "tests/regression/hwsmoke.lua").read_bytes(), "TXT"))
    notes = (ROOT / "packaging" / ("compact.txt" if compact else "standard.txt")).read_text()
    notes += f"\nBuild {build.id}\nExpected banner: {build.manifest['banners']['lua-small' if compact else 'lua']}\n"
    notes += "Hardware acceptance of this distribution is recorded separately.\n"
    members += [Member("README.TXT", notes.encode(), "TXT"),
                Member("LICENSE.TXT", (ROOT / "LICENSE.txt").read_bytes(), "TXT")]
    guides = {"docs/INSTALL.md": "INSTALL.TXT", "docs/COMPATIBILITY.md": "COMPAT.TXT",
              "docs/USAGE.md": "USAGE.TXT", "examples/README.md": "EXAMPLES.TXT"}
    local = {**guides, **{str(p.relative_to(ROOT)): p.name.upper() for p in examples}}
    for name, filename in guides.items():
        members.append(Member(filename, render_guide(name, local, commit).encode(), "TXT"))
    return members


def release(args):
    build = resolve(args.build)
    report = approved_report(args.report, build)
    commit, names = committed_sources(build)
    version = (ROOT / "VERSION").read_text().strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?", version):
        raise BuildError("VERSION must contain a release version")
    tc = Toolchain.discover(args.sdk)
    tc.require_packaging()
    out = new_unique_dir(ROOT / "build/release-staging", f"lua-iigs-{version}-{utc_stamp()}")
    say(f"Assembling local release candidate in {rel(out)}")
    assemble(args, build, report, commit, names, version, tc, out)
    destination = ROOT / "dist" / out.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise BuildError(f"candidate destination already exists: {destination}")
    out.rename(destination)
    say(f"Candidate ready: {rel(destination)} (hardware acceptance and publication remain separate)")
    args.release_path = destination
    return 0


def assemble(args, build, report, commit, names, version, tc, out):
    containers = {}
    for base, compact in (("lua", False), ("luasmall", True)):
        containers[base] = build_container(tc, out, base, base.upper(), product_members(build, compact, commit), image_size="1600K")
    from .packages import package
    ns = SimpleNamespace(sdk=args.sdk, build=str(build.dir), kinds=["library", "library-small", "trace", "host"], report=args.report)
    package(ns)
    components = ns.package_path
    sdk = {n: components / n for n in ("lualib.po", "LUALIB.SHK", "luasmlib.po", "LUASMLIB.SHK")}
    sdk["LICENSE.txt"] = ROOT / "LICENSE.txt"
    example = [Member(p.name.upper(), p.read_bytes(), "TXT" if p.suffix == ".lua" else "CSRC")
               for p in sorted((ROOT / "examples/embedding").iterdir()) if p.suffix in (".c", ".h", ".lua")]
    example += [Member("README.TXT", (ROOT / "packaging/embedding.txt").read_bytes(), "TXT"),
                Member("LICENSE.TXT", (ROOT / "LICENSE.txt").read_bytes(), "TXT")]
    embed = build_container(tc, out / "work", "embed", "EMBED", example)
    sdk.update({"EMBED.SHK": out / "work/EMBED.SHK", "embed.po": out / "work/embed.po"})
    component_record = read_json(components / "PACKAGE-MANIFEST.json")
    sdk_record = dict(component_record)
    sdk_record["containers"] = {k: component_record["containers"][k] for k in ("library", "library-small")}
    sdk_record["containers"]["embedding-example"] = embed
    sdk_record["package_identity"] = digest_json({k: v["members"] for k, v in sdk_record["containers"].items()})[:12]
    write_json(out / "work/SDK-MANIFEST.json", sdk_record)
    sdk["SDK-MANIFEST.json"] = out / "work/SDK-MANIFEST.json"
    guides = bundle_guides(out / "work/guides", commit)
    sdk.update(guides)
    (out / "work/README.txt").write_text("Lua IIgs embedding SDK\n\n"
        "Extract LUALIB.SHK for full Lua, or LUASMLIB.SHK for compact Lua. Keep their headers and VM objects separate.\n"
        "EMBED.SHK contains the C embedding example for the full library. Read docs/EMBEDDING.md for the host contract and SDK commands.\n"
        "Transfer the SHK or PO containers to preserve ProDOS metadata.\n")
    sdk["README.txt"] = out / "work/README.txt"
    sdk["BUILD-MANIFEST.json"] = build.dir / "BUILD-MANIFEST.json"
    sdk_name = f"lua-iigs-{version}-sdk.zip"
    zip_files(out / sdk_name, sdk)
    diagnostics = {n: components / n for n in ("luatrace.po", "LUATRACE.SHK", "iigshost.po", "IIGSHOST.SHK")}
    diagnostics["BUILD-MANIFEST.json"] = build.dir / "BUILD-MANIFEST.json"
    diagnostics.update(guides)
    (out / "work/DIAGNOSTICS.txt").write_text("Lua IIgs diagnostics\n\n"
        "Read tests/hardware/PROCEDURE.md and the adjacent kit guides.\n"
        "Keep each kit in its own directory; all use the name TEST.SHK.\n"
        "Transfer the SHK or PO containers to preserve ProDOS metadata.\n"
        "Local preflight results are emulator checks; hardware acceptance is pending.\n")
    diagnostics["README.txt"] = out / "work/DIAGNOSTICS.txt"
    kits = {}
    from .kits import hardware_suite
    for kit in ("suite", "lua", "small", "luac", "host"):
        ns = SimpleNamespace(sdk=args.sdk, build=str(build.dir), release=None, exe=None,
                             kit=kit, group="full" if kit == "suite" else "smoke", prefix="20:", preflight=None)
        hardware_suite(ns)
        for name in ("TEST.SHK", "TEST.po", "KIT-MANIFEST.json", "SHA256SUMS"):
            diagnostics[f"{kit}/{name}"] = ns.package_path / name
        kits[kit] = read_json(ns.package_path / "KIT-MANIFEST.json")
    diag_record = dict(component_record)
    diag_record["containers"] = {k: component_record["containers"][k] for k in ("trace", "host")}
    diag_record["package_identity"] = digest_json({k: v["members"] for k, v in diag_record["containers"].items()})[:12]
    write_json(out / "work/DIAGNOSTICS-MANIFEST.json", diag_record)
    diagnostics["DIAGNOSTICS-MANIFEST.json"] = out / "work/DIAGNOSTICS-MANIFEST.json"
    diag_name = f"lua-iigs-{version}-diagnostics.zip"
    zip_files(out / diag_name, diagnostics)
    # Export the commit itself, even if an editor changes working files during packaging.
    prefix = f"lua-iigs-{version}/"
    source_name = f"lua-iigs-{version}-source.zip"
    result = subprocess.run(["git", "archive", "--format=zip", "--prefix=" + prefix,
                             "--output=" + str(out / source_name), commit], cwd=ROOT, capture_output=True)
    if result.returncode:
        raise BuildError("could not export the committed source tree")
    from .common import sha256
    with zipfile.ZipFile(out / source_name, "a", compression=zipfile.ZIP_DEFLATED) as archive:
        source_manifest = {"schema": "lua-iigs-source/1", "commit": commit,
                           "files_sha256": {name: sha256(archive.read(prefix + name)) for name in names}}
        archive.writestr(prefix + "SOURCE-MANIFEST.json", json.dumps(source_manifest, indent=2) + "\n")
        if archive.testzip():
            raise BuildError("source ZIP integrity check failed")
    write_json(out / "SOURCE-MANIFEST.json", source_manifest)
    # A completed candidate must still describe the tree and tests selected at entry.
    if committed_sources(build)[0] != commit:
        raise BuildError("source commit changed during release assembly")
    approved_report(args.report, build)
    shutil.copyfile(build.dir / "BUILD-MANIFEST.json", out / "BUILD-MANIFEST.json")
    shutil.copyfile(args.report, out / "TEST-REPORT.json")
    release_manifest = {"schema": "lua-iigs-release/1", "version": version, "tag": "v" + version,
                        "status": "local candidate; not published", "utc": utc_iso(), "source_commit": commit,
                        "build_id": build.id, "build_manifest_sha256": build.manifest_sha256,
                        "test_report_sha256": sha256_file(out / "TEST-REPORT.json"), "test_summary": report["summary"],
                        "containers": containers, "embedding_source_container": embed,
                        "components": read_json(components / "PACKAGE-MANIFEST.json"), "kits": kits,
                        "executables_sha256": {name.upper(): build.manifest["artifacts"][key]["sha256"]
                                                for name, key in EXECUTABLES.items()
                                                if name in ("lua", "luac", "luasmall", "luatrace", "iigshost")},
                        "executable_containers": {
                            "LUA": {"archive": "LUA.SHK"}, "LUAC": {"archive": "LUA.SHK"},
                            "LUASMALL": {"archive": "LUASMALL.SHK"},
                            "LUATRACE": {"zip": diag_name, "archive": "LUATRACE.SHK"},
                            "IIGSHOST": {"zip": diag_name, "archive": "IIGSHOST.SHK"}},
                        "hardware_validation": "pending; see docs/VALIDATION.md for previous artifact evidence"}
    write_json(out / "RELEASE-MANIFEST.json", release_manifest)
    (out / "README.txt").write_text(f"Lua IIgs {version} — local release candidate\n\n"
        "Start with LUA.SHK or lua.po. Extract with GS ShrinkIt, then run lua -E hello.lua.\n"
        "LUASMALL.SHK is the bytecode-only alternative. SDK and diagnostics are separate ZIP bundles.\n"
        "Hardware acceptance and maintainer review are pending. Nothing has been published.\n")
    shutil.rmtree(out / "files")
    shutil.rmtree(out / "work")
    write_sums(out, [p.name for p in out.iterdir() if p.is_file()])
