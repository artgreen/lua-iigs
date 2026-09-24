#!/usr/bin/env python3
"""Preflight and package a standalone LUAC hardware regression batch."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
# A single sequence drives local process execution and the ORCA EXEC file.
STEPS = [
    ("prepare", "lua", ["-E", "-v", "test.lua", "prepare"], None),
    ("version", "luac", ["-v"], None),
    ("compile-small", "luac", ["-o", "lc.small.out", "lc.small.lua"], None),
    ("small", "lua", ["-E", "test.lua", "small"], None),
    ("compile-debug", "luac", ["-o", "lc.debug.out", "lc.big.lua"], None),
    ("debug", "lua", ["-E", "test.lua", "debug"], None),
    ("compile-stripped", "luac", ["-s", "-o", "lc.strip.out", "lc.big.lua"], None),
    ("stripped", "lua", ["-E", "test.lua", "stripped"], None),
    ("reject-syntax", "luac", ["-p", "lc.bad.lua"], "lc.bad.log"),
    ("syntax", "lua", ["-E", "test.lua", "syntax", "{lcstatus}"], None),
    ("reject-depth", "luac", ["-p", "lc.deep.lua"], "lc.deep.log"),
    ("depth", "lua", ["-E", "test.lua", "depth", "{lcstatus}"], None),
    ("compile-recovery", "luac", ["-o", "lc.again.out", "lc.small.lua"], None),
    ("recovery", "lua", ["-E", "test.lua", "recovery"], None),
    ("finish", "lua", ["-E", "test.lua", "finish"], None),
]
EXE = {"lua": "LUATEST", "luac": "LUACTEST"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def batch(prefix="20:"):
    if not re.fullmatch(r"(?:[0-9]{1,2}:)?", prefix):
        raise ValueError("prefix must be a number followed by a colon, or empty")
    lines = ["* Standalone published LUAC checks. Run in a dedicated test directory.",
             "set exit on"]
    for name, exe, args, errfile in STEPS:
        lines.append("echo LUACPROBE step " + name)
        if errfile:
            lines.append("unset exit")
        line = prefix + EXE[exe].lower() + " " + " ".join(args)
        lines.append(line + (" >&" + errfile if errfile else ""))
        if errfile:
            lines.extend(["set lcstatus {status}", "set exit on"])
    lines.append("exit 0")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-dir", required=True, type=Path,
                        help="Release containing LUA.SHK, LUAC.SHK and RELEASE-MANIFEST.json")
    parser.add_argument("--sdk", required=True, type=Path)
    parser.add_argument("--iix", default="iix")
    parser.add_argument("--prefix", default="20:", help="ORCA executable prefix (default 20:); empty uses shell lookup")
    args = parser.parse_args()
    try:
        script = batch(args.prefix)
    except ValueError as exc:
        parser.error(str(exc))
    release = args.release_dir.resolve()
    manifest = json.loads((release / "RELEASE-MANIFEST.json").read_text())
    parent = ROOT / "build/diagnostics"
    parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="luacprobe1-", dir=parent))
    stage, package = work / "run", work / "package"
    stage.mkdir(); package.mkdir()
    payload = {}
    for name, dest in [("LUA", "LUATEST"), ("LUAC", "LUACTEST")]:
        data = subprocess.check_output(["nulib2", "-p", str(release / (name + ".SHK")), name])
        if sha(data) != manifest["executables_sha256"][name]:
            raise ValueError("release executable hash mismatch: " + name)
        payload[dest] = data
    payload["LICENSE.TXT"] = subprocess.check_output(["nulib2", "-p", str(release / "LUAC.SHK"), "LICENSE.TXT"])
    payload["TEST.LUA"] = (ROOT / "tests/luacprobe.lua").read_bytes()
    payload["TEST"] = script.encode()
    payload["README.TXT"] = (
        "LUACPROBE 1: standalone compiler checks\n"
        f"Extract into a dedicated writable test directory. Run {args.prefix}test\n"
        "TEST is an ORCA EXEC script (SRC B0, auxiliary 0006).\n"
        "Expect LUACPROBE 1 PASSED checks=6 and then the # prompt.\n"
        "The batch stops on unexpected errors; syntax/depth errors are intentional.\n"
        "It creates and removes files named lc.* listed in TEST.LUA.\n"
        "Programs are unchanged published release bytes, renamed for testing.\n"
        "Release: " + manifest["tag"] + "; build: " + manifest["build_id"] + "\n"
        "LUA SHA256: " + sha(payload["LUATEST"]) + "\n"
        "LUAC SHA256: " + sha(payload["LUACTEST"]) + "\n"
    ).encode()
    for name, data in payload.items():
        (stage / name.lower()).write_bytes(data)
    report = {"test": "LUACPROBE 1", "release": manifest["tag"], "build_id": manifest["build_id"],
              "shell_prefix": args.prefix, "hardware_result": "pending", "local_environment": "installed GoldenGate; commands launched separately",
              "shell_batch_validation": "generated from preflight sequence; ORCA batch execution requires hardware",
              "executables_sha256": {n: sha(payload[n]) for n in EXE.values()},
              "source_sha256": sha(payload["TEST.LUA"]), "steps": []}
    env = dict(os.environ, GOLDEN_GATE=str(args.sdk.resolve()))
    status = None
    with (work / "preflight.log").open("w") as log:
        for name, exe, argv, errfile in STEPS:
            command = [args.iix, "--memcheck", str(stage / EXE[exe].lower())]
            command += [str(status) if v == "{lcstatus}" else v for v in argv]
            print("Preflight " + name, flush=True)
            result = subprocess.run(command, cwd=stage, env=env, stdin=subprocess.DEVNULL,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
            text = result.stdout.decode(errors="replace")
            log.write("STEP " + name + "\n" + text + "\n"); log.flush()
            if re.search(r"MemCheck:|\bBRK\b|\bFAIL(?:ED)?\b|mm=degraded", text):
                raise ValueError("failure/corruption in " + name)
            if errfile:
                if result.returncode == 0:
                    raise ValueError("invalid input accepted: " + name)
                (stage / errfile).write_bytes(result.stdout)
                status = result.returncode
            elif result.returncode:
                raise ValueError("nonzero status in " + name)
            if exe == "lua":
                marker = ("LUACPROBE 1 PASSED checks=6 - expect shell prompt next" if name == "finish"
                          else "LUACPROBE 1 PHASE PASSED " + name)
                if marker not in text.splitlines():
                    raise ValueError("missing completion in " + name)
            report["steps"].append({"name": name, "exit_code": result.returncode,
                                    "result": "expected rejection" if errfile else "passed"})
    image, archive = package / "TEST.po", package / "TEST.SHK"
    def run(*command):
        return subprocess.check_output(list(map(str, command)), stderr=subprocess.STDOUT)
    run("acx", "create", "--prodos", "--prodos-order", "-s", "800K", "-n", "LUACTEST", "-d", image)
    report["transfer_sha256"] = {}
    for name, data in payload.items():
        native = data if name in EXE.values() else data.replace(b"\r\n", b"\n").replace(b"\n", b"\r")
        (package / name).write_bytes(native)
        kind, aux = ("EXE", "0") if name in EXE.values() else (("SRC", "6") if name == "TEST" else ("TXT", "0"))
        run("acx", "import", "-d", image, "--raw", "-t", kind, "--aux", aux, "-n", name, package / name)
        report["transfer_sha256"][name] = sha(native)
    run("cp2", "create-file-archive", archive)
    run("cp2", "copy", image, archive)
    for name, digest in report["transfer_sha256"].items():
        if sha(run("nulib2", "-p", archive, name)) != digest:
            raise ValueError("archive readback mismatch: " + name)
    attrs = []
    for name, typ, aux in [("LUATEST", "0xb5", "0x0000"), ("LUACTEST", "0xb5", "0x0000"), ("TEST", "0xb0", "0x0006")]:
        text = run("cp2", "get-attr", archive, name).decode()
        if typ not in text.lower() or aux not in text.lower():
            raise ValueError("wrong metadata: " + name)
        attrs.append(text)
    (work / "attributes.txt").write_text("\n".join(attrs))
    report["archive_sha256"] = sha(archive.read_bytes())
    report["local_result"] = "six checks passed; all processes returned"
    (work / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Verified kit: " + str(work))


if __name__ == "__main__":
    main()
