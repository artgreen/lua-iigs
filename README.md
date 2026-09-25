# Lua for the Apple IIgs

Lua 5.4.6 for the Apple IIgs: run scripts, use an interactive prompt,
compile bytecode, or embed Lua in an ORCA/C application.

## Giving back

One of the original goals of this project remains:

> Give back to the Apple community by bringing a powerful tool to the Apple IIgs

## Distribution

**[Download distribution 0.3.0](https://github.com/artgreen/lua-iigs/releases/tag/v0.3.0).**
The maintainer reported successful acceptance testing and approved this release.
See [validation](docs/VALIDATION.md) for the recorded evidence and its scope.

## Download and run

Choose the **standard distribution**, `LUA.SHK` or `lua.po`. It contains
`LUA`, the `LUAC` compiler, thirteen standalone examples, and a quick smoke test.
Extract the archive with GS ShrinkIt, or copy the files from the ProDOS
image, preserving their file types. From an ORCA-compatible shell:

```text
lua -E hello.lua
lua -E hwsmoke.lua
lua -E -i
```

The smoke test ends with `SMOKE DONE - expect shell prompt next`.
Leave the interactive prompt with `os.exit()`.
Lua is a shell executable; the transfer image is not a boot disk.
See [installation](docs/INSTALL.md) and [usage](docs/USAGE.md).

The [examples](examples/README.md) include an adventure, blackjack, Life,
mazes, Mandelbrot text graphics, word counts, and coroutine demos.

## Which package?

| Package | Use |
| --- | --- |
| Standard: `LUA.SHK` / `lua.po` | Source scripts, interactive prompt, compiler, examples |
| Compact: `LUASMALL.SHK` / `luasmall.po` | Smaller, bytecode-only interpreter; includes LUAC |
| Embedding: `lua-iigs-0.3.0-sdk.zip` | Full and compact libraries, matching headers, VM objects, C example |
| Diagnostics: `lua-iigs-0.3.0-diagnostics.zip` | Traced interpreter and hardware acceptance kits |
| Source: `lua-iigs-0.3.0-source.zip` | Complete buildable source, documentation, and tests |

The port uses 32-bit Lua integers and SANE extended floating point.
The standard `utf8` library, dynamic C-module loading, and `io.popen` are
not enabled. Desktop Lua bytecode is not interchangeable with IIgs bytecode.
See [compatibility](docs/COMPATIBILITY.md) for limits and supported behavior.

The established test platform is an accelerated ROM 03 IIgs with 8 MB RAM.
This is a tested configuration, not an established minimum requirement.
[Validation status](docs/VALIDATION.md) distinguishes hardware observations,
emulator checks, and the new distribution candidate.

## Build

On the development Mac, install GoldenGate, an ORCA/C 2.2.x SDK,
GNU make, and Python 3.9 or later. Packaging also needs AppleCommander,
CiderPress II, and nulib2. These dependencies are not bundled.

```sh
cp local.mk.example local.mk
make doctor
make
make test
```

See [building](docs/BUILDING.md), [embedding](docs/EMBEDDING.md),
[examples](examples/README.md), and [tests](tests/README.md).
The [porting notes](docs/PORTING.md) explain the changes from upstream Lua;
[release instructions](docs/RELEASING.md) describe the distribution process.

Lua's copyright and permission notice is preserved in [LICENSE.txt](LICENSE.txt).

## Powered by

- [ORCA/C](https://github.com/byteworksinc/ORCA-C)
- [GoldenGate](https://juiced.gs/store/golden-gate/)
- [Lua](https://www.lua.org/)
