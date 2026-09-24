# Lua for the Apple IIgs

Lua 5.4.6 ported to the Apple IIgs with ORCA/C. The project provides a
command-line interpreter and REPL, the `luac` bytecode compiler, and a
static library for embedding Lua in an ORCA/C program.

## Current status

The runtime on `master` has completed targeted testing on real hardware.
Exact build identities and checksums are preserved in the
[tested-build record](docs/validation/2026-09-22/README.md).

On an accelerated ROM 03 IIgs with 8 MB RAM, the user reported successful
targeted tests, clean returns to the shell, five warm coroutine/allocation
test pairs, another pair after a full power-cycle, and additional mixed-script
use in one warm session. The original silent `tableovf.lua` completed with
49,152 entries in about **18 minutes**. Silence alone was not a hang.

These are results for an identified build on one machine, not a percentage
of the complete upstream suite or a guarantee for every Lua workload.
The repaired/adapted `files.lua` passes on hardware in portable/small-file
mode, with explicit skips; stock GoldenGate still has EOF/text-translation
issues. The upstream `T` C API test harness is unavailable, and some tests
are scaled or skipped for this port.
See [known limitations](docs/LIMITATIONS.md) and the chronological
[hardware results](docs/validation/HARDWARE_RESULTS.md).

## Run Lua

Build a kit with `--plain-name lua` as described below, or use a distribution
prepared from that kit. Extract `LUA.SHK` with GS ShrinkIt, or copy from
`lua.po`, preserving executable metadata. From an ORCA-compatible shell in
the installed directory:

```text
lua -E -v
lua -E -v hwsmoke.lua
lua -E myscript.lua
```

For a kit build, check the printed identifier against its `BUILD.TXT`.
The smoke test should print `SMOKE DONE - expect shell prompt next` and
return to `#`. Run `lua -E -i` for the interactive prompt; `os.exit()`
leaves it. The `-E` option ignores Lua environment settings, including
`LUA_INIT` and `LUA_PATH`; omit it when you intentionally need those settings.

Lua modules default to `?.lua;?/init.lua`, relative to the working directory.
Keep test helpers such as `tracegc.lua` beside the scripts that require them.
The interpreter is a shell executable, not a Finder-launched desktop app
or a boot disk.

For transfer details, expected test output, and new-build validation, follow
[hardware testing](HARDWARE_TESTING.md). Preserve the exact tested artifacts:
a rebuild has its own identity and needs validation.

## Build and develop

The supported development workflow uses GoldenGate's `iix`, an ORCA/C 2.2.x
SDK (the recorded builds used 2.2.1), `make`, Python 3, and native
AppleCommander `acx`. The SDK and tools are not bundled in Git.

From the repository root, with those tools installed:

```sh
python3 tools/hardware-kit.py --sdk /path/to/orca-sdk --plain-name lua
```

This builds in a fresh directory, runs the local checks, and produces
metadata-preserving ProDOS images plus a manifest and checksums. It does
not create ShrinkIt archives, copy to a NAS, or run tests on the real IIgs.
See [building and packaging](docs/BUILDING.md) for setup, individual build
targets, archive creation, and artifact verification.

Embedding applications must request the configured stack size and call
`lua_iigs_initstack()` from `main` before creating a Lua state. See the
[embedding guide](docs/EMBEDDING.md); older clients need this initialization.

## Documentation

- [Documentation map](docs/README.md): current guides, provenance, and history.
- [Tests](tests/README.md): commands, coverage, skips, and expected failures.
- [Examples](examples/README.md): interactive demos and the C bridge.
- [Port limitations](docs/LIMITATIONS.md): numeric types, stack limits, modules, and open work.
- [Implementation notes](docs/CORRUPTION-ANALYSIS.md): stack, allocator, and arithmetic protections.
- [Tested-build provenance](docs/validation/2026-09-22/README.md): exact tested inputs and artifacts.

The interpreter, compiler, and static library are implemented. A system tool
set and an NDA were early project goals; neither is implemented here.
Lua's copyright and permission notice is retained in [src/lua.h](src/lua.h),
and the imported tests carry their notice in [tests/all.lua](tests/all.lua).
