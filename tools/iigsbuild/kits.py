"""Real-hardware test kits ('make hardware-suite'), one implementation for
every kit. Each kit is a TEST.SHK archive (plus the matching TEST.po image)
containing an ORCA EXEC batch named TEST, a Lua entry point TEST.LUA, the
executables under test renamed LUATEST/LUACTEST/IIGSHOST, and readme and
license text. Stable names let the same commands be reused on the IIgs:

    yankit xvf /nas/lua.test/test.shk
    20:test

Kits:
  suite  reusable Lua regression suite on the full interpreter
  small  bytecode acceptance for the parser-free interpreter (compiled by
         the same build's luac), source rejection, debug + stripped forms
  luac   standalone compiler checks (LUACPROBE 1)
  host   native embedding / C-hook host (HOSTCHECK 1)

Executables come from an identified build (BUILD=) or a published release
directory (RELEASE=, verified against RELEASE-MANIFEST.json). They are never
rebuilt. A local GoldenGate preflight runs the same steps as the batch;
its result is recorded as an emulator result, and the hardware result is
left pending.
"""
from __future__ import annotations

from pathlib import Path
import re
import subprocess
from typing import Dict, List

from .batch import Step, check_prefix, render
from .common import (KITS, ROOT, BuildError, digest_json, new_unique_dir, read_json, rel, say, sha256,
                     utc_iso, utc_stamp, write_json)
from .contracts import FAILURE, compact_manifest, lua_value, suite_manifest, validate_suite
from .packaging import Member, build_container, write_sums

LICENSE = ROOT / "LICENSE.txt"


# -- inputs ------------------------------------------------------------------
def executables(args, tc, needed: List[str]) -> dict:
    """Map lua/luac/luasmall/iigshost -> bytes, from BUILD= or RELEASE=."""
    explicit = dict(item.split("=", 1) for item in (getattr(args, "exe", None) or []) if "=" in item)
    if sum(map(bool, (args.build, args.release, explicit))) != 1:
        raise BuildError("select exactly one input: BUILD=<identified build>, RELEASE=<release dir>, "
                         "or EXES=\"lua=<path> luac=<path> ...\" (existing files, never rebuilt)")
    out = {}
    if explicit:
        missing = [n for n in needed if n not in explicit]
        if missing:
            raise BuildError(f"EXES must name {', '.join(needed)} for this kit (missing {', '.join(missing)})")
        for name in needed:
            path = Path(explicit[name]).expanduser()
            if not path.is_file():
                raise BuildError(f"no executable at {path}")
            out[name] = path.read_bytes()
        return {"source": {"kind": "explicit executables", "build_id": None,
                           "files": {n: {"path": rel(Path(explicit[n]).resolve()), "sha256": sha256(out[n])}
                                     for n in needed}}, "bytes": out}
    if args.build:
        from .identified import resolve
        from .runtests import EXECUTABLES
        build = resolve(args.build)
        for name in needed:
            out[name] = build.path(EXECUTABLES[name]).read_bytes()
        return {"source": {"kind": "identified build", "build_id": build.id, "build_dir": build.dir.name,
                           "build_manifest_sha256": build.manifest_sha256}, "bytes": out}
    release = args.release.resolve()
    manifest = read_json(release / "RELEASE-MANIFEST.json")
    if not manifest:
        raise BuildError(f"{release} has no RELEASE-MANIFEST.json")
    names = {"lua": "LUA", "luac": "LUAC", "iigshost": "IIGSHOST", "luasmall": "LUASMALL"}
    for name in needed:
        member = names[name]
        archive = release / (member + ".SHK")
        if not archive.is_file():
            raise BuildError(f"release {manifest.get('tag')} has no {archive.name} (needed for {name})")
        data = subprocess.run([tc.nulib2, "-p", str(archive), member], capture_output=True).stdout
        if sha256(data) != manifest["executables_sha256"].get(member):
            raise BuildError(f"release hash mismatch for {member}; refusing to package")
        out[name] = data
    return {"source": {"kind": "published release", "tag": manifest.get("tag"),
                       "build_id": manifest.get("build_id")}, "bytes": out}


# -- kit definitions ---------------------------------------------------------
def suite_kit(args, tc, exe) -> dict:
    data = suite_manifest()
    group = args.group
    if group not in data["groups"]:
        raise BuildError(f"unknown suite group {group!r}: {', '.join(data['groups'])}")
    files = {"TEST.LUA": (ROOT / "tests/suite.lua").read_bytes(),
             "SUITECFG.LUA": ("return " + lua_value(data) + "\n").encode()}
    for name in [*data["tests"], "tracegc"]:
        files[name.upper() + ".LUA"] = (ROOT / "tests" / (name + ".lua")).read_bytes()
    steps = [Step("suite", "luatest", ["-E", "-v", "test.lua", group], suite_group=group)]
    preflight = args.preflight or "runtime"
    return {"volume": "LUASUITE", "title": f"IIgs regression suite group {group}. Existing executable, no rebuild.",
            "exes": {"LUATEST": exe["lua"]}, "text": files, "binary": {}, "steps": steps, "groups": data["groups"],
            "preflight_steps": [] if preflight == "none" else
            [Step("suite", "luatest", ["-E", "-v", "test.lua", preflight], suite_group=preflight)],
            "expect": f"SUITE COMPLETE group={group} passed={len(data['groups'][group])} failed=0 with_skips=N",
            "readme": [f"IIgs regression suite {data['version']}: group {group} "
                       f"({len(data['groups'][group])} tests) in one Lua state.",
                       "Other groups: 20:luatest -E -v test.lua smoke|acceptance|runtime|io|stress|full",
                       "tableovf previously took about 18 minutes and is silent until it completes.",
                       "Require SUITE COMPLETE and then the shell prompt. Stops on the first failure."]}


def small_kit(args, tc, exe, work: Path) -> dict:
    """Parser-free runtime: every Lua file is bytecode compiled by the same build's luac."""
    plan, data = compact_manifest(), suite_manifest()
    tests = {**data["tests"], **plan["tests"]}
    groups = {"compact": plan["groups"]["debug"], "stripped": plan["groups"]["stripped"]}
    config = {"version": data["version"], "groups": groups, "suffix": {"stripped": ".lus"},
              "tests": {name: tests[name] for name in groups["compact"]}}
    stage = work / "compile"
    stage.mkdir()
    (stage / "luac").write_bytes(exe["luac"])
    sources = {"test": (ROOT / "tests/suite.lua").read_bytes(),
               "suitecfg": ("return " + lua_value(config) + "\n").encode()}
    for name in groups["compact"] + plan["helpers"]:
        sources[name] = (ROOT / "tests" / (name + ".lua")).read_bytes()
    binary = {}
    for name, text in sources.items():
        (stage / (name + ".lua")).write_bytes(text)
        forms = [(False, ".LUA")]
        if name in groups["stripped"] or name in plan["helpers"]:
            forms.append((True, ".LUS"))
        for strip, suffix in forms:
            out = name + suffix.lower() + ".out"
            argv = [tc.iix, str(stage / "luac")] + (["-s"] if strip else []) + ["-o", out, name + ".lua"]
            result = subprocess.run(argv, cwd=stage, env=tc.env(), capture_output=True, stdin=subprocess.DEVNULL)
            if result.returncode or not (stage / out).is_file():
                raise BuildError(f"luac could not compile {name}.lua for the compact kit")
            binary[name.upper() + suffix] = (stage / out).read_bytes()
    steps = [
        Step("version", "luatest", ["-E", "-v"], marker=r"Lua \(IIgs\)"),
        Step("reject-source", "luatest", ["-E", "source.lua"], capture=("source.log", "srcstatus"),
             echo="COMPACT source rejection. An error message goes to source.log."),
        Step("verify-rejection", "luatest", ["-E", "nosource.lua", "cli", "{srcstatus}"],
             marker=r"^NOSOURCE 1 CLI REJECTED status=\d+$"),
        Step("debug", "luatest", ["-E", "-v", "test.lua", "compact"], suite_group="compact"),
        Step("stripped", "luatest", ["-E", "-v", "test.lua", "stripped"], suite_group="stripped"),
    ]
    return {"volume": "LUACOMPACT", "title": "Compact Lua bytecode acceptance. Parser-free runtime, no rebuild.",
            "exes": {"LUATEST": exe["luasmall"]}, "binary": binary, "groups": groups,
            "text": {"SOURCE.LUA": b'print("SOURCE RAN - this must not appear")\n'},
            "steps": steps, "preflight_steps": steps,
            "expect": f"SUITE COMPLETE group=stripped passed={len(groups['stripped'])} failed=0 with_skips=N",
            "readme": ["Compact (parser-free) Lua acceptance. All .LUA/.LUS files except SOURCE.LUA",
                       "are bytecode compiled by the same build's luac. SOURCE.LUA is text and",
                       "must be rejected. Tests needing the parser are listed in tests/compact.json.",
                       f"Two groups run: compact ({len(groups['compact'])} debug chunks) and "
                       f"stripped ({len(groups['stripped'])} chunks).",
                       "tableovf previously took about 18 minutes and is silent until it completes.",
                       "Require both SUITE COMPLETE lines and then the shell prompt."]}


LUAC_STEPS = [
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


def luac_steps() -> List[Step]:
    steps = []
    for name, exe, argv, errfile in LUAC_STEPS:
        marker = None
        if exe == "lua":
            marker = ("^LUACPROBE 1 PASSED checks=6 - expect shell prompt next$" if name == "finish"
                      else "^LUACPROBE 1 PHASE PASSED " + name + "$")
        steps.append(Step(name, "luatest" if exe == "lua" else "luactest", argv,
                          capture=(errfile, "lcstatus") if errfile else None, marker=marker,
                          echo="LUACPROBE step " + name))
    return steps


def luac_kit(args, tc, exe) -> dict:
    steps = luac_steps()
    return {"volume": "LUACTEST", "title": LUAC_TITLE,
            "exes": {"LUATEST": exe["lua"], "LUACTEST": exe["luac"]}, "binary": {},
            "text": {"TEST.LUA": (ROOT / "tests/luacprobe.lua").read_bytes()},
            "steps": steps, "preflight_steps": steps, "groups": {},
            "expect": "LUACPROBE 1 PASSED checks=6 - expect shell prompt next",
            "readme": ["LUACPROBE 1: standalone compiler checks, debug and stripped bytecode,",
                       "two intentional compiler errors, and valid compilation afterward.",
                       "It creates and removes files named lc.* listed in TEST.LUA."]}


def host_steps() -> List[Step]:
    return [
        Step("prepare", "luatest", ["-E", "-v", "test.lua", "prepare"], marker=r"^HOSTCHECK 1 PREPARED$"),
        Step("host", "iigshost", [">host.out"], capture=("host.err", "hoststatus"),
             echo="HOSTCHECK starting native host. This phase runs quietly."),
        Step("verify", "luatest", ["-E", "test.lua", "verify", "{hoststatus}"],
             marker=r"^HOSTCHECK 1 HOST VERIFIED yields=\d+$"),
        Step("finish", "luatest", ["-E", "test.lua", "finish"],
             marker=r"^HOSTCHECK 1 PASSED - expect shell prompt next$"),
    ]


def host_kit(args, tc, exe) -> dict:
    steps = host_steps()
    return {"volume": "HOSTCHECK", "title": HOST_TITLE,
            "exes": {"LUATEST": exe["lua"], "IIGSHOST": exe["iigshost"]}, "binary": {},
            "text": {"TEST.LUA": (ROOT / "tests/hostcheck.lua").read_bytes(),
                     "HWSMOKE.LUA": (ROOT / "tests/hwsmoke.lua").read_bytes()},
            "steps": steps, "preflight_steps": steps, "groups": {},
            "expect": "HOSTCHECK 1 PASSED - expect shell prompt next",
            "readme": ["HOSTCHECK 1: native C embedding and hook yields. The host is quiet until it",
                       "returns. host.out/host.err/host.state are replaced on each run and removed",
                       "after success."]}


NEEDS = {"suite": ["lua"], "small": ["luasmall", "luac"], "luac": ["lua", "luac"], "host": ["lua", "iigshost"]}


# -- preflight -----------------------------------------------------------------
def preflight(tc, stage: Path, steps: List[Step], groups: Dict[str, list], logs: Path) -> list:
    results, variables = [], {}
    with (logs / "preflight.log").open("wb") as log:
        for step in steps:
            argv = [variables.get(a.strip("{}"), a) if a.startswith("{") else a for a in step.args]
            redirect_out = [a for a in argv if a.startswith(">")]
            argv = [a for a in argv if not a.startswith(">")]
            say(f"  preflight {step.name}")
            try:
                result = subprocess.run([tc.iix, "--memcheck", str(stage / step.exe), *argv], cwd=stage,
                                        env=tc.env(), stdin=subprocess.DEVNULL, capture_output=True,
                                        timeout=3600)
            except subprocess.TimeoutExpired as exc:
                raise BuildError(f"preflight {step.name}: no result within the 3600s local limit "
                                 "(not a hardware limit)") from exc
            text = (result.stdout + result.stderr).decode(errors="replace")
            log.write(f"STEP {step.name} exit={result.returncode}\n".encode() + result.stdout + result.stderr)
            log.flush()
            if step.capture:
                errfile, var = step.capture
                # As in the ORCA shell: '>&file' receives error output only;
                # standard output goes to '>file' when given.
                (stage / errfile).write_bytes(result.stderr)
                for target in redirect_out:
                    (stage / target[1:]).write_bytes(result.stdout)
                variables[var] = str(result.returncode)
                if re.search(r"MemCheck:|\bBRK\b", text):
                    raise BuildError(f"preflight {step.name}: memory corruption")
                results.append({"step": step.name, "exit_code": result.returncode, "result": "status captured"})
                continue
            if result.returncode or FAILURE.search(text):
                raise BuildError(f"preflight {step.name} failed (exit {result.returncode}); see {rel(logs)}")
            if step.marker and not re.search(step.marker, text, re.M):
                raise BuildError(f"preflight {step.name}: missing completion marker")
            entry = {"step": step.name, "exit_code": 0, "result": "passed"}
            if step.suite_group:
                entry.update(validate_suite(text, step.suite_group, groups))
            results.append(entry)
    return results


def hardware_suite(args) -> int:
    from .toolchain import Toolchain
    tc = Toolchain.discover(args.sdk)
    tc.require_compiler()
    tc.require_packaging()
    prefix = check_prefix("" if args.prefix == "none" else args.prefix)
    inputs = executables(args, tc, NEEDS[args.kit])
    label = inputs["source"].get("build_id") or inputs["source"].get("tag") or "explicit"
    work = new_unique_dir(KITS, f"{utc_stamp()}-{args.kit}-{label}")
    say(f"Preparing {args.kit} kit from {inputs['source']['kind']} {label} in {rel(work)}")
    exe = inputs["bytes"]
    spec = (small_kit(args, tc, exe, work) if args.kit == "small" else
            {"suite": suite_kit, "luac": luac_kit, "host": host_kit}[args.kit](args, tc, exe))
    batch = render(spec["title"], spec["steps"], prefix)
    readme = "\n".join([f"{args.kit.upper()} hardware kit. Extract into a dedicated writable test directory.",
                        f"Run: {prefix}test", *spec["readme"],
                        f"Expected final result: {spec['expect']}, then the shell prompt.",
                        "TEST is an ORCA EXEC file (SRC $B0, aux $0006). Executables are EXE $B5/$0000.",
                        f"Input: {inputs['source']['kind']} {label}. No executable was rebuilt.",
                        *[f"{n} SHA256 {sha256(d)}" for n, d in spec["exes"].items()]]) + "\n"
    members = [Member(name, data, "EXE") for name, data in spec["exes"].items()]
    members += [Member("TEST", batch.encode(), "EXEC")]
    members += [Member(name, data, "TXT") for name, data in spec["text"].items()]
    members += [Member(name, data, "BIN") for name, data in sorted(spec["binary"].items())]
    members += [Member("README.TXT", readme.encode(), "TXT"), Member("LICENSE.TXT", LICENSE.read_bytes(), "TXT")]
    stage, logs = work / "run", work / "logs"
    stage.mkdir()
    logs.mkdir()
    for member in members:
        (stage / member.name.lower()).write_bytes(member.native if member.kind == "EXE" else member.data)
    results = preflight(tc, stage, spec["preflight_steps"], spec["groups"], logs) if spec["preflight_steps"] else []
    package = work / "package"
    container = build_container(tc, package, "TEST", spec["volume"], members)
    record = {
        "schema": "lua-iigs-kit/1", "kit": args.kit, "utc": utc_iso(), "input": inputs["source"],
        "shell_prefix": prefix, "run_command": f"{prefix}test",
        "executables_sha256": {n: sha256(d) for n, d in spec["exes"].items()},
        "kit_identity": digest_json([m.record() for m in members])[:12],
        "batch": batch.splitlines(),
        "preflight": {"environment": "GoldenGate with --memcheck, commands launched separately; "
                                     "not ORCA batch execution, not hardware",
                      "steps": results} if results else "skipped",
        "container": container,
        "hardware_result": "pending: record the observed banner, final lines, and shell return separately",
    }
    write_json(package / "KIT-MANIFEST.json", record)
    write_sums(package, ["TEST.po", "TEST.SHK", "KIT-MANIFEST.json"])
    say(f"Verified kit: {rel(package / 'TEST.SHK')}")
    say(f"On the IIgs, in a dedicated test directory:\n  yankit xvf <transfer path>/test.shk\n  {prefix}test")
    return 0


LUAC_TITLE = "Standalone LUAC checks. Run in a dedicated test directory."
HOST_TITLE = "Native C host and hook test. No interpreter rebuild."


def luac_batch(prefix: str = "20:") -> str:
    return render(LUAC_TITLE, luac_steps(), prefix)


def host_batch(prefix: str = "20:") -> str:
    return render(HOST_TITLE, host_steps(), prefix)
