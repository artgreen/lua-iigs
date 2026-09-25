# Tests

Run `make test` from the repository root. It checks tooling, 16 targeted
Lua scripts, LUAC, compact bytecode execution, and native hosts under
GoldenGate memory checking. Add `CHECKS="unit targeted luac compact hosts trace"`
to include traced execution. Run `make test-build` for build-system integration.
The tooling-only command is `python3 -m unittest discover -s tests/tooling`.
With `make test`, the tooling group also runs the standalone example programs
under the built interpreter. It checks their results and interactive/file-input
paths; tooling-only runs without `TEST_LUA` skip these emulator-dependent checks.

| Directory | Purpose |
| --- | --- |
| `upstream/` | Imported Lua 5.4 suite with IIgs adaptations; original notice in all.lua |
| `regression/` | IIgs smoke, numeric, allocator, I/O, and recovery checks |
| `native/` | C host, hook yields, allocator fault injection, Memory Manager probes |
| `tooling/` | Python checks for builds, releases, packaging, and completion contracts |
| `hardware/` | Suite manifests, drivers, and hardware acceptance instructions |

Tooling stages Lua sources into a flat scratch directory for IIgs-compatible
names and module lookup. Duplicate names are rejected. Test runs never edit
the source scripts. `tools/run-tests.py` runs individual named tests from
that same staged inventory; `make suite GROUP=runtime` runs the reusable suite.

A pass requires the expected completion markers, successful exit, and no
memory-corruption diagnostics. Skips remain visible. `api.lua` and `code.lua`
need the unavailable upstream `T` harness; `main.lua` skips Unix-shell tests,
and `verybig.lua` skips programs beyond target limits. No complete upstream
suite pass or percentage is claimed.

`files.lua` remains an expected failure under stock GoldenGate due to EOF
and newline behavior. Its adapted hardware pass excludes Unix processes,
nonportable dates, and cross-handle write/read visibility. Focused large-file,
large-transfer, dumped-bytecode, and file-lifetime checks live in regression/
and are separate from the default pass set. See [compatibility](../docs/COMPATIBILITY.md).

The C-host checks cover required stack initialization, native C-hook yields,
recovery, and allocator failure handling. `memfree` is built but requires
real hardware facilities to run. These hosts do not replace Lua's T harness.

Use the [hardware procedure](hardware/PROCEDURE.md),
[suite guide](hardware/SUITE.md), [compact guide](hardware/COMPACT.md),
[compiler guide](hardware/LUAC_TESTING.md), and [host guide](hardware/HOST_TESTING.md).
