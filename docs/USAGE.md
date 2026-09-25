# Using Lua

Run these commands from the directory containing the installed executables
and examples, or use the executable prefix configured in your ORCA shell.

```text
lua -E myscript.lua
lua -E -i
lua -E -e "print(2 + 2)"
luac -o program.luo myscript.lua
lua -E program.luo
```

`-E` ignores Lua environment settings, including `LUA_INIT` and `LUA_PATH`.
Omit it when you intentionally use those settings. `lua -E -i` starts the
interactive prompt; `os.exit()` returns to the shell.

Pure Lua modules default to `?.lua;?/init.lua`, relative to the working
directory. Keep a module beside the script using it, or configure
`package.path`. Without `-E`, `LUA_PATH_5_4` or `LUA_PATH` can override it.
C modules must be linked into a host; see [embedding](EMBEDDING.md).

Try `lua -E adventure.lua` for a short adventure, `lua -E blackjack.lua`
for a card game, or `lua -E maze.lua 42 solve` for a maze and its solution.
The standard package includes thirteen programs covering text graphics,
algorithms, file tools, and coroutine demos. `lua -E warehouse.lua` runs
a deterministic simulation with progress output.
See the [example catalog](../examples/README.md).

`luac -s -o program.luo myscript.lua` strips debug information. The compact
interpreter runs compatible compiled chunks with `luasmall -E program.luo`.
Compile on the IIgs when exact floating-point comparisons matter: GoldenGate
and hardware can fold constants at different precision. Keep the compiler
and runtime configurations compatible; desktop Lua bytecode is not portable.

Performance depends heavily on the workload. The table-growth stress test
took about 18 minutes silently on the established hardware. That test is
part of diagnostics, not the standard startup check.
