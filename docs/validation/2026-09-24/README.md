# Published v0.2.1 executable acceptance

The broader validation phase is now complete; see the
[phase closeout](PHASE-CLOSEOUT.md) for final coverage, confirmed hardware
runs, and reusable kits. Entries below retain the chronological evidence.

Status: user-reported hardware pass of the requested RELEASECHECK 1 run.

RELEASECHECK 1 uses LUA extracted from a fresh download of the published
v0.2.1 LUA.SHK, renamed to LUATEST without changing its bytes. Its expected
banner is `IIgs e026f5b-13178cdf3c75 plain`. The archive SHA-256 was verified
against the release checksums, and the executable against RELEASE-MANIFEST.
[Provenance](releasecheck-provenance.json) and [package checksums](releasecheck-sha256.txt)
identify the exact artifacts. No interpreter rebuild was performed.

The [driver](releasecheck.lua) is transferred as TEST.LUA and sequentially
runs HWSMOKE.LUA, NUMCONV.LUA, MATHFIX.LUA, and FILEFIX.LUA in one invocation.
The first three are extracted unchanged from the release archive (MATH.LUA
is renamed MATHFIX.LUA). FILEFIX.LUA is files.lua from merged PR #16,
commit a0648fe7654fc2a23a82cd187701429550d4a999, with LF converted to CR.
No other test content is changed. The math run uses its full adapted scope;
portable/small-file flags are enabled only for the file run.

The existing skips remain: platform-dependent 0^0 in math, and Unix
processes, nonportable dates, large files, and cross-handle buffer
visibility in files.lua. The smoke script's shell-return message is
intermediate here; R2 follows it automatically.

## Preflight

All four stages and the final marker completed, exit 0, under the isolated
diagnostic GoldenGate described in the [I/O investigation](../IO_INVESTIGATION.md).
Its EOF/text adjustments remain emulator-only. Stack usage was 7,980 bytes.
The [log](releasecheck-preflight.log) is local emulator evidence, not a
hardware result. Floating-point precision reported by this emulator differs
from the hardware reports; preflight alone does not establish hardware behavior.

Every file was extracted from the new ShrinkIt archive and compared with its
packaging input. LUATEST retains EXE B5/0000 metadata. After the NAS was
remounted, the package was copied to the existing NAS TEST.SHK path and
read back byte-for-byte. Its SHA-256 is
`18dd5ef359ff7f5793eefdf0f8cd5e3e351f4300917dce865123e73ea147110d`.
The published release is unchanged.

## Hardware result

After the verified package was staged and the expected banner, four-stage
completion, and shell return were requested, the user reported "everything
passed". Record one reported acceptance pass on the established accelerated
ROM 03 / 8 MB setup. This is a user report, not a new photograph or captured
hardware log; the preflight log above remains emulator evidence only.

The reported run covers smoke, 90 numeric conversion checks, the full adapted
math test, and the repaired portable/small-file I/O and date/time test with
the listed skips. It validates the published plain interpreter bytes for
this scope. It does not establish repeated cold/warm acceptance of these
exact release bytes or validation of the other release executables.

## Hardware run

Use the same commands in the established test directory:

```text
yankit xvf /nas/lua.test/test.shk
15:luatest -E -v test.lua
```

Capture the actual executable banner and final result. Expect R1 through R4
PASSED, then `RELEASECHECK 1 PASSED - expect shell prompt next` and `#`.
A script marker without the shell return is not a completed acceptance run.
This acceptance covers the published plain interpreter only, not LUAC,
LUATRACE, or IIGSHOST.

## Follow-up: LARGEFILE 1

Status: local preflight passed and the user reports the hardware test passed.

The next TEST.SHK contains [largefile.lua](../../../tests/largefile.lua) as
TEST.LUA and the same published v0.2.1 interpreter as LUATEST. It needs about
257 KiB for a temporary binary file on the temporary-file volume. It does not
open a reader while a writer is open. It removes the temporary file on
completion and attempts cleanup on a caught test failure.

The test writes 262,143 bytes in chunks of at most 4,096 bytes, then verifies
every byte after reopening. A 257-byte repeating pattern includes every byte
value and changes phase across a 64 KiB boundary. It checks absolute,
forward/backward relative, and end-relative seeks; writes patches across
64/128/192 KiB boundaries; and appends to 262,163 bytes, crossing 256 KiB.
A second full verification checks both changed and unchanged data. Finally,
it truncates and reopens the file to verify that old trailing data is gone.
This does not test large single allocations/transfers or text translation.

The installed GoldenGate emulator completes this test with exit 0, the
expected final marker, and stack usage 5,729 bytes; no diagnostic emulator
patches are needed for this preflight. See the [log](largefile-preflight.log),
[provenance](largefile-provenance.json), and [checksums](largefile-sha256.txt).
Archive files were extracted and compared with their packaging inputs;
LUATEST's hash matches the published release and metadata remains EXE B5/0000.

Use the same extraction/run commands above. The expected final marker is
`LARGEFILE 1 PASSED bytes=262163 - expect shell prompt next`, followed by `#`.
Progress appears every 32 KiB. No hardware runtime estimate is established.

After this package was staged and the final pass marker and shell return
were requested, the user reported "all tests work". Record one reported
hardware pass on the established accelerated ROM 03 / 8 MB setup. No new
photograph or hardware log accompanied the report; the log linked above
is emulator evidence only. The result covers the diagnostic's byte checks,
boundary seeks/updates, append, and truncation through 262,163 bytes. It
does not establish large single transfers, larger file sizes, other storage
devices, or repeatability across cold/warm launches.

## Follow-up: BIGIO 1

Status: local preflight passed and the user reports the hardware test passed.

After PR #17 merged the release-acceptance and LARGEFILE records, the next
diagnostic [bigio.lua](../../../tests/bigio.lua) targets larger single
transfers, using the same published plain interpreter. It exercises 32,767,
32,768, 65,535, 65,536, 65,537, 131,072, and 131,073 bytes. Native C int is
16 bits, but the ORCA/C headers define size_t as unsigned long; these values
test potential boundary defects, not a presumed universal 64 KiB limit.

Each case builds a payload containing every byte value with period 257,
performs one write call, closes, and reopens separately for counted reads,
read-all, and a counted request 17 bytes beyond EOF. Exact bytes, lengths,
file sizes, and positions are checked. Only a temporary binary file is
used; readers never overlap a writer. Payload construction uses concatenation
because string.rep's separate INT_MAX limit would otherwise prevent testing
the I/O path. This does not claim that every string API supports these sizes.

Installed GoldenGate completes all seven cases with exit 0 and stack usage
5,788 bytes. See the [preflight log](bigio-preflight.log),
[provenance](bigio-provenance.json), and [checksums](bigio-sha256.txt).
The archive contents were extracted and byte-compared, and the unchanged
LUATEST hash and EXE B5/0000 metadata verified.

The same TEST.SHK path and extraction/run commands are used. Expect operation
and size markers followed by `BIGIO 1 PASSED cases=7 - expect shell prompt next`
and `#`. No hardware runtime estimate is established.

After the verified package was staged and the final marker and shell return
were requested, the user reported "passed". Record one reported hardware
pass on the established accelerated ROM 03 / 8 MB setup. No new photograph
or hardware log accompanied this result; the linked preflight log remains
emulator evidence. The reported pass covers all seven sizes, single writes,
counted reads, read-all, and reads extending past EOF through 131,073 bytes
of returned data. It does not establish larger sizes, arbitrary string-library
operations, other storage devices, or repeated cold/warm testing.

## Follow-up: BYTEFILE 1

Status: local preflight passed and the user reports the hardware test passed.

The next package contains [bytefile.lua](../../../tests/bytefile.lua) and the
unchanged published v0.2.1 plain interpreter. It generates 117,077 bytes of
source containing 9,000 arithmetic statements, loads from a temporary file,
and checks execution with three input values. Nested closures retain their
upvalues across garbage collection; binary string constants are checked too.

Both debug and stripped dumps must exceed 64 KiB. Each is reloaded from
memory and disk, with exact saved-byte comparisons and execution checks.
Wrong-mode and truncated-chunk loads must be rejected; valid bytecode is
then reloaded and executed again. Only the known-valid chunks are executed.
Two temporary files are removed afterward. This tests string.dump/load/loadfile,
not the separate LUAC executable or cross-platform bytecode compatibility.

Installed GoldenGate completes both variants, exit 0, with stack usage
7,151 bytes. The local dumps measured 90,751 and 72,130 bytes; source-path
metadata can change the debug dump size on hardware. See the
[preflight log](bytefile-preflight.log), [provenance](bytefile-provenance.json),
and [checksums](bytefile-sha256.txt). Archive contents were extracted and
compared to packaging inputs, including the unchanged release executable
and its EXE B5/0000 metadata.

Use the same TEST.SHK path and commands. Expect
`BYTEFILE 1 PASSED variants=2 - expect shell prompt next`, followed by `#`.
The test prints each phase before running it; no hardware timing estimate
has been established.

After staging and instructions requesting both variants and shell return,
the user reported "passed" and requested the next test. Record one reported
hardware pass with the published plain interpreter on the established setup.
No new photograph or hardware log was supplied. This covers this generated
program and the stated loader checks, not the separate LUAC executable,
arbitrary bytecode, cross-platform compatibility, or cold/warm repeatability.

## Follow-up: FILELIFE 1

Status: local preflight passed; one user-reported hardware pass.

[filelife.lua](../../../tests/filelife.lua) uses the unchanged published
interpreter for 120 cases: five cleanup paths, 12 rounds, two GC modes
(incremental and generational). The paths are normal return and error
unwinding with a to-be-closed file, cancellation of a suspended coroutine
holding a file, early exit from an io.lines loop, and collection of an
abandoned ordinary file userdata without an explicit close.

Retained handles must report closed where inspectable. Each case reopens
the file to compare all written data, then removes it. A weak reference
checks that the abandoned userdata is collected after two full collections.
Writers request full buffering where applicable. This checks resulting
data and Lua-visible cleanup, not when the runtime writes its buffer or
OS-wide descriptor/memory leak counts. Only a temporary file is used.

Installed GoldenGate completes all 120 cases, exit 0, stack usage 7,230 bytes.
See the [preflight log](filelife-preflight.log),
[provenance](filelife-provenance.json), and [checksums](filelife-sha256.txt).
Package contents were extracted and compared with inputs; the executable
hash matches the release and its metadata remains EXE B5/0000.

Use the same TEST.SHK path and commands. Every operation prints progress.
Expect `FILELIFE 1 PASSED cases=120 - expect shell prompt next`, then `#`.
After instructions requesting the final marker and shell return, the user
reported "test passed. running suite now". Record one reported FILELIFE pass
with the unchanged published interpreter. No new photograph, hardware log,
or timing was supplied. The combined suite was still pending at that point;
its subsequent photographed pass is recorded below.

## Reusable regression suite 1

Status: local combined preflight passed; one photographed full-suite hardware
pass with clean shell return.

The [suite guide](../../../tests/SUITE.md) documents the 23-test driver,
named groups, and reproducible packaging. It reuses the same published
v0.2.1 executable (SHA-256
`431a82d763f25dfcf0c320d21406b599ef9e6c184197b7d034e9c41fd2599d0a`).
No runtime rebuild or release change was made.

- Installed GoldenGate: `runtime` completed 15/15 adapted scripts, seven
  with explicit skips, exit 0; [log](suite-runtime.log) and
  [report](suite-runtime-report.json).
- Isolated I/O diagnostic GoldenGate: `full` completed 23/23 adapted scripts,
  eight with explicit skips, exit 0; [log](suite-full.log) and
  [report](suite-full-report.json). This is the separately patched emulator
  from the I/O investigation, not stock GoldenGate or real hardware.
- Both combined runs reported maximum stack use of 20,299 bytes. An early
  harness using protected calls consumed too much native stack for `pm`;
  the final driver directly invokes chunks in the Lua VM. Standalone tests
  remain useful because aggregation changes the execution context.
- Fifteen runner/kit unit tests passed with real-IIgs-binary fault injection
  enabled. Injected printed failure, missing marker, and error after marker
  all failed without proceeding to the next test or producing a summary.
- Every ShrinkIt member was extracted and byte-compared; LUATEST metadata
  is EXE `$B5` / auxiliary `$0000`. [Package hashes](suite-package.json)
  bind the archive to the scripts and executable. The separate `SUITE.SHK`
  package leaves the active FILELIFE `TEST.SHK` package unchanged.

The default run includes the long table-overflow test last. Require
`SUITE COMPLETE group=full passed=23 failed=0 with_skips=8` (the local skip
count) followed by a clean shell return; retain any changed skip counts and
their reasons. Individual prior hardware passes do not establish that the
combined driver has passed. Native hosts and LUAC remain separate checks.

### Full suite passes on the IIgs

The user supplied a photograph showing FILELIFE's 120-case completion,
`SUITE PASS filelife`, `TABLEOVF PASSED entries=49152`, and
`SUITE PASS tableovf`, followed by:

```text
SUITE COMPLETE group=full passed=23 failed=0 with_skips=8
Expect shell prompt next
#
```

This confirms one complete run of the combined driver and clean return to
the shell on the established accelerated ROM03/8 MB setup. Eight adapted
tests reported intentional skips; those skipped sections are not validated
by this result. The photo shows only the final screen, not the build banner
or every individual test's output. Package/build association follows the
staged kit and session context; [hardware report](suite-hardware.json)
references the preserved package hashes. No new elapsed time, cold-start
claim, or repeatability count is inferred. Native hosts and LUAC remain
separate checks.

## Standalone LUACPROBE 1

Status: six local compiler checks passed; one photographed hardware pass
with a successful ORCA batch run and clean shell return.

The [LUAC test guide](../../../tests/LUAC_TESTING.md) describes the six checks
and ORCA batch entry point. The kit extracts the unchanged published v0.2.1
compiler and interpreter, verifies their release manifest hashes, and renames
them LUACTEST and LUATEST. Compiler SHA-256:
`a21493e2793b77149f99fc89fc00fb89a9b886cafadca24c8bfb24194b407d61`.

Installed GoldenGate completed a small compile, large debug and stripped
compiles, syntax/depth rejection, and compilation after those errors. The
large source is 117,073 bytes; debug/stripped binaries measured 90,744 and
72,126 bytes locally. Three inputs verify arithmetic, a binary constant, and
a captured upvalue after GC. Every native process returned; expected-error
status and diagnostics were both checked. The deepest compiler case reported
17,447 bytes of stack use. See [preflight](luac-preflight.log).

Seventeen kit/runner tests passed, including rejection of a premature final
phase, an unexpectedly successful invalid compile, and an unrelated file
error. The local process sequence generates the packaged ORCA EXEC script;
GoldenGate preflight does not execute that shell script. The hardware run
must confirm its launch, redirection and status propagation too.

Every archived member was byte-compared with its input. The executables are
EXE B5/0000; TEST is SRC B0/0006 (ORCA EXEC). See
[provenance and hashes](luac-provenance.json) and
[metadata](luac-metadata.txt). The full suite archive remains unchanged.

Extract the next `/nas/lua.test/test.shk`, then run `20:test` from the test
directory. Require `LUACPROBE 1 PASSED checks=6 - expect shell prompt next`
and `#`. Hardware completion is recorded below; no timing was supplied.

### LUAC batch launch correction

The user reported a parsing error from the semicolon in the first comment
line, and corrected the executable prefix from `15:` to `20:`. The generated
batch now uses a period in that comment, contains no semicolons, and uses
`20:` for every executable call. The packager accepts `--prefix` for other
setups, and the current command guides use the user-confirmed prefix.

All six native compiler checks passed again locally, and all twenty
kit/runner checks passed, including new batch-separator and prefix tests.
The rebuilt archive contains the unchanged interpreter/compiler and Lua
verifier. Every member was extracted and compared and the EXE/SRC metadata
was checked. See the [corrected package hashes](luac-shellfix-provenance.json)
and [preflight](luac-shellfix-preflight.log). This supersedes the first
LUAC probe archive at the same NAS path. Hardware completion was pending
at that point; the following result confirms the corrected batch.

### LUACPROBE 1 passes on hardware

The user reported "it all passed" and supplied a photograph showing the
stripped binary verified at 72,126 bytes, both expected compiler errors,
syntax/depth PHASE PASSED markers, and a successful recovery compile whose
binary measured 175 bytes. The final output is:

```text
LUACPROBE 1 PASSED checks=6 - expect shell prompt next
#
```

This confirms one six-check hardware pass and clean batch exit on the
established accelerated ROM03/8 MB setup. The corrected `20:` prefix is
visible in compiler diagnostics. Successful error-verification phases also
confirm the batch's stderr redirection and status propagation in this run.
The photo shows the latter portion of the run, not its initial version
banner or the earlier debug binary's size. Association with the unchanged
v0.2.1 executables follows the staged corrected archive and session context.
See [hardware report](luac-hardware.json). No elapsed time, cold-start result,
or repeated-run claim is inferred. Native C-host checks remain separate.

## Native HOSTCHECK 1

Status: local preflight and one photographed hardware run passed, including
post-host smoke and return to the shell.

The [native host guide](../../../tests/HOST_TESTING.md) describes the next
batch. It uses the unchanged published v0.2.1 IIGSHOST binary (SHA-256
`4d8a7695f6a3accd5792fd1979dacd706ea0fcd2ecbd56cfed0b35f915187f93`)
and the same published interpreter as the suite and compiler checks. This
targets the release artifact; earlier IIGSDBG observations belong to their
previous diagnostic build.

Installed GoldenGate reports `IIGSHOST PASSED yields=100`, exit 0, stack
usage 5,208 bytes. The Lua verifier accepted its stdout/stderr and exit
status, then a fresh Lua process completed the smoke test, with stack usage
5,514 bytes. See [preflight](host-preflight.log). Twenty-two kit/runner tests
passed with real-IIgs-binary verifier fault injection: nonzero status,
incidental/duplicate/invalid yield markers, error/degradation output, and
a failing post-host smoke cannot produce the final pass marker.

The archive preserves EXE B5/0000 for IIGSHOST and LUATEST and SRC B0/0006
for TEST. Every member was extracted and byte-compared. See
[provenance](host-provenance.json) and [metadata](host-metadata.txt).
The ORCA batch uses `20:`, has no semicolon separators, captures host stdout
and stderr, and saves status immediately before invoking the verifier.
Local preflight launches native processes separately, not the ORCA batch.

Extract `/nas/lua.test/test.shk` and run `20:test`. The native-host phase
is quiet until it returns. Require `HOSTCHECK 1 PASSED - expect shell
prompt next` and then `#`.

### HOSTCHECK 1 passes on hardware

Following the user's report that it seemed to work, a photograph confirms
the interpreter banner `IIgs e026f5b-13178cdf3c75 plain`,
`IIGSHOST PASSED yields=100`, and `HOSTCHECK 1 HOST VERIFIED yields=100`.
The subsequent fresh interpreter completes smoke stages S0 through S4,
prints `HOSTCHECK 1 PASSED - expect shell prompt next`, and returns to `#`.

Record one confirmed native-host batch pass on the established accelerated
ROM03/8 MB setup. The native executable's identity follows the staged,
hash-verified v0.2.1 archive; the photographed banner belongs to LUATEST.
No duration or cold-start/repeated-run result was supplied. See the
[hardware report](host-hardware.json). Next validation is a full Lua-suite
run after power-off/on using the existing separate suite archive.

### Second full-suite hardware pass

In response to the power-off/on and full-suite instructions, the user
supplied a new photograph showing:

```text
SUITE COMPLETE group=full passed=23 failed=0 with_skips=8
Expect shell prompt next
#
```

The screen also confirms FILELIFE's 120 cases and TABLEOVF's 49,152 entries.
This establishes a second completed full-suite hardware run and clean
shell return. The user subsequently confirmed that this run followed a
complete power-off/on, establishing one cold-start full-suite pass.
No elapsed time or initial build
banner is visible. Artifact association follows the unchanged suite
archive and session context. See the updated [hardware report](suite-hardware.json).
