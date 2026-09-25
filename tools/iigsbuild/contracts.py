"""Completion contracts and manifests shared by every test runner.

A pass needs zero exit status, the script's exact completion marker, and
no recognized corruption, failure, or allocator-degradation output.
Intentional skips stay visible in results.
"""
from __future__ import annotations

import json
import re

from .common import ROOT, BuildError

TESTS = ("hwsmoke", "sieve", "coroutine", "cobeacon", "cstack", "pm",
         "hwdiag2", "hwtest", "hookyield", "mmalloc", "tableovf",
         "errors", "events", "math", "verybig", "numconv")
FAILURE = re.compile(r"MemCheck:|\bBRK\b|\bFAIL(?:ED)?\b|SOME TESTS FAILED|"
                     r"\[mm\] selftest state=-1|mm=degraded")
COMPLETION = {
    "numconv": r"^NUMCONV PASSED checks=90$",
    "hwsmoke": r"^SMOKE DONE - expect shell prompt next$",
    "sieve": r"^chain=40.*caught: .*C stack overflow$",
    "cobeacon": r"^BEACON DONE(?: \(C API harness skipped\))?$",
    "hwdiag2": r"^ALL DIAGNOSTICS PASSED$",
    "hwtest": r"^(?:ALL TESTS PASSED|HWTEST PASSED WITH SKIPS)$",
    "mmalloc": r"^MMALLOC PASSED$",
    "tableovf": r"^TABLEOVF PASSED entries=\d+$",
    "verybig": r"^\(>64k programs: skipped on 16-bit int\)$",
    "nosource": r"^NOSOURCE 1 PASSED parser=(?:yes|no) checks=\d+$",
    "bufprobe": r"^BUFPROBE 3 DONE cases=6 errors=0$",
    "largefile": r"^LARGEFILE 1 PASSED bytes=262163 - expect shell prompt next$",
    "bigio": r"^BIGIO 1 PASSED cases=7 - expect shell prompt next$",
    "filelife": r"^FILELIFE 1 PASSED cases=120 - expect shell prompt next$",
}
SKIP = re.compile(r"\bskip(?:ped|ping)?\b", re.I)


def validate(test, output, traced=False, parser=None):
    """Raise ValueError on failure/incomplete output; retain skip evidence."""
    if FAILURE.search(output):
        raise ValueError("diagnostic failure or degraded allocator")
    if not re.search(COMPLETION.get(test, r"^OK$"), output, re.M):
        raise ValueError("missing completion marker")
    if test == "nosource" and parser is not None:
        want = "yes" if parser else "no"
        if f"parser={want} " not in output:
            raise ValueError(f"runtime reported the wrong parser mode (expected parser={want})")
    if traced and "[M7] state closed" not in output:
        raise ValueError("missing shutdown marker")
    # Only this workload is required to initialize the MM path. Small
    # workloads (e.g. sieve) legitimately leave it untested.
    if traced and test == "mmalloc" and "[mm] selftest state=1" not in output:
        raise ValueError("Memory Manager not armed by allocation test")
    skips = [line.strip() for line in output.splitlines() if SKIP.search(line)]
    return {"status": "passed with skips" if skips else "passed",
            "environment": "GoldenGate, not hardware", "skips": skips}


def suite_manifest() -> dict:
    data = json.loads((ROOT / "tests/hardware/suite.json").read_text())
    names = data["groups"]["full"]
    if len(names) != len(set(names)) or set(names) != set(data["tests"]):
        raise BuildError("suite.json: full group must contain each test exactly once")
    for group in data["groups"].values():
        if len(group) != len(set(group)) or not set(group) <= set(names):
            raise BuildError("suite.json: invalid suite group")
    for name in names:
        if not re.fullmatch(r"[a-z][a-z0-9]*", name) or len(name + ".lua") > 15:
            raise BuildError("suite.json: invalid ProDOS test filename " + name)
    return data


def compact_manifest() -> dict:
    """Bytecode acceptance plan for the parser-free runtime (tests/hardware/compact.json)."""
    data = json.loads((ROOT / "tests/hardware/compact.json").read_text())
    suite = suite_manifest()
    known = set(suite["tests"]) | set(data["tests"])
    for form in ("debug", "stripped"):
        group = data["groups"][form]
        if len(group) != len(set(group)) or not set(group) <= known:
            raise BuildError(f"compact.json: invalid {form} group")
    if set(data["groups"]["stripped"]) - set(data["groups"]["debug"]):
        raise BuildError("compact.json: stripped group must be a subset of debug")
    overlap = set(data["groups"]["debug"]) & set(data["requires_parser"])
    if overlap:
        raise BuildError(f"compact.json: tests both accepted and parser-dependent: {sorted(overlap)}")
    return data


def lua_value(value) -> str:
    """Serialize ASCII strings, integers, arrays and string-keyed tables to Lua."""
    if isinstance(value, bool):
        return "true" if value else "false"
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


def validate_suite(text, group, groups):
    """A marker before an error, missing tests, or a truncated log cannot pass."""
    if FAILURE.search(text):
        raise ValueError("failure or corruption in output")
    rows = re.findall(r"^SUITE PASS ([a-z0-9]+)( WITH SKIPS)?$", text, re.M)
    if [name for name, _ in rows] != groups[group]:
        raise ValueError("missing, duplicate or out-of-order test completions")
    partial = sum(bool(skip) for _, skip in rows)
    expected = f"SUITE COMPLETE group={group} passed={len(rows)} failed=0 with_skips={partial}"
    if text.splitlines().count(expected) != 1:
        raise ValueError("missing or inconsistent suite summary")
    return {"status": "passed with skips" if partial else "passed",
            "tests": [{"name": name, "status": "passed with skips" if skip else "passed"}
                      for name, skip in rows],
            "skip_evidence": [s for s in text.splitlines() if SKIP.search(s)]}
