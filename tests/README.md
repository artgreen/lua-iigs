# Tests and coverage

Run the commands in this guide from the repository root. They execute the
IIgs binaries under GoldenGate, not natively on the Mac and not on real
hardware. Select the SDK as explained in [building](../docs/BUILDING.md).

## Commands

```sh
make test
make test BUILD=<build id>
make test CHECKS="targeted luac"
make test CONFIG=luatrace
make test CONFIG=lua-small
make suite GROUP=runtime
make test-build
```

`make test` brings the development builds up to date, then runs the
default checks: `unit targeted luac compact hosts`. With `BUILD=` it tests
an identified build instead and rebuilds nothing. `CONFIG=luatrace` runs
the targeted scripts with the trace contracts, and `CONFIG=lua-small` runs
the LUAC and compact checks. `make suite` runs the
[repeatable suite](SUITE.md) in one Lua state; `make test-build` is the
build-system integration test. Each run writes `report.json`:

- in `build/test-reports/<id>-<utc>/` for identified builds (kept);
- in `build/test-runs/` for dev builds (disposable).

The report records executable hashes, the test identity (a hash of the
scripts and contracts), the emulator identity, each check's status, and
intentional skips.

| Check group | Contents |
| --- | --- |
| `unit` | Python unit tests for contracts, packaging, batches, and the build tooling |
| `targeted` | the 16 scripts below, as independent processes, on full Lua |
| `luac` | debug and stripped bytecode (hwsmoke on full, numconv and nosource on both runtimes); clean rejection of a syntax error and of excessive nesting; valid compile afterward |
| `compact` | [bytecode acceptance on parser-free Lua](COMPACT.md), plus rejection of source from a script and from stdin |
| `hosts` | iigshost, allocfail, bridge demo and bridge cstack, mmtest; memfree is built but needs real hardware |
| `trace` | the targeted scripts on `luatrace`, requiring state closure and MM activation for `mmalloc` |

The older independent-process runner still works for ad hoc and broader
upstream runs:

```sh
make -C tests tests
make -C tests suite
python3 tools/run-tests.py --lua build/dev/lua/out/lua coroutine hwdiag2
python3 tools/generate-cobeacon.py --check
```

`make -C tests tests` runs the sixteen targeted scripts. `make -C tests
suite` runs the thirty scripts in the broader `passing` group, followed by
the known `files` failure. The two sets overlap but are not
interchangeable. `tests/all.lua` is not the supported IIgs driver: its
exact version check expects `Lua 5.4`, whereas this port reports
`Lua (IIgs) 5.4`.

Every runner uses `iix --memcheck` with `-E` and closed stdin. It copies the
tests into a fresh scratch directory, creates the required `libs/P1`
directory, and saves the logs. Local timeouts apply to GoldenGate, not to
physical IIgs run times.

A targeted pass requires three things: a zero process exit, the script's
completion marker, and no recognized corruption or allocator-degradation
report. Trace checks additionally require state closure, and successful MM
activation for `mmalloc`. Non-targeted scripts in the broader group get
exit and memory checks only, so "completed" does not mean all assertions
ran.

`make -C tests fails` expects `files.lua` to return a nonzero status
without a recognized corruption report. An unexpected pass makes that
target fail for review. The check does not match the exact historical
error, so inspect its log before concluding that the same failure recurred.

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

The [native C-host batch](HOST_TESTING.md) runs the embedding host and the
native C-hook yield/resume path. It verifies the host's output and status,
then runs a fresh Lua smoke test. The [LUAC batch](LUAC_TESTING.md) covers
the standalone compiler on hardware. Both come from
`make hardware-suite KIT=host` and `KIT=luac`, and use the `TEST.SHK` /
`20:test` workflow.

The local `hosts` group of `make test` runs:

- `iigshost.c`: refuses state creation before stack initialization;
  recovers from deep Lua-stack recursion; rejects oversized array/vector
  requests; checks retained table data; yields and resumes from a native
  C hook (100 yields observed). This is separate from the upstream T
  harness.
- `allocfail.c`: compiles the actual allocator with fault-injection
  wrappers, and checks bounded fallback, old-data retention, and exactly
  one expected degradation warning. That deliberate warning is not an
  ordinary runtime pass.
- The bridge demo, and `cstack` through the embedding host.
- `mmtest`: the raw Memory Manager probe, requiring `MMTEST DONE errs=0`.
- `memfree`: built only; the query tools it needs are unavailable locally.

The build system has its own tests: `make test-build` (integration) and
`tests/test_build_tools.py` (unit). See
[building](../docs/BUILDING.md#tests).

## Coverage boundaries and diagnostics

The T harness is absent: `api.lua` and `code.lua` return after skip notices,
and other tests omit T-dependent sections. `main.lua` currently sets `_iigs`
true and immediately returns, so its successful exit is not interpreter-CLI
coverage. Several inherited tests hard-code IIgs adaptations; a host-native
or unmodified upstream-suite pass is not claimed. `tracegc.lua` is a helper.

`nosource.lua` checks source rejection on the parser-free runtime, and
source loading on full Lua; see [compact testing](COMPACT.md).

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

`largefile.lua` is a separate hardware diagnostic for binary offsets through
256 KiB. It writes and rereads every byte in small chunks, checks set/cur/end
seeks, updates across boundaries, appends beyond 256 KiB, and checks truncation.
It uses one temporary file and closes writers before reopening for reading.
This covers large file offsets, not single transfers or Lua strings above
65,535 bytes. Progress markers accompany the work; require the final PASSED
marker and shell return. It is outside the default targeted regression set.

`bigio.lua` separately checks large single binary transfers at 32/64/128 KiB
boundaries. Seven sizes cover 32,767 through 131,073 bytes; each case checks
a single write, counted read, read-all, and partial read at EOF with exact
byte/length/position assertions. It uses concatenation to build payloads
without depending on string.rep's separate INT_MAX limit. Require
`BIGIO 1 PASSED cases=7` and a shell return. This diagnostic is also outside
the default targeted regression set.

`bytefile.lua` generates a source chunk with 9,000 arithmetic statements,
executes it, dumps debug and stripped bytecode larger than 64 KiB, and reloads
both from memory and disk. It checks binary constants, nested closures after
GC, rejection of wrong-mode/truncated input, and recovery with valid code.
Require `BYTEFILE 1 PASSED variants=2` and shell return. It uses two temporary
files and is a separate diagnostic, not validation of the LUAC executable
or bytecode compatibility with other platforms.

`filelife.lua` repeats five file cleanup paths for 12 rounds in each of
incremental and generational GC: normal scope exit, error unwinding,
coroutine cancellation, early io.lines exit, and an abandoned writer's
finalization. It checks closed handles where inspectable, data after reopen,
and temporary-file removal. Require `FILELIFE 1 PASSED cases=120` and shell
return. This separate diagnostic does not measure OS-wide resource counts.

`cobeacon.lua` is generated from `coroutine.lua`. Regenerate after changing
the source test with `python3 tools/generate-cobeacon.py`; `--check` verifies
synchronization. Historical B numbering is retained, and some markers label
comments rather than operations. `stackcal.lua`, `hwdiag.lua`, and
`cobisect.lua` are human-read localization tools outside the automated pass
set. Temporary table/host beacon packages from the hardware session are not
required for distribution or routine regression testing.
