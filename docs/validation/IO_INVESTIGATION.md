# File I/O investigation, 2026-09-23

Status: all 38 focused probe checks pass on real hardware. Test-fixture
defects are repaired; the broader test still needs hardware validation.
No Lua runtime I/O change is included, and v0.2.1 is unchanged.

## Restoring the upstream test

The official [Lua test archive](https://www.lua.org/tests/) lists
`lua-5.4.6-tests.tar.gz` with SHA-256
`63ed5f5bcfd15dfd2f72e04c2f8c10585bb8de9e558df62b335cb9e5c1a4ef34`.
The downloaded archive was checked against that hash before comparison.

Its files.lua contains single bytes E1 and E7, not UTF-8 replacement
characters. The port now spells those bytes as `\xE1` and `\xE7`, preserving
them through source encoding and ASCII transfer. The five-byte read must
equal `"\xE1lo"`; `{a}` is returned by the second, line-format result.
The leftover diagnostic read, undefined `s`, and printing loop were removed.
Platform detection now uses `_VERSION` instead of unconditionally enabling
IIgs adaptations. After the hardware probe, the two old CR assertions were
restored to upstream LF expectations; see the follow-up below.

## What the repaired test reveals

With the installed GoldenGate, the repaired file proceeds through the
fixture assertions and stops at repeated EOF reads with:

```text
EOF read deadlock. Application will terminate.
```

GoldenGate's `Platform/FDFile.cpp`, `FDFile::safe_read`, explicitly exits
after five consecutive nonzero-size reads that return EOF, even for regular
files. Lua's upstream test deliberately performs more than five such
reads. This is not evidence of a Lua hang.

For diagnosis only, a separate emulator copy changes the guard to
`if (++_eof >= 5 && ::isatty(_file))`. The installed emulator is untouched.
The source was copied from local GoldenGate revision
`9dd1b3d861e33d43e8052d8a8edfa0e52de4529e`, which already has local loader,
memory-manager, and CPU-submodule changes. Results from this diagnostic
build are therefore labeled separately from the normal release checks.

Under that isolated emulator, the repaired files.lua next fails at line 377:
the expected `;end of file\n` is returned with a final CR byte (0D).
The Lua executable is the unmodified v0.2.1 build
`IIgs e026f5b-13178cdf3c75 plain`.

## Focused probe

`tests/ioprobe.lua` creates and removes its own temporary file, testing:

- 4,352 binary bytes containing every possible byte value, seek, and append;
- the restored upstream E1/E7 fixtures;
- fresh text files through counted, whole-file, and line reads, including
  whole/count reads after a line read;
- repeated EOF reads and seek recovery.

Truncating an existing BIN file does not necessarily reset its GS/OS file
type. The probe deletes its temporary file before creating a new text
fixture, so the earlier binary phase cannot conceal text-file behavior.

With the isolated emulator, IOPROBE 1 completes 38 checks with four failures:

```text
expected : 41 0A 42 0A
disk rb/a: 41 0D 42 0D
text r/a : 41 0D 42 0D
text r/4 : 41 0D 42 0D
text r/L : 41 0A 42 0A
line then a: 42 0D
line then 2: 42 0D
```

The four failures concern logical newline consistency in counted/all reads;
the binary, byte-fixture, line-read, and EOF checks pass. Here `disk rb/a`
means bytes observed through the IIgs binary stream, not an independent
inspection of the Mac host file. At this stage there was no hardware
result; the follow-up below establishes that these differences do not
occur in the tested hardware setup. The probe reports all differences; its
completion line alone is not a pass when `failures` is nonzero.

## Initial hardware step

The stable NAS archive contains this probe as TEST.LUA and the unchanged
hardware-tested LUATEST from the math investigation. Repeat:

```text
yankit xvf /nas/lua.test/test.shk
15:luatest -E -v test.lua
```

Expect the `IOPROBE 1` banner. Capture the hexadecimal text results, any
FAIL lines, final counts, and shell return. Do not classify files.lua as
passing or alter its expected-failure status until the remaining issues
are resolved. The full script also contains OS/date/large-file sections
that this focused probe does not certify.

## Hardware result: all 38 checks pass

The supplied photograph identifies `IIgs aa385d7-13178cdf3c75 plain` and
`IOPROBE 1 DONE checks=38 failures=0`, followed by a shell prompt. All text
read modes and the binary view contain LF (0A), including reads after a
line read. Binary roundtrip/seek/append, restored E1/E7 fixtures, repeated
EOF reads, and seek recovery pass too. Record one complete probe run on
the existing accelerated ROM 03 / 8 MB hardware.

Thus the locally observed CR mismatch and EOF abort are not reproduced by
this probe on hardware. Do not change Lua to compensate for those emulator
behaviors. The two legacy files.lua branches expecting CR on the IIgs were
restored to the upstream LF assertions; no additional assertions were removed.

## Next step: broader file test

FILECHECK 2 runs the repaired files.lua with upstream `_port=true` and
`_soft=true`. Its banner explicitly reports exclusion of Unix process tests,
nonportable date cases, and the large-file block. Other file operations,
buffering checks, and portable date/time tests remain active. TEST.LUA is
the driver; FILEFIX.LUA is an exact renamed copy of the repository test so
the user's existing FILES.LUA is preserved. LUATEST remains unchanged.

For preflight only, the isolated emulator was additionally changed to
disable regular-file `crlf` translation in GSOS/Open.cpp (both open paths)
and GSOS/SetFileInfo.cpp. Standard-stream translation remains enabled. This
matches the bytes seen in the hardware probe; it is not a change to the
installed emulator or proof of broader hardware behavior. With these
diagnostic changes, FILECHECK 2 reaches the buffering block and fails at
line 683: the separate reader sees output before the explicitly fully
buffered writer closes. That observation still needs hardware comparison.

Use the same extraction and execution commands above. Expect `FILECHECK 2`
and capture any assertion with its preceding section heading. A completed
run ends with `FILECHECK 2 FINISHED - expect shell prompt next`; its explicit
skips must remain part of the result, rather than claiming full upstream
coverage. No broader hardware pass has been recorded yet.
