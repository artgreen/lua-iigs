# PR #13 review disposition

This records the response to the inline stack-guard finding and the numbered
[automated review](https://github.com/artgreen/lua-iigs/pull/13#issuecomment-5777966180).
Validation evidence is in [the candidate record](validation/2026-09-22/README.md).
The original LUAPATH baseline is preserved; this review candidate still needs
hardware confirmation.

| Finding | Disposition |
| --- | --- |
| Inline P1: library/bridge guard absent | Fixed. Shared public lua_iigs_initstack contract, expanded bridge stack, and state creation refused before initialization. C-host regression verifies refusal/recovery. |
| 1: silent allocator degradation | Fixed observability. One unconditional warning identifies the last probe failure; luaL_iigsmmstatus and -v expose status. Fallback remains strictly below 30,000 bytes, so recurrence of the >32KB corruption was not established by this finding. |
| 2: kit does not verify MM activation | Fixed. The traced mmalloc workload must initialize MM successfully. Degradation rejects any ordinary test run. Small scripts need not initialize it; sieve legitimately leaves it untested. |
| 3: cutoff/probe-size mismatch | Documented the conservative 16KB cutoff. Added full payload tests above 32KB and across banks. Kept the small startup attribute probe to avoid disabling MM merely because a larger startup probe cannot allocate under memory pressure. Its limited meaning is explicit. |
| 4: missing table overflow coverage | Added tableovf for append/rehash overflow and preserved entries; the C host separately invokes the array-size rejection branch and checks retained data. |
| 5: false hwtest pass | Fixed. Unsupported Lua-hook yielding is counted as skipped; ALL TESTS PASSED requires no skips. Deep C recursion checks the error, and GC checks live data. The actual C-hook yield/resume path now has a C regression test. |
| 6: fallback dead zones | Fixed both; allocator fault injection covers initial heap exhaustion and transient MM failure. Large requests remain excluded from C-heap fallback. |
| 7: stale planning document | Replaced the planning entry point with current links. Published current constants/limits and retained the old notebook as explicitly historical evidence, including retracted theories rather than deleting them. |
| 8: baseline provenance | Preserved original manifest/checksums and tied its runtime inputs to commit 9add073. Explained pre-commit banner and post-build documentation difference; no claim of byte-identical rebuilds. |
| 9: duplicated stack constants/prototype | Shared size/slack/derived usable size in luaconf.h. All hosts use the same declaration in lua.h; no handwritten extern. Documented outermost-frame and process-global restrictions. |
| 10: unwired/stale tests | Targeted runner shared with kit; added hookyield/errors/events/math/verybig and new regressions. Broad runner now propagates failures and creates scratch dirs. Only files remains expected-failing. Human-read localizers stay outside the pass/fail set. mmtest/memfree have build targets; mmtest returns nonzero on detected errors. |
| 11: unconditional platform flags | Changed events/verybig and related test flags to detect this port's version. Regenerated cobeacon to match coroutine. |
| 12: MAXCCALLS comment | Clarified restoration of upstream 200 from port-specific 128 and the separate portable counter behavior. Kept upstream value for other platforms. The suggested 56% unprobed-window increase does not describe initialized IIgs hosts, which probe on every checked call. Uninitialized hosts now fail state creation. |
| 13: misplaced checkcstack comment | Replaced with an accurate description directly above the function. |

Additional suggestions addressed:

- Shrink failures produce trace diagnostics while retaining the larger block;
  requested-size GC accounting can understate physical memory after failure.
- Deliberate refusal to dispose an invalid handle is documented, including
  the three-probe bound. Disposing an untrusted handle is not a safe fix.
- Correct limit formatting using a cast after clamping (Lua's formatter
  does not support the suggested %u), stale stack-size/grammar comments,
  and explicit default-path limitations; path root cause remains unproven.
- Anchored completion markers and closed stdin for automated invocations.
- Optional library-copy errors now propagate; missing parseconf grep is quiet.
  Restored the explanatory library-build failure comment.
- Added a cobeacon generator and synchronization check. Kept its historical
  beacon numbering to remain comparable with hardware photographs.
- Documented diagnostic-only scripts and standalone tool limitations.
- Building/testing bridge exposed its missing module declaration and an
  existing explicit-free/shutdown-GC double-free; both were corrected.

Not claimed complete: real hardware validation of this candidate, the full
upstream T C API harness, or the pre-existing files.lua I/O defect. None is
silently represented as passing by the new targeted validation report.
