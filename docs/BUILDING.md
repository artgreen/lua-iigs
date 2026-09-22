# Building and packaging

Run the commands below from the repository root unless stated otherwise.
The target is an ORCA-compatible IIgs shell executable. These commands run
on the development Mac through GoldenGate, not in the IIgs shell.

## Toolchain

Install GoldenGate (`iix`), `make`, Python 3, and an ORCA/C 2.2.x SDK. The
recorded hardware builds used ORCA/C 2.2.1. Packaging also requires native
AppleCommander `acx`; optional ShrinkIt conversion uses CiderPress II `cp2`
and independent archive verification uses `nulib2`.

The local SDK directory `.orca-sdk-2.2.1/` is ignored by Git and is not
provisioned by the build scripts. It must be a complete GoldenGate SDK root,
including `Languages`, headers, and libraries. Select it explicitly:

```sh
export GOLDEN_GATE="$PWD/.orca-sdk-2.2.1"
command -v iix make python3 acx
```

Substitute your actual SDK location if different. The root and source
Makefiles default to this local SDK when it exists; an explicitly set
`GOLDEN_GATE` takes precedence. `iix --sdk` alone does not select the compiler
root. A system installation with ORCA/C 2.1.0 is not the validated toolchain.

## Recommended: isolated hardware kit

```sh
python3 tools/hardware-kit.py --plain-name lua
```

To override tool locations:

```sh
python3 tools/hardware-kit.py --sdk /path/to/orca-sdk --acx /path/to/acx --plain-name lua
```

Use `lua` for distribution. During hardware comparisons, use a distinct
name such as `luatest` for a changed runtime. The name must start
with a letter, contain only letters, digits, or dots, and fit 15 characters;
`luatrace` is reserved. The default plain name is `luaplain`. For the names
shown here, the output is:

```text
build/hardware/<UTC timestamp>-<unique suffix>/
  source/          exact input snapshot
  plain/           separate objects, interpreter, compiler, library, C hosts
  trace/           separate objects and traced interpreter
  logs/            build, test, and image-verification logs
  package/
    lua.po
    luatrace.po
    iigshost.po
    manifest.json
    SHA256SUMS
    HARDWARE_TESTING.md
```

Each image is an 800 KB ProDOS transfer image, not a boot disk. The plain
and trace images each contain their interpreter, fifteen targeted scripts,
`tracegc.lua`, `README.TXT`, and `BUILD.TXT`. IIGSHOST has a separate image.
The kit builds and tests `luac`, the library, allocator fault injection,
bridge, and mmtest locally; those executables are not all included on the
transfer images. `memfree` is built but not run locally.

The builder runs fifteen scripts in each variant with GoldenGate memory
checking and completion contracts. It refuses to finish packaging after a
failed check. The checks and intentional skips are recorded in the manifest.
Its local timeouts are not hardware timing limits. See [test coverage](../tests/README.md).

The banner combines the current Git HEAD prefix with a digest of the input
snapshot and the variant. Uncommitted input edits are included in the digest;
HEAD alone does not identify the built source. `HARDWARE_TESTING.md` is one of
the inputs, so even a documentation update can change the next build's ID.
Existing objects, `build/lua`, earlier kits, and `lua.po` are not overwritten.

The builder does **not** produce `.SHK` archives, upload files, or perform
hardware validation. The NAS archives used during the session were created
and verified separately.

## Individual development targets

```sh
make lua
make luac
make liblua
make bridge
make mmtest memfree
```

| Target | Output |
| --- | --- |
| `make lua` | `build/lua` and `src/lua` |
| `make luac` | `build/luac` and `src/luac` |
| `make liblua` | `src/lua.lib` and copies of it and the existing `src/lvm.a` in `build/` |
| `make bridge` | root `bridge` embedding demo |
| `make mmtest memfree` | root standalone Memory Manager probes |

Run `make lua` before `make liblua` or `make bridge`: the current library
recipe assumes `src/lvm.a` already exists. Specify a target: bare `make`
currently selects `bridge`, not an all-tools build. Build sequentially:
interpreter/compiler modes share source objects and rewrite `src/parseconf.h`.
Use the isolated kit for release evidence or
plain/trace comparisons. A normal `make lua` build does not receive the kit's
unique build-ID macro and must not be labeled the archived tested binary.

Quick local checks after building:

```sh
iix --memcheck build/lua -E tests/hwsmoke.lua
iix build/luac -o build/hwsmoke.out tests/hwsmoke.lua
iix --memcheck build/lua -E build/hwsmoke.out
make -C tests tests LUA="$PWD/build/lua"
```

`make clean` cleans source objects and restores the Lua parser configuration;
it does not erase archived kits. The legacy `release`, `disks`, `luadisk`,
and bridge-disk targets use an older AppleCommander `ac` interface and have
not been validated as the current transfer workflow. In particular, macOS
`/usr/sbin/ac` is an unrelated accounting utility. Use the kit's `acx` path.
Do not use `make cleanrelease` to tidy a tree containing preserved artifacts;
it attempts removal of top-level build/image outputs.

## ShrinkIt archives and transfer verification

For a completed kit, replace the example path below with the directory
printed by the builder. Use a new output directory for each build; do not
overwrite archived packages. Distribution executables and archives can use
`lua` and `LUA.SHK` without carrying temporary investigation names.

```sh
cd build/hardware/REPLACE-WITH-KIT-DIRECTORY/package
shasum -a 256 -c SHA256SUMS
cp2 create-file-archive LUA.SHK
cp2 copy lua.po LUA.SHK
cp2 get-attr LUA.SHK LUA
nulib2 -p LUA.SHK LUA > /private/tmp/lua-extracted
cmp /private/tmp/lua-extracted ../plain/build/lua
shasum -a 256 LUA.SHK > ARCHIVE-SHA256SUMS
```

The executable metadata should be EXE (`$B5`) with auxiliary type `$0000`.
Create trace/host archives similarly if needed. Disk-to-archive copying
preserves the metadata; extracting a naked executable and copying it over a
NAS generally does not establish that its metadata survived. Plain `.PO`
images are an alternative if the receiving setup can mount them.

Copy the containers, manifest, and checksums to a new NAS directory and
verify the destination files by reading them back. The session NAS was
`/Volumes/nas`; the scripts do not mount it. On the IIgs, use GS ShrinkIt to
extract the archive, or copy from the mounted ProDOS image with a tool that
preserves file types. [Hardware testing](../HARDWARE_TESTING.md) describes
what to run after transfer.

## Preserving evidence

Keep the kit's source snapshot, objects, tools' hashes, executable hashes,
logs, images, and manifest together. Preserve ProDOS/Mac metadata when
copying ORCA object and library files too: a byte-only copy can be rejected
by the linker as not being an object file. In-place links to the original
staged objects avoid that transfer problem.

The checked-in [validation records](README.md#evidence-and-provenance) refer
to original package checksums. Run their `SHA256SUMS` in the corresponding
archived package directory, not in the documentation directory, where the
image files are absent and the README may have been updated.

## Clean source distribution

Use a Git export of the intended commit, not a zip of the working directory:

```sh
mkdir -p dist
git archive --format=zip --prefix=lua-iigs/ --output=dist/lua-iigs-source.zip HEAD
```

This exports committed source and documentation. Uncommitted edits are not
included. The local SDK, `build/` kits/logs/archives, generated `images/`,
`dist/`, editor settings not tracked by Git, and loose output files do not
belong in a source distribution. Do not add them just to make a local build
appear self-contained. Preserve tested binaries locally, and distribute
selected `.PO`/`.SHK` containers separately when preparing binary packages.

Historical transcripts live under `docs/history/`; dated validation manifests
remain under `docs/validation/`. Temporary executable names in those records
identify evidence and should not be substituted into the public run examples.
