# Building, testing, and packaging

Run the commands below from the repository root on the development Mac.
They build IIgs ORCA shell executables through GoldenGate (`iix`); nothing
here runs on the IIgs itself. `make help` prints the command reference.

`make` is the public interface. Every command calls the shared Python
tooling in [`tools/iigsbuild/`](../tools/iigsbuild/), which is the single
implementation of tool discovery, builds, tests, packaging, checksums,
metadata verification, and reports.

## Setup

Requirements:

| Tool | Used for | Notes |
| --- | --- | --- |
| GNU `make`, Python 3.9+ | everything | standard library only |
| GoldenGate `iix` | compile, link, run under emulation | |
| ORCA/C **2.2.x** SDK | the compiler, linker, headers, libraries | recorded builds used 2.2.1 |
| AppleCommander `acx` | ProDOS `.po` images | only type **names** work; see [packaging](#packaging) |
| CiderPress II `cp2` | ShrinkIt archives, metadata readback | |
| `nulib2` | independent archive extraction | |

The SDK is not in Git. The tooling looks for it in this order:

1. `GOLDEN_GATE` (environment, command line, or `local.mk`);
2. `./.orca-sdk-2.2.1` in this checkout;
3. `.orca-sdk-2.2.1` in the primary Git worktree (so linked worktrees
   share one SDK).

It never selects the system `/Library/GoldenGate` implicitly: that install
has carried ORCA/C 2.1.0, which cannot compile this source. `iix --sdk`
alone does not select the compiler.

Machine-specific settings belong in an untracked `local.mk`:

```sh
cp local.mk.example local.mk
```

Edit it to set `GOLDEN_GATE`, `IIX`, `ACX`, `CP2`, `NULIB2`, or `JOBS` as
needed. Then check the setup:

```sh
make doctor
```

`doctor` does more than check that files exist. It compiles, links, and
runs a probe with the selected SDK, and round-trips a tiny `.po`/`.SHK`
with metadata readback. It also reports the compile-concurrency setting and
any legacy generated files left in `src/`.

## Commands

| Command | Result |
| --- | --- |
| `make` / `make all` | full Lua, LUAC, and the full embedding library |
| `make lua` | interpreter with the source parser (configuration `lua`) |
| `make lua-small` | compact, bytecode-only interpreter (configuration `lua-small`) |
| `make luac` | bytecode compiler, always parser-enabled (configuration `luac`) |
| `make luatrace` | full interpreter with Memory Manager tracing |
| `make liblua` | full embedding library: `lua.lib`, `lvm.a`, `include/` |
| `make liblua-small` | parser-free embedding library: `luasmall.lib`, `lvm.a`, `include/` |
| `make hosts` | `iigshost allocfail bridge mmtest memfree` (each also a target) |
| `make everything` | every configuration, library, and host |
| `make test` | default local regression checks ([tests](../tests/README.md)) |
| `make test-build` | build-system integration tests |
| `make suite GROUP=runtime` | the reusable Lua suite, run locally |
| `make identify` | identified build of every configuration |
| `make package BUILD=<id>` | verified `.po`/`.SHK` packages of an identified build |
| `make hardware-suite BUILD=<id>` | `TEST.SHK` kit for the real IIgs |
| `make stage FROM=<dir> DEST=<dir>` | copy verified containers to the transfer share |
| `make kit` | identify, test, then package (replaces `tools/hardware-kit.py`) |
| `make sizes [BUILD=<id>]` | measured sizes and compact-runtime savings |
| `make verify-concurrency` | prove parallel compiles equal serial ones |
| `make clean` | remove disposable outputs and preserve evidence |
| `make clean-legacy` | archive loose outputs left by the old Makefiles |

Options (on the command line or in `local.mk`):

| Variable | Meaning |
| --- | --- |
| `GOLDEN_GATE`, `IIX`, `ACX`, `CP2`, `NULIB2` | tool locations |
| `JOBS=N` | concurrent compiler processes ([concurrency](#concurrency)) |
| `CONFIG=` | `lua`, `lua-small`, or `luatrace` for `make test` / `make suite` |
| `CHECKS=` | subset for `make test`: `unit targeted luac compact hosts trace` |
| `BUILD=` | identified build: a directory, its name, or a unique ID prefix |
| `RELEASE=` | published release directory with `RELEASE-MANIFEST.json` |
| `EXES="lua=<path> ..."` | explicit existing executables for a hardware kit |
| `KIT=` | `suite` (default), `small`, `luac`, or `host` |
| `GROUP=`, `PREFLIGHT=` | suite group for the kit, and for its local preflight (`none` skips) |
| `PREFIX=` | ORCA executable prefix in kit batches, default `20:`; `none` for shell lookup |
| `KINDS=`, `REPORT=` | package kinds; a test report to cite in the package manifest |
| `BUILD_LABEL=`, `CONFIGS=`, `COMPARE_RELEASE=` | options for `make identify` |
| `FROM=`, `DEST=`, `REPLACE=1` | options for `make stage` |
| `PYTHON=` | interpreter to run the tooling (default `python3`) |

## Configurations

| Configuration | Generated `parseconf.h` | Products | Notes |
| --- | --- | --- | --- |
| `lua` | `BUILD_IS_LUA` | `lua`, `lua.lib`, `lvm.a`, hosts | historical default; link order unchanged |
| `lua-small` | `BUILD_IS_LUA`, `LUA_NO_PARSER` | `luasmall`, `luasmall.lib`, `lvm.a` | `lcode`, `llex`, `lparser` neither compiled nor linked |
| `luac` | `BUILD_IS_LUAC` | `luac` | the compiler always has the parser |
| `luatrace` | `BUILD_IS_LUA`, `LUA_IIGS_MMTRACE` | `luatrace` | traced diagnostics build |

`parseconf.h` is generated separately for each configuration, in
`<configuration>/gen/`. It is no longer tracked in `src/`, and switching
targets never rewrites a tracked file. `src/luaconf.h` includes it, so
every translation unit and every embedding host sees the same parser
selection. That includes `llex.c` and `lcode.c`, which previously did not
include it. `luaconf.h` rejects a missing or contradictory selection.
Identified builds add `LUA_IIGS_BUILD_ID` to the same header.

Compile flags (`-I -P -D +O`), the unit list, and the link order come from
the historical `src/Makefile`, now in
[`configs.py`](../tools/iigsbuild/configs.py). Each link is made with
`+S`, and the symbol table is kept as `<exe>.map`. The build checks that
map: the parser entry points (`luaY_parser`, `luaK_code`, `luaX_next`,
`luaX_init`) must be present in parser configurations and absent from
`lua-small`.

Measured sizes (identified build `63eca55c48e5`, default banners, 2026-09-24):

| Product | Full | Compact | Saving |
| --- | ---: | ---: | ---: |
| interpreter | 362,344 | 309,037 | 53,307 bytes (14.7%) |
| embedding library | 524,380 | 412,143 | 112,237 bytes (21.4%) |

Executable sizes vary by a few bytes with the banner text.

What the compact runtime can and cannot run is described in
[compact runtime testing](../tests/COMPACT.md).

## Build directories

Development builds are incremental and disposable:

```text
build/dev/<configuration>/
  gen/parseconf.h      generated configuration
  obj/                 objects, .deps/ content-hash stamps
  hostobj/             host/probe objects (lua configuration)
  out/                 executables, .map link maps, libraries, include/
  logs/                compiler, linker, and makelib output
  state.json           configuration + toolchain + recipe fingerprint
```

An object is reused only if nothing it depends on has changed: its
source, every header it includes, and the configuration fingerprint. The
includes are found by scanning quoted `#include` lines along ORCA's own
search path. The fingerprint covers the generated header, compile flags,
recipe version, and the toolchain's identity: hashes of the compiler,
linker, runtime libraries, ORCA/C headers, and `iix`. When the fingerprint
changes, the configuration's objects and outputs are discarded before
rebuilding. Timestamps are not used.

Failures are loud and leave no plausible-looking output behind. ORCA can
exit with an error yet still leave a partial `.root` after a failed compile,
or a truncated executable after an unresolved link. The tooling therefore
builds in private staging names and renames them into place only on
success. A product whose inputs failed to build is removed rather than left
stale.

## Concurrency

Compiler concurrency is not assumed. Compiles run serially until
`make verify-concurrency` shows, for the exact toolchain fingerprint, three
things:

- Parallel compiles produce objects and an executable byte-identical to a
  serial build.
- No tool writes to ORCA's shared work prefix `14:`, which GoldenGate maps
  to the temporary directory. The check makes that directory read-only.
- Both parallel rounds agree.

The machine-local record in `build/local/concurrency.json` then enables up
to eight concurrent compiler processes. An explicit `JOBS=N` always wins.
Links and library creation are serial. On the recorded setup, all 33
outputs were identical across one serial and two 8-way builds, with no
temp-prefix writes. A clean build of one configuration then takes about 5 s
instead of about 20 s.

`make -j` is safe but does not add parallelism: the Makefile is
`.NOTPARALLEL`, and each build directory is locked, so two `make`
processes wait for each other instead of interleaving.

## Identified builds

```sh
make identify
```

This builds every configuration and host from a byte snapshot of the
sources, into `build/builds/<build id>-<utc>/`:

```text
source/              the exact bytes compiled
<configuration>/     gen/obj/out as above
logs/                banner checks
BUILD-MANIFEST.json  identities, hashes, configuration, parser evidence
```

The **build ID** covers only what can change executable bytes: `src/`
sources, the recipe, configuration macros, and the toolchain identity.
Documentation, tests, and packaging code are excluded, so a docs-only or
packaging-only change keeps the same build ID and banner (for example
`IIgs 63eca55c48e5 plain`). The manifest separately records:

- the Git commit, and whether the snapshot matches it;
- host-source hashes;
- every artifact's hash and size;
- the parser-symbol evidence;
- a comparison with any earlier build of the same ID.

It records no local paths. The finished directory is made read-only.
Tests and packaging recheck every artifact hash before use and refuse a
modified build. Nothing ever rebuilds an identified build in place.

`BUILD_LABEL` overrides the banner prefix, which is useful for reproducing
an older banner. `COMPARE_RELEASE=<release dir>` compares the executables
with a release's recorded hashes.

### Reproducibility

Byte-for-byte reproduction is claimed only where it has been demonstrated.
On 2026-09-24, with the same ORCA/C 2.2.1 SDK and GoldenGate 2.1.0, this
command reproduced all four v0.2.1 release executables:

```sh
make identify BUILD_LABEL="IIgs e026f5b-13178cdf3c75" COMPARE_RELEASE=<v0.2.1 download directory>
```

The results were byte-identical to the release: LUA `431a82d7…`, LUAC
`a21493e2…`, LUATRACE `76c854eb…`, and IIGSHOST `4d8a7695…` (see the
[validation record](validation/2026-09-24-build-system/README.md)). Other
toolchains, and any configuration not compared, have no such claim.

## Tests

`make test` runs the default local checks under GoldenGate `--memcheck`:
unit tests, the 16 targeted scripts, LUAC debug and stripped bytecode on
both runtimes, compact acceptance with source rejection, and the native
hosts. Use `BUILD=<id>` to test an identified build instead of the dev
builds. Identified-build reports go to `build/test-reports/` and are kept.
Dev reports go to the disposable `build/test-runs/`. Every report
records:

- the executable hashes;
- a **test identity**: a hash of the scripts, manifests, and contracts,
  kept separate from the build ID;
- the emulator identity;
- each check's status and intentional skips.

These are emulator results, never hardware results. See
[tests/README.md](../tests/README.md).

## Packaging

```sh
make package BUILD=<id> REPORT=build/test-reports/<...>/report.json
```

This writes to `build/packages/<id>-<utc>/`, one `.po` and one `.SHK` per
kind (`KINDS=` selects a subset):

| Kind | Container | Contents |
| --- | --- | --- |
| `runtime` | `lua.po`, `LUA.SHK` | `LUA`, targeted scripts, `TRACEGC.LUA` |
| `small` | `luasmall.po`, `LUASMALL.SHK` | `LUASMALL` |
| `compiler` | `luac.po`, `LUAC.SHK` | `LUAC` |
| `trace` | `luatrace.po`, `LUATRACE.SHK` | `LUATRACE`, scripts |
| `library` | `lualib.po`, `LUALIB.SHK` | `LUA.LIB`, `LVM.A`, headers incl. `PARSECONF.H` |
| `library-small` | `luasmlib.po`, `LUASMLIB.SHK` | `LUASMALL.LIB`, `LVM.A`, headers |
| `host` | `iigshost.po`, `IIGSHOST.SHK` | `IIGSHOST` |

Each also contains `README.TXT` and `LICENSE.TXT`.
`PACKAGE-MANIFEST.json` records the build ID and manifest hash, the cited
test report and its summary, and a **package identity** (a hash of the
members), plus every member's hash and type. A copy of
`BUILD-MANIFEST.json` and a `SHA256SUMS` file sit alongside. Rewording a
readme changes the package identity, not the build.

ProDOS metadata:

| Kind | Type / aux |
| --- | --- |
| executable | EXE `$B5` / `$0000` |
| ORCA library | LIB `$B2` / `$0000` |
| ORCA object | OBJ `$B1` / `$0000` |
| text, Lua source | TXT `$04` / `$0000` (CR line endings) |
| ORCA EXEC batch | SRC `$B0` / `$0006` |
| ORCA/C header/source | SRC `$B0` / `$0008` |
| Lua bytecode | BIN `$06` / `$0000` |

Verification is independent of creation. Every member is extracted again
(with `acx` for images and `nulib2` for archives) and compared byte for
byte. Its type and aux are read back with `cp2`, and the member set must
match exactly. This matters: `acx` silently stores `NON $00` when it is
given a numeric type such as `$B5`, and `nulib2 -p` exits 0 for a missing
member. Existing containers are never overwritten, and executables are
copied from the identified build, never rebuilt.

## Hardware kits

```sh
make hardware-suite BUILD=<id> KIT=suite
make hardware-suite BUILD=<id> KIT=small
make hardware-suite RELEASE=build/release-v0.2.1-download KIT=luac
make hardware-suite EXES="lua=path/to/validated/lua" KIT=suite
```

Each kit is written to `build/hardware-suites/<utc>-<kit>-<id>/package/`
as `TEST.SHK` and `TEST.po`. They contain:

- `TEST`, an ORCA EXEC batch;
- `TEST.LUA`;
- the executables under test, as `LUATEST`, `LUACTEST`, or `IIGSHOST`;
- the scripts, `README.TXT`, and `LICENSE.TXT`;
- beside the containers, a `KIT-MANIFEST.json` with all hashes, the
  batch, and the preflight result.

The stable names allow the same IIgs commands every time:

```text
yankit xvf /nas/lua.test/test.shk
20:test
```

| Kit | Checks | Guide |
| --- | --- | --- |
| `suite` | reusable regression suite (`GROUP=full` default; 23 tests) | [SUITE.md](../tests/SUITE.md) |
| `small` | compact runtime: source rejection, debug and stripped bytecode groups | [COMPACT.md](../tests/COMPACT.md) |
| `luac` | LUACPROBE 1 standalone compiler checks | [LUAC_TESTING.md](../tests/LUAC_TESTING.md) |
| `host` | HOSTCHECK 1 native embedding and C-hook yields | [HOST_TESTING.md](../tests/HOST_TESTING.md) |

Batch files have one command per line and contain no semicolons, not even
in comments. `PREFIX` sets the executable prefix: the confirmed `20:` by
default, or `PREFIX=none` for shell lookup. The batch text and the local
preflight come from the same step list. The generated LUAC and HOSTCHECK
command lines are identical to the batches validated on hardware. The
preflight runs each step as a separate GoldenGate process and is recorded
as an emulator result. The hardware result stays `pending` until someone
records it.

The suite's full group includes `tableovf`, which took about **18 minutes
silently** on the accelerated IIgs. Stock GoldenGate cannot pass the full
I/O group, so the suite kit preflights `runtime` by default.

### Transfer

```sh
make stage FROM=build/hardware-suites/<kit dir> DEST=/Volumes/nas/lua.test
```

This copies the containers, manifest, and `SHA256SUMS` after rechecking
the sums, then reads each copy back. Metadata travels inside the `.SHK` or
`.po`; do not copy naked executables. A different existing file is never
replaced silently. Without `REPLACE=1` the copy is refused. With it, the
old files are first moved to `DEST/replaced-<utc>/` and a notice is
printed. Do not replace a staged kit or a published release without a
reason.

The established test machine is an accelerated ROM 03 IIgs with 8 MB RAM.
GS/OS was tentatively reported as 6.04. Newly built executables need their
own hardware run; earlier hardware passes belong to the exact executables
they tested. See [hardware testing](../HARDWARE_TESTING.md).

## Cleaning

`make clean` uses an allow-list. It removes:

- `build/dev/`
- `build/test-runs/`
- untracked legacy outputs that the old Makefiles left in source
  directories: `src/*.a *.root *.sym *.lib`, `src/lua`, `src/luac`,
  `src/parseconf.h`, root and `tests/` objects, `bridge`, `mmtest`,
  `memfree`, and `luac.out`

It never touches:

- `build/builds`, `build/packages`, `build/hardware-suites`,
  `build/test-reports`, `build/hardware`, `build/diagnostics`,
  `build/archive`, `build/release-*`, `build/worktrees`, and `build/local`
- `dist/` and `docs/validation/`
- any file tracked by Git

`make clean-legacy` moves old loose outputs (`build/lua`, `build/luac`,
`build/lua.lib`, …) into `build/archive/legacy-<utc>/` rather than
deleting them, because some served as evidence. `DRY_RUN=1` previews
either command.

## Migrating from the old workflow

| Old | New |
| --- | --- |
| `make lua` → `build/lua`, `src/lua` | `make lua` → `build/dev/lua/out/lua` |
| `make luac` (rewrote `src/parseconf.h`) | `make luac` → `build/dev/luac/out/luac` |
| `make lua` before `make liblua` | `make liblua` alone → `build/dev/lua/out/{lua.lib,lvm.a,include/}` |
| editing `luaconf.h` for `LUA_NO_PARSER` | `make lua-small` / `make liblua-small` |
| bare `make` built `bridge` | `make` builds lua, luac, liblua; `make bridge` still works |
| `make mmtest memfree` | unchanged names, outputs in `build/dev/lua/out/` |
| `make -C src ...` | forwards to the root Makefile (deprecated) |
| `make -C tests tests` | still works; default `LUA` is `build/dev/lua/out/lua`; prefer `make test` |
| `python3 tools/hardware-kit.py` | `make kit` (the script forwards; `--plain-name` is ignored) |
| `tools/test-suite.py run/package` | `make suite EXE=...` / `make hardware-suite EXES="lua=..."` |
| `tools/luac-test-kit.py`, `tools/host-test-kit.py` | `make hardware-suite KIT=luac RELEASE=...` (or `KIT=host`) |
| `tools/test_support.py` | `tools/iigsbuild/contracts.py` (shim kept) |
| `make release disks luadisk testdisk bridgedisk cleanrelease minitest` | removed (they used an unrelated `ac`); `make package` / `make hardware-suite` |
| copies into `../../../luagsdemo/lib` | removed; nothing writes outside this repository except `make stage` |
| `make clean` restored `src/parseconf.h` | `make clean` removes dev outputs only |

After switching an existing checkout, run `make clean` once to remove old
objects from `src/`. The old `build/hardware/<utc>/` kits, releases, and
diagnostics remain as recorded evidence. The new tooling reads release
directories but never writes to them.

## Source distribution

Export a committed tree with Git rather than zipping the working directory:

```sh
mkdir -p dist
git archive --format=zip --prefix=lua-iigs/ --output=dist/lua-iigs-source.zip HEAD
```

The SDK, `build/`, `dist/`, `local.mk`, and loose outputs do not belong in
a source distribution. Identified builds keep their own `source/`
snapshot for provenance. Historical transcripts live under `docs/history/`,
and dated validation records under `docs/validation/`.
