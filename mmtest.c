/*
** mmtest.c -- standalone Memory Manager probe for the Apple IIgs.
**
** Performs exactly the tool sequence lua's hybrid allocator uses,
** announcing every step BEFORE doing it and printing every returned
** value, so a photo of the screen shows precisely what the real
** Memory Manager did -- with no Lua involved at all.
**
** Build:  iix compile -P +O mmtest.c ; iix link mmtest KEEP=mmtest
*/

#pragma memorymodel 1
#pragma lint -1

#include <stdio.h>
#include <stdlib.h>
#include <memory.h>
#include <orca.h>

static int errs = 0;

static void say (const char *s) {
  printf("%s\n", s);
  fflush(stdout);
}

static void sayx (const char *label, unsigned long v) {
  printf("  %s=%08lX\n", label, v);
  fflush(stdout);
}

/* fill block with 'pat' and verify every byte; report first mismatch */
static int fillcheck (const char *name, char *p, long n, int pat) {
  long i;
  for (i = 0; i < n; i++) p[i] = (char) pat;
  for (i = 0; i < n; i++) {
    if (p[i] != (char) pat) {
      printf("  %s MISMATCH at +%08lX got %02X want %02X\n",
             name, i, (unsigned char) p[i], pat);
      fflush(stdout);
      errs++;
      return 0;
    }
  }
  printf("  %s fill+verify ok (%ld bytes of %02X)\n", name, n, pat);
  fflush(stdout);
  return 1;
}

/* re-verify without refilling (detects later overlap) */
static int recheck (const char *name, char *p, long n, int pat) {
  long i;
  for (i = 0; i < n; i++) {
    if (p[i] != (char) pat) {
      printf("  %s CLOBBERED at +%08lX got %02X want %02X\n",
             name, i, (unsigned char) p[i], pat);
      fflush(stdout);
      errs++;
      return 0;
    }
  }
  printf("  %s still intact\n", name);
  fflush(stdout);
  return 1;
}

static Handle grab (const char *label, long size, Word attr) {
  Handle h;
  printf("%s: NewHandle size=%08lX attr=%04X\n", label, size, attr);
  fflush(stdout);
  h = NewHandle(size, userid(), attr, NULL);
  printf("  toolerr=%04X handle=%08lX\n", toolerror(), (unsigned long) h);
  fflush(stdout);
  if (toolerror() || h == NULL) { errs++; return NULL; }
  sayx("master", (unsigned long) *h);
  CheckHandle(h);
  printf("  CheckHandle toolerr=%04X\n", toolerror());
  fflush(stdout);
  if (toolerror()) { errs++; return NULL; }
  return h;
}

int main (void) {
  Handle a = NULL, b = NULL, big = NULL;
  char *pa = NULL, *pb = NULL, *pc = NULL, *pbig = NULL;
  Word full = (Word)(attrLocked | attrFixed | attrNoSpec | attrNoCross);
  Word nocrossless = (Word)(attrLocked | attrFixed | attrNoSpec);

  say("MMTEST start");
  printf("userid=%04X\n", userid()); fflush(stdout);
  /* (FreeMem/MaxBlock omitted: GoldenGate doesn't implement $1B02) */

  a = grab("T1 16K block A", 16388L, full);
  if (a != NULL) { pa = (char *) *a; fillcheck("A", pa, 16388L, 0xA5); }

  b = grab("T2 16K block B", 16388L, full);
  if (b != NULL) { pb = (char *) *b; fillcheck("B", pb, 16388L, 0x5A); }
  if (pa != NULL) recheck("A", pa, 16388L, 0xA5);

  say("T3 malloc 20000 between MM blocks");
  pc = (char *) malloc(20000L);
  sayx("malloc", (unsigned long) pc);
  if (pc != NULL) fillcheck("C", pc, 20000L, 0x33);
  if (pa != NULL) recheck("A", pa, 16388L, 0xA5);
  if (pb != NULL) recheck("B", pb, 16388L, 0x5A);

  big = grab("T4 45K no-cross", 45060L, full);
  if (big == NULL) {
    say("T4 failed; T5 45K may-cross instead");
    big = grab("T5 45K may-cross", 45060L, nocrossless);
  }
  if (big != NULL) { pbig = (char *) *big; fillcheck("BIG", pbig, 45060L, 0xC3); }
  if (pa != NULL) recheck("A", pa, 16388L, 0xA5);
  if (pb != NULL) recheck("B", pb, 16388L, 0x5A);
  if (pc != NULL) recheck("C", pc, 20000L, 0x33);

  if (a != NULL) {
    say("T6 SetHandleSize shrink A to 8K");
    SetHandleSize(8196L, a);
    printf("  toolerr=%04X\n", toolerror()); fflush(stdout);
    recheck("A(8K)", pa, 8196L, 0xA5);
    if (pb != NULL) recheck("B", pb, 16388L, 0x5A);
  }

  say("T7 DisposeHandle A, B, BIG");
  if (a != NULL) { DisposeHandle(a);
    printf("  A toolerr=%04X\n", toolerror()); fflush(stdout); }
  if (b != NULL) { DisposeHandle(b);
    printf("  B toolerr=%04X\n", toolerror()); fflush(stdout); }
  if (big != NULL) { DisposeHandle(big);
    printf("  BIG toolerr=%04X\n", toolerror()); fflush(stdout); }
  if (pc != NULL) recheck("C", pc, 20000L, 0x33);

  printf("MMTEST DONE errs=%d\n", errs);
  fflush(stdout);
  return 0;
}
