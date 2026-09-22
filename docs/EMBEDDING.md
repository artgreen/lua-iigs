# Embedding Lua in an IIgs application

From the repository root, run `make lua` followed by `make liblua`.
The first step builds the VM object that the current library target assumes
already exists.
Link both `src/lvm.a` and `src/lua.lib`, using headers from the same build.
The Makefile also copies both into `build/`. The VM object is separate from
the library; linking only `lua.lib` is incomplete.

## Required stack initialization

Every IIgs host must:

1. Include `lua.h` and request `#pragma stacksize LUA_IIGS_STACK_SIZE`.
2. Declare a local `char` in `main` whose frame remains alive during all Lua use.
3. Call `lua_iigs_initstack(&anchor)` before `lua_newstate` or `luaL_newstate`.
4. Check for a null state and close every created state before leaving that frame.

The initializer estimates guard positions within the requested bank-0 stack;
it cannot allocate or enlarge that stack. Calling it from a helper whose
frame returns does not meet the contract. The guard and error-grace state
are process-global, shared by all Lua states. Keep those states on the same
native stack; do not reinitialize the guard while Lua is active on another
stack. Hosts that omit initialization receive NULL from state creation.

This requirement was added in PR #13. The interpreter, compiler, bridge,
and focused C-host regression follow it. A custom allocator passed to
`lua_newstate` does not remove the stack-initialization requirement, and
is not automatically the hybrid allocator used by `luaL_newstate`.

## Minimal shell host

Save as `host.c` in the repository root. The example loads one script,
reports a load/runtime error, and closes the state.

```c
#pragma path "src"
#include <stdio.h>
#include "lua.h"
#include "lauxlib.h"
#include "lualib.h"

#pragma memorymodel 1
#pragma stacksize LUA_IIGS_STACK_SIZE

int main(int argc, char *argv[]) {
    char anchor;
    lua_State *L;
    int status;

    if (argc != 2) {
        fprintf(stderr, "Usage: host script.lua\n");
        return 1;
    }
    lua_iigs_initstack(&anchor);
    L = luaL_newstate();
    if (L == NULL) {
        fprintf(stderr, "Cannot create Lua state\n");
        return 1;
    }
    luaL_openlibs(L);
    status = luaL_loadfile(L, argv[1]);
    if (status == LUA_OK)
        status = lua_pcall(L, 0, LUA_MULTRET, 0);
    if (status != LUA_OK)
        fprintf(stderr, "%s\n", lua_tostring(L, -1));
    lua_close(L);
    return status == LUA_OK ? 0 : 1;
}
```

With the SDK selected as in [building](BUILDING.md):

```sh
make lua
make liblua
iix compile -I -P -D +O host.c
iix link host src/lvm src/lua.lib KEEP=host
iix --memcheck host tests/hwsmoke.lua
```

The minimal host is not the interpreter CLI: it does not implement `-E`,
`-v`, a REPL, or construct the interpreter's `arg` table. It opens the
standard libraries directly. Production hosts can wrap library setup in a
protected call if they need to recover from initialization errors too.

## Registering a C module

The default port has no native shared-library loader. Link the module into
your host and register its `luaopen_...` function after opening libraries:

```c
luaL_requiref(L, "test_iface", luaopen_test_iface, 1);
lua_pop(L, 1);
```

Then Lua can call `require("test_iface")`. The bundled example is
`test.c` (host), `testiface.c` (Lua bindings), `testbridge.c` (C collection),
and `bridge.lua` (script). Run it on the development Mac with:

```sh
make lua
make bridge
iix --memcheck bridge bridge.lua
```

The bridge's explicit free is idempotent with its GC finalizer, but the demo
is not a hardened container API: indices, allocation failures, and access
after explicit free are not fully validated. Do not copy those unchecked
operations into an application without adding its required checks.

## Validation and diagnostics

`tests/iigshost.c` exercises the library initialization contract, overflow
recovery, array/vector limits, and yielding from a native C hook. The
hardware-kit builder compiles, links, runs, and packages that host. A Lua
`debug.sethook` callback cannot replace the native yielding-hook test.

`luaL_iigsmmstatus()` returns a read-only string describing the hybrid
allocator's startup state: `untested`, `ok`, `degraded`, or `disabled`.
It does not trigger a probe. The status applies to this auxiliary-library
allocator, not an arbitrary custom allocator supplied by a host.

See [implementation notes](CORRUPTION-ANALYSIS.md) for the current stack
floors, allocator thresholds, and recovery behavior. Keep all objects and
headers consistent when changing those settings, and validate a rebuilt
host on hardware; the interpreter's pass does not certify a new embedding.
