# Published v0.2.1 executable acceptance

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
