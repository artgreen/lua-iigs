#!/usr/bin/env python3
"""Verify and package the published native C embedding/C-hook test for hardware."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def batch(prefix="20:"):
    if not re.fullmatch(r"(?:[0-9]{1,2}:)?", prefix):
        raise ValueError("prefix must be numeric with a colon, or empty")
    return "\n".join([
        "* Native C host and hook test. No interpreter rebuild.",
        "set exit on",
        prefix + "luatest -E -v test.lua prepare",
        "echo HOSTCHECK starting native host. This phase runs quietly.",
        "unset exit",
        prefix + "iigshost >host.out >&host.err",
        "set hoststatus {status}",
        "set exit on",
        prefix + "luatest -E test.lua verify {hoststatus}",
        prefix + "luatest -E test.lua finish",
        "exit 0", ""])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-dir", required=True, type=Path)
    parser.add_argument("--sdk", required=True, type=Path)
    parser.add_argument("--iix", default="iix")
    parser.add_argument("--prefix", default="20:")
    args = parser.parse_args()
    try:
        script = batch(args.prefix)
    except ValueError as exc:
        parser.error(str(exc))
    release = args.release_dir.resolve()
    manifest = json.loads((release / "RELEASE-MANIFEST.json").read_text())
    parent = ROOT / "build/diagnostics"
    parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="hostcheck1-", dir=parent))
    stage, package = work / "run", work / "package"
    stage.mkdir(); package.mkdir()
    payload = {}
    for name, dest in [("LUA", "LUATEST"), ("IIGSHOST", "IIGSHOST")]:
        data = subprocess.check_output(["nulib2", "-p", str(release / (name + ".SHK")), name])
        if sha(data) != manifest["executables_sha256"][name]:
            raise ValueError("release hash mismatch: " + name)
        payload[dest] = data
    payload["LICENSE.TXT"] = subprocess.check_output(["nulib2", "-p", str(release / "IIGSHOST.SHK"), "LICENSE.TXT"])
    payload["TEST"] = script.encode()
    payload["TEST.LUA"] = (ROOT / "tests/hostcheck.lua").read_bytes()
    payload["HWSMOKE.LUA"] = (ROOT / "tests/hwsmoke.lua").read_bytes()
    payload["README.TXT"] = (
        "HOSTCHECK 1: native C embedding and hook yields\n"
        f"Extract into a dedicated writable test directory. Run {args.prefix}test\n"
        "The native host is quiet until it returns. No hardware time limit is specified.\n"
        "Checks initialization, stack recovery, vector/array limits, retained data and C-hook yields.\n"
        "A fresh Lua smoke run follows. Require HOSTCHECK 1 PASSED and then #.\n"
        "Failure logs host.out and host.err are retained. Successful runs remove them and host.state.\n"
        "These three filenames belong to the test and are replaced on each run.\n"
        "Release " + manifest["tag"] + " build " + manifest["build_id"] + "\n"
        "IIGSHOST SHA256 " + sha(payload["IIGSHOST"]) + "\n"
        "LUATEST SHA256 " + sha(payload["LUATEST"]) + "\n"
    ).encode()
    for name, data in payload.items():
        (stage / name.lower()).write_bytes(data)
    report = {"test": "HOSTCHECK 1", "release": manifest["tag"], "build_id": manifest["build_id"],
              "shell_prefix": args.prefix, "hardware_result": "pending",
              "local_environment": "installed GoldenGate, separate native processes; not ORCA batch execution",
              "executables_sha256": {n: sha(payload[n]) for n in ("LUATEST", "IIGSHOST")},
              "source_sha256": {n: sha(payload[n]) for n in ("TEST", "TEST.LUA", "HWSMOKE.LUA")}}
    env = dict(os.environ, GOLDEN_GATE=str(args.sdk.resolve()))
    with (work / "preflight.log").open("wb") as log:
        def run_native(exe, argv, marker=None):
            print("Preflight " + exe + " " + " ".join(argv), flush=True)
            result = subprocess.run([args.iix, "--memcheck", str(stage / exe), *argv], cwd=stage,
                                    env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, timeout=300)
            log.write(result.stdout + result.stderr); log.flush()
            text = (result.stdout + result.stderr).decode(errors="replace")
            if result.returncode or re.search(r"MemCheck:|\bBRK\b|\bFAIL(?:ED)?\b|mm=degraded", text):
                raise ValueError("native preflight failure: " + exe)
            if marker and not re.search(marker, text, re.M):
                raise ValueError("missing completion: " + exe)
            return result
        run_native("luatest", ["-E", "-v", "test.lua", "prepare"], r"^HOSTCHECK 1 PREPARED$")
        host = run_native("iigshost", [], r"^IIGSHOST PASSED yields=\d+$")
        (stage / "host.out").write_bytes(host.stdout)
        (stage / "host.err").write_bytes(host.stderr)
        run_native("luatest", ["-E", "test.lua", "verify", str(host.returncode)], r"^HOSTCHECK 1 HOST VERIFIED yields=\d+$")
        run_native("luatest", ["-E", "test.lua", "finish"], r"^HOSTCHECK 1 PASSED - expect shell prompt next$")
    def run(*command):
        return subprocess.check_output(list(map(str, command)), stderr=subprocess.STDOUT)
    image, archive = package / "TEST.po", package / "TEST.SHK"
    run("acx", "create", "--prodos", "--prodos-order", "-s", "800K", "-n", "HOSTCHECK", "-d", image)
    report["transfer_sha256"] = {}
    for name, data in payload.items():
        binary = name in ("LUATEST", "IIGSHOST")
        native = data if binary else data.replace(b"\r\n", b"\n").replace(b"\n", b"\r")
        (package / name).write_bytes(native)
        kind, aux = ("EXE", "0") if binary else (("SRC", "6") if name == "TEST" else ("TXT", "0"))
        run("acx", "import", "-d", image, "--raw", "-t", kind, "--aux", aux, "-n", name, package / name)
        report["transfer_sha256"][name] = sha(native)
    run("cp2", "create-file-archive", archive)
    run("cp2", "copy", image, archive)
    for name, digest in report["transfer_sha256"].items():
        if sha(run("nulib2", "-p", archive, name)) != digest:
            raise ValueError("archive readback mismatch: " + name)
    attrs = []
    for name, typ, aux in [("LUATEST", "0xb5", "0x0000"), ("IIGSHOST", "0xb5", "0x0000"), ("TEST", "0xb0", "0x0006")]:
        text = run("cp2", "get-attr", archive, name).decode()
        if typ not in text.lower() or aux not in text.lower():
            raise ValueError("wrong metadata: " + name)
        attrs.append(text)
    (work / "attributes.txt").write_text("\n".join(attrs))
    report["archive_sha256"] = sha(archive.read_bytes())
    report["local_result"] = "native host and post-host smoke passed, all processes returned"
    (work / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Verified kit: " + str(work))


if __name__ == "__main__":
    main()
