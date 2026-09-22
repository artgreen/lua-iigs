
#pragma path "src"

#include <stdio.h>
#include <stdlib.h>
#include "lua.h"
#include "lauxlib.h"
#include "lualib.h"
#include "testiface.h"

#ifdef LUA_USE_IIGS
#pragma memorymodel 1
#pragma stacksize LUA_IIGS_STACK_SIZE
#endif

int main(int argc, char *argv[]) {
    lua_State *L;
#ifdef LUA_USE_IIGS
    char stackanchor;
    lua_iigs_initstack(&stackanchor);
#endif
    // Initialize the LUA state
    printf("Initialize the LUA state\n");
    L = luaL_newstate();
    if (L == NULL) {
        fprintf(stderr, "Cannot create Lua state\n");
        return 1;
    }
    printf("Opening libs\n");
    luaL_openlibs(L);

    // Load the test_iface library
    printf("Loading test_iface library\n");
    luaL_requiref(L, "test_iface", luaopen_test_iface, 1);
    lua_pop(L, 1);

    // Load and execute the LUA script
    printf("Executing %s\n", argc > 1 ? argv[1] : "bridge.lua");
    if (luaL_loadfile(L, argc > 1 ? argv[1] : "bridge.lua") || lua_pcall(L, 0, 0, 0)) {
        fprintf(stderr, "Error running script: %s\n", lua_tostring(L, -1));
        lua_close(L);
        return 1;
    }

    // Close the LUA state
    printf("Closing LUA state... Byeeeeeeeeeee!\n");
    lua_close(L);
    return 0;
}
