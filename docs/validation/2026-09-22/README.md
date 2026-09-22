# PR-review candidate validation, 2026-09-22

Candidate: `IIgs 9add073-776024bcfb02 plain`, executable LUAREVIEW.
Built from the review working tree before committing; 9add073 is the
parent HEAD, not the tree being claimed as the candidate. The accompanying
manifest hashes identify the exact source/tooling inputs. These inputs
match the commit introducing this record. Unlike the preserved September
21 baseline, this candidate has **not been run on real hardware**.

Local kit: `build/hardware/20260922T145111Z-5t_54b1b/`.
The original package manifest and checksums are preserved unchanged;
ARCHIVE-SHA256SUMS covers the ShrinkIt archives in nas-transfer. Large
binaries, images, archives, and raw logs remain gitignored. The NAS was not
mounted when this candidate was prepared, so no new NAS copy was made.

## Completed checks

- Fifteen targeted scripts in each of plain and trace builds under
  GoldenGate --memcheck. Intentional T-harness/16-bit-limit skips are
  listed in the manifest rather than silently represented as coverage.
- hwtest: 19 assertions passed, 0 failed, 1 skipped (Lua hook yielding).
- iigshost: rejected initialization omission, caught stack overflow,
  rejected an oversized array while preserving its old entry, checked
  the vector-growth limit/error format at INT_MAX, and
  completed 100 yields/resumes from a real C hook with the correct sum.
- tableovf: caught table overflow after 49,152 successful insertions;
  all surviving entries remained intact before and after collection.
- mmalloc: complete, distinct payload checks through 131,072 bytes; traced run
  explicitly confirms the startup MM probe succeeded.
- allocfail: forced small-heap failure before MM initialization; forced
  transient MM failure with bounded C-heap fallback; verified large
  allocations never fall back; failed growth preserves the original data;
  failed startup probes emit exactly one warning and remain degraded.
- bridge demo and cstack completed without memory alteration/BRK reports.
  The demo's explicit free followed by shutdown GC is safe.
- mmtest completed with errs=0. memfree was compiled only (GoldenGate
  does not implement all the Memory Manager query tools it uses).
- luac: source/bytecode smoke roundtrip and excessive parser nesting
  rejected with C stack overflow and no memory alteration/BRK reports.
- Seven Python negative/synchronization checks passed. They reject
  incidental OK strings, corruption despite success markers, missing MM
  activation in the allocation test, and missing shutdown markers.
- The new runner propagates a failed invocation as nonzero. The broader
  30-script passing group completed with exit/memory checks; some scripts
  skip unsupported sections and some are helpers, so this is not a claim
  of full upstream API coverage. Logs: build/test-runs/tmpuo_vkpag.
- files.lua still fails at line 323 after a garbled I/O roundtrip, matching
  the historical unresolved issue (build/test-runs/tmpcn74sg45/files.log).
- Images were exported and compared byte-for-byte; archive executables
  were independently extracted with NuLib2 and compared. EXE $B5/$0000
  metadata was verified. All three transfer images remain 800 KB.

## Hardware handoff

Preserve the existing LUAPATH installation. Extract LUAREVIEW.SHK into a
new directory and IIGSHOST.SHK alongside it using GS ShrinkIt. Check the
candidate banner above. Follow the candidate sequence in HARDWARE_TESTING.md.
LUATRACE.SHK is available if a failure needs localization. A returned shell
prompt is required after every command; none of the checks above substitutes
for that real-hardware validation.
