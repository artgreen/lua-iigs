# Install Lua on the Apple IIgs

Use an ORCA-compatible shell. The recorded hardware is an accelerated
ROM 03 IIgs with 8 MB RAM; smaller and unaccelerated configurations have
not been established as supported minimums. GS/OS was reported tentatively
as 6.0.4; the exact system version still needs confirmation.

1. Download `LUA.SHK` (standard) or the equivalent `lua.po` transfer image.
2. Transfer the container as binary. Do not apply text conversion to it.
3. Extract with GS ShrinkIt into a writable directory, or mount/copy from
   the ProDOS image with a tool that preserves file types.
4. Open the shell, change to that directory, and run:

```text
lua -E -v
lua -E hello.lua
lua -E hwsmoke.lua
```

Expect the Lua version/build banner, a greeting, then
`SMOKE DONE - expect shell prompt next` and a return to the shell prompt.
Compare the banner with the package README and build manifest.

Executables must retain type EXE `$B5`, auxiliary type `$0000`.
A file copied as ordinary host data may lose this metadata. Transfer the
`.SHK` or `.po` container and extract it on the IIgs instead.
The disk image is a transfer volume, not a bootable operating system.

For compact Lua, install `LUASMALL.SHK`. Compile your script with its LUAC
on the IIgs, then run the resulting binary chunk:

```text
luac -o hello.luo hello.lua
luasmall -E hello.luo
```

The compact package includes `HELLO.LUA` for this check. It has no text
parser or interactive Lua prompt. Preserve `.luo` files as binary.
See [compatibility](COMPATIBILITY.md) for floating-point constant folding
and bytecode restrictions, and [usage](USAGE.md) for modules and examples.
