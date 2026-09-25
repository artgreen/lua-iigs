# Compact (parser-free) runtime testing

The `lua-small` configuration builds Lua with `LUA_NO_PARSER`:

- Its interpreter (`luasmall`) and library (`luasmall.lib`) contain no
  lexer, parser, or code generator. `lcode`, `llex`, and `lparser` are
  neither compiled nor linked, and the link map is checked for the parser
  entry points.
- It runs precompiled bytecode produced by `luac` from the **same build**.
- Every text chunk is refused with an ordinary, catchable error:

  ```text
  attempt to load a text chunk (parser not included in this build)
  ```

  That applies to `load`, `loadfile`, `dofile`, `require` of a source
  module, a script named on the command line, and source on stdin. The
  interpreter keeps working afterward.
- `-e` and the interactive REPL are unavailable, as before.

The upstream suite is written in source and uses `load` on text heavily, so
it cannot run unchanged on this runtime. The acceptance path instead compiles
the scripts with `luac`, in both debug and stripped (`luac -s`) forms, and
runs the ones that do not inherently need the parser. The plan is data in
[compact.json](compact.json). The parser-free and debug-info-free
classifications there are measured results, not guesses.

## Runtime fix

With `LUA_NO_PARSER`, `f_parser` in `src/ldo.c` previously fell through for
text input and read the uninitialized closure pointer `cl`. It now raises
the syntax error above before `cl` can be used. Parser-enabled builds
compile the same statements in the same order. Rebuilt with the v0.2.1
banner, the full, trace, compiler, and host executables are byte-identical
to the v0.2.1 release (see [building](../docs/BUILDING.md#reproducibility)).

## Local checks

```sh
make test CHECKS="luac compact"
make test CONFIG=lua-small
```

Both run the same checks, all under GoldenGate `--memcheck`:

- `nosource` (a new test) in debug and stripped form. On the compact
  runtime it checks rejection through `load(text)`, mode `t`, mode `b`,
  `loadfile`, and `dofile`. It repeats the rejections 60 times, inside and
  outside coroutines, with a memory check. It then runs a
  `string.dump`/`load(binary)` round trip, tables, metatables, coroutines,
  and GC. On full Lua the same script confirms that text still loads
  (`parser=yes`).
- The debug-bytecode group, 15 chunks: nosource, numconv, sieve,
  coroutine, cobeacon, cstack, hookyield, mmalloc, events, verybig,
  bufprobe, largefile, bigio, filelife, and tableovf.
- The stripped group, 7 chunks: nosource, numconv, sieve, cstack, mmalloc,
  events, and verybig.
- A source script and source on stdin are both rejected, with nonzero
  status and no execution. `nosource.lua cli <status>` verifies the
  captured rejection, and a following bytecode run proves the runtime
  still works.
- LUAC debug and stripped bytecode for `hwsmoke` (full runtime), and for
  `numconv` and `nosource` (both runtimes).

Result on 2026-09-24: every check passed (see the
[validation record](../docs/validation/2026-09-24-build-system/README.md)).

## Tests that need the parser

These cannot pass on a parser-free runtime:

| Test | Reason |
| --- | --- |
| hwsmoke | round-trips a text chunk |
| math | builds numeric literals with `load(text)` |
| pm | `dostring()` evaluates generated source |
| hwdiag2 | compiles large constant tables from generated source |
| hwtest | checks that a valid text chunk compiles |
| errors | checks parser error messages |
| bytefile | generates and compiles a 9,000-statement chunk |

These fail for reasons unrelated to the parser: `ioprobe` and `files` hit
the stock GoldenGate EOF abort on both runtimes. Among the other upstream
scripts:

- `attrib`, `big`, `bitwise`, `calls`, `constructs`, `db`, `gc`, `goto`,
  `locals`, `sort`, `strings`, and `vararg` load text.
- `literals` also fails as precompiled bytecode on the *full* runtime,
  because of a string-sharing check.
- `api`, `bwcoercion`, `closure`, `code`, `gengc`, `heavy`, `main`,
  `nextvar`, and `tpack` complete as bytecode. `api`, `code`, and `main`
  return early.

These fail in stripped form on **both** runtimes, because they check line
numbers, names, or tracebacks: coroutine, cobeacon, hookyield, errors, and
hwtest.

## Hardware kit

```sh
make hardware-suite BUILD=<id> KIT=small
```

The kit contains:

- `LUATEST`, the compact interpreter, and `LUACTEST`, the same build's
  compiler.
- The test sources as text `*.LUA`. The batch compiles them **on the
  IIgs** into `*.LUO` (debug) and `*.LUS` (stripped).
- `TEST.LUA` (the suite driver) and `SUITECFG.LUA`, as host-compiled
  bytecode (BIN `$06`). The kit builder checks that both contain no
  floating-point constants.
- `SOURCE.LUA`, which the compact runtime must reject.

The test chunks are compiled on the IIgs because host compilation changes
the constants they contain. The first hardware run, with chunks compiled
under GoldenGate, failed `coroutine.lua:881`, which is
`a / b == 10/12`. `luac` folds `10/12` at compile time, and GoldenGate's
SANE emulation computes it at 53-bit host-double precision, while the
IIgs computes `a / b` at 64-bit extended precision. POWPROBE 1 confirmed
this on hardware:

- `10/12` compiled on the IIgs compares equal;
- the GoldenGate-folded constant does not, on full and compact Lua alike;
- integer powers such as `10^12` match everywhere.

This is a property of cross-compiled bytecode, not of the compact runtime
(see [limitations](../docs/LIMITATIONS.md)). Compiling on the target also
exercises `luac` on hardware. The kit's 1600 KB `.po` image is larger than
usual; transfer the `.SHK`.

On the IIgs:

```text
yankit xvf /nas/lua.test/test.shk
20:test
```

The batch runs six steps:

1. Print the banner.
2. Compile 16 debug and 8 stripped chunks with `LUACTEST`.
3. Run `SOURCE.LUA`, capturing its status and messages in `source.log`.
4. Verify the rejection with `nosource.luo`.
5. Run the `compact` group.
6. Run the `stripped` group.

Require both `SUITE COMPLETE` lines and a shell prompt. `tableovf` is in
the debug group and previously took about 18 minutes silently on the full
runtime. No compact executable has been run on real hardware yet, so
every compact result above is an emulator result.
