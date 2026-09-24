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

For routine checks of an existing interpreter, the
[repeatable regression suite](tests/SUITE.md) runs all 23 Lua regressions
from one kit with one command. It also offers smaller groups. The steps
below prepare a new runtime build. The separate kits cover the compact
runtime, LUAC, and the native C host.

1. Make an identified build and test it locally:

   ```sh
   make identify
   make test BUILD=<build id>
   ```

   Keep its `BUILD-MANIFEST.json` and test report. Do not overwrite a
   known-good installation while testing a changed runtime.
2. Package it, or prepare a kit, without rebuilding:

   ```sh
   make package BUILD=<build id>
   make hardware-suite BUILD=<build id> KIT=suite
   ```

3. Stage the containers to the transfer share:

   ```sh
   make stage FROM=<package or kit directory> DEST=/Volumes/nas/<new directory>
   ```

   Staging refuses to replace different files unless `REPLACE=1` is given.
   Transfer the `.SHK` archive or the `.po` image, never a naked executable:
   the containers carry EXE `$B5` / aux `$0000` metadata, which a NAS copy
   can lose. The images are 800 KB transfer disks, not boot disks.
4. Extract into a separate test directory with GS ShrinkIt, keeping the
   interpreter and scripts together. Keep `tracegc.lua` beside `cstack.lua`.
   IIGSHOST comes in its own package and kit.
5. Power fully off and on before the first validation run, then use your
   normal ORCA-compatible shell. Keep accelerator settings consistent
   across runs.

The recorded shell runs these kits with the executable prefix `20:`
(`20:test`). Kits are generated with a different prefix using `PREFIX=`.

Commands below assume the executable is named `lua`. The runtime package
contains `LUA`; kits rename the interpreter `LUATEST`. Check the printed
banner against the build ID in `BUILD-MANIFEST.json` or the kit's
`README.TXT`. Do not assume the shell ran the right binary merely because
a command named `lua` exists: an earlier failed run lacked the expected
build identifier, while the identified build passed.

## First checks

From the test directory:

```text
lua -E -v
lua -E -v hwsmoke.lua
lua -E -v coroutine.lua
lua -E -v hwdiag2.lua
```

`-E` ignores Lua environment initialization and module-path settings.
`-v` prints the Lua version, the build ID, and allocator status. Development
builds (`make lua`) carry no build ID; use an identified build for comparison.

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

Use the traced executable from the same identified build (`LUATRACE` package):

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
