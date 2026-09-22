# Lua tests

Upstream tests originate at https://www.lua.org/tests/.

`make -C tests tests LUA=/absolute/path/to/lua` runs the targeted regression
set under GoldenGate with memory checking, timeouts, explicit completion
markers, and nonzero status for failures. Logs and test scratch files are
isolated under build/test-runs. `make -C tests suite` runs the broader suite
and the known files.lua failure separately; an unexpected pass needs review.
C API portions requiring the unavailable T module remain skipped. The
verybig test covers its RK section and explicitly skips >64K programs on
IIgs. Platform scaling uses the IIgs version string, not an unconditional
flag. No host-platform run is claimed by these IIgs checks.

The hardware kit uses the same targeted contracts and adds:

- iigshost.c: initialization is required, stack-error recovery, oversized
  array/vector rejection and error formatting, and real C-hook yields/resumes
  (saved-PC regression).
- allocfail.c: actual allocator code with injected allocation failures,
  bounded fallback, retained data after failed growth, and one warning.
- mmalloc.lua: complete data checks across 16KB/32KB/64KB boundaries.
- tableovf.lua: append/rehash overflow, preserved entries, and GC afterward.
- hookyield.lua: call/line/count hook correctness; Lua hooks cannot yield.

`hwtest.lua` reports its unsupported Lua hook as a skip. The C-host test
covers the yielding C-hook path separately. The upstream C API harness is
still not supplied. Neither a completion marker nor GoldenGate proves
hardware reliability outside the exercised workloads.

`cobeacon.lua` is generated from coroutine.lua by
`python3 tools/generate-cobeacon.py`. The kit rejects an out-of-date copy;
`--check` verifies synchronization. Historical B numbering is retained.
Some B markers identify explanatory comments rather than operations.

Human-read localization tools (`stackcal.lua`, `hwdiag.lua`, `cobisect.lua`)
are intentionally outside the regression pass/fail set. They are useful
when a hardware failure needs narrowing, not evidence of full coverage.
Standalone `make mmtest memfree` builds Memory Manager probes. mmtest returns
failure if it detects an error; memfree requires real hardware tool support.
