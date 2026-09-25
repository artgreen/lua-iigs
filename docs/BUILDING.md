# Building and testing

## Setup

The maintained development setup is macOS with GNU make, Python 3.9+,
GoldenGate `iix`, and an ORCA/C 2.2.x SDK (recorded builds use 2.2.1).
Packaging requires AppleCommander `acx`, CiderPress II `cp2`, and `nulib2`.
The SDK and tools are external dependencies.

```sh
cp local.mk.example local.mk
make doctor
```

Set `GOLDEN_GATE` to the SDK root in `local.mk` or the environment.
Otherwise the tooling checks `.orca-sdk-2.2.1` in this directory, then
in the primary Git worktree. It never implicitly selects the system
`/Library/GoldenGate`. Set `IIX`, `ACX`, `CP2`, and `NULIB2` as needed.
`doctor` compiles, links, runs, and verifies a packaging round trip.

A source archive works without a `.git` directory. Its source manifest
preserves the originating commit and file hashes. Set the SDK path as above.

## Commands

| Command | Result |
| --- | --- |
| `make` | Full interpreter, LUAC, full embedding library |
| `make lua-small` | Compact bytecode-only interpreter |
| `make liblua-small` | Compact embedding library |
| `make luatrace` | Diagnostic interpreter |
| `make bridge` | C embedding example |
| `make hosts` | Native regression hosts and probes |
| `make everything` | All configurations, libraries, and hosts |
| `make test` | Python, targeted Lua, LUAC, compact, and native-host checks |
| `make test CHECKS="unit targeted luac compact hosts trace"` | All local check groups |
| `make test-build` | Build-system integration checks |
| `make suite GROUP=runtime` | Reusable Lua suite under GoldenGate |
| `make identify` | Immutable build snapshot with hashes and build ID |
| `make test BUILD=<directory>` | Test that exact build without rebuilding |
| `make package BUILD=<directory>` | Verified component containers |
| `make release BUILD=<directory> REPORT=<report.json>` | Complete local release candidate |
| `make hardware-suite BUILD=<directory> KIT=suite` | Real-hardware acceptance kit |
| `make sizes BUILD=<directory>` | Product sizes |
| `make clean` | Remove only `build/dev` and `build/test-runs` |

`make` is the public interface to `tools/iigsbuild`. Per-configuration
outputs live at `build/dev/<configuration>/out/`. Full and compact libraries
include their own generated `parseconf.h` and separately linked `lvm.a`.
No build writes into `src/`.

## Build identity and incremental work

Objects are reused only when source/header hashes, configuration, and
selected toolchain match. Failed compiles and links discard partial products
and stale executables. Parser symbols must be absent from compact builds
and present in parser-enabled builds.

`make identify` captures exact runtime and host sources under
`build/builds/<id>-<utc>/source/`, builds all products, and writes
`BUILD-MANIFEST.json`. The completed build is read-only. Its ID covers
runtime sources, configuration, compile/link recipe, and toolchain; docs,
tests, and packaging changes do not change executable identity. Host sources
and outputs are separately hashed. Source archives retain provenance without Git.

Identified builds are verified before testing or packaging. Use the full
printed directory when more than one build shares an ID. A new build is not
a hardware pass; record the exact executable hashes tested on the IIgs.
`BUILD_LABEL` can reproduce an earlier banner for binary comparison, and
`COMPARE_RELEASE=<directory>` compares with a recorded release manifest.

## Concurrency

Compiles are serial until `make verify-concurrency` proves parallel objects
and outputs match serial builds, with no shared temporary-prefix writes.
The verification is specific to the toolchain. `JOBS=N` explicitly overrides
that setting. Links and library creation remain serial; build-directory
locks serialize competing invocations. A shared workspace lock keeps outputs
and scratch files alive through each command; cleanup takes that lock exclusively.
Compiler cache checks include both `.a` and `.root` outputs. Missing or modified
companions trigger recompilation. Library failures invalidate dependent host outputs.
`make -j` adds no compile parallelism.

## Packaging and transfer

Packages contain ProDOS file metadata: EXE `$B5/$0000`, LIB `$B2/$0000`,
OBJ `$B1/$0000`, text `$04/$0000`, ORCA EXEC `$B0/$0006`, C source/header
`$B0/$0008`, and bytecode BIN `$06/$0000`. Text gets CR line endings;
executable and bytecode bytes are preserved.

Every member is extracted from both containers and compared byte for byte.
Metadata and the exact member set are read back independently. Existing
containers are never overwritten. Packaging never rebuilds executables.

```sh
make stage FROM=<package-directory> DEST=/Volumes/nas/lua.test
```

Staging rechecks checksums and reads copied containers back. It refuses a
different existing file unless `REPLACE=1` is given, which archives the old
copy before replacement. Stage only into a dedicated transfer directory.

Hardware kits accept `KIT=suite`, `lua`, `small`, `luac`, or `host`.
See [hardware procedure](../tests/hardware/PROCEDURE.md).
Identified builds, reports, packages, kits, and `dist/` survive `make clean`.
