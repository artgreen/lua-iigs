
#pragma path "src"
#pragma noroot

#include "lua.h"
#include "lauxlib.h"
#include "lualib.h"
#include "testiface.h"

// Lua function to create a new collection object
int l_newCollection(lua_State *L) {
    size_t size = luaL_checkinteger(L, 1);
    Collection *collection = newCollection(size);
    void *userdata = lua_newuserdata(L, sizeof(Collection *));
    *(Collection **)userdata = collection;
    luaL_getmetatable(L, "test_iface.collection");
    lua_setmetatable(L, -2);
    return 1;
}

// Lua function to free a collection object
int l_freeCollection(lua_State *L) {
    Collection **collection = (Collection **)luaL_checkudata(L, 1, "test_iface.collection");
    freeCollection(*collection);
    return 0;
}

// Lua function to get the size of a collection
int l_getCollectionSize(lua_State *L) {
    Collection **collection = (Collection **)luaL_checkudata(L, 1, "test_iface.collection");
    size_t size = getCollectionSize(*collection);
    lua_pushinteger(L, size);
    return 1;
}

// Lua function to set a value in a collection
int l_setCollectionValue(lua_State *L) {
    Collection **collection = (Collection **)luaL_checkudata(L, 1, "test_iface.collection");
    size_t index = luaL_checkinteger(L, 2);
    int value = luaL_checkinteger(L, 3);
    setCollectionValue(*collection, index, value);
    return 0;
}

// Lua function to get a value from a collection
int l_getCollectionValue(lua_State *L) {
    Collection **collection = (Collection **)luaL_checkudata(L, 1, "test_iface.collection");
    size_t index = luaL_checkinteger(L, 2);
    int value = getCollectionValue(*collection, index);
    lua_pushinteger(L, value);
    return 1;
}

// List of functions to be registered with the test_iface module
static const luaL_Reg test_iface_functions[] = {
        {"newCollection", l_newCollection},
        {"freeCollection", l_freeCollection},
        {"getCollectionSize", l_getCollectionSize},
        {"setCollectionValue", l_setCollectionValue},
        {"getCollectionValue", l_getCollectionValue},
        {NULL, NULL}
};

// Function to create the test_iface module
int luaopen_test_iface(lua_State *L) {
    // Create a metatable for the Collection object
    luaL_newmetatable(L, "test_iface.collection");
    lua_pushvalue(L, -1);
    lua_setfield(L, -2, "__index");
    lua_pushcfunction(L, l_freeCollection);
    lua_setfield(L, -2, "__gc");
    lua_pop(L, 1);

    // Create a table to hold the test_iface functions
    luaL_newlib(L, test_iface_functions);

    // Return the table as the test_iface module
    return 1;
}
