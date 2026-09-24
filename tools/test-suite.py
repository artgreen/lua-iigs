#!/usr/bin/env python3
"""Run or package the reusable IIgs suite, using an explicitly selected executable."""
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
import time

from test_support import FAILURE

ROOT = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def lua_value(value):
    """Manifest contains ASCII strings, integers, arrays and string-keyed tables."""
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=True)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, list):
        return "{" + ",".join(map(lua_value, value)) + "}"
    if isinstance(value, dict):
        return "{" + ",".join("[" + lua_value(k) + "]=" + lua_value(v)
                               for k, v in value.items()) + "}"
    raise ValueError("unsupported manifest value")


def manifest():
    data = json.loads((ROOT / "tests/suite.json").read_text())
    names = data["groups"]["full"]
    if len(names) != len(set(names)) or set(names) != set(data["tests"]):
        raise ValueError("full group must contain each test exactly once")
    for group in data["groups"].values():
        if len(group) != len(set(group)) or not set(group) <= set(names):
            raise ValueError("invalid suite group")
    for name in names:
        if not re.fullmatch(r"[a-z][a-z0-9]*", name) or len(name + ".lua") > 15:
            raise ValueError("invalid ProDOS test filename")
    return data


def validate_suite(text, group, data):
    """A marker before an error, missing tests, or a truncated log cannot pass."""
    if FAILURE.search(text):
        raise ValueError("failure or corruption in output")
    rows = re.findall(r"^SUITE PASS ([a-z0-9]+)( WITH SKIPS)?$", text, re.M)
    if [name for name, _ in rows] != data["groups"][group]:
        raise ValueError("missing, duplicate or out-of-order test completions")
    partial = sum(bool(skip) for _, skip in rows)
    expected = f"SUITE COMPLETE group={group} passed={len(rows)} failed=0 with_skips={partial}"
    if text.splitlines().count(expected) != 1:
        raise ValueError("missing or inconsistent suite summary")
    return {"status": "passed with skips" if partial else "passed",
            "tests": [{"name": name, "status": "passed with skips" if skip else "passed"}
                      for name, skip in rows],
            "skip_evidence": [s for s in text.splitlines() if re.search(r"\bskip\w*\b", s, re.I)]}


def prepare(work, exe, data):
    stage = work / "tests"
    stage.mkdir()
    payload = {"LUATEST": exe.read_bytes(), "SUITECFG.LUA": ("return " + lua_value(data) + "\n").encode(),
               "TEST.LUA": (ROOT / "tests/suite.lua").read_bytes()}
    for name in [*data["tests"], "tracegc"]:
        payload[name.upper() + ".LUA"] = (ROOT / "tests" / (name + ".lua")).read_bytes()
    for name, content in payload.items():
        (stage / name.lower()).write_bytes(content)
    return stage, payload


def package(work, payload, provenance):
    dest = work / "package"
    dest.mkdir()
    payload["README.TXT"] = (
        "IIgs regression suite 1\nRun in a dedicated writable directory.\n"
        "LUATEST -E -v TEST.LUA [smoke|acceptance|runtime|io|stress|full]\n"
        "Default: full (23 tests). tableovf previously took about 18 minutes.\n"
        "Require SUITE COMPLETE then the shell prompt; stops on first failure.\n"
        "Intentional skips remain visible. BUFPROBE sharing output is observational.\n"
        "Standalone LUAC: tools/luac-test-kit.py. Native host: tools/host-test-kit.py.\n"
        "Allocator fault injection and raw MM probes use tools/hardware-kit.py separately.\n"
        "Executable SHA256: " + provenance["executable_sha256"] + "\n"
    ).encode()
    payload["LICENSE.TXT"] = (ROOT / "LICENSE.txt").read_bytes()
    # TXT files use native CR; executable bytes and metadata remain intact.
    transferred = {name: (content if name == "LUATEST" else content.replace(b"\r\n", b"\n").replace(b"\n", b"\r"))
                   for name, content in payload.items()}
    image, archive = dest / "SUITE.po", dest / "SUITE.SHK"
    def run(*args):
        return subprocess.check_output(list(map(str, args)), stderr=subprocess.STDOUT)
    run("acx", "create", "--prodos", "--prodos-order", "-s", "800K", "-n", "LUASUITE", "-d", image)
    for name, content in transferred.items():
        path = dest / name
        path.write_bytes(content)
        run("acx", "import", "-d", image, "--raw", "-t", "EXE" if name == "LUATEST" else "TXT", "-n", name, path)
    run("cp2", "create-file-archive", archive)
    run("cp2", "copy", image, archive)
    for name, content in transferred.items():
        if run("nulib2", "-p", archive, name) != content:
            raise ValueError("archive readback mismatch: " + name)
    attrs = run("cp2", "get-attr", archive, "LUATEST").decode()
    (dest / "attributes.txt").write_text(attrs)
    if "0xb5" not in attrs.lower() or "0x0000" not in attrs.lower():
        raise ValueError("LUATEST must be EXE ($B5), auxiliary type $0000")
    provenance["transfer_sha256"] = {name: sha(content) for name, content in transferred.items()}
    provenance["archive_sha256"] = sha(archive.read_bytes())
    print(f"Verified archive: {archive}")


def main():
    data = manifest()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "package"))
    parser.add_argument("--lua", type=Path, required=True, help="Existing IIgs executable; never rebuilt")
    parser.add_argument("--group", choices=data["groups"], default="full")
    parser.add_argument("--iix", default="iix", help="Emulator executable (recorded in report)")
    parser.add_argument("--timeout", type=int, default=1800, help="Whole local run limit, seconds; no hardware deadline")
    parser.add_argument("--sdk", type=Path, default=Path(os.environ.get("GOLDEN_GATE", ROOT / ".orca-sdk-2.2.1")))
    args = parser.parse_args()
    exe = args.lua.resolve()
    if not exe.is_file() or args.timeout <= 0:
        parser.error("select an existing executable and positive timeout")
    parent = ROOT / "build/suites"
    parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=args.action + "-", dir=parent))
    stage, payload = prepare(work, exe, data)
    report = {"suite_version": data["version"], "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "executable_sha256": sha(exe.read_bytes()),
              "source_sha256": {name: sha(content) for name, content in payload.items()},
              "manifest_sha256": sha((ROOT / "tests/suite.json").read_bytes()),
              "hardware_result": "not established by this tool"}
    failed = False
    try:
        if args.action == "package":
            package(work, payload, report)
        else:
            command = [args.iix, "--memcheck", str(stage / "luatest"), "-E", "-v", "test.lua", args.group]
            report.update(environment="GoldenGate, not hardware", group=args.group,
                          emulator=str(Path(shutil.which(args.iix) or args.iix).resolve()))
            report["emulator_sha256"] = sha(Path(report["emulator"]).read_bytes())
            started = time.monotonic()
            print(f"Running {args.group}; live log: {work / 'suite.log'}", flush=True)
            # File-backed output preserves progress even after a timeout/abort.
            with (work / "suite.log").open("wb") as log:
                result = subprocess.run(command, cwd=stage, stdin=subprocess.DEVNULL,
                                        stdout=log, stderr=subprocess.STDOUT, timeout=args.timeout,
                                        env=dict(os.environ, GOLDEN_GATE=str(args.sdk.resolve())))
            report["elapsed_seconds"] = round(time.monotonic() - started, 2)
            report["exit_code"] = result.returncode
            if result.returncode:
                raise ValueError(f"exit status {result.returncode}")
            report.update(validate_suite((work / "suite.log").read_text(errors="replace"), args.group, data))
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        failed = True
        report.update(status="failed", error=str(exc))
        print(f"FAILED: {exc}")
    finally:
        (work / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"Report: {work / 'report.json'}")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
