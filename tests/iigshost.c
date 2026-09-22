/* Linked against lua.lib: host initialization and native C-hook yielding. */
#pragma path "../src"
#include <stdio.h>
#include <string.h>
#include "lua.h"
#include "lauxlib.h"
#include "lualib.h"
#include "lstate.h"
#include "ltable.h"
#include "lmem.h"
#pragma memorymodel 1
#pragma stacksize LUA_IIGS_STACK_SIZE

static void yieldhook(lua_State *L, lua_Debug *ar) {
  (void)ar;
  lua_yield(L, 0);
}

/* Directly exercise the array-size guard; appending tableovf.lua also
** exercises hash growth/rehash and need not hit this exact branch. */
static int arraylimit(lua_State *L) {
  Table *t;
  lua_newtable(L);
  lua_pushinteger(L, 42);
  lua_rawseti(L, -2, 1);
  lua_pushvalue(L, -1);
  lua_setglobal(L, "array_under_test");
  t = hvalue(s2v(L->top.p - 1));
  luaH_resize(L, t, 32769u, 0);
  return 0;
}

static int vectorlimit(lua_State *L) {
  int size = MAX_INT;
  luaM_growaux_(L, NULL, MAX_INT, &size, sizeof(int), UINT_MAX, "test vector");
  return 0;
}

int main(void) {
  char anchor;
  lua_State *L, *co;
  int status, nresults, yields = 0;
  /* A forgotten initializer must fail before allocating a Lua state. */
  L = luaL_newstate();
  if (L != NULL) {
    fprintf(stderr, "FAIL unarmed host accepted\n");
    return 1;
  }
  lua_iigs_initstack(&anchor);
  L = luaL_newstate();
  if (L == NULL) return 1;
  luaL_openlibs(L);
  if (luaL_dostring(L,
      "local function f() return 1 + f() end "
      "local ok,e=pcall(f); assert(not ok and e:find('stack overflow',1,true)); "
      "assert(2+3==5)") != LUA_OK) {
    fprintf(stderr, "FAIL host recovery: %s\n", lua_tostring(L, -1));
    lua_close(L);
    return 1;
  }
  lua_pushcfunction(L, vectorlimit);
  status = lua_pcall(L, 0, 0, 0);
  if (status != LUA_ERRRUN || lua_tostring(L, -1) == NULL ||
      strcmp(lua_tostring(L, -1), "too many test vector (limit is 32767)") != 0) {
    fprintf(stderr, "FAIL vector limit formatting\n");
    lua_close(L);
    return 1;
  }
  lua_pop(L, 1);
  lua_pushcfunction(L, arraylimit);
  status = lua_pcall(L, 0, 0, 0);
  if (status != LUA_ERRRUN || lua_tostring(L, -1) == NULL ||
      strstr(lua_tostring(L, -1), "table overflow") == NULL) {
    fprintf(stderr, "FAIL array limit\n");
    lua_close(L);
    return 1;
  }
  lua_pop(L, 1);
  if (luaL_dostring(L, "assert(array_under_test[1]==42); collectgarbage(); "
                       "assert(array_under_test[1]==42)") != LUA_OK) {
    fprintf(stderr, "FAIL array after rejected resize\n");
    lua_close(L);
    return 1;
  }
  co = lua_newthread(L);  /* keep thread rooted on parent stack */
  if (luaL_loadstring(co,
      "local s=0; for i=1,2000 do s=s+i end; return s") != LUA_OK) {
    lua_close(L);
    return 1;
  }
  lua_sethook(co, yieldhook, LUA_MASKCOUNT, 40);
  do {
    status = lua_resume(co, L, 0, &nresults);
    if (status == LUA_YIELD) yields++;
    if (yields > 10000) break;
  } while (status == LUA_YIELD);
  if (status != LUA_OK || nresults != 1 || yields < 2 ||
      lua_tointeger(co, -1) != 2001000L) {
    fprintf(stderr, "FAIL C hook: status=%d yields=%d\n", status, yields);
    lua_close(L);
    return 1;
  }
  lua_close(L);
  printf("IIGSHOST PASSED yields=%d\n", yields);
  return 0;
}
