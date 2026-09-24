# Tests and coverage

Run commands in this guide from the repository root. These automation
commands execute the IIgs binary under GoldenGate, not natively on the Mac
and not on real hardware. Build `build/lua` first and select the SDK as
explained in [building](../docs/BUILDING.md).

## Commands

```sh
make -C tests tests LUA="$PWD/build/lua"
make -C tests suite LUA="$PWD/build/lua"
python3 tools/run-tests.py --lua "$PWD/build/lua" coroutine hwdiag2
python3 -m unittest discover -s tests -p 'test_kit_checks.py'
python3 tools/generate-cobeacon.py --check
```

The first command runs sixteen targeted scripts; `suite` runs the thirty
entries in the broader `passing` group followed by the known `files` failure.
These sets overlap but are not interchangeable: the broader group does not
include every targeted regression. Run both when appropriate to a runtime
change. `tests/all.lua` is not the supported IIgs driver: its exact version
check expects `Lua 5.4`, whereas this port reports `Lua (IIgs) 5.4`.

The runner invokes `iix --memcheck` with `-E` and closed stdin. It copies
tests into a fresh `build/test-runs/<unique directory>/tests/`, creates the
required `libs/P1` scratch directory, and saves output logs beside it.
`LUA` overrides the executable; `TIMEOUT=600` overrides the Makefile's
300-second per-script local timeout. Direct runner use supports `--timeout`.
These limits apply to GoldenGate, not to physical IIgs run times.

A targeted pass requires zero process exit, its completion marker, and no
recognized corruption or allocator-degradation reports. Trace validation in
the hardware-kit builder additionally requires state closure and successful
MM activation for `mmalloc`. The general runner does not enable the builder's
trace-specific contracts. Non-targeted scripts in the broader group get
exit/memory checks only; "completed" does not mean all assertions ran.

`make -C tests fails` expects `files.lua` to return a nonzero status without
a recognized corruption report. An unexpected pass makes that target fail
for review. The expected-failure check does not match the exact historical
error, so inspect its log before concluding the same failure recurred.

## Targeted scripts

The authoritative list and completion rules are in
[tools/test_support.py](../tools/test_support.py).

| Script | Purpose / final marker |
| --- | --- |
| `hwsmoke` | Small arithmetic, source/bytecode, coroutine, and GC checks; `SMOKE DONE` |
| `sieve` | Nested coroutine chain must catch C-stack overflow |
| `coroutine` | IIgs-scaled coroutine regression; `OK`, with T sections skipped |
| `cobeacon` | Same coroutine test with flushed section markers; `BEACON DONE` |
| `cstack` | Deliberate overflow/recovery paths; `OK`; requires `tracegc.lua` |
| `pm` | Pattern matching, including recursive substitutions; `OK` |
| `hwdiag2` | Large allocations, compiler constants, and stack recovery; `ALL DIAGNOSTICS PASSED` |
| `hwtest` | Known-answer regression checks; currently 19 pass, 0 fail, 1 skip |
| `hookyield` | Lua call/line/count hook checks; does not yield from a C hook |
| `mmalloc` | Full payload checks across 16 KB, 32 KB, and 64 KB boundaries; `MMALLOC PASSED` |
| `tableovf` | Table growth rejected cleanly; entries preserved before/after GC; `TABLEOVF PASSED` |
| `errors`, `events`, `math` | Adapted upstream regressions; `OK` |
| `numconv` | Integer/float boundaries, table keys, rounding, and invalid conversions; `NUMCONV PASSED checks=90` |
| `verybig` | RK section; explicit skip of programs beyond 16-bit limits |

`tableovf.lua` takes about **18 minutes on the recorded accelerated IIgs**
and prints only at completion. It retained 49,152 entries. Do not use the
local timeout as a hardware deadline. See [hardware testing](../HARDWARE_TESTING.md)
for commands and clean-exit requirements.

`math.lua` explicitly skips the `0^0` comparison on the IIgs: the hardware
probe returned NaN there, unlike GoldenGate. Its random-number assertions
use 53 generated bits even when hardware reports a 64-bit float significand.
With the minimum-integer conversion fix, the revised script passes locally
and on the recorded real IIgs, alongside all 90 `numconv` checks and a clean
shell return. See the [hardware record](../docs/validation/HARDWARE_RESULTS.md).

## C and build checks

`python3 tools/hardware-kit.py --plain-name luanext` runs the targeted set in
both plain and trace variants, then additional checks as part of packaging:

- `iigshost.c`: refuse state creation before stack initialization; recover
  from deep Lua-stack recursion; reject oversized array/vector requests;
  check retained table data; yield/resume from a native C hook (100 yields
  observed). This is separate from the upstream T harness.
- `allocfail.c`: compile the actual allocator with fault-injection wrappers;
  check bounded fallback, old-data retention, and one expected degradation
  warning. This deliberately generated warning is not an ordinary runtime pass.
- Bridge demo and `cstack` through the embedding host.
- `mmtest`: raw Memory Manager probe, requiring `MMTEST DONE errs=0`.
- `luac`: source/bytecode smoke round trip and clean excessive-nesting error.
- `memfree`: compilation only; required query tools are unavailable locally.

The kit builds these hosts itself; `make -C tests tests` does not build or
run them. Root `make mmtest memfree` builds the standalone probes. The kit
is the maintained end-to-end route for C-host validation.

## Coverage boundaries and diagnostics

The T harness is absent: `api.lua` and `code.lua` return after skip notices,
and other tests omit T-dependent sections. `main.lua` currently sets `_iigs`
true and immediately returns, so its successful exit is not interpreter-CLI
coverage. Several inherited tests hard-code IIgs adaptations; a host-native
or unmodified upstream-suite pass is not claimed. `tracegc.lua` is a helper.

`hwtest.lua` reports its unsupported Lua-hook yield case as a skip and prints
`HWTEST PASSED WITH SKIPS`. Earlier baseline output counted that unsupported
case as a pass; [the evidence record](../docs/validation/HARDWARE_RESULTS.md)
preserves the correction. Avoid quoting a whole-suite percentage.

`files.lua` is still expected-failing in the stock GoldenGate suite because
of its repeated-EOF abort and text translation differences. Its duplicate
read, undefined variable, and corrupted fixture bytes have been repaired.
The real IIgs passes all 38 focused I/O checks and FILECHECK 4: the adapted
file test with portable date/time checks. That run excludes Unix processes,
nonportable dates, large files, and cross-handle buffer visibility. The
hardware refuses a reader while a writer is open; the IIgs buffer tests
check final data after close/reopen instead. See the
[I/O investigation](../docs/validation/IO_INVESTIGATION.md).
`ioprobe.lua` is a diagnostic outside the default pass set. It prints byte
comparisons and failure counts, and deliberately exercises repeated EOF
reads that terminate the installed GoldenGate. Use hardware or the documented
isolated emulator for the complete probe; a DONE line is not a pass by itself.
`bufprobe.lua` records sharing behavior before/after writes, flush, and close.
Its zero error count verifies final data, not cross-handle buffer visibility;
record the per-case observations as well.

`cobeacon.lua` is generated from `coroutine.lua`. Regenerate after changing
the source test with `python3 tools/generate-cobeacon.py`; `--check` verifies
synchronization. Historical B numbering is retained, and some markers label
comments rather than operations. `stackcal.lua`, `hwdiag.lua`, and
`cobisect.lua` are human-read localization tools outside the automated pass
set. Temporary table/host beacon packages from the hardware session are not
required for distribution or routine regression testing.
