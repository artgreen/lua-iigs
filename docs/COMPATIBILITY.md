# Compatibility and limits

## Platform

Lua runs as an ORCA shell EXE. It is not a Finder application, NDA, system
tool set, or boot disk. The tested hardware is an accelerated ROM 03 IIgs
with 8 MB RAM. Other hardware configurations need their own validation.

## Language and libraries

The base is Lua 5.4.6. `_VERSION` reports `Lua (IIgs) 5.4`.
Lua integers are 32-bit signed `long`; floating point is the 10-byte SANE
`long double` representation. Native C `int` is 16 bits.

The standard interpreter has the source parser and interactive prompt.
The compact interpreter omits the parser and rejects text chunks.
The `utf8` library is not built or registered by default (its source is
retained). Native dynamic-library loading and `io.popen` are unsupported.
Link C modules into a host and register them with `luaL_requiref`.
Pure Lua modules use `?.lua;?/init.lua` by default.

## Resource limits

- The executable requests 24,832 bytes of bank-0 native stack. Additional
  general RAM does not enlarge that stack. Deep C calls and nested coroutine
  resumes can return `C stack overflow` at modest depths.
- Lua's stack is capped at 15,000 slots.
- Table arrays are capped at 32,768 slots and hash parts at 16,384 nodes.
  A sequential append regression retained 49,152 entries; that is not a
  universal capacity guarantee for other table shapes.
- Some string operations, references, parser counters, and instruction
  operands have 16-bit bounds. Do not infer a universal string or program
  size limit from a single test.

See [internals](INTERNALS.md) for the protections and allocator behavior.

## Numbers and bytecode

Bytecode depends on the integer, floating-point, and instruction formats.
Use compatible IIgs builds of `luac` or `string.dump`; desktop Lua 5.4
bytecode is not an interchange format. Transfer chunks as binary.

GoldenGate folds floating-point constants using host-double precision;
hardware uses SANE extended precision. A GoldenGate-compiled `10/12` can
compare unequal to the same division at runtime on the IIgs. Compile on
the IIgs for hardware arithmetic, or avoid exact floating-point equality.
This applies to both full and compact runtimes.

On the tested IIgs, `0^0` returns NaN; GoldenGate returns 1. The adapted
math suite skips this comparison. Random floating-point output is capped
at 53 generated bits; other arithmetic is not reduced to that precision.
The minimum-float-to-integer conversion workaround from distribution 0.2.1
is retained, including correct conversion of `-2147483648.0`.

## Files and testing boundaries

The tested ORCA runtime refuses a reader while a writer has the same file
open, even after flush. Adapted tests check data after close and reopen.
Two simultaneous readers worked. Stock GoldenGate differs from hardware
in repeated-EOF handling and text newline translation, so `files.lua`
remains a known local failure despite the adapted hardware pass.

The upstream `T` C API harness is absent. Some inherited tests are scaled,
skipped, or no-ops; passing them is not a complete upstream-suite pass.
Unix process behavior and nonportable date cases are excluded. Binary I/O
through 262,163 bytes was tested using small transfers; that does not
establish arbitrary single-transfer or string sizes.

See [validation](VALIDATION.md) and the [test guide](../tests/README.md).
