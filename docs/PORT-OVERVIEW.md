# What changed to run Lua on the Apple IIgs

The port keeps Lua 5.4.6's language and execution engine largely intact.
Most of the work adapts it to ORCA/C, the small bank-0 native stack,
16-bit C integers, and the IIgs Memory Manager. The hardest reliability
changes prevent memory corruption and turn resource limits into recoverable
Lua errors.

This review compares every file in `src/` at commit `b2b1d80` with the
[official Lua 5.4.6 archive](https://www.lua.org/ftp/lua-5.4.6.tar.gz).
The archive was verified against the SHA-256 published in the
[Lua download index](https://www.lua.org/ftp/):
`7d5ea1b9cb6aa0b59ca3dde1c6adcb57ef83a1ba8e5432c0ecd06bf439b3ad88`.
The reviewed `src/` tree is identical to release-source commit `e026f5b`
(v0.2.1); later test/documentation work does not change this runtime inventory.

Of upstream's 61 C/header files, **41 differ and 20 are unchanged**.
Of the 41, **22 contain only compiler/segment directives**, and `llimits.h`
adds only an explanatory comment. The remaining 18 contain configuration,
interface, diagnostic, or functional changes. The Unix build is replaced by
the root Makefile and shared build tooling. A `parseconf.h` is generated
for each build configuration, rather than tracked in `src/`. These are file counts, not a measure of risk or
percentage of functionality rewritten.

| Area | Change from base Lua | Why it was needed / visible effect | Main source files |
| --- | --- | --- | --- |
| Target configuration | Added `LUA_USE_IIGS` and conditional IIgs configuration. | Selects the port's types, compiler settings, allocator, stack guards, and optional build paths. | [luaconf.h](../src/luaconf.h) |
| Compiler and memory model | Added ORCA/C `noroot`, `lint -1`, `memorymodel 1`, and named segment directives across the C sources. `lctype.c` uses model 0; debug and I/O segments are marked dynamic. The retained, unbuilt UTF-8 source also uses model 0. | Makes the C sources fit the ORCA compiler/linker and segmented-memory environment. The character-table exception is a retained compiler workaround; its comment does not establish the underlying cause. | Most `src/*.c`; [lctype.c](../src/lctype.c), [ldebug.c](../src/ldebug.c), [liolib.c](../src/liolib.c) |
| Build and static linking | Replaced the Unix build with `iix compile`, `link`, and `makelib`, driven by the root Makefile and `tools/iigsbuild`. Each configuration has its own generated `parseconf.h`, which `luaconf.h` includes, distinguishing interpreter, parser-free interpreter, and compiler builds. Failed compiles, links, and library builds discard partial outputs. The VM object is linked separately from `lua.lib`. | Produces ORCA shell executables and embeddable static libraries using the IIgs toolchain. | [root Makefile](../Makefile), [configs.py](../tools/iigsbuild/configs.py), [luaconf.h](../src/luaconf.h) |
| Numeric representation | Selected 32-bit `long` Lua integers and 10-byte SANE `long double` floats instead of upstream's default `long long`/`double`. | Uses the target's supported numeric types. Lua integers are 32-bit even though native C `int` is 16-bit; bytecode must match this port's representation. | [luaconf.h](../src/luaconf.h) |
| Minimum-integer conversion | Special-cased exact `-2147483648.0` in `lua_numbertointeger`; retained range checks for other values. | Works around the observed hardware conversion to the incorrect positive `0x7fff0000`. Restores boundary comparisons, integer conversion, rounding results, and numeric table lookups. | [luaconf.h](../src/luaconf.h) |
| Random floating-point precision | Capped the random generator's floating-point output at 53 bits. | Keeps generated random values consistent with GoldenGate's narrower SANE emulation. Real hardware still reports a 64-bit significand; this does not reduce all Lua arithmetic to 53 bits. | [lmathlib.c](../src/lmathlib.c) |
| Native stack allocation and embedding | Interpreter and compiler request 24,832 bytes of stack. Added `lua_iigs_initstack()` and require it before state creation; uninitialized hosts receive NULL. | The normal shell stack is too small. Embedders must request the same stack and initialize a long-lived anchor in `main`; having more general RAM does not enlarge bank 0. | [lua.c](../src/lua.c), [luac.c](../src/luac.c), [lua.h](../src/lua.h), [lstate.c](../src/lstate.c), [luaconf.h](../src/luaconf.h) |
| Stack overflow detection and recovery | Added byte-based soft/hard stack floors, a temporary grace period for error handling, and rearming after protected errors. Floors reserve 7,168/4,096 bytes above an estimated stack base after a 1,024-byte startup allowance. | Lua's existing call counter cannot account for widely varying C frame sizes. This reserves room for errors and interrupt activity instead of letting recursion overwrite nearby memory. The margins are empirical. | [lstate.c](../src/lstate.c), [lstate.h](../src/lstate.h), [ldo.c](../src/ldo.c) |
| Coroutine resume protection | Added a separate stack-floor check at `lua_resume`. | Continuation resumes bypass the normal C-call entry check. Deep chains now fail with `C stack overflow` before overrunning the shared native stack. | [ldo.c](../src/ldo.c), [lstate.c](../src/lstate.c) |
| Stack buffer footprint | Reduced the initial `luaL_Buffer` from the upstream formula's 640 bytes on this target to 256 bytes. | Reduces native stack use, especially during recursive string substitutions. Buffers can still grow on the heap. | [luaconf.h](../src/luaconf.h) |
| Large-allocation handling | Replaced the auxiliary library's plain `realloc` allocator with a hybrid: small allocations use the C heap; requests of at least 16,384 bytes prefer raw Memory Manager handles. Each block carries a 4-byte ownership header. Growth allocates/copies/frees; copies support bank crossings. | Avoids the large C-heap allocation path associated with observed real-hardware corruption. Failed growth preserves the old block; failed shrinking retains a larger physical block. A host-supplied custom allocator is not automatically replaced. | [lauxlib.c](../src/lauxlib.c) |
| Memory Manager checks and fallback | Added lazy handle/placement/pattern probes, alternative handle attributes, reserved-bank rejection, and removal of the no-cross-bank restriction for allocations exceeding one bank. If the MM path fails, C-heap fallback is restricted to payloads below 30,000 bytes. | Makes unusable allocation paths fail cleanly. The startup probe checks only a small sample, not every possible allocation. Unvalidated probe handles are deliberately retained rather than risking an invalid disposal. | [lauxlib.c](../src/lauxlib.c) |
| Vector arithmetic | Changed the IIgs growth-limit parameter to unsigned, clamped it to `INT_MAX`, replaced `nelems + 1 <= size` with `nelems < size`, and widened operands before byte-size multiplication when shrinking. | Prevents 16-bit overflow from bypassing bounds or truncating/freeing live arrays. Limit error formatting remains compatible with Lua's formatter. | [lmem.c](../src/lmem.c), [lmem.h](../src/lmem.h) |
| Table bounds and counts | Added an explicit array-resize check against `MAXASIZE` and made the rehash population count unsigned. | Rejects oversized array requests before 16-bit indexing breaks, and correctly counts a full 32,768-slot array. The size formulas themselves were already upstream. | [ltable.c](../src/ltable.c) |
| C API references | Added an `INT_MAX` guard before allocating a new `luaL_ref` reference. | Stops a 16-bit reference number from wrapping and aliasing existing references. Freed reference numbers can still be reused. | [lauxlib.c](../src/lauxlib.c) |
| Debug-hook instruction pointers | Used a pointer-to-pointer cast to update `savedpc` with typed instruction-pointer arithmetic. | Works around ORCA/C's rejection of the original expression while preserving upstream instruction-sized increments/decrements. Also corrects an earlier port workaround that moved by one byte and broke hook/yield execution. | [ldo.c](../src/ldo.c), [ldebug.c](../src/ldebug.c) |
| Input-buffer pointer compatibility | Changed IIgs `Zio.p` from `const char *` to `char *`. | Lets the stock `zgetc` pointer-update macro compile with ORCA/C. The current parser again uses upstream `zgetc`, replacing an earlier incorrect hand-expanded version. | [lzio.h](../src/lzio.h), [ldo.c](../src/ldo.c) |
| Lua module search paths | Defaulted `package.path` to `?.lua;?/init.lua`. | Removes Unix installation directories and the `./` prefix that failed in hardware module-loading tests. The underlying GS/OS/stdio cause remains unproven. Environment or Lua code can override the path. | [luaconf.h](../src/luaconf.h) |
| Standard-library footprint | Removed UTF-8 from automatic library registration and the standard build list; retained its source. | An early size/load-time tradeoff. The distributed interpreter does not provide the standard `utf8` library by default. | [linit.c](../src/linit.c), [src/Makefile](../src/Makefile), [lutf8lib.c](../src/lutf8lib.c) |
| Identification and diagnostics | Changed the version label to `Lua (IIgs)`; added optional build identity, allocator-status API/banner, allocation tracing, and interpreter lifecycle markers. Includes a silent-trace option and an allocator-disable switch. | Makes tested builds identifiable and helps distinguish loading, execution, cleanup, and allocator failures. `mm=untested` before the first probe is normal. These diagnostics are not new Lua language features. | [lua.h](../src/lua.h), [lua.c](../src/lua.c), [lauxlib.c](../src/lauxlib.c), [lauxlib.h](../src/lauxlib.h) |
| Optional parser-free interpreter | Added conditional lexer/parser initialization and code, plus interpreter option/REPL changes controlled by `LUA_NO_PARSER`. Text chunks are rejected with a catchable syntax error (`ldo.c`), and the parser units are omitted from the link. | The `lua-small` build: about 53 KB smaller, runs bytecode compiled by `luac`. A separate product, not the validated default; it is not a claim that the port cannot execute source scripts. | [lua.c](../src/lua.c), [ldo.c](../src/ldo.c), [llex.c](../src/llex.c), [lparser.c](../src/lparser.c), [lstate.c](../src/lstate.c) |
| Optional SYS16 path | Added `LUA_IIGS_BUILD_S16` conditionals for startup/REPL behavior and rejected incompatible compiler/parser-free combinations. | Experimental scaffolding for a different launch environment. Disabled; the validated products are shell EXEs, not completed Finder applications. | [lua.c](../src/lua.c), [luac.c](../src/luac.c), [luaconf.h](../src/luaconf.h) |

Some important IIgs behavior comes from upstream portability code rather
than new patches:

| Behavior | What the comparison establishes |
| --- | --- |
| 15,000 Lua stack slots | Upstream already selects this limit when C `int` is smaller than 32 bits. The added native-stack guards are a separate change. |
| 200 nested C calls | The current value matches upstream. `llimits.h` only adds a comment explaining the additional byte-based guard; an earlier port value of 128 is no longer active. |
| Array/hash limits of 32,768/16,384 | These follow upstream's formulas on a 16-bit target. The port adds a missing resize check and fixes count signedness, rather than introducing those formulas. |
| No dynamic C-module loading or `io.popen` | The configuration uses upstream's unsupported-platform paths. Neither loader nor pipe implementation was rewritten for GS/OS. C modules can be linked into a host. |
| File I/O and text handling | `liolib.c` changes only compiler/segment directives. Recent EOF, newline, sharing, and buffering investigations led to test adaptations, not a replacement I/O implementation. |
| `0^0` on hardware | The math test skips this platform-dependent comparison. The runtime was not patched to force the desktop result. |
| VM, GC, bytecode, and most libraries | `lvm.c`, `lgc.c`, `ldump.c`, `lundump.c`, and most library implementation files change only directives. Bytecode format code stays upstream, although its configured numeric representation differs. |

For completeness, the source-file accounting is:

| Classification | Files |
| --- | --- |
| Functional/configuration/interface/diagnostic changes (18) | `lauxlib.c`, `lauxlib.h`, `ldebug.c`, `ldo.c`, `linit.c`, `llex.c`, `lmathlib.c`, `lmem.c`, `lmem.h`, `lparser.c`, `lstate.c`, `lstate.h`, `ltable.c`, `lua.c`, `lua.h`, `luac.c`, `luaconf.h`, `lzio.h` |
| Compiler/segment directives only (22) | `lapi.c`, `lbaselib.c`, `lcode.c`, `lcorolib.c`, `lctype.c`, `ldblib.c`, `ldump.c`, `lfunc.c`, `lgc.c`, `liolib.c`, `loadlib.c`, `lobject.c`, `lopcodes.c`, `loslib.c`, `lstring.c`, `lstrlib.c`, `ltablib.c`, `ltm.c`, `lundump.c`, `lutf8lib.c`, `lvm.c`, `lzio.c` |
| Comment only (1) | `llimits.h` |
| Unchanged C/header files (20) | `lapi.h`, `lcode.h`, `lctype.h`, `ldebug.h`, `ldo.h`, `lfunc.h`, `lgc.h`, `ljumptab.h`, `llex.h`, `lobject.h`, `lopcodes.h`, `lopnames.h`, `lparser.h`, `lprefix.h`, `lstring.h`, `ltable.h`, `ltm.h`, `lualib.h`, `lundump.h`, `lvm.h` |
| Build files | Replaced `src/Makefile` (now a deprecated forwarder); `parseconf.h` is generated per build rather than tracked; no upstream `src/` files removed. |

The project also adds hardware probes, adapted tests, repeatable suites,
build manifests, and metadata-preserving ProDOS/ShrinkIt packaging outside
the base Lua sources. Those make the port testable and distributable, but
are not interpreter changes. See [tests](../tests/README.md),
[building](BUILDING.md), [embedding](EMBEDDING.md), and the chronological
[hardware evidence](validation/HARDWARE_RESULTS.md) for those supporting
pieces and their validation scope. This document is a static change review;
it does not claim a complete upstream test-suite pass.
