
#pragma path "src"

#include <stdio.h>
#include <stdlib.h>
#include "lua.h"
#include "lauxlib.h"
#include "lualib.h"
#include "testiface.h"

int main(int argc, char *argv[]) {
    // Initialize the LUA state
    printf("Initialize the LUA state\n");
    lua_State *L = luaL_newstate();
    printf("Opening libs\n");
    luaL_openlibs(L);

    // Load the test_iface library
    printf("Loading test_iface library\n");
    luaL_requiref(L, "test_iface", luaopen_test_iface, 1);
    lua_pop(L, 1);

    // Load and execute the LUA script
    printf("Executing bridge.lua\n");
    if (luaL_loadfile(L, "bridge.lua") || lua_pcall(L, 0, 0, 0)) {
        fprintf(stderr, "Error running script: %s\n", lua_tostring(L, -1));
        lua_close(L);
        return 1;
    }

    // Close the LUA state
    printf("Closing LUA state... Byeeeeeeeeeee!\n");
    lua_close(L);
    return 0;
}
