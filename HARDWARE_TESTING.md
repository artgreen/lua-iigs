# Lua IIgs hardware troubleshooting

Target for this session: ROM 03, 8 MB RAM, hardware acceleration enabled.
The user tentatively reports GS/OS "6.04". Exact OS version, accelerator
model/speed, shell version, and storage device remain unconfirmed.
Keep the accelerator enabled during the next tests for a consistent baseline.

The July 7 resume-guard fix passed GoldenGate but did not resolve the
reported hardware crash at that time. The identified September build has
since passed the targeted tests on hardware (see HARDWARE_RESULTS.md).
These images are diagnostic builds, not a
hardware-certified release. Each includes a build identifier printed by -v.

## First hardware run

1. Use the newly generated LUATRACE image. It is an 800 KB ProDOS transfer
   disk, not a boot disk. Boot your normal GS/OS/ORCA-compatible shell and
   copy its files into a fresh directory on your usual disk, preserving
   the EXE file type. Change to that directory.
2. Start from a cold boot. Run `luatrace -E -v hwsmoke.lua`.
3. Record the build identifier and the last output. Success is `SMOKE DONE`,
   then `[M5] script done`, `[M6] closing state`, `[M7] state closed`, and
   return to a working shell prompt. M7 is printed before C runtime cleanup;
   returning to the shell is still required.
4. If smoke succeeds, run `luatrace -E -v cobeacon.lua`. Allow at least
   five minutes on an unaccelerated machine; tracing can make it slower.
   Photograph the last section marker and trace messages if it fails.
   Report whether it froze, garbled text, rebooted, or printed a Lua error.
   B0 means the diagnostic started. Later B numbers name the last entered
   section, not necessarily the exact failing statement. Normal completion
   is B27, the C API skip notice, OK, BEACON DONE, and M5 through M7.
5. After any crash or screen corruption, power-cycle before another run.

Do not redirect output to a disk file for the first run: preserve what is
visible on screen without adding file-write activity to the failing workload.
The `-E` switch excludes LUA_INIT startup scripts as a variable.

## After the first result

If traced tests pass, repeat from the LUAPLAIN image with `luaplain -E -v hwsmoke.lua`
and `luaplain -E -v cobeacon.lua`. The ordinary build has no M markers. Previous
reports suggest tracing can affect the failure, so a trace-only pass is not
enough. Keep accelerator and other system settings unchanged for this pair.

If BEACON DONE and M5 appear but M7 does not, investigate shutdown/GC. If M7
appears but the shell does not return, investigate runtime cleanup. If a B
section is the last marker, reduce that section to a minimal reproducer.
No B0 means startup, library initialization, or loading the script failed.

Once both builds pass, run hwdiag2.lua, hwtest.lua, sieve.lua, cstack.lua,
pm.lua, and the original coroutine.lua individually. The sieve deliberately
exceeds the available C stack: a caught 'C stack overflow' is expected.
Other diagnostics must report their normal completion markers with no FAIL.
Repeat launches and exits ten times without rebooting, then repeat after a
cold boot. Record configuration and results; only then treat this as evidence
of reliability on this particular machine. C API tests requiring Lua's T
test library remain skipped.

Always check the build ID printed by -v. An earlier `lua` invocation lacked
the expected ID and corrupted the screen; the identical new binary worked
when invoked under the unique name LUAPLAIN. Avoid selecting an old command
from the shell's search path. Updates may use another unique executable
name; follow the instructions shipped with that update.

The original September build needed `-e "package.path='?.lua'"` to run
cstack.lua on the GS. The updated IIgs default is `?.lua;?/init.lua`, so
TRACEGC.LUA can be loaded from the working directory without this override.
Keep that helper alongside the test. The default no longer assumes Unix
`/usr/local` installation directories; applications can set package.path or
use LUA_PATH when running without -E to select other module directories.

## Rebuilding on the Mac

Run `python3 tools/hardware-kit.py` from the repository. It requires iix,
make, ORCA/C 2.2.x, and native AppleCommander acx. Override the SDK or acx
path with `--sdk` / `--acx` if needed. Use `--plain-name luapath`, for example,
to give an update a unique executable/image name. Each run creates a new directory under
build/hardware with source snapshots, separate plain/trace objects, logs,
and a package directory. It preserves the previous binaries and lua.po.

The builder runs fifteen targeted diagnostics on each interpreter under
GoldenGate with memory checking, plus a luac bytecode roundtrip and an
excessive-parser-nesting test. It also checks the library host with C-hook
yields and array limits, allocator fault injection, the bridge, and mmtest.
It compiles memfree but does not run that hardware-only tool. It refuses
to package failed runs, records source/compiler hashes, and verifies each
disk's executable and text files by exporting and comparing them. See manifest.json and
SHA256SUMS beside the images. GoldenGate results do not certify real hardware.


## PR-review candidate (hardware validation pending)

Preserve LUAPATH and its files. Build the new candidate using
`python3 tools/hardware-kit.py --plain-name luareview`; its source digest
and banner differ from the baseline. A separate iigshost.po image contains
the IIGSHOST executable (keeping all transfer images at 800 KB). Transfer via a ProDOS image or ShrinkIt archive to keep
EXE/TXT metadata intact. Do not overwrite the known-good installation.

After confirming the new `luareview -E -v` build ID, run hwsmoke.lua,
mmalloc.lua, tableovf.lua, hwtest.lua, and cstack.lua with that executable,
and run `iigshost` directly. MMALLOC PASSED and TABLEOVF PASSED are required;
hwtest now says HWTEST PASSED WITH SKIPS for the unsupported Lua hook.
IIGSHOST PASSED verifies the yielding C-hook path separately. Every command
must return to the shell with no screen corruption. Then repeat the
coroutine/hwdiag2 pair and one cold-boot pair for this new candidate.

The version output includes `IIgs mm=untested/ok/degraded/disabled`.
Untested is normal before any large allocation; it does not run a probe.
A degraded warning is always printed if the startup MM probes fail. Stop
and report it; do not accept that run as validating the hybrid allocator.
The traced mmalloc test must show `[mm] selftest state=1`; smaller tests
such as sieve need not initialize the MM path. An ok status certifies the
small startup probe, not every allocation size or hardware configuration.

The source-only library has a required initialization contract described
in docs/CORRUPTION-ANALYSIS.md. Existing embedders must request the larger
stack and initialize its guard before creating a state.
