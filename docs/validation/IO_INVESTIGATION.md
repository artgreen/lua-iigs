# File I/O investigation, 2026-09-23

Status: test-fixture defects repaired; the full test still fails locally.
Hardware confirmation of the focused I/O probe is pending. No Lua runtime
I/O change is included in this investigation, and v0.2.1 is unchanged.

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
IIgs adaptations. Existing platform-specific assertions otherwise remain.

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
inspection of the Mac host file. No result yet establishes whether the
same behavior occurs on real hardware or identifies the responsible C
library routine. The probe reports all differences and continues; its
completion line alone is not a pass when `failures` is nonzero.

## Hardware step

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
