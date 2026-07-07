/*
** memfree.c -- print the real machine's memory situation.
** (Hardware-oriented: GoldenGate lacks FreeMem/$1B02 and friends.)
** Build: iix compile -P +O memfree.c ; iix link memfree KEEP=memfree
*/

#pragma memorymodel 1

#include <stdio.h>
#include <memory.h>
#include <orca.h>

int main (void) {
  printf("MEMFREE (userid=%04X)\n", userid());
  fflush(stdout);
  printf("TotalMem    = %08lX (%lu KB)\n", TotalMem(), TotalMem() >> 10);
  printf("FreeMem     = %08lX (%lu KB)\n", FreeMem(), FreeMem() >> 10);
  printf("MaxBlock    = %08lX (%lu KB)\n", MaxBlock(), MaxBlock() >> 10);
  printf("RealFreeMem = %08lX (%lu KB)\n", RealFreeMem(), RealFreeMem() >> 10);
  fflush(stdout);
  return 0;
}
