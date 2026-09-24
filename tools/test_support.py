"""Shared, explicit completion contracts for the IIgs targeted checks."""
import re

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
}


def validate(test, output, traced=False):
    """Raise on failure/incomplete output; retain intentional skip evidence."""
    if FAILURE.search(output):
        raise ValueError("diagnostic failure or degraded allocator")
    if not re.search(COMPLETION.get(test, r"^OK$"), output, re.M):
        raise ValueError("missing completion marker")
    if traced and "[M7] state closed" not in output:
        raise ValueError("missing shutdown marker")
    # Only this workload is required to initialize the MM path. Small
    # workloads (e.g. sieve) legitimately leave it untested.
    if traced and test == "mmalloc" and "[mm] selftest state=1" not in output:
        raise ValueError("Memory Manager not armed by allocation test")
    skips = [line.strip() for line in output.splitlines()
             if re.search(r"\bskip(?:ped|ping)?\b", line, re.I)]
    return {"status": "passed with skips" if skips else "passed",
            "environment": "GoldenGate, not hardware", "skips": skips}
