# Build-system replacement: validation record

Date: 2026-09-24. Branch `codex/build-system`, based on `master` at
`52d780b`, which already includes the `codex/transfer-validation` work
(PR #18).

Every result here comes from the development Mac under GoldenGate. **None
is a hardware result.** The new executables have not run on the IIgs. The
earlier hardware passes remain attached to the exact executables they
tested (the v0.2.1 release and the kits recorded in
[HARDWARE_RESULTS](../HARDWARE_RESULTS.md)).

## Environment

| Item | Value |
| --- | --- |
| ORCA/C | 2.2.1 (repository-local SDK, selected through the primary worktree) |
| Emulator | GoldenGate `iix` 2.1.0 (compiled Sep 16 2025) |
| Packaging | AppleCommander `acx` 13.0, CiderPress II `cp2` 1.2.1-dev2, `nulib2` |
| Python | 3.9.6 (system) and 3.14.6, both used |
| Toolchain fingerprint | `e5de3e21c50190b3` (hashes in [build-manifest.json](build-manifest.json)) |

## Runtime behavior preserved: v0.2.1 reproduced byte for byte

`src/` has not changed since the v0.2.1 commit `e026f5b`, apart from this
branch's two edits:

- the `ldo.c` fix;
- `luaconf.h` including the generated `parseconf.h`, and `llex.c`
  including it too.

To check the effect of the new recipe and those edits on existing
products, the new build system rebuilt everything with the v0.2.1 banner
label:

```sh
make identify BUILD_LABEL="IIgs e026f5b-13178cdf3c75" COMPARE_RELEASE=<v0.2.1 download>
```

| Release executable | SHA-256 (release) | Rebuilt |
| --- | --- | --- |
| LUA | `431a82d763f25dfc…` | identical |
| LUAC | `a21493e2793b7714…` | identical |
| LUATRACE | `76c854ebef118e5c…` | identical |
| IIGSHOST | `4d8a7695f6a3accd…` | identical |

See [v0.2.1-release-comparison.json](v0.2.1-release-comparison.json) and
[v0.2.1-label-build-manifest.json](v0.2.1-label-build-manifest.json).
This shows three things:

- The historical compile flags, unit list, and link order are preserved.
- Propagating the configuration through `luaconf.h` does not change
  full-build code.
- The `ldo.c` fix does not affect parser-enabled builds.

It also demonstrates byte-for-byte reproducibility of these four
executables with this toolchain. No broader reproducibility claim is made.

## Final identified build

`make kit` on the committed tree produced build **`63eca55c48e5`**, from
directory `63eca55c48e5-20260924T231837Z` at commit `cad7d14`, with inputs
matching the commit. The default banners are `IIgs 63eca55c48e5 plain`,
`small`, and `trace`. See [build-manifest.json](build-manifest.json).

| Executable | Bytes | SHA-256 prefix |
| --- | ---: | --- |
| lua | 362,344 | `2bd98bff0bd81822` |
| luasmall | 309,037 | `a7f277060f091a00` |
| luac | 370,941 | `a21493e2793b7714` (= v0.2.1) |
| luatrace | 364,126 | `0af1fa9ef6a509c4` |
| lua.lib | 524,380 | `aee7320b44c925ef` |
| luasmall.lib | 412,143 | `51673dc2ba427d2c` |
| iigshost | 355,241 | `4d8a7695f6a3accd` (= v0.2.1) |

The manifest compares the build with the two earlier builds of the same ID:

- **The v0.2.1-label build (compiled serially, before concurrency was verified):** 26 artifacts identical
  and 8 different. All 8 carry the banner: three executables, their link
  maps, and two shipped `parseconf.h` headers. Every other object,
  library, and host matched, even though this build used 8-way parallel
  compiles.
- **A default-label build made earlier from commit `2ba655f`:** 34 of 34
  artifacts identical. That commit differs only in manifest-writing code.
  Its manifest recorded the version line instead of the banner, and was
  corrected by `cad7d14`.

Package identity changed with that readme correction (`efddcaae03d8` →
`5039793fa25b`), but the build, the executables, and the kit identities
did not. This is the intended separation between executable identity and
package/test identity.

## Compact runtime

| | Full | Compact | Saving |
| --- | ---: | ---: | ---: |
| interpreter | 362,344 | 309,037 | 53,307 bytes (14.7%) |
| library | 524,380 | 412,143 | 112,237 bytes (21.4%) |

The `+S` link maps show `luaY_parser`, `luaK_code`, `luaX_next`, and
`luaX_init` absent from `luasmall` and present in `lua`, `luac`, and
`luatrace`. `lcode`, `llex`, and `lparser` are neither compiled nor linked
for the compact configuration.

Before the fix, `f_parser` read an uninitialized `cl` for text input.
Text is now rejected with `attempt to load a text chunk (parser not
included in this build)`, and the test covers `load`, `loadfile`,
`dofile`, `require`, a command-line script, and stdin. `nosource.lua`
passed on the compact runtime in debug and stripped form, and on full Lua
(where text loads). Bytecode acceptance, including which tests need the
parser or debug information, is in [COMPACT.md](../../../tests/COMPACT.md).

## Local regression

[test-report.json](test-report.json) records 59 of 59 checks, 13 with
intentional skips (test identity `ccd763851463`):

| Group | Result |
| --- | --- |
| unit | 45 Python tests passed |
| targeted | 16/16 on `lua` (skips: T harness, `0^0`, >64k programs) |
| luac | hwsmoke, numconv, nosource as debug and stripped bytecode on both runtimes; syntax error and 500-level nesting rejected cleanly; valid compile afterward |
| compact | 15 debug and 7 stripped chunks on `luasmall`; script, stdin, and `load` source rejected; works afterward |
| hosts | iigshost (100 yields), allocfail (one expected degradation), bridge demo, bridge cstack, mmtest; memfree built only |

[test-report-trace.json](test-report-trace.json): the 16 targeted scripts
passed on `luatrace` with the trace contracts (state closure, and MM
activation for `mmalloc`).

`make suite GROUP=runtime` passed 15 tests. `GROUP=io` still fails on stock
GoldenGate, as documented; the failure propagated as a nonzero `make`
exit.

## Build system

`make test-build`, 48 checks on a private copy of the tree, all passed:

- The libraries build independently, without any interpreter build.
- Clean builds of every configuration succeed, and a repeated build
  compiles nothing.
- Switching configurations six times compiles nothing, and outputs stay
  identical.
- A source edit recompiles one unit. A header edit recompiles exactly its
  18 dependents. A modified SDK copy discards and rebuilds the
  configuration, and switching back rebuilds again.
- `make -j8` from clean, and two concurrent `make` processes, give
  identical outputs.
- A compile error, and an unresolved link, both fail `make`. They remove
  the failed object, the stale executable, and ORCA's truncated link
  output, and leave no partial files.
- Bytecode and compact checks pass.
- Packaging an identified build does not recreate `build/dev`. A
  corrupted image member is detected, and a tampered identified build is
  refused.
- `make clean` removes only disposable and legacy in-tree outputs, and
  preserves evidence directories and tracked files. `make clean-legacy`
  archives the old loose outputs.

`make verify-concurrency` gave 33 outputs byte-identical across one serial
and two 8-way parallel builds, with a read-only temporary directory (ORCA
prefix `14:`) and no writes to it. See
[concurrency.json](concurrency.json).

## Packages and hardware kits (prepared, not run on hardware)

[package-manifest.json](package-manifest.json) and
[package-sha256.txt](package-sha256.txt) cover seven packages: runtime,
small, compiler, trace, library, library-small, and host. Each was
verified by extraction and `cp2` metadata readback. The manifest cites the
test report above.

| Kit | GoldenGate preflight | Manifest |
| --- | --- | --- |
| suite (`GROUP=full`, preflight `runtime`) | passed | [kit-suite-manifest.json](kit-suite-manifest.json) |
| small (compact) | passed: banner, source rejection, compact and stripped groups | [kit-small-manifest.json](kit-small-manifest.json) |
| luac | passed: LUACPROBE 1, all 15 steps | [kit-luac-manifest.json](kit-luac-manifest.json) |
| host | passed: HOSTCHECK 1 | [kit-host-manifest.json](kit-host-manifest.json) |

The command lines of the generated LUAC and HOSTCHECK batches are
byte-identical to those of the batches validated on hardware; only the
comment title differs. Nothing was staged to the NAS, and no release was
published.

## Needs real hardware

- Every new executable in build `63eca55c48e5`. `luac` and `iigshost` are
  byte-identical to v0.2.1, so their recorded v0.2.1 hardware evidence
  applies to those bytes. `lua`, `luatrace`, and `luasmall` are new bytes.
- The compact runtime as a whole. No parser-free executable has ever run
  on the IIgs. Its first run should use `KIT=small`, noting that
  `tableovf` previously took about 18 minutes silently.
- The generated `TEST` batches as ORCA batch files. Their command
  structure is proven, but the new compact batch and the suite `TEST`
  wrapper have not been executed by the ORCA shell.
- The I/O group on stock GoldenGate, which remains an expected local
  failure; hardware results for it exist only for the earlier kits.

## Hardware follow-up: compact kit, first run (user photograph)

The first compact-kit run, from `/nas/lua.test/test.shk` with `20:test`,
used build `63eca55c48e5` on the accelerated ROM 03 IIgs.

- **Passed:** 1/15 `nosource`, 2/15 `numconv`, and 3/15 `sieve`, which
  caught `C stack overflow` at `chain=40`.
- **Failed:** 4/15 `coroutine`, in "testing yields inside metamethods",
  with `coroutine.lua:881: assertion failed!`. The shell prompt then
  returned normally. The driver stops at the first failure, so tests
  5–15 and the stripped group did not run. No crash or screen corruption
  was reported.

Line 881 is `assert(run(function () return a ^ b end, {"pow"}) == 10^12)`.
`luac` folds `10^12` into the float constant `1000000000000.0` at compile
time, and this kit's bytecode was compiled under GoldenGate. `a ^ b` is
computed by the IIgs's SANE `pow` at run time.

The same line passed on hardware when the suite ran from source, because
both sides were then computed on the IIgs. It also passes under
GoldenGate. The working hypothesis is therefore a difference between
GoldenGate's host-precision `pow` and the real SANE `pow` for `10^12`. That
would make it a property of cross-compiled bytecode, not a
compact-runtime defect.

To test the hypothesis, POWPROBE 1 is staged at `/nas/lua.pow/test.shk`
(kit manifest in `build/diagnostics/*-powprobe1-*`). It prints run-time
versus folded results for five powers, three ways: full Lua from source,
full Lua from the GoldenGate-compiled bytecode, and compact Lua from the
same bytecode. Result pending.
