# Testing Lua on a real IIgs

The merged runtime has passed the targeted tests, repeated warm launches,
and a cold-boot follow-up on an accelerated ROM 03 IIgs with 8 MB RAM.
The user also reported successful mixed-script use in the same warm session.
GS/OS was tentatively reported as "6.04"; the exact OS/shell version,
accelerator model/speed, and storage device remain unconfirmed.

[Hardware results](docs/validation/HARDWARE_RESULTS.md) records the observations and exact
historical build identities. The instructions below are for validating a
new build or installation. The completed sequence does not need to be
repeated solely because documentation changed.

## Prepare and transfer

1. Build a verified kit using the [build guide](docs/BUILDING.md). Keep its
   manifest, checksums, and original executable. Do not overwrite a known-good
   installation while testing a changed runtime.
2. Transfer a ProDOS `.po` image or a ShrinkIt `.SHK` archive. The kit images
   are 800 KB transfer disks, not boot disks. Copying a naked executable
   through a NAS may lose its file type; use GS ShrinkIt or a disk-image
   tool that preserves EXE `$B5` / auxiliary `$0000` metadata.
3. Place the interpreter and scripts together in a separate test directory.
   Keep `tracegc.lua` beside `cstack.lua`. Extract the separate `iigshost`
   executable there too. The kit does not package every tool it builds.
4. Power fully off/on before the first validation run, then use your normal
   ORCA-compatible shell. Keep accelerator settings consistent across runs.

Commands below assume the executable is named `lua`. If the kit was built
with a unique test name, substitute that name. Check the banner against
`BUILD.TXT` from the same kit; do not assume the shell selected the right
binary merely because a command named `lua` exists. An earlier failed run
lacked the expected build identifier, while the identified build passed.

## First checks

From the test directory:

```text
lua -E -v
lua -E -v hwsmoke.lua
lua -E -v coroutine.lua
lua -E -v hwdiag2.lua
```

`-E` ignores Lua environment initialization and module-path settings.
`-v` prints the Lua version, the kit's build ID, and allocator status. Normal
Makefile builds lack the kit's unique ID; use an identified kit for comparison.

| Script | Required result |
| --- | --- |
| `hwsmoke.lua` | `SMOKE DONE - expect shell prompt next` |
| `coroutine.lua` | `OK`; upstream C API harness skip notices are expected |
| `hwdiag2.lua` | `E99 DONE fails=0` and `ALL DIAGNOSTICS PASSED` |

Every command must also return to a usable shell prompt, shown as `#` in
the recorded sessions. A printed success line alone does not establish clean
shutdown. After screen corruption, a crash, or an interrupted suspect run,
power-cycle before continuing.

## Allocation, stack, and C-host checks

```text
lua -E -v mmalloc.lua
lua -E -v tableovf.lua
lua -E -v hwtest.lua
lua -E -v cstack.lua
lua -E -v sieve.lua
lua -E -v pm.lua
iigshost
```

| Test | Expected completion |
| --- | --- |
| `mmalloc.lua` | `MMALLOC PASSED` |
| `tableovf.lua` | `TABLEOVF PASSED entries=49152` on the recorded build |
| `hwtest.lua` | 19 passed, 0 failed, 1 skipped; `HWTEST PASSED WITH SKIPS` |
| `cstack.lua` | `OK` after deliberate stack-overflow recovery tests |
| `sieve.lua` | `chain=40`, a caught `C stack overflow`, and shell return |
| `pm.lua` | `OK` |
| `iigshost` | `IIGSHOST PASSED yields=100` on the recorded build |

The sieve deliberately exceeds the native C-stack capacity. Its caught
error is the intended result. Chain depth can vary with the build; it is
not a general limit on the number of independent Lua coroutines.

**Allow time for silent tests.** Original `tableovf.lua` took approximately
18 minutes on the tested accelerated machine and completed successfully.
It constructs error-message strings for every assertion even when the check
passes. IIGSHOST also stays silent until completion or an error; its hardware
duration was not measured. Five or nine minutes of silence did not establish
a hang. Eighteen minutes is an observation, not a universal deadline.

The remaining targeted scripts are listed in [tests/README.md](tests/README.md).
Local GoldenGate coverage and a user report of extra scripts must not be
presented as individually documented hardware passes for every script.

## Repeatability for a changed runtime

Run this pair five times without rebooting:

```text
lua -E -v coroutine.lua
lua -E -v hwdiag2.lua
```

Then power fully off/on and run the pair once more. This is twelve launches:
ten warm and two after the power-cycle. Require each script's success marker
and a clean shell return. Record the build ID, count, configuration, and any
failure; stop at a failure rather than continuing in potentially damaged
memory. This sequence is already complete for the preserved September 22
build, with additional mixed-script warm-session success reported.

## When a failure needs localization

Use the same kit's traced executable:

```text
luatrace -E -v hwsmoke.lua
luatrace -E -v cobeacon.lua
```

Trace output includes lifecycle markers `[M5] script done`, `[M6] closing
state`, and `[M7] state closed`, plus Memory Manager events. M7 precedes
C-runtime cleanup, so shell return is still required. `cobeacon.lua` adds
flushed B markers to the coroutine test. Some markers precede explanatory
comments rather than test operations; the last marker narrows a region,
not necessarily a failing instruction. Success ends with B27, `OK`, and
`BEACON DONE (C API harness skipped)` in the current no-T configuration.

Record the exact command, build ID, elapsed time, last output, and whether
it froze, corrupted text, rebooted, or printed a Lua error. Prefer a photo
for an initial corruption report rather than adding file-output activity.
Tracing changes timing and layout; confirm a fix with the ordinary build too.

The temporary TABPROBE/TABQUIET/TABEAGER/IIGSDBG packages described in the
results journal were investigation artifacts, not distribution executables
or prerequisites for this test sequence.

## Allocator status and module lookup

`IIgs mm=untested` is normal before an allocation needs the Memory Manager;
`-v` does not force a probe. `ok` means the startup probe succeeded, not that
every allocation size or machine is certified. `degraded` means the probe
failed and only bounded C-heap fallback is available. Report degradation;
do not count it as validating the hybrid allocator. `disabled` identifies a
build with the hybrid allocator compiled out.

For a traced allocation check, `luatrace -E -v mmalloc.lua` must include
`[mm] selftest state=1`. Small workloads need not activate the MM path.

The default Lua module path is `?.lua;?/init.lua`. The current build does not
need the old `-e "package.path='?.lua'"` workaround for `cstack.lua`. If
`tracegc` is missing, check the working directory and extracted helper before
changing the runtime. C-library search-path text in an error does not imply
that dynamic C modules are supported; see [limitations](docs/LIMITATIONS.md).
