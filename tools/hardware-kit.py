#!/usr/bin/env python3
"""Clean, isolated ORCA/C builds, checked in GoldenGate and packaged for IIgs.

Requires iix, make, an ORCA/C 2.2.x SDK, and AppleCommander's native acx.
Existing src objects, build/lua, and user disk images are never overwritten.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TESTS = ("hwsmoke", "sieve", "coroutine", "cobeacon", "cstack", "pm",
         "hwdiag2", "hwtest")
SCRIPTS = TESTS + ("tracegc",)  # cstack requires this helper


def sha(data):
    return hashlib.sha256(data).hexdigest()


def run(argv, cwd, env, log, timeout=300):
    with log.open("wb") as out:
        result = subprocess.run([str(a) for a in argv], cwd=cwd, env=env,
                                stdout=out, stderr=subprocess.STDOUT,
                                timeout=timeout)
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}); see {log}")
    return log.read_text(errors="replace")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", type=Path,
                        default=Path(os.environ.get("GOLDEN_GATE", ROOT / ".orca-sdk-2.2.1")))
    parser.add_argument("--acx", default=shutil.which("acx") or str(Path.home() / ".local/bin/acx"))
    parser.add_argument("--plain-name", default="luaplain",
                        help="Distinct plain executable/image name (ProDOS, up to 15 characters)")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9.]{0,14}", args.plain_name) or args.plain_name.lower() == "luatrace":
        parser.error("--plain-name must be a distinct ProDOS filename, not luatrace")
    sdk = args.sdk.resolve()
    if not (sdk / "Languages").is_dir():
        parser.error("Select an ORCA/C 2.2.x SDK with --sdk")
    for tool in ("iix", "make", args.acx):
        if not shutil.which(tool):
            parser.error(f"Required tool is missing: {tool}")
    inputs = sorted([*ROOT.joinpath("src").glob("*.c"),
                     *ROOT.joinpath("src").glob("*.h"), ROOT / "src/Makefile",
                     Path(__file__), ROOT / "HARDWARE_TESTING.md",
                     *(ROOT / "tests" / (t + ".lua") for t in SCRIPTS)])
    # Keep an immutable snapshot of exactly the source bytes being built.
    snapshot = {str(p.relative_to(ROOT)): p.read_bytes() for p in inputs}
    hashes = {name: sha(data) for name, data in snapshot.items()}
    digest = sha(json.dumps(hashes, sort_keys=True).encode())[:12]
    commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    ident = f"{commit}-{digest}"
    parent = ROOT / "build/hardware"
    parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=stamp + "-", dir=parent))
    print(f"Building {ident} in {work}", flush=True)
    source = work / "source"
    for name, data in snapshot.items():
        dest = source / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    logs = work / "logs"
    logs.mkdir()
    env = dict(os.environ, GOLDEN_GATE=str(sdk))
    manifest = {"id": ident, "commit": commit, "utc": stamp,
                "plain_name": args.plain_name,
                "source_sha256": hashes, "sdk": str(sdk),
                "compiler_sha256": {}, "executables": {}, "checks": {}}
    for p in sorted((sdk / "Languages").iterdir()):
        if p.is_file():
            manifest["compiler_sha256"][p.name] = sha(p.read_bytes())
    for variant in ("plain", "trace"):
        stage = work / variant
        shutil.copytree(source / "src", stage / "src")
        (stage / "build").mkdir()
        config = stage / "src/luaconf.h"
        prefix = f'#define LUA_IIGS_BUILD_ID "IIgs {ident} {variant}"\n'
        if variant == "trace":
            prefix += "#define LUA_IIGS_MMTRACE\n"
        config.write_bytes(prefix.encode() + config.read_bytes())
        # Independent clean directories prevent mixing traced/untraced objects.
        run(["make", "lua"], stage / "src", env, logs / f"{variant}-build.log", 1200)
        exe = stage / "build/lua"
        manifest["executables"][variant] = sha(exe.read_bytes())
        output = run(["iix", exe, "-E", "-v"], stage, env, logs / f"{variant}-version.log")
        if f"IIgs {ident} {variant}" not in output:
            raise RuntimeError("Build identification missing")
        testdir = stage / "tests"
        shutil.copytree(source / "tests", testdir)
        results = {}
        for test in TESTS:
            output = run(["iix", "--memcheck", exe, "-E", test + ".lua"],
                         testdir, env, logs / f"{variant}-{test}.log")
            if re.search(r"MemCheck:|\bBRK\b|\bFAIL(?:ED)?\b|SOME TESTS FAILED", output):
                raise RuntimeError(f"{variant}/{test}: diagnostic failure; see {logs}")
            expected = {"hwsmoke": "SMOKE DONE", "sieve": "C stack overflow",
                        "cobeacon": "BEACON DONE", "hwdiag2": "ALL DIAGNOSTICS PASSED",
                        "hwtest": "ALL TESTS PASSED"}.get(test, "OK")
            if expected not in output:
                raise RuntimeError(f"{variant}/{test}: missing completion marker {expected}")
            if variant == "trace" and "[M7] state closed" not in output:
                raise RuntimeError(f"{variant}/{test}: missing shutdown marker")
            results[test] = "passed (GoldenGate, not hardware)"
            print(f"  {variant}: {test} passed", flush=True)
        manifest["checks"][variant] = results
        if variant == "plain":
            run(["make", "luac"], stage / "src", env, logs / "luac-build.log", 1200)
            compiler = stage / "build/luac"
            output = run(["iix", "--memcheck", compiler, "-o", "smoke.out", "hwsmoke.lua"],
                         testdir, env, logs / "luac-smoke.log")
            if re.search(r"MemCheck:|\bBRK\b", output):
                raise RuntimeError("luac reported memory corruption")
            output = run(["iix", "--memcheck", exe, "smoke.out"],
                         testdir, env, logs / "luac-roundtrip.log")
            if "SMOKE DONE" not in output or re.search(r"MemCheck:|\bBRK\b", output):
                raise RuntimeError("luac smoke roundtrip failed")
            manifest["checks"]["luac-roundtrip"] = "passed"
            (testdir / "deep.lua").write_text("return " + "(" * 500 + "1" + ")" * 500 + "\n")
            result = subprocess.run(["iix", "--memcheck", str(compiler), "-p", "deep.lua"],
                                    cwd=testdir, env=env, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, timeout=300)
            (logs / "luac-depth.log").write_bytes(result.stdout)
            output = result.stdout.decode(errors="replace")
            if (result.returncode == 0 or "C stack overflow" not in output
                    or re.search(r"MemCheck:|\bBRK\b", output)):
                raise RuntimeError("luac did not reject excessive parser nesting cleanly")
            manifest["checks"]["luac-depth"] = "clean C stack overflow, no corruption"
    package = work / "package"
    package.mkdir()
    for variant, name in (("plain", args.plain_name), ("trace", "luatrace")):
        transferdir = work / variant / "transfer"
        transferdir.mkdir()
        exe = work / variant / "build/lua"
        image = package / (name + ".po")
        run([args.acx, "create", "--prodos", "--prodos-order", "-s", "800K",
             "-n", "LUA" if variant == "plain" else "LUATRACE", "-d", image],
            work, env, logs / f"{variant}-disk-create.log")
        run([args.acx, "import", "-d", image, "--raw", "-t", "EXE", "-n", name, exe],
            work, env, logs / f"{variant}-disk-exe.log")
        # Import ASCII with CR line endings explicitly; do not set high bits.
        diskfiles = {t + ".lua": snapshot["tests/" + t + ".lua"] for t in SCRIPTS}
        diskfiles["readme.txt"] = snapshot["HARDWARE_TESTING.md"]
        diskfiles["build.txt"] = (f"IIgs {ident} {variant}\nSHA256 {manifest['executables'][variant]}\n").encode()
        for filename, data in diskfiles.items():
            data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r")
            transfer = transferdir / filename
            transfer.write_bytes(data)
            run([args.acx, "import", "-d", image, "--raw", "-t", "TXT", "-n", filename, transfer],
                work, env, logs / f"{variant}-disk-{filename}.log")
            exported = subprocess.check_output([args.acx, "export", "-d", str(image), "--raw", filename.upper()])
            if exported != data:
                raise RuntimeError(f"Text damaged while packaging {filename}")
        # Read the executable back from the image; compare every byte.
        exported = subprocess.check_output([args.acx, "export", "-d", str(image), "--raw", name.upper()])
        if sha(exported) != manifest["executables"][variant]:
            raise RuntimeError(f"Executable damaged while packaging {image}")
        run([args.acx, "list", "-d", image], work, env, logs / f"{variant}-catalog.log")
    (package / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (package / "HARDWARE_TESTING.md").write_bytes(snapshot["HARDWARE_TESTING.md"])
    files = sorted(package.iterdir())
    (package / "SHA256SUMS").write_text("".join(f"{sha(p.read_bytes())}  {p.name}\n" for p in files))
    print(f"Verified hardware kit: {package}", flush=True)


if __name__ == "__main__":
    main()
