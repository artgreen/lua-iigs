# Real IIgs test results

This is a chronological evidence journal. Commands, pending items, and
artifact paths inside dated entries describe that moment in the investigation;
they are not current installation instructions. Use the
[hardware guide](../../HARDWARE_TESTING.md) for new testing. Local `build/` and
NAS paths below are relative to the original project environment.

Latest acceptance build: **published v0.2.1 plain interpreter /
`IIgs e026f5b-13178cdf3c75 plain`**, renamed LUATEST without changing bytes.
This phase is complete: two photographed full-suite runs passed (23 tests,
eight with intentional skips), including one user-confirmed cold start.
Standalone LUAC passed six checks; the native host passed with 100 yields
and post-host smoke. All returned to the shell. See the
[phase closeout](2026-09-24/PHASE-CLOSEOUT.md) and September 24 entries for
provenance, scope, and explicit skips. The earlier candidate
`IIgs aa385d7-13178cdf3c75 plain` passed math and FILECHECK 4 on September 23.

Earlier repeatability build: **LUAREVIEW / `IIgs 9add073-776024bcfb02 plain`**.
The user reports completion of the requested five warm coroutine/hwdiag2
pairs and one post-power-cycle pair, plus additional mixed-script testing
in one warm session. See the September 22 entries for evidence and scope.

Preserved prior baseline: **LUAPATH / `IIgs b69d628-9766f6d19a8d plain`**.
Its warm-run and cold-boot checks completed with 14 warm launches
and two post-power-cycle launches passed. Earlier "pending" entries below
describe the state when recorded; later entries close those checks.
Coverage is limited to the documented workloads and machine configuration.
The baseline runtime source is commit `9add073`; its banner predates that
commit. See [preserved provenance](2026-09-21/README.md).

Review correction: the baseline hwtest's "20 passed" includes one unsupported
Lua-hook yield case incorrectly counted as a pass. That path was untested;
the recorded hardware runs and clean shell returns are still valid evidence.
The merged build has separate skip reporting and a C-hook test.
Its diagnostic companions have hardware passes, and the user subsequently
confirmed all outstanding runs, including the original silent tests, passed
and returned to the shell. Original tableovf.lua took about 18 minutes and
reported 49,152 entries. The requested candidate repeatability sequence is
also reported complete; see the final September 22 entry below.

## 2026-09-21: traced coroutine diagnostic passes

Machine reported by user: ROM 03, 8 MB RAM. The user later reported GS/OS
"6.04" tentatively and confirmed hardware acceleration is enabled. The
exact OS version, accelerator model/speed, shell version, and storage
device remain unconfirmed. Keep acceleration enabled for the next tests
to preserve the configuration used for the successful runs.

The user supplied a photograph after receiving the diagnostic kit staged
at `<NAS mount>/LUA.20260921` (kit ID `b69d628-9bf53392629b`). The photograph
does not show the version banner, so the executable ID is contextual rather
than independently confirmed by the image.

Visible results:

- cobeacon.lua reaches B27 and prints OK and BEACON DONE.
- The unavailable C API test harness is explicitly skipped.
- M5 reports script completion; M6 reports closing the state.
- An allocator free event appears, followed by M7 (state closed).
- The shell's `#` prompt returns. Visible output is legible and contains no
  error or screen corruption.

Conclusion: one successful traced coroutine diagnostic run on real hardware,
including Lua state shutdown and return to the shell. This is not yet a
repeatability result or evidence for the ordinary interpreter. The photo
does not establish the smoke test result.

Next: extract LUA.SHK into a separate directory and run the ordinary build's
hwsmoke.lua and cobeacon.lua with `-E -v`. If both pass, test the original
coroutine.lua and the remaining hardware diagnostics, then repeated launches
and cold boots as described in HARDWARE_TESTING.md.

## 2026-09-21: corruption reported during ordinary cobeacon invocation

The next user photograph shows `lua -E -v cobeacon.lua`, widespread text
corruption, and markers through B11. Earlier smoke-test output above that
command is also garbled; a monitor/register display is visible. The image
alone does not establish when those earlier screen locations were damaged.

Crucially, both visible Lua copyright banners lack the diagnostic build-ID
line. The cobeacon invocation's copyright banner is immediately followed by
B0. The shipped plain interpreter prints `IIgs b69d628-9bf53392629b plain`
between these lines when invoked with `-v`. An older executable being found
under the name `lua` is therefore a hypothesis that must be excluded before
attributing this failure to the new plain binary. Corruption of output is
another possibility. Boot history and the executable's extraction directory
have been requested.

Rechecked the NAS LUA.SHK against its local archive: hashes match. Extracted
LUA from that NAS archive and compared all bytes with the locally tested
plain interpreter: identical, with the expected build-ID string present.

B6-B11 are print calls inserted among comments before the sieve loop; they
are not six independent test operations. The last visible B11 is not enough
to assign the origin of the corruption to the sieve, especially given the
other corrupted screen regions.

Next discriminator: cold-boot and invoke the exact same verified plain
binary under a unique name, LUAPLAIN. First run only `luaplain -E -v` and
confirm the build-ID line and clean shell return before any Lua script.

## 2026-09-21: identified plain build passes smoke and coroutine beacon tests

The user confirmed that `luaplain -E -v` prints the expected identifier and
that `luaplain -E -v hwsmoke.lua` reaches SMOKE DONE. Subsequent photographs
show the smoke markers S0-S4 and SMOKE DONE, followed by the command
`luaplain -E -v cobeacon.lua` and the exact build identifier
`IIgs b69d628-9bf53392629b plain`.

The final photograph shows B27, the expected C API harness skip notice, OK,
BEACON DONE, and a returned shell prompt. The visible screen is clean.
This confirms a successful ordinary-build coroutine diagnostic run, without
allocator/lifecycle tracing, after the smoke test.

The missing identifier in the previous corrupt run, followed by success
with the byte-identical executable under its unique name, strongly supports
older-command selection as an explanation for that run. The executable
actually selected by the earlier `lua` command has not been inspected, so
this is not yet a proven root cause for every historical hardware failure.

Next: run `luaplain -E -v coroutine.lua` (the original test without beacon
prints). Then run the allocation and stack diagnostics and check repeated
launches/exits and cold-boot repeatability before declaring reliability.
The C API tests requiring the unavailable T harness remain untested.

## 2026-09-21: original coroutine test passes on the identified plain build

The next photograph shows `cd /apps/lua`, followed by
`luaplain -E -v coroutine.lua`, the expected build identifier
`IIgs b69d628-9bf53392629b plain`, normal test output, OK, and the shell
prompt. No screen corruption is visible. The unavailable C API test
harness is skipped as expected.

This establishes a successful run of the repository's original coroutine
test without the additional beacon prints or allocator/lifecycle tracing.
The test retains the repository's IIgs-specific workload limits. The
photograph starts with "Loading shell...", which does not by itself prove
a cold boot.

The reported extraction/run directory is now visible as `/apps/lua`.
Next: `luaplain -E -v hwdiag2.lua` to test large strings, growing tables,
compiler constant arrays, and stack-error recovery. Expected completion:
E99 DONE fails=0, ALL DIAGNOSTICS PASSED, and return to the shell.

## 2026-09-21: allocation/stack diagnostic reports zero failures

The user supplied a photograph in response to the hwdiag2.lua run. It shows
constant-array checks for 2,400, 2,900, 3,000, and 3,200 entries reporting
OK, stack recursion stopping cleanly at depth 7, E73 chain caught OK,
E99 DONE fails=0, and ALL DIAGNOSTICS PASSED. No corruption is visible.
The diagnostic's failure total covers its earlier string/table checks,
whose individual output is above the photographed region.

Neither the command/build banner nor a returned shell prompt is visible in
this image. Record this as diagnostic completion in the ongoing LUAPLAIN
test sequence; clean process exit still needs confirmation for this run.
After confirming shell return, the next check is hwtest.lua (known-answer
checks spanning the earlier corruption fixes).

## 2026-09-21: both hardware diagnostics return to the shell

The user confirms that both commands (`hwdiag2.lua` and `hwtest.lua`)
returned to the shell prompt. This closes the outstanding exit-confirmation
question for hwdiag2.lua: it reported zero diagnostic failures and exited.
For hwtest.lua, clean return is confirmed, but its final pass/fail summary
has not yet been supplied. That script can return normally even when its
checks report failures, so do not infer ALL TESTS PASSED from exit alone.

After confirming hwtest's summary, the remaining packaged targeted checks
are cstack.lua, sieve.lua, and pm.lua. The sieve is deliberately too deep
and should catch C stack overflow; the other two should report OK.

## 2026-09-21: hwtest, sieve, and pattern matching pass; cstack helper lookup fails

The user reports clean exits and expected pass strings for the completed
tests. Photos confirm hwtest's `20 passed, 0 failed` / ALL TESTS PASSED,
sieve's chain=40 / primes=6 followed by a caught C stack overflow and shell
return, and pm.lua's OK followed by shell return. The latter two commands
show the expected plain build ID.

cstack.lua exits with a normal Lua module-loading error at line 5:
`module 'tracegc' not found`. Its stack tests never begin. The search list
includes `./tracegc.lua` but not the bare relative name `tracegc.lua`.
Rechecked LUAPLAIN.SHK on the NAS: TRACEGC.LUA is included. Whether it was
extracted into the GS working directory is not yet known; handling of the
`./` prefix on the real system is another possible cause.

Next diagnostic command, verified to pass locally under GoldenGate:
`luaplain -E -v -e "package.path='?.lua'" cstack.lua`.
This tests bare-name module lookup without rebuilding the interpreter or
changing the stack test. If still missing, ensure TRACEGC.LUA is extracted
alongside CSTACK.LUA in `/apps/lua` and retry. Real-hardware cstack coverage
remains outstanding until it reaches OK and returns to the shell.

## 2026-09-21: cstack passes with bare relative module lookup

The user photograph shows the identified plain build running
`luaplain -E -v -e "package.path='?.lua'" cstack.lua`. Every test section
completes, followed by OK and the shell prompt. Visible recursion counts
match the local run (3793, 6, 3, 6, 7, 6, 7); no corruption is visible.
The helper is therefore available with bare-name lookup in this run.
This supports a default-module-path compatibility issue. There has been
no user report of extracting an additional helper between the two runs.

All eight targeted diagnostics now have successful real-hardware results
for the September plain build, with the path override required for cstack.
This is one-pass targeted coverage, not repeatability or full-suite proof.

Apply an IIgs-only default Lua module path of `?.lua;?/init.lua`, leaving
other platforms and explicit LUA_PATH_DEFAULT overrides unchanged. Build
and validate separately, distribute under the unique name LUAPATH, and
confirm cstack passes without -e on hardware before repeatability testing.

The update is built as `IIgs b69d628-9766f6d19a8d plain` (LUAPATH), with
source and logs under `build/hardware/20260921T195254Z-isvxzp3_`. Both new
variants passed all eight local diagnostics without path overrides, and
luac passed its bytecode-roundtrip and excessive-nesting checks. The plain
archive was checked for EXE type $B5 / aux $0000, all archived bytes were
compared with the verified image, and cstack ran successfully from files
extracted from the archive (CR text, default path) under GoldenGate.
LUAPATH.SHK and PATHFIX.TXT are staged on the NAS in LUA.20260921. This
update's real-hardware validation remains pending.

## 2026-09-21: module-path update hardware follow-up succeeds

The user photograph supplied after the requested LUAPATH checks shows the
tail of cstack.lua ending with OK and a shell prompt, followed by the command
`luapath -E -v coroutine.lua`, the identifier
`IIgs b69d628-9766f6d19a8d plain`, normal coroutine test output, OK, and the
shell prompt. No corruption is visible. The cstack command and banner are
above the photographed region; its association with the requested new-build
test without a path override follows the test sequence rather than a visible
command line. The new-build coroutine pass is directly identified.

Next reliability check: alternate coroutine.lua and hwdiag2.lua five times
each (ten separate LUAPATH launches) without rebooting. Every coroutine run
must report OK; every allocation diagnostic must report E99 DONE fails=0
and ALL DIAGNOSTICS PASSED; every process must return to the shell. Then
power off/on and run each once more with acceleration still enabled.
Record counts and any failure. These runs are pending, not yet passed.

## 2026-09-21: seven repeated test pairs pass

The user reports running the requested LUAPATH coroutine.lua / hwdiag2.lua
pair seven times without issue: 14 successful interpreter launches in the
ongoing warm-run sequence. This exceeds the planned five pairs. No further
warm runs are needed for this check.

Cold-boot repeatability remains pending: power fully off/on, retain the
normal accelerated configuration, then run each command once and confirm
its success message and clean shell return. This result establishes repeat
success for these two workloads; it does not establish full-suite coverage
or resolve the previously documented file-I/O issue.

## 2026-09-21: cold-boot checks pass; tested baseline established

In response to the requested full power-off/on and one run each of
coroutine.lua and hwdiag2.lua, the user reports "all clean". Record both
post-power-cycle tests as passed, with their expected success messages and
shell returns. Combined with the seven warm pairs, the repeatability phase
completed 16 successful interpreter launches: eight of each workload.

Keep the exact LUAPATH build `IIgs b69d628-9766f6d19a8d plain` as the tested
baseline. Its source snapshot, compiler/source hashes, local verification
logs, executable, disk image, and ShrinkIt archive are preserved under
`build/hardware/20260921T195254Z-isvxzp3_`. The archive is
`nas-transfer/LUAPATH.SHK`; it was copied and checksum-verified on the NAS
as `<NAS mount>/LUA.20260921/LUAPATH.SHK`. The NAS copy was not accessible
from the Mac at this final documentation update; the local artifacts remain.

The completed session establishes successful targeted operation, clean
shutdown, repeated launches, and cold-boot repeatability on this accelerated
ROM 03 / 8 MB machine. It does not certify all Lua workloads, other machines,
the unavailable C API harness, or resolution of the historically failing
files.lua test. Preserve this build while investigating those separately.


## 2026-09-22: review candidate prepared; hardware confirmation pending

PR-review fixes are packaged as LUAREVIEW, banner
`IIgs 9add073-776024bcfb02 plain`. This is a new executable; it does not
inherit the LUAPATH hardware result. The original binary and checksums
remain preserved. Library hosts now require explicit stack initialization.

GoldenGate checks cover both interpreter variants, the library host's
C-hook yields and size-limit errors, allocator failure injection, bridge,
and compiler. See [candidate validation](2026-09-22/README.md)
and [review disposition](../PR13-REVIEW.md) for coverage and limitations.
The historical files.lua failure remains reproducible locally.

ShrinkIt archives and images are ready locally under
`build/hardware/20260922T145111Z-5t_54b1b/`. The NAS was not mounted, so this
session did not copy the new candidate there. The next hardware sequence is
listed in HARDWARE_TESTING.md; no new hardware results are claimed here.

## 2026-09-22: progress companions pass on hardware

After the NAS was remounted, the review kit was copied to
`<NAS mount>/LUA.20260922` and every copied file was read back and verified.
The user reported runs of tableovf.lua and IIGSHOST lasting at least five
minutes, with no IIGSHOST output. Both original tests print only at completion;
neither a hang nor an eventual successful completion was established.
The user answered "yes" to a combined question about power-cycling between
runs and successful basic LUAREVIEW tests. This answer does not identify
individual test results or establish durations.

Progress companions were built from the exact review candidate inputs:
IIGSDBG adds flushed phase markers to the C host; TABPROBE adds markers to
the table test and constructs failure-message strings only on failed checks.
Both passed locally under GoldenGate. The interpreter and original tests
were not replaced. Sources, logs, manifest, and packaged artifacts are in
`build/diagnostics/20260922-progress/`; the verified NAS package is
`<NAS mount>/LUA.20260922/PROGRESS/PROGRESS.SHK` (SHA-256
`b9f38fa28cc6a2e0d360e224880ca300a3c3585017af150721cf2cc6349b5079`).

The user's next photograph shows:

- TABPROBE's final post-GC checks through 49,152 entries, followed by
  `TABPROBE PASSED entries=49152` and the next shell command.
- `iigsdbg`, with the exact entry marker
  `776024bcfb02 host-beacons-1`, progressing through H0-H11.
- Successful recovery from deep Lua-stack recursion, vector and array
  limit checks, retained-entry validation and garbage collection, followed
  by 100 native C-hook yields and state closure.
- `IIGSDBG PASSED yields=100` followed by the shell prompt, with no visible
  screen corruption.

This establishes one hardware pass and clean exit for each diagnostic
companion. The TABPROBE invocation/banner is above the photographed region;
its association with LUAREVIEW follows the requested test sequence.
Elapsed times and time spent in individual phases have not been reported.
The host uses the candidate Lua library, but its extra output changes timing
and code layout. These passes do not establish why the original silent runs
were slow, or prove that those original binaries complete on hardware.
Preserve LUAPATH as the previously repeat-tested baseline.

## 2026-09-22: table timing comparison remains inconclusive

The user reports TABPROBE completed in under seven minutes, while original
tableovf.lua had not returned after nine minutes. Record the original as
incomplete at that observation time, not a demonstrated hang. The user
raised the possibility that periodic output prevents a runtime fault.

The scripts differ in more than output: tableovf constructs an assertion
message on every successful check, while TABPROBE builds a message only on
failure. At 49,152 entries and two passes, the original performs 98,304
extra message constructions, as well as the successful assert calls. This
adds allocation/collection work; its hardware cost is not yet measured.
TABPROBE also factors verification into a function and adds progress logic.
The existing comparison cannot isolate an output-sensitive fault.

Two new companions are prepared under
`build/diagnostics/20260922-table-ab/` using the unchanged candidate:

- TABQUIET: original fill and inline verification loops, failure-only
  message construction, no progress output or flushes. Final success only.
- TABEAGER: original eager assertions retained, with flushed progress
  markers every 4,096 entries and around collection.

Both pass under GoldenGate with memory checks and 49,152 verified entries;
local elapsed times were approximately 1.9 and 9.3 seconds respectively.
These are not hardware estimates. Image and ShrinkIt contents were extracted
and byte-compared. Hardware results for these two companions are pending.
Use a fresh power-cycle before each comparison, record elapsed times and
progress intervals, and require the final success marker and shell return.
Do not infer a hardware failure deadline from the local measurements.
The package is staged at `<NAS mount>/LUA.20260922/TABLEAB/TABLEAB.SHK`;
all five transfer files were read back and matched their local bytes.

## 2026-09-22: both table comparison companions pass

The user reports `luareview -E -v tabquiet.lua` passed with 49,152 entries.
The initially typed negative count was explicitly corrected as a typo.
After proceeding to TABEAGER, the user reports "they passed". Record both
comparison scripts as user-reported hardware passes. No elapsed times,
phase timings, photographs, or separate shell-return confirmation were
supplied for these two runs.

TABQUIET establishes completion of the table-limit and before/after-GC
integrity checks without periodic output. TABEAGER establishes completion
with the original eager assertion-message construction and progress output.
Together with TABPROBE, these results strengthen the explanation that the
original test's extra successful-assert/message work caused a long runtime.
They do not measure that cost on hardware, or establish completion of the
original silent TABLEOVF or IIGSHOST. A timing/layout-sensitive problem in
those exact originals is not ruled out. No runtime fix is inferred from
these diagnostic passes.

## 2026-09-22: original silent tests pass and return to the shell

The user reports: "they all passed", explicitly identifying original
tableovf.lua as completing in about 18 minutes with `entries=49152`, and
confirms "all ran, all returned to the # prompt". In the ongoing test
sequence, this closes the outstanding original TABLEOVF/IIGSHOST completion
checks and the separate shell-return checks for TABQUIET and TABEAGER.
Record these as user-reported passes on the review candidate. IIGSHOST's
elapsed time and exact final output were not transcribed in this update;
no additional per-test run counts are inferred.

The original silent table workload therefore completed successfully without
progress output. Its earlier five-/nine-minute observations were premature
to classify as a hang. The observed approximately 18-minute duration applies
to this accelerated ROM 03 / 8 MB configuration, not a universal deadline.
TABPROBE's previously reported under-seven-minute duration and the eager
assertion-message work support a workload-cost explanation; they do not
isolate or precisely measure allocation versus collection costs.

No interpreter change was needed to obtain these passes. The tested
originals and diagnostic variants are preserved. This closes the present
silent-test investigation; it does not establish repeatability counts for
LUAREVIEW, full upstream API coverage, or resolution of files.lua.

## 2026-09-22: LUAREVIEW repeatability and mixed-script session pass

After being asked to run `coroutine.lua` and `hwdiag2.lua` with LUAREVIEW
five times each without rebooting, then once each after a full power-cycle,
the user reports "it has passed every single test". Record the requested
sequence as completed by user report: ten warm launches and two cold-boot
follow-up launches, with the requested success markers and shell returns.
This is contextual confirmation of the instructed sequence, not a captured
per-invocation log.

The user also reports running additional scripts successfully and continued
operation after many different scripts in the same warm session. Script
names, counts, and durations were not supplied, so record this as additional
qualitative stability evidence without adding it to the twelve counted
launches or claiming coverage of particular unlisted scripts.

LUAREVIEW `IIgs 9add073-776024bcfb02 plain` now has successful targeted
hardware checks, clean exits, the requested warm/cold repeatability checks,
and additional mixed-script session evidence on the accelerated ROM 03 /
8 MB machine. No further repetition of this sequence is needed to close
this validation phase. Preserve both this exact candidate and the earlier
LUAPATH baseline. The unavailable upstream T harness and historical
files.lua failure remain separate limitations; these results do not claim
all upstream tests pass or certify other hardware configurations.

## 2026-09-23: release math assertion isolated to zero raised to zero

The hardware photograph identifies `IIgs ae2f43c-1ccc85f13f42 plain`, the
v0.2.0 release interpreter, running `15:lua -E -v math.lua`. It reports
32-bit integers, a 64-bit float significand, and an assertion at line 176,
then returns to the shell. The initial `mm=untested` banner is an allocator
status, not evidence of this arithmetic failure's cause.

A standalone POWPROBE then repeated all 49 variable-base/exponent
comparisons from -3 through 3 on that same interpreter. The supplied
photograph shows exactly one failure, `i=0 j=0`: both powers, their
reciprocal comparison, and their difference are NaN. It ends with
`POWPROBE DONE checked=49 failures=1` and a shell prompt. The other 48
comparisons passed. Under GoldenGate, this release interpreter reports
53 significand bits and passes all 49 comparisons.

The candidate math test now explicitly skips only the IIgs `0^0`
comparison; the existing `_port` option retains its broader portable-test
behavior. Source review also found that the seeded random-float assertions
used the detected float precision, although the IIgs generator deliberately
produces 53 bits. Both the seeded and statistical tests now share that
53-bit expectation. This second issue was identified from code, not an
additional hardware assertion. No interpreter code changed.

The complete revised math script passes with the explicit skip under the
release's plain and traced interpreters using GoldenGate with memory checks;
the trace includes state closure. An exact rational check of the known
seeded sample confirms that truncating its low 11 bits leaves a difference
of `470 * 2^-64`, within `2^-53` but outside `2^-64`.

The candidate is supplied separately as MATHFIX.LUA so the original release
test can be retained. Its complete real-hardware result is still pending;
these findings do not establish that the remainder of math.lua passes on
hardware or change the published v0.2.0 artifacts.

### Follow-up: revised math test fails at the minimum integer

The user reports `mathfix.lua:200 assertion failed!`. In the supplied
candidate this is `assert(minint + 0.0 == minint)`, where the configured
minimum integer is -2,147,483,648. This is a required numeric equality,
not another power-domain exception. The assertion is retained; the
complete revised math test has not passed hardware validation.

MINPROBE 1 separates integer-to-float conversion, mixed equality and
ordering, conversion back to integer, table lookup, and boundary rejection.
It also reports the native bytes of the arithmetic, literal, and parsed
minimum floats, plus rounding results. The released interpreter passes
all 33 checks under GoldenGate. Real-hardware probe results and a confirmed
cause are pending. No runtime correction is claimed from this report.

### MINPROBE hardware result and minimum-integer fix candidate

The next photograph shows `MINPROBE DONE checked=33 failures=5` and a
clean shell return. The arithmetic, literal, and parsed minimum floats all
have bytes `00000000000000801ec0`, matching the locally observed correct
extended representation. However, converting that float back yields
`2147418112` (`0x7fff0000`). The failing checks are both mixed equality
directions, conversion to integer, table lookup, and literal roundtrip.
Floor, ceil, and the integral part of modf also report the same wrong
integer. Ordering, the minimum plus one, -1, zero, the maximum, and the
out-of-range rejection checks pass.

This isolates the observed fault to conversion back to integer at the exact
minimum, rather than storage of the floating value. It does not by itself
identify the responsible instruction or library routine. The candidate
IIgs `lua_numbertointeger` macro returns `LUA_MININTEGER` directly for this
exact value, bypassing its C cast. Other values retain the existing range
checks and conversion. The math assertion remains enabled.

The new targeted `numconv.lua` regression exercises 90 checks covering
boundary roundtrips, equality, ordering, bit coercion, rounding, normalized
table keys, fractional boundaries, infinities, and NaN rejection. The
candidate interpreter and complete revised math test still require a
real-hardware run.

For successive hardware probes, reuse `/nas/lua.test/test.shk`, extracting
`TEST.LUA`; identify the actual probe revision by its printed banner.
When testing runtime changes, the archive also carries `LUATEST` so the
installed release can be retained. Local diagnostic snapshots preserve
earlier probe bytes even when the NAS archive is updated in place.

Candidate `IIgs aa385d7-13178cdf3c75 plain` and its trace variant pass all
16 targeted scripts under GoldenGate memory checks. The hardware-kit
builder also passes its embedding, allocator fault-injection, bridge,
Memory Manager, and compiler roundtrip/depth checks. The broader 30-script
group completes under the runner's respective contracts, including existing
skips; `files.lua` retains its expected line-323 nil-value failure.

The combined `MATHCHECK 2` driver runs MINPROBE, NUMCONV, and MATHFIX in
one interpreter process and passes locally, ending with
`MATHCHECK 2 PASSED - expect shell prompt next`. Its ShrinkIt archive is
extracted and byte-compared before transfer; LUATEST has EXE B5/0000
metadata. These are local results, not a hardware pass for the fix.

### 2026-09-23: MATHCHECK 2 passes on the real IIgs

The user's next photograph shows the complete combined driver reaching:

- `MINPROBE DONE checked=33 failures=0`
- `NUMCONV PASSED checks=90`
- `OK` at the end of the adapted math test
- `MATHCHECK 2 PASSED - expect shell prompt next`

The screen shows the minimum correctly returned as -2,147,483,648 by
tointeger, floor, ceil, and modf. The math test reports 32-bit integers and
a 64-bit float significand, explicitly skips its `0^0` comparison, and
completes both random-number sections. A shell prompt with a subsequently
typed command confirms return to the shell.

Record one hardware pass of the supplied LUATEST/MATHCHECK 2 candidate
(`IIgs aa385d7-13178cdf3c75 plain`) on the existing accelerated ROM 03 /
8 MB setup. The cropped photograph does not repeat the build banner;
candidate identity follows the delivered archive and ongoing test sequence.
The typed command is not evidence of another completed run.

This validates the minimum-integer workaround and complete adapted math
test on that machine. It does not establish repeated-run counts or remove
the explicit power-domain exception. The published v0.2.0 release remains
unchanged; the fix and test updates are on `codex/math-portability`.

## 2026-09-23: focused file I/O probe passes on hardware

The photograph identifies `IIgs aa385d7-13178cdf3c75 plain` and
`IOPROBE 1 DONE checks=38 failures=0`, with a clean shell return. All text
read modes report LF bytes, and the binary, restored fixture, repeated EOF,
and seek checks pass. This does not certify the broader files.lua script.
It distinguishes the earlier local newline/EOF failures from this hardware
result; see the [I/O investigation](IO_INVESTIGATION.md) for the next test.

### FILECHECK 2 reaches buffering, then fails at the second open

The next photograph shows the same build returning to the shell after
FILEFIX.LUA line 680 reports `no such file or directory` opening a reader.
The writer had opened successfully immediately before it. This precedes
the buffering setup and write, so it is not the emulator's line-683
visibility assertion. No buffering or full files.lua hardware pass is
recorded. BUFPROBE 3 will compare creation and second-open behavior.

### BUFPROBE 3 isolates writer sharing

The next photograph shows `IIgs aa385d7-13178cdf3c75 plain`, six cases,
`errors=0`, and a shell prompt. In all five writer cases, the second reader
reports `open-err:4` before write, after write, and after flush. After close,
it reads the correct data. This includes preexisting files, r+, binary mode,
and unbuffered output. Two simultaneous readers succeed in B6. The result
supports a writer-sharing restriction in this setup; it does not establish
buffer visibility or identify the responsible OS/runtime/storage layer.
FILECHECK 4 adapts that assumption and is awaiting hardware results.

### FILECHECK 4 completes on hardware

The next photograph confirms `IIgs aa385d7-13178cdf3c75 plain` and
`FILECHECK 4 FINISHED - expect shell prompt next`, followed by `#`.
Full, unbuffered, and line-buffered modes each report correct close/reopen
data. Portable date/time checks finish; `no daylight saving information`
is informational, not a failed assertion.

This is one hardware pass of the repaired/adapted files.lua using portable
and small-file flags. The run explicitly excludes Unix processes,
nonportable dates, the large-file block, and cross-handle buffer visibility.
It does not certify those cases or resolve the stock emulator's EOF/text
translation differences. The interpreter is unchanged from the successful
math tests; this investigation changed tests and documentation only.

## 2026-09-24: published v0.2.1 acceptance prepared

RELEASECHECK 1 will test the exact published plain interpreter bytes,
`IIgs e026f5b-13178cdf3c75 plain`, renamed to LUATEST for the existing test
commands. Smoke, 90 numeric conversion checks, the full adapted math test,
and the repaired portable/small-file I/O test run in one invocation.
The package's executable hash matches the published release manifest;
no interpreter was rebuilt. The isolated diagnostic emulator completes
the combined run, but hardware validation is pending. See the
[September 24 record](2026-09-24/README.md) for provenance, scope, and logs.

### Published v0.2.1 acceptance passes

After transfer verification and instructions specifying the release banner,
all four stages, the final RELEASECHECK 1 marker, and shell return, the user
reported "everything passed". Record one user-reported hardware acceptance
pass of the published plain interpreter on the established machine. No new
hardware photograph/log was supplied for this run.

This covers smoke, 90 numeric conversion checks, full adapted math, and
portable/small-file I/O with date/time. The documented platform-dependent
math and file-test skips remain. It does not validate LUAC, LUATRACE,
IIGSHOST, larger files, or repeated cold/warm runs of the exact release bytes.

### LARGEFILE 1 prepared; hardware result pending

The follow-up package retains the exact published v0.2.1 plain interpreter
and adds a binary-file diagnostic crossing 64/128/192/256 KiB boundaries.
It checks sequential integrity, seeks, updates, append, and truncation with
small transfers and a single open handle at a time. Installed GoldenGate
completes the test with the expected marker, exit 0, and stack usage 5,729
bytes. This is preflight evidence only; no hardware pass is recorded yet.
See the [September 24 record](2026-09-24/README.md#follow-up-largefile-1).

### LARGEFILE 1 passes on hardware

After staging the verified archive and requesting its final marker and shell
return, the user reported "all tests work". Record one reported hardware pass
with the published v0.2.1 plain interpreter, `e026f5b-13178cdf3c75`, on the
established setup. No new hardware photograph or log was supplied.

The test verifies every byte before and after updates, seeks around the
64/128/192 KiB boundaries, appends across 256 KiB to 262,163 bytes, and checks
truncation. Transfers are at most 4,096 bytes and writers close before readers
open. This pass does not extend to large single transfers, larger file sizes,
other storage devices, or repeated cold/warm testing of this diagnostic.

### BIGIO 1 prepared; hardware result pending

The next package keeps the published v0.2.1 plain interpreter and tests
single binary transfers at seven sizes around 32/64/128 KiB. Each case
checks single-write data through counted reads, read-all, and partial reads
at EOF, with exact byte/length/position comparisons. Installed GoldenGate
completes all cases with exit 0 and stack usage 5,788 bytes. Hardware results
are pending; see the [September 24 record](2026-09-24/README.md#follow-up-bigio-1).

### BIGIO 1 passes on hardware

After staging the verified package and requesting `BIGIO 1 PASSED cases=7`
and the shell prompt, the user reported "passed". Record one reported pass
with the unchanged published v0.2.1 plain interpreter on the established
setup. No new hardware photograph or log was supplied.

The seven sizes span 32,767 through 131,073 bytes. Each case checks a single
write, counted read, read-all, and a counted request extending 17 bytes past
EOF, with exact data, lengths, file sizes, and positions. This extends the
earlier large-file/small-chunk coverage to large single transfers; it does
not establish a maximum supported size, other storage configurations, or
repeatability across cold/warm launches.

### BYTEFILE 1 prepared; hardware result pending

The next diagnostic uses the same published interpreter to compile and
execute source exceeding 64 KiB, dump debug and stripped bytecode exceeding
64 KiB, and reload both from memory and files. It checks nested closures,
binary constants, GC, rejection of truncated/wrong-mode input, and valid
reloads after errors. Installed GoldenGate completes both variants with
exit 0 and stack usage 7,151 bytes. Hardware validation is pending; see the
[September 24 record](2026-09-24/README.md#follow-up-bytefile-1).

### BYTEFILE 1 passes on hardware

Following the staged package and instructions requesting both variants and
shell return, the user reported "passed" and asked to continue testing.
Record one reported hardware pass with the unchanged published interpreter.
No new hardware photograph or log was supplied. Coverage includes this
generated source program, debug/stripped bytecode over 64 KiB, memory/file
reloads, nested closures after GC, and recovery after rejected loads.
This does not validate the separate LUAC executable or arbitrary bytecode.

### FILELIFE 1 prepared; hardware result pending

The next package retains the published interpreter and checks repeated file
cleanup after normal return, errors, coroutine cancellation, early loop
exit, and garbage collection. Five paths run 12 times in each of incremental
and generational GC, with data, handle-state, and deletion assertions.
Installed GoldenGate completes all 120 cases with exit 0 and stack usage
7,230 bytes. Hardware validation is pending; see the
[September 24 record](2026-09-24/README.md#follow-up-filelife-1).

### FILELIFE 1 passes on hardware; combined suite started

After instructions requesting the 120-case completion marker and shell
return, the user reported "test passed. running suite now". Record one
reported FILELIFE pass with the unchanged published v0.2.1 interpreter on
the established setup. No new photograph, hardware log, or timing was
supplied. This covers the five file-cleanup paths in both GC modes, not
OS-wide resource counts or repeatability across launches.

The user has started the reusable 23-test suite. Its combined hardware
result remains pending; the FILELIFE result does not establish a suite pass.

### Reusable full suite passes on hardware

The next photograph shows `SUITE COMPLETE group=full passed=23 failed=0
with_skips=8` followed by `Expect shell prompt next` and a usable `#` prompt.
The visible preceding stages include FILELIFE's 120 cases and TABLEOVF
retaining 49,152 entries, each followed by its suite PASS line.

Record one photographed full-suite pass on the established accelerated
ROM03/8 MB machine. Eight scripts include intentional skips. The final
screen does not show the build banner; association with the published
v0.2.1 executable comes from the staged kit and session context. No new
timing or cold/warm repeatability claim is made. See the
[dated record](2026-09-24/README.md#full-suite-passes-on-the-iigs) and
[hardware report](2026-09-24/suite-hardware.json).

### Standalone LUAC test prepared; hardware result pending

The next kit uses the published v0.2.1 LUAC executable, renamed LUACTEST,
and the same published Lua interpreter. Six checks cover small compilation,
large debug/stripped bytecode, syntax/depth rejection, and compilation after
errors. Installed GoldenGate preflight passed all native processes and
result checks. The new ORCA EXEC batch launch itself remains untested on
hardware. See the [dated record](2026-09-24/README.md#standalone-luacprobe-1).

### LUAC batch launch feedback

The user reported that a semicolon in the batch's first comment line caused
a parsing error, and that the current executable prefix is `20:` rather
than `15:`. Both are corrected in the next package, with a configurable
prefix for future setups. Local native checks still pass; no LUAC hardware
completion is claimed from this launch feedback.

### Standalone LUAC passes all six hardware checks

The user reported "it all passed" with a photograph showing
`LUACPROBE 1 PASSED checks=6 - expect shell prompt next` and a returned `#`.
Visible output includes 72,126-byte stripped bytecode, the intended syntax
and C-stack-overflow errors, their verified phase markers, and a successful
175-byte recovery compile. This confirms the corrected ORCA batch using
`20:`, including error redirection/status checks and clean shell return.

Record one six-check pass on the established setup. Initial version banners
are outside the photo; build association follows the staged v0.2.1 package
and session context. No hardware timing or repeatability count was supplied.
See the [dated record](2026-09-24/README.md#luacprobe-1-passes-on-hardware) and
[hardware report](2026-09-24/luac-hardware.json).

### Published native C-host test prepared

The next HOSTCHECK batch uses the published v0.2.1 IIGSHOST executable,
checks initialization/stack and allocation guards, retained data, and
native C-hook yield/resume, then launches a fresh Lua smoke test. Installed
GoldenGate reports 100 yields and successful completion of all processes.
Hardware validation of this release-host batch is pending. See the
[dated record](2026-09-24/README.md#native-hostcheck-1).

### Published native C-host passes on hardware

A follow-up photograph confirms `IIGSHOST PASSED yields=100`, the verifier's
matching yield count, all post-host Lua smoke stages, the final
`HOSTCHECK 1 PASSED - expect shell prompt next`, and a returned `#`.
The visible interpreter build is `e026f5b-13178cdf3c75 plain`; native-host
identity follows the staged published v0.2.1 archive. Record one confirmed
hardware run, with no elapsed time or cold-start/repeatability claim.
See the [dated record](2026-09-24/README.md#hostcheck-1-passes-on-hardware)
and [hardware report](2026-09-24/host-hardware.json).

### Second reusable full-suite pass

After the power-off/on test request, a new photograph shows another
`SUITE COMPLETE group=full passed=23 failed=0 with_skips=8` and a returned
`#`. FILELIFE reports 120 cases and TABLEOVF reports 49,152 entries.
Record two confirmed completed suite runs in total. The user subsequently
confirmed a complete power-off/on before the second run, establishing one
cold-start full-suite pass. No elapsed time was supplied. See the
[dated record](2026-09-24/README.md#second-full-suite-hardware-pass) and
[hardware report](2026-09-24/suite-hardware.json).
