# Standalone LUAC hardware checks

LUACPROBE 1 tests the published standalone compiler with a matching Lua
interpreter. This is separate from the 23-script suite: `bytefile.lua`
tests Lua's compiler/loader APIs, while this batch launches LUAC itself.

All six checks completed once on the recorded accelerated ROM03/8 MB IIgs,
including the corrected ORCA batch and clean shell return. See the
[hardware record](../docs/validation/2026-09-24/README.md#luacprobe-1-passes-on-hardware).

Extract the verified `TEST.SHK` into a dedicated writable test directory:

```text
yankit xvf /nas/lua.test/test.shk
20:test
```

`TEST` is an ORCA EXEC script, file type SRC `$B0`, auxiliary `$0006`.
`20:` is the executable prefix confirmed for the current ORCA shell setup; otherwise launch `test` from
the current directory. The batch invokes `LUACTEST` and `LUATEST` with the
same prefix. These are renamed release executables, with unchanged bytes.
`TEST.LUA` is the phase verifier, not the batch entry point for this kit.
The archive also contains the license and a short readme.

The batch runs six checks:

1. Compile a small program and verify arithmetic, binary constants, and a
   nested closure with three inputs, including closure use after GC.
2. Compile source larger than 64 KiB into debug bytecode, require the binary
   to exceed 64 KiB, and verify its results.
3. Repeat using `-s`; require smaller bytecode, still above 64 KiB, and the
   same correct results.
4. Reject malformed source with nonzero status and the expected diagnostic.
5. Reject excessive parser nesting with nonzero status and `C stack overflow`.
6. Compile another valid program after both errors and verify its results.

Syntax and stack-overflow messages in checks 4–5 are expected. The helper
requires both nonzero status and the intended diagnostic; an unrelated file
error cannot count as a successful rejection. All other nonzero statuses
stop the batch. Generated outputs are removed before compilation, and a
phase-state file prevents skipped/out-of-order phases from producing a pass.
Temporary filenames are the explicit `lc.*` names listed in `luacprobe.lua`;
the test replaces those names and removes them after success. Use a dedicated
directory and retain failed-run files for diagnosis.

Require:

```text
LUACPROBE 1 PASSED checks=6 - expect shell prompt next
#
```

Record the last phase/error if it stops earlier. There is no established
hardware timing estimate. Every phase is announced before it starts.

## Reproduce the kit

From the repository root:

```sh
python3 tools/luac-test-kit.py --release-dir /path/to/release --sdk /path/to/orca-sdk
TEST_LUA=/path/to/lua GOLDEN_GATE=/path/to/orca-sdk \
  python3 -m unittest discover -s tests -p 'test_*checks.py'
```

The release directory must contain `LUA.SHK`, `LUAC.SHK`, and
`RELEASE-MANIFEST.json`. Executables are extracted and checked against the
manifest. No compilation or changes to runtime binaries occur.
`--prefix 20:` selects the hardware executable prefix (the default); use a
different numeric prefix or `--prefix ""` for shell lookup on other setups.
The generated batch contains no semicolons, including in its comment line.

One command sequence generates both the ORCA batch file and local preflight.
Locally, Python launches each IIgs program in GoldenGate, saves diagnostics,
passes expected-error status to the Lua verifier, and checks process results
and completion markers. GoldenGate does not run the ORCA batch itself; batch
launch, variable expansion, and redirection still require hardware testing.
The syntax and SRC/EXEC metadata follow the Byte Works ORCA/Shell 2.0.4
source (`make`, `cmd.asm` BRun/Exit, and `io.asm` ParseIO). `>&` redirects
stderr; `{status}` is saved immediately after each expected error.

Outputs are isolated under `build/diagnostics/luacprobe1-*`: preflight log,
provenance/hashes, metadata inspection, `TEST.po`, and `TEST.SHK`. Every
archive member is extracted and checked; both executable types and the
batch file's SRC/EXEC metadata are verified. The tool does not copy to a NAS
or publish a release. See the [dated evidence](../docs/validation/2026-09-24/README.md#standalone-luacprobe-1).
