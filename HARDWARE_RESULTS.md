# Real IIgs test results

Current baseline: **LUAPATH / `IIgs b69d628-9766f6d19a8d plain`**.
The planned warm-run and cold-boot checks are complete: 14 warm launches
and two post-power-cycle launches passed. Earlier "pending" entries below
describe the state when recorded; the final entry closes those checks.
Coverage is limited to the documented workloads and machine configuration.
The baseline runtime source is commit `9add073`; its banner predates that
commit. See [preserved provenance](docs/validation/2026-09-21/README.md).

Review correction: the baseline hwtest's "20 passed" includes one unsupported
Lua-hook yield case incorrectly counted as a pass. That path was untested;
the recorded hardware runs and clean shell returns are still valid evidence.
The current review candidate has separate skip reporting and a C-hook test,
but has not yet been tested on this machine.

## 2026-09-21: traced coroutine diagnostic passes

Machine reported by user: ROM 03, 8 MB RAM. The user later reported GS/OS
"6.04" tentatively and confirmed hardware acceleration is enabled. The
exact OS version, accelerator model/speed, shell version, and storage
device remain unconfirmed. Keep acceleration enabled for the next tests
to preserve the configuration used for the successful runs.

The user supplied a photograph after receiving the diagnostic kit staged
at `/Volumes/nas/LUA.20260921` (kit ID `b69d628-9bf53392629b`). The photograph
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
as `/Volumes/nas/LUA.20260921/LUAPATH.SHK`. The NAS copy was not accessible
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
and compiler. See [candidate validation](docs/validation/2026-09-22/README.md)
and [review disposition](docs/PR13-REVIEW.md) for coverage and limitations.
The historical files.lua failure remains reproducible locally.

ShrinkIt archives and images are ready locally under
`build/hardware/20260922T145111Z-5t_54b1b/`. The NAS was not mounted, so this
session did not copy the new candidate there. The next hardware sequence is
listed in HARDWARE_TESTING.md; no new hardware results are claimed here.
