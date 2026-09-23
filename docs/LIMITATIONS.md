# Platform limits and outstanding work

The tested target is an ORCA-compatible shell on one accelerated ROM 03
IIgs with 8 MB RAM. Exact system software, accelerator model/speed, and
storage details are not all known. Other hardware and shell configurations
need their own validation. No full upstream-suite pass percentage is claimed.

## Lua and native data types

`src/luaconf.h` enables `LUA_USE_IIGS`. Lua reports `_VERSION` as
`Lua (IIgs) 5.4`, with release 5.4.6 in the command-line banner. Code that
requires the exact string `Lua 5.4` may need adaptation.

The default Lua integer is ORCA/C `long` (32 bits), and `lua_Number` is
`long double` (the 10-byte SANE representation). Native C `int` is 16 bits;
this is why Lua's integer range does not describe every internal counter's
capacity. Lua's stack is capped at 15,000 slots in this configuration.

Bytecode depends on the configured integer, floating-point, and instruction
representations. Use this port's `luac` or `string.dump` with a compatible
interpreter; desktop-generated Lua 5.4 bytecode is not a portable interchange
format. Transfer bytecode as binary, never with text line-ending conversion.
Source scripts are the appropriate format for moving between platforms.

## Memory and recursion

The executable requests 24,832 bytes of bank-0 stack, with byte-based guards
in addition to Lua's C-call counter. Available general RAM does not enlarge
that native stack. Nested C calls and chains of coroutine resumes can reach
a clean `C stack overflow` at modest depths. Many independent coroutines are
a different workload from a deeply nested resume chain.

The array portion of a table is capped at 32,768 slots and the hash portion
at 16,384 nodes in the current 16-bit configuration. The sequential append
regression retained 49,152 entries before rejecting growth. This does not
promise that every table shape can reach that count; memory pressure and
other internal limits can stop growth sooner.

Some string-library operations retain `INT_MAX`-based size limits, and
compiler counts, references, and instruction operands have port-specific
bounds. Do not treat an individual boundary as a universal maximum string
or program size. Error recovery at these boundaries is part of the tests.
The implementation details and allocator fallback limits are in
[CORRUPTION-ANALYSIS.md](CORRUPTION-ANALYSIS.md).

`math.random` limits generated floating-point precision to 53 bits in this
port, even though the target floating-point type has a wider significand.
This keeps that path compatible with the locally tested GoldenGate behavior.

On the tested real IIgs, `0^0` evaluates to NaN; GoldenGate evaluates it to
1. The hardware power probe passed the other 48 comparisons for bases and
exponents from -3 through 3. The adapted math test explicitly skips that
single comparison and uses the generator's 53-bit precision when checking
seeded random floats. These are test adaptations, not interpreter changes.
A later hardware assertion exposed a separate runtime defect: converting the exact
minimum float (-2,147,483,648.0) back to an integer returned +2,147,418,112.
The candidate now returns the exact minimum directly in the IIgs conversion
macro, retaining the existing range checks for all other inputs. The fixed
candidate passed the 33-check probe, 90-check conversion regression, and
complete adapted math test in one real-IIgs run, returning to the shell.
This fix is included in v0.2.1 (v0.2.0 still has the defect); see the
[hardware record](validation/HARDWARE_RESULTS.md).

## Modules and host facilities

Pure Lua modules are found through `?.lua;?/init.lua` by default, relative
to the working directory. `package.path` can be set in Lua; `LUA_PATH_5_4`
or `LUA_PATH` can override it when the interpreter is run without `-E`.

The default IIgs configuration does not enable a native dynamic-library
loader. `package.loadlib` uses the unsupported-loader stub; `.so` entries
in `package.cpath` are inherited defaults, not usable IIgs shared libraries.
Link C modules into a host and register them with `luaL_requiref`; see
[embedding](EMBEDDING.md). `io.popen` is also unsupported in this configuration.
Other OS and file facilities depend on the ORCA runtime and shell; the
repository does not establish full Unix behavior.

The default configuration includes the text parser and builds shell EXE
programs. `LUA_NO_PARSER` and `LUA_IIGS_BUILD_S16` are experimental options,
not the validated distribution configuration. The kit packages EXE files;
it is not a SYS16/Finder-app packaging workflow. No Lua system tool set or
NDA is implemented by this repository.

## Outstanding validation and defects

- **`files.lua` remains an expected failure in the local suite.** The
  duplicate diagnostic read and undefined variable have been removed, and
  the original E1/E7 fixture bytes restored from the verified upstream
  archive. The repaired test exposes GoldenGate's five-read EOF abort.
  With that emulator guard restricted to terminals in an isolated build,
  it reaches a text newline mismatch: counted/whole-file reads return CR
  while line reads return LF. A focused probe reproduces four mismatches
  locally; hardware confirmation and any runtime fix remain pending. See
  [the I/O investigation](validation/IO_INVESTIGATION.md).
- **The upstream `T` C API harness is not supplied.** `api.lua`, `code.lua`,
  and T-dependent sections skip coverage. The focused C-host regression
  checks real C-hook yields, initialization, and selected limits; it does
  not replace that harness.
- **The broader suite includes adaptations and no-op tests.** For example,
  `main.lua` unconditionally skips its Unix-shell tests and `verybig.lua`
  skips programs that cannot fit the 16-bit limits. See the [test guide](../tests/README.md).
- **Additional platform coverage is open.** The preserved build's targeted
  warm/cold runs and mixed-script use do not certify every application,
  allocator pressure scenario, or hardware configuration.

Next, run IOPROBE 1 on hardware using the preserved math-tested interpreter.
It checks binary integrity, the restored fixtures, text read modes, and
repeated EOF reads. Earlier corruption theories and timing estimates remain
history, not established causes of this I/O failure.
