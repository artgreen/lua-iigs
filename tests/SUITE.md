# Repeatable IIgs regression suite

This suite collects the 23 Lua regressions used during hardware validation.
It uses an existing interpreter without rebuilding it. The default `full`
group runs every script in one Lua state, stops at the first failure, and
prints per-test results followed by a summary. Intermediate scripts may say
"expect shell prompt next"; only the final suite summary ends the run.

The manifest is [suite.json](suite.json); the driver is [suite.lua](suite.lua).
The packaging tool generates `SUITECFG.LUA` from that manifest and installs
the driver as the stable `TEST.LUA` entry point. There are no numbered test
filenames to retype when updating a kit.

The full group has completed twice on the recorded accelerated ROM03 IIgs
with 8 MB RAM: each run passed 23 adapted tests, eight with intentional
skips, and returned to the shell prompt. The user confirmed that the second
run followed a complete power-off/on, establishing one cold-start pass.
See the [hardware record](../docs/validation/2026-09-24/README.md#full-suite-passes-on-the-iigs)
for the tested artifact and evidence boundaries.

## Run on hardware

Prepare a kit from an identified build, a published release, or explicit
existing executables. None of these is rebuilt:

```sh
make hardware-suite BUILD=<build id>
make hardware-suite RELEASE=build/release-v0.2.1-download
make hardware-suite EXES="lua=path/to/validated/lua"
```

The kit is `TEST.SHK` (plus `TEST.po`). It contains:

- `LUATEST`;
- all 23 scripts and `TRACEGC.LUA`;
- the driver as `TEST.LUA` and its generated `SUITECFG.LUA`;
- a `TEST` ORCA EXEC batch that runs the chosen group (`GROUP=full` by
  default);
- a readme and license.

Archive extraction preserves EXE `$B5` / aux `$0000` and SRC `$B0` /
`$0006`. Stage the kit with `make stage` (see
[building](../docs/BUILDING.md#transfer)). Then, after the current test has
returned to the shell:

```text
yankit xvf /nas/lua.test/test.shk
20:test
```

`20:` is the confirmed executable prefix in this ORCA shell setup; kits
for other setups are generated with `PREFIX=`. The batch runs
`20:luatest -E -v test.lua full`, so another group can be run directly:

```text
20:luatest -E -v test.lua io
```

Extract and run in the test directory. Future kits reuse these names. The
two recorded full-suite passes used the earlier `SUITE.SHK` layout (same
`LUATEST`, driver, and scripts, with no `TEST` batch), launched with
`20:luatest -E -v test.lua`.

The default run ends with:

```text
SUITE COMPLETE group=full passed=23 failed=0 with_skips=8
Expect shell prompt next
#
```

The recorded local run had eight scripts with intentional skips; the driver
counts what it actually observes. `passed` means the selected adapted script
completed, not that its skipped sections ran. Any error, missing completion,
missing test, crash, or missing shell return is an unsuccessful run. Tests
after a failure are **not run**; fix/investigate it and restart the group.
Observe and record the build banner, final summary, skips, and shell return.

`tableovf` previously took about **18 minutes** on the accelerated IIgs and
is silent until completion. It is last in `full`; allow additional time for
the other tests. There is no hardware timeout or total runtime promise.

To select a smaller group, append its name: `20:luatest -E -v test.lua io`.

| Group | Tests | Coverage |
| --- | ---: | --- |
| `smoke` | 2 | Smoke and 90 numeric-conversion checks |
| `acceptance` | 4 | Smoke, conversions, adapted math, portable file/date checks |
| `runtime` | 15 | All former targeted checks except the long table-overflow test |
| `io` | 7 | Focused bytes/EOF, sharing observations, adapted files, large offsets, large transfers, source/bytecode, file lifetime |
| `stress` | 1 | Table growth/overflow, data retention and collection |
| `full` | 23 | Runtime + I/O + stress, without duplicate tests |

For warm-session repeatability, rerun the same command after `#` returns.
Each invocation creates a fresh Lua state; individual scripts within one
invocation share a state. For cold-start validation, power-cycle first.
After a crash or screen corruption, power-cycle before continuing.

## Local execution and packaging

```sh
make suite GROUP=runtime
make suite BUILD=<build id> GROUP=runtime
make suite EXE=/path/to/lua GROUP=smoke
TEST_LUA=build/dev/lua/out/lua python3 -m unittest discover -s tests -p 'test_suite_checks.py'
```

`make suite` copies the executable and scripts into a fresh
`build/test-runs/suite-*` directory, runs the suite with `-E -v` and
`--memcheck`, and saves `suite.log` plus a JSON report. It passes only
with all of these:

- zero exit status;
- ordered completion of every test;
- a matching summary;
- no recognized corruption or failure output.

Logs are kept even on timeout. `TIMEOUT` is a whole-run local limit in
seconds (default 1800), not a hardware deadline.

`make hardware-suite` needs `acx`, `cp2`, and `nulib2`, and writes to
`build/hardware-suites/<utc>-suite-<id>/package/`. Before packaging it
preflights the runtime group in GoldenGate (`PREFLIGHT=none` skips this).
It compares every extracted member with its input and checks each file
type. Text gets native CR line endings, while executable bytes stay
unchanged. `KIT-MANIFEST.json` records the source, transfer, executable,
batch, and archive hashes, plus the preflight result, with the hardware
result left pending. Packaging does not validate the executable on
hardware. The tool neither publishes a release nor copies to the NAS on
its own (`make stage` does that on request).

**Stock GoldenGate cannot pass the complete I/O group:** its repeated-EOF
abort and text translation differ from the recorded real IIgs. The suite
does not hide these failures or automatically skip I/O. Use `runtime` for
the supported stock-emulator subset. Full local preflight used the explicitly
selected diagnostic emulator described in the
[I/O investigation](../docs/validation/IO_INVESTIGATION.md); it is not a
hardware result or an installed-emulator change.

## Scope and maintenance

- `files` enables portable/small-file mode, excluding Unix processes,
  nonportable date cases, and its upstream large-file block. `largefile` and
  `bigio` separately cover the binary boundaries we tested.
- `bufprobe` verifies final data and prints sharing observations. Zero errors
  does not establish that readers can see an open writer's buffer.
- Coroutine tests still skip the unavailable upstream `T` harness. Math
  retains the documented IIgs `0^0` adaptation and random precision limits.
- The runner calls each chunk directly, avoiding extra native-stack frames
  from `pcall`/`dofile`. It restores globals, standard library members, standard
  input/output, and GC mode between successful cases. It is not a sandbox or
  a substitute for independent-process testing with `tools/run-tests.py`.
- Native embedding/C-hook tests, allocator fault injection, raw Memory
  Manager probes, and the separate LUAC executable are covered by
  `make test` (locally) and the `host`/`luac` kits. They require separately built executables; a Lua
  suite pass does not claim their coverage. See [C/build checks](README.md#c-and-build-checks).
  The [standalone LUAC batch](LUAC_TESTING.md) provides the hardware
  compiler checks with one launch command.
  The [native host batch](HOST_TESTING.md) covers C embedding and native
  C-hook yield/resume, followed by a fresh interpreter smoke run.
- Earlier one-off beacon and numeric localization probes remain historical
  evidence; their maintained regression coverage is represented here by the
  canonical tests, rather than duplicated diagnostic packages.

When adding a regression, add its script and strict Lua-pattern completion
contract to `suite.json`, include it in the appropriate group and `full`,
then run the group and runner checks. Printed completion alone is insufficient:
the script must also return normally. Keep explicit skips in the output and
update the count/scope documentation. Newly combined runs need hardware
confirmation even when the individual tests previously passed.
