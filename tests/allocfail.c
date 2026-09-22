/* Fault-inject the actual allocator implementation on the target ABI.
** Include lauxlib.c so static allocation paths can be exercised without
** adding test controls to the shipped library. Link against lua.lib;
** its lauxlib member is not needed because this object supplies it. */
#define LUA_LIB
#pragma path "../src"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <memory.h>
#include <orca.h>
#include "lua.h"
#pragma memorymodel 1
#pragma stacksize LUA_IIGS_STACK_SIZE

static int fail_heap, fail_mm;
static long fail_size;
static int mm_calls;
static void *fault_malloc(size_t n) {
  if (fail_heap) return NULL;
  return malloc(n);
}
static Handle fault_newhandle(long n, Word user, Word attr, Pointer where) {
  mm_calls++;
  if (fail_mm || n == fail_size) return NULL;
  return NewHandle(n, user, attr, where);
}
#define malloc fault_malloc
#define NewHandle fault_newhandle
#include "../src/lauxlib.c"
#undef malloc
#undef NewHandle

#define CHECK(c) do { if (!(c)) { \
  fprintf(stderr, "FAIL allocator at line %d\n", __LINE__); return 1; \
} } while (0)

int main(void) {
  void *p, *q;
  int calls;
  CHECK(strcmp(luaL_iigsmmstatus(), "untested") == 0);
  fail_heap = 1;
  p = any_new(64);
  CHECK(p != NULL && mma_state == 1);
  CHECK(*(Handle *)((char *)p - MMA_HDR) != NULL);
  any_free(p);
  fail_heap = 0;

  /* MM is healthy, but one allocation cannot be satisfied. */
  fail_size = 20000L + MMA_HDR;
  p = any_new(20000);
  CHECK(p != NULL && mma_state == 1);
  CHECK(*(Handle *)((char *)p - MMA_HDR) == NULL);
  any_free(p);
  fail_size = 40000L + MMA_HDR;
  CHECK(any_new(40000) == NULL); /* never send this size to the C heap */
  fail_size = 0;

  p = any_new(20000);
  CHECK(p != NULL);
  memset(p, 0x5A, 20000);
  fail_size = 40000L + MMA_HDR;
  q = l_alloc(NULL, p, 20000, 40000);
  CHECK(q == NULL && ((char *)p)[0] == 0x5A && ((char *)p)[19999] == 0x5A);
  fail_size = 0;
  any_free(p);

  /* Startup MM failure: warn once, bound fallback, retain degraded state. */
  mma_state = 0;
  fail_mm = 1;
  p = any_new(20000);
  CHECK(p != NULL && mma_state == -1);
  any_free(p);
  calls = mm_calls;
  CHECK(any_new(30000) == NULL);
  CHECK(any_new(40000) == NULL);
  p = any_new(20000);
  CHECK(p != NULL && mm_calls == calls);
  any_free(p);
  CHECK(strcmp(luaL_iigsmmstatus(), "degraded") == 0);
  puts("ALLOCFAIL PASSED");
  return 0;
}
