# Proposed Changes — Lua IIgs Corruption Fix (2026-07-05)

## Executive summary

The years-old "random Lua internal data corruption" was traced to **C stack
overflow on the 65816**, not (primarily) to 16-bit integer assumptions.

Evidence chain:

1. ORCA/C programs get a **4KB bank-0 stack** by default (ORCA/C 2.2 manual);
   this repo set no `#pragma stacksize` anywhere. The manual explicitly warns
   overflow "can result in corrupting memory being used by the operating
   system, tools, or other programs."
2. **GoldenGate quietly launches programs with 16KB instead of 4KB**
   (`InitialLoad(..., 0x4000)` in GoldenGate `bin/orca.cpp`) — why emulation
   always seemed healthier than real hardware.
3. Measured with `iix --memcheck` stack high-water: `strings.lua` needs
   **5.3KB** (already over hardware's 4KB), `errors.lua` needs **30.5KB**,
   ~**820 bytes per nested pcall level**. `LUAI_MAXCCALLS=128` would need
   ~45KB+, so Lua's built-in guard **could never fire before the hardware
   stack ran out**, silently shredding adjacent bank-0 memory. Hence random
   corruption, the string-table crash at exit (`luaS_remove` walking a
   clobbered chain), and the mysterious hangs.
4. Reproducer (before fix): `cstack.lua` under memcheck gave
   `MemCheck: memory altered at 004800` + BRK crash. After fix: clean pass.

Validation after fix: **27/28 suite tests exit 0 with zero memcheck alerts
and zero BRKs**, including `cstack.lua` (previously in the `fails` list) and
`heavy.lua` (previously "corruption per memcheck"). The one failure,
`attrib.lua`, is environmental (missing `tests/libs/` directory, predates
this work).

All Part 1 changes are already applied to the working tree (NOT committed).

---

## Part 1 — Changes applied to the working tree

### 1. Real stack segment — `src/lua.c`, `src/luac.c`

`#pragma stacksize 32512` in both; `main()` records the stack top:

```c
#ifdef LUA_USE_IIGS
  char stackanchor;
  luaE_setcstacktop(&stackanchor, 31488);  /* pragma size minus pre-main slack */
#endif
```

- 32512 = 127×256 (pragma rounds to 256-byte multiples; staying under 32768
  avoids any 16-bit-signed parsing edge).
- 31488 = 32512 − 1024 under-claims deliberately so the computed base never
  lands below the true segment base.

**Knob:** on real hardware a 32KB bank-0 allocation may fail on a loaded
system. For a hardware build consider 24576 in the pragma with 23552 in
`luaE_setcstacktop` — always change the two numbers together.

### 2. Byte-based C-stack guard — `src/lstate.c`, `src/lstate.h`, `src/ldo.c`

The core fix. A count of C calls cannot protect a stack whose frames range
from ~150 bytes (parser) to ~1KB (recursive `gsub` carrying a stack-resident
`luaL_Buffer`): 128 corrupts, and even 48 still corrupted the gsub+metatable
path while breaking `errors.lua`. So the guard is byte-based:

- `luaE_setcstacktop(top, size)` computes two floors from the real segment.
- `luaE_cstacklow(hard)` compares the address of a local against them:
  - **soft floor** (base + 8192): raise catchable `"C stack overflow"` —
    8KB reserved so error-object construction, the message handler, and
    traceback formatting all fit;
  - **hard floor** (base + 2048): throw `LUA_ERRERR` (stock Lua's
    "error while handling error" tier).
- A **grace flag** suppresses repeat soft reports while error handling runs
  below the soft floor (otherwise the message handler's own calls re-trigger
  the probe forever and every overflow degenerates to `LUA_ERRERR` — this
  exact failure was observed). The flag re-arms when the stack recovers
  above the soft floor, or when any protected call catches an error
  (`luaE_cstackrearm()` hook in `luaD_rawrunprotected`). This mirrors stock
  Lua's `MAXCCALLS / 10 * 11` hysteresis.
- Below the hard floor the probe always escalates regardless of the flag
  (first version had a blind spot here; nested-coroutine recovery in
  `cstack.lua` found it).

Both guard call sites (`luaE_incCstack` in lstate.c, `ccall` in ldo.c) use
one macro from lstate.h:

```c
#define luaE_cstackover(L)  (getCcalls(L) >= LUAI_MAXCCALLS || luaE_cstacklow(0))
```

Non-IIgs builds get the stock count-only definition — the diff is
upstream-neutral. If `luaE_setcstacktop` is never called the probe stays
disabled (relevant for the library build; see Part 2 item 4).

### 3. `LUAI_MAXCCALLS` 128 → 200 (stock) — `src/llimits.h`

With the byte probe doing the real protection, the count reverts to its
stock role (parser nesting semantics, vanilla-matching error behavior).

### 4. `LUAL_BUFFERSIZE` 640 → 256 on IIgs — `src/luaconf.h`

`luaL_Buffer` lives on the C stack; the default formula
(`16 * sizeof(void*) * sizeof(lua_Number)`) yields 640 bytes with 4-byte
pointers and the 10-byte SANE `lua_Number`. Recursive string operations paid
that per level. 256 only affects when the buffer spills to heap.

### 5. Platform-realistic test expectation — `tests/errors.lua`

`testrep` uses 25 nesting levels under `_iigs` (was 100). Measured capacity:
~123 levels of cheap constructs (parens), fewer for `{` / `a(` nesting;
100 levels of the heavy constructs cannot fit in a 64KB bank, period. The
500-level "must fail cleanly" half is unchanged and passes — that is the
guard working. Follows the existing `_iigs` convention.

### 6. New calibration script — `tests/stackcal.lua`

`pcall` recursion at a requested depth; combined with memcheck's
"Stack Usage" line it measures bytes-per-level. Useful when retuning for a
hardware build.

---

## Part 2 — Recommended changes NOT yet applied

1. **Commit hygiene**: add `.orca-sdk-2.2.1/`, `build/`, and `src/lua`
   (stray artifact) to `.gitignore`. Suggested commit split: (a) engine fix
   (`src/`), (b) test adjustments (`tests/`).
2. **Stale comments**: `lua.c` pragma comment still says "at
   LUAI_MAXCCALLS=128" — reword ("needs far more") since it's now 200. The
   `llimits.h` IIgs prose sits in a portable file; for upstream cleanliness
   move it to `luaconf.h`.
3. **tests/Makefile**: move `cstack` from `fails :=` to `passes :=`. Also
   `TIMEOUT_EXE := /usr/bin/timeout` doesn't exist on this Mac
   (`brew install coreutils` → `gtimeout`, or drop).
4. **Library build / bridge embedders**: they don't run our `main()`, so the
   probe is disabled there. In `bridge.c` / host programs add the same three
   lines (a `#pragma stacksize`, a local `char anchor`,
   `luaE_setcstacktop(&anchor, size-1024)`) before `luaL_newstate()`,
   or the bridge keeps the old corruption behavior.
5. **Hardware debug build**: for real-IIgs testing compile with
   `#pragma debug 25` (stack-overflow check at each function entry +
   traceback + stack-repair verification) so any residual overflow is a loud
   runtime error, not silent corruption. Too slow for release builds.
6. **README**: update the "String catalog corruption" issue with the
   resolution — collateral damage of stack overflow; the crash at exit was
   `luaS_remove` walking a corrupted hash chain.

---

## Toolchain notes (discovered/changed today)

- `/Library/GoldenGate` had regressed to **ORCA/C 2.1.0**, which cannot
  compile this repo (`inline` etc.). A local SDK with **ORCA/C 2.2.1**
  (bugfix release over 2.2.0) was built at `.orca-sdk-2.2.1/` from GitHub
  release `byteworksinc/ORCA-C` tag `orcac-221`.
- Build/run with `GOLDEN_GATE=$PWD/.orca-sdk-2.2.1`:
  `GOLDEN_GATE=$PWD/.orca-sdk-2.2.1 make lua`
  (`iix --sdk=` only remaps headers, not the compiler — GOLDEN_GATE remaps
  the whole root; see GoldenGate `Platform/Unix.cpp` `FindRoot`).
- A backup of the 2.1.0 files is at `/Library/GoldenGate/.backup-orcac-2.1.0`.
- `iix --memcheck` prints `Stack Usage: N` (bank-0 stack/DP high-water;
  saturates at buffer size; float-using scripts show inflated numbers
  because SANE's direct page sits at the buffer bottom) and
  `MemCheck: memory altered at XXXXXX` for out-of-allocation corruption.

## Round 2 — 16-bit audit findings and fixes (applied same day, later)

Two of three audit agents reported; findings below are verified against the
code and (where marked) by reproducer. All fixes applied to the working tree.

### R2-1. CORRUPTION (reproduced): `luaM_shrinkvector_` 16-bit byte-size multiply — `src/lmem.c`

`cast_sizet((*size) * size_elem)` multiplied int×int in 16 bits before
widening. Every Proto array shrink in `close_func` (end of compiling every
function/chunk) hit it: byte sizes > 32767 wrapped → arrays silently
truncated/freed or spurious LUA_ERRMEM. Thresholds: ~8192 instructions
(4 B each) or ~2979 constants (11 B each) in one function.

**Reproduced before fix**: a script with a 3,100-string table literal
compiled into a corrupted chunk — `attempt to call a nil value (global '?')`
(the constant for `print` was garbage). After fix: loads and runs.
Reproducer preserved at scratchpad `bigconst.lua`; consider adding a suite
test. Note `luac`-compiled chunks sidestep this path (lundump allocates
exact sizes) — explains historically confusing script-size-dependent
failures.

Fix: `cast_sizet(*size) * cast_sizet(size_elem)` (both operands widened
before multiply).

### R2-2. CORRUPTION (port-introduced, reprocible only via C hooks): savedpc const-cast moved the pc by 1 byte — `src/ldebug.c`, `src/ldo.c`

The old workaround `Instruction *spc = (Instruction *)&(ci->u.l.savedpc);
(*spc)--;` reinterpreted the stored 32-bit POINTER VALUE as an integer and
subtracted 1 — moving `savedpc` back one BYTE instead of one 4-byte
Instruction. Consequences: a C count/line hook that yields (lua_yield from
a lua_sethook hook — the classic watchdog pattern) resumed the VM at a
misaligned pc → decoded garbage opcodes → arbitrary corruption. The
luaD_hookcall variant self-cancelled (++ then --) but gave wrong line info
inside call hooks.

Fix: cast the pointer-to-pointer — `Instruction **spc =
(Instruction **)&(ci->u.l.savedpc); (*spc)--;` — so ++/-- is pointer
arithmetic. Cannot be regression-tested from pure Lua (yield-from-hook
needs a C hook; "attempt to yield across a C-call boundary" otherwise);
`tests/hookyield.lua` (new) covers the hookcall roundtrip + line-info
sanity, `db.lua` passes.

### R2-3. CORRUPTION (boundary): `luaM_growaux_` guard bypass at nelems == 32767 — `src/lmem.c`

`if (nelems + 1 <= size)` wraps when nelems == INT_MAX == the growth limit
(MAXARG_Bx = SHRT_MAX = 32767 here), bypassing the "too many opcodes/
constants" error exactly when it should fire, then writing one past the
array (and `fs->pc++` wrapping negative after that). Fix: `if (nelems <
size)` — algebraically identical, overflow-free.

### R2-4. CORRUPTION (hard to reach, port-introduced): growaux doubling overflow with limit=USHRT_MAX — `src/lmem.c`

The port's `unsigned int limit` (needed — vanilla's int limit would have
seen USHRT_MAX as −1) let the parser's Vardesc array (limit 65535) double
16384→"32768"→int-wrap→−32768→clamped to 4 by the MINSIZEARRAY test →
array silently SHRUNK to 4 entries while the caller writes entry 16385.
Requires >16K live local-variable descriptors (~82 nesting levels × 200
locals); the byte stack guard likely trips first, but only coincidentally.
Fix: clamp `limit` to INT_MAX at function entry (also fixes `%d` printing
65535 as −1 in the error message).

### R2-5. CORRUPTION (memory-gated): OP_SETLIST can push the array part past MAXASIZE — `src/ltable.c`

A constructor with ~30K literals plus a multret tail (`{0,0,...,f()}`) can
request an array size up to ~47K. MAXASIZE = 2^15 on this platform and
vanilla has NO check (unreachable on 32/64-bit builds). Beyond 2^15,
numusearray stops counting (elements silently uncounted → undersized
rehash → re-entrant resize on stale pointers) and binsearch's `(i+j)/2`
wraps at 65535 (legal sizes have exactly zero headroom). Fix: explicit
`if (newasize > MAXASIZE) luaG_runerror(L, "table overflow");` at the top
of `luaH_resize` (IIgs-only, mirrors setnodevector's MAXHBITS check).
Needs ≥ ~650KB free to trigger — future-proofing for big-RAM machines.

### R2-6. Hygiene (applied): `rehash` totaluse int→unsigned — `src/ltable.c`

A full 2^15 array part made `totaluse` wrap negative; the final result was
correct only via mod-65536 wraparound on two's-complement. Made unsigned so
correctness is by design, not luck.

### R2-7. Hygiene (applied): f_parser zgetc workaround removed — `src/ldo.c`

The hand-inlined zgetc advanced a LOCAL copy of `z->p` without writing it
back (latent landmine, currently masked because n==0 on first read). The
port already made `Zio.p` non-const in lzio.h, so stock `zgetc(p->z)`
compiles fine. Reverted to vanilla.

### Audit conclusions worth keeping (no code change)

- strt.nuse cannot overflow (growth funnels through the nuse==MAX_INT
  check; cap = 32767 interned short strings, clean error beyond).
- lmod(hash,size) can never use a size inconsistent with a string's
  chain — the historical string-table crash is fully attributed to the
  stack overflow.
- `twoto(15)` (1<<15 signed) is NOT reachable: setnodevector checks
  lsize > MAXHBITS(14) before shifting; crafted binary chunks fail with a
  clean "table overflow".
- Largest safe table: 32,768 array entries (~352KB) + 16,384 hash nodes
  (~384KB); beyond → clean errors (with R2-5 in place).
- GC pacing arithmetic: two minor wrong-result overflows in traversal
  work-counting (lgc.c:565 `2*sizenode` at max table; traverseproto sum
  >32767 wraps) — pacing noise only, NOT fixed (left as-is to minimize
  diff; flag if GC behaves oddly on huge protos).
- Hash quality: hashes and the RNG seed are 16-bit (makeseed keeps 16
  bits of time); distribution/DoS quality, not correctness.
- Every `%d` va_arg call site in the tree passes a genuine int (scanned);
  `%I` correctly takes long. No varargs width mismatches.

## Round 3 — parser/libs audit results and fixes (applied same day, later still)

The third audit agent diagnosed math.random empirically (bit-exact) and
swept llex/lparser/lcode/ldump/lundump/lzio/lauxlib/lstrlib/ltablib/
lbaselib. Fixes applied:

### R3-1. WRONG-RESULT (reproduced, fixed): math.random "extra bits" — `src/lmathlib.c` + `tests/math.lua`

Root cause is an emulator/hardware precision mismatch, not a logic bug:
the build correctly selects the 64-bit `unsigned long long` Rand64 path
with FIGS = LDBL_MANT_DIG = 64 (right for real SANE's 64-bit mantissa),
but **GoldenGate emulates SANE at host-double (53-bit) precision**. The
ull→extended conversion stores full 64-bit significands; when a draw has
leading zero bits, significant bits below 2⁻⁵³ survive normalization in
double, so `t * 2^53 % 1 ~= 0` for ~28% of draws → math.lua:877 assert.
Verified bit-for-bit against seed 1007 draws (agent reproduced target
fraction bits on host as trunc53((h·2³² + l)·2⁻⁶⁴)). On real SANE
hardware the OLD code would have passed this test.

Fix: clamp FIGS to 53 under LUA_USE_IIGS (exact under both GoldenGate
and real SANE; same float-randomness as every double-based Lua), plus
`tests/math.lua` clamps its `randbits` to 53 under `_iigs` (real
hardware probes floatbits=64, but random() now yields 53 mantissa bits —
without the clamp the per-bit statistics loop would spin forever on
hardware). **math.lua now passes end-to-end** — it was on the historic
fails list.

### R3-2. WRONG-RESULT (latent, fixed): luaL_ref 16-bit wrap — `src/lauxlib.c`

`ref = (int)lua_rawlen(L, t) + 1` wraps past 32766 live references in
one registry table → negative/aliased refs silently overwrite unrelated
entries. Needs ~32K refs (~0.5MB) — possible on big-RAM machines. Now
raises "too many references" at the boundary.

### R3-3. Toolchain footgun (fixed): Makefiles default GOLDEN_GATE

The agent found that rebuilding without GOLDEN_GATE silently uses the
system 2.1.0 toolchain: lmathlib fails loudly (19 errors, no log2), but
worse, 2.1.0-era float.h (LDBL_MANT_DIG 53!) would misconfigure a build
that partially succeeds. Both Makefiles now `export GOLDEN_GATE ?=
<repo>/.orca-sdk-2.2.1` when that directory exists (caller override
still wins). Verified: `make lua` with no environment builds with 2.2.1.

### R3-4. Audit conclusions, no code change needed

- lzio.h const removal is sound: nothing writes through `z->p`; the real
  historical "binary string load() failure" was the hand-inlined zgetc
  (fixed in R2-7).
- lundump `loadInt` goes through `loadUnsigned(S, INT_MAX)` which raises
  "integer overflow" on oversized counts — foreign 64-bit-host bytecode
  is REJECTED cleanly (also by header size checks: lua_Integer 8≠4,
  lua_Number 8≠10). No silent truncation.
- The README's "assumes short is smaller than int" instance is the
  vanilla `luaM_growaux_` int limit taking USHRT_MAX (= −1 as 16-bit
  int) from lparser's Vardesc array — the port's unsigned-limit change
  was the right call (now hardened by R2-3/R2-4).
- Platform caps that fail cleanly (verified on target): string.rep/pack
  results capped at 32767 bytes (lstrlib MAXSIZE — could be widened to
  2³¹−1 if ever needed; concat/sub/find/gsub already handle longer
  strings fine); string.byte slices, table.sort/unpack ≥32767 → clean
  errors; source files ≥32767 lines → "chunk has too many lines"; jumps
  ±16383 → "control structure too long".
- Hostile hand-crafted bytecode can still truncate 17/25-bit operand
  decodes (cast_int) — same exposure as stock Lua; load() of untrusted
  binaries is documented-unsafe upstream.

## Round 4 — REAL HARDWARE results and the allocator replacement (2026-07-06)

First runs on a real 8MB IIgs (thanks to hwtest/hwdiag/hwdiag2):

**Confirmed working on hardware:** interning (3000 strings), constant
tables up to 2400, big tables via appends (per hwdiag D40), string ops,
GC, and the byte-based stack guard's early rungs.

**New hardware-only defect found:** allocations above ~32KB obtained
through ORCALib malloc/realloc alias other live memory. Evidence:
- hwdiag const-3200 failed DETERMINISTICALLY across runs at idx 472
  with an internal 'proto'-tagged TValue pointing at the chunk's own
  Proto (21C774 both runs) — i.e. two live objects overlapping, not a
  random stomp. const-2400 (26,400-byte array) passed; const-3200
  (35,200 bytes) failed: the bracket straddles 32,768.
- Collateral stomps hit the bank-0/E1 text pages (80-column screens
  showing alternating-column garbage) and once crashed hard enough to
  reboot into a garbled ROM banner + "Check startup device!".
- GoldenGate cannot reproduce ANY of this: it reimplements the Memory
  Manager natively, so real-MM block placement / SetHandleSize
  fallback paths / address-dependent arithmetic in ORCALib never
  diverge under emulation. (A 65816 emulator runs the same CODE
  identically; only reimplemented tools can differ.)

**Fix applied: hybrid allocator in lauxlib.c (l_alloc).** Lua's
frealloc contract supplies the old size on every call, which makes the
C heap's bookkeeping unnecessary: every block gets a 4-byte header
holding either its Memory Manager Handle or NULL (= C heap block).
- Blocks >= 16KB (MMA_BIG) go straight to NewHandle
  (attrLocked|attrFixed|attrNoSpec, +attrNoCross when they fit in one
  bank), sidestepping ORCALib entirely for the size class where the
  hardware bug lives. Grows are a fresh block + explicit C byte copy
  (large memory model handles bank crossings); shrinks trim in place
  via SetHandleSize.
- Blocks < 16KB stay on ORCALib malloc (suballocated - a first attempt
  that put EVERY tiny block in its own fixed MM handle fragmented the
  address space into "not enough memory" under GG; fixed handles never
  compact). Small blocks fall back to the MM if the C heap is full.
- Define LUA_IIGS_NO_MMALLOC to revert to plain realloc/free.
- build/lua-libcmalloc preserved (pre-allocator binary) for hardware
  A/B comparison.

**Hardware procedure note:** after any corruption event, COLD
POWER-CYCLE before the next run - warm resets carry poisoned memory
and video soft-switch state (observed: garbled ROM boot banner).

**Status:** hybrid allocator passes hwdiag2 + full suite under
GoldenGate; awaiting hardware re-test (cold boot, new build/lua,
run tests/hwdiag2.lua).

## Round 5 — HARDWARE VALIDATED (2026-07-06 evening)

The remaining "instant blow-up" saga, in order of exoneration:
- mmtest.c on hardware: raw MM call sequence PERFECT (errs=0) - the
  hybrid allocator's tool calls were never wrong.
- luac -l: hwdiag2's main chunk is only 171 instructions, so no MM-path
  allocation even occurs during script load - killing the "dies at
  first MM call" theory.
- The real failure: "#pragma stacksize 32512" was too aggressive a
  bank-0 ask on a real system (ORCA/C manual: 32K is possible "often",
  not always). Depending on boot state it either failed the load
  outright ("Memory Manager: Out of memory") or squeezed bank 0 to the
  point of destabilizing the console/system (the garbled-screen
  crashes). Battery-RAM damage from an early crash ("Check startup
  device!") added boot-to-boot variance.

**Fix:** stack request reduced to 24,832 bytes (lua.c pragma +
luaE_setcstacktop(,23808), luac.c pragma). Guard floors scale
automatically. Stack-sensitive tests (errors/cstack/coroutine/hwtest/
hwdiag2) all pass under GG at the smaller size.

**Hardware proof (photo):** luatr24 ran tests/hwdiag2.lua to
completion on the real 8MB IIgs: 133KB/195KB/197KB MM allocations
filled+verified at real addresses (bank-crossing blocks included),
shrinks/disposes clean, "E73 chain caught ok" (stack guard works on
iron), **"E99 DONE fails=0 / ALL DIAGNOSTICS PASSED / [M5] script
done"**. The corruption saga - C-stack overflow, 16-bit int bugs,
ORCALib >32KB heap aliasing, and the oversized bank-0 stack - is
closed end to end.

Tooling added along the way: mmtest.c (raw MM probe), memfree.c
(TotalMem/FreeMem/MaxBlock report), LUA_IIGS_MMTRACE build option
(lifecycle + MM-event tracing to stderr), build/lua-libcmalloc and
build/luatr24 comparison binaries.

Recommended hardware follow-ups: run tests/hwtest.lua for the
self-verifying proof; check the Control Panel battery-RAM settings
(RAM disk size, slots) once more after the earlier corruption events.

## Open items / next investigations

- ~~`math.lua:877`~~ RESOLVED in R3-1 (GoldenGate 53-bit SANE emulation
  vs FIGS=64; clamped to 53). math.lua passes.
- ~~`verybig.lua`~~ RESOLVED: its RK section passes; the ">64k programs"
  half is structurally impossible with 16-bit int (code capped at 32767
  instructions/function, arrays at 2^15) and is now `_iigs`-skipped with
  a message — and thanks to R2-5 the attempt fails cleanly rather than
  corrupting. Suite standing: **every test passes under memcheck except
  files.lua.**
- `files.lua`: the one remaining failure — garbled data on write/read
  round-trips (e.g. reading back gibberish then nil at line 323). Matches
  the historical commit note about io line endings flip-flopping between
  \r and \n: GS/OS/ORCA stdio text-mode translation in liolib paths.
  This is an io-subsystem investigation (liolib.c + ORCALib stdio text
  translation), unrelated to integer widths — good candidate for the
  next session.
- `attrib.lua` RESOLVED: it needs the vanilla suite's scratch dirs
  `tests/libs/` and `tests/libs/P1/` (created; passes with them). Git
  doesn't track empty dirs — add `.gitkeep` files or a `make testdirs`
  step so a fresh clone keeps passing. The test writes scratch files
  into `libs/` at runtime; consider gitignoring `tests/libs/*`.
- Full 16-bit int audit of the engine (in progress).
- **All validation so far is under GoldenGate.** The fix specifically closes
  the emulator/hardware gap (the binary now carries its own stack segment),
  but a run on real hardware — ideally the `#pragma debug 25` build first —
  is the true final test.
