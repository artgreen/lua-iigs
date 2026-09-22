# Tested build provenance, 2026-09-22

Archived executable: LUAREVIEW, banner `IIgs 9add073-776024bcfb02 plain`.
Runtime source commit: `c5aab9c39b0a13621ad0dee9f1a67206b91f3d11`.
PR #13 merged into master as `b911c3c9cdc89f33b622b0cea768ef171877a1fd`.
The temporary name identifies the tested artifact; ordinary installations
and new distribution builds use `lua`.
Built from the review working tree before committing; 9add073 is the
parent HEAD, not the tree being claimed as the candidate. The accompanying
manifest hashes identify the exact source/tooling inputs. These inputs
match the commit introducing this record. Subsequent hardware testing has
user-reported targeted passes, including the original silent TABLEOVF and
IIGSHOST, with all runs returning to the shell. Original tableovf.lua took
about 18 minutes and reported 49,152 entries. See
[hardware results](../HARDWARE_RESULTS.md) for the diagnostic sequence
and evidence limits. The user also confirmed the requested five warm
coroutine/hwdiag2 pairs and one post-power-cycle pair (twelve launches),
with additional successful mixed-script testing in a warm session. These
are user-reported results; extra scripts/counts were not enumerated.

Local kit: `build/hardware/20260922T145111Z-5t_54b1b/`.
The original package manifest and checksums are preserved unchanged;
ARCHIVE-SHA256SUMS covers the ShrinkIt archives in nas-transfer. Large
binaries, images, archives, and raw logs remain gitignored. The NAS was not
mounted when this candidate was prepared. After remounting, the kit was
staged at `/Volumes/nas/LUA.20260922` and all copied bytes were verified.

## Recorded local checks (GoldenGate)

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

## Preserved transfer artifacts

Preserve the existing LUAPATH installation. Extract LUAREVIEW.SHK into a
new directory and IIGSHOST.SHK alongside it using GS ShrinkIt. Check the
archived banner above. The [hardware sequence](../../../HARDWARE_TESTING.md)
is complete for this build; it remains the procedure for validating changes.
LUATRACE.SHK is available if a failure needs localization. A returned shell
prompt was reported after the hardware runs. The local checks above are
listed separately so they are not mistaken for individually logged hardware
coverage. A rebuild must not inherit the archived binary's identity or results.

Plain executable SHA-256:
`5f56255a4f01b4685e59628835158f3194cc13d65cf4b09f259a6ccc9105a13d`.
LUAREVIEW.SHK SHA-256:
`bc545bff24ee7a4b0b15b1c4e68b29fb04842c579fb933c94ddaca111045c811`.

`SHA256SUMS` covers the original package directory, including its historical
HARDWARE_TESTING.md. The current guide has changed; do not overwrite that
checksum or run it against this documentation directory. ARCHIVE-SHA256SUMS
covers the separately generated archives under `nas-transfer/`. A fresh
clone contains the records, not these ignored binaries or images.

The files.lua failure recorded above remains unresolved. A later source
review found test-side instrumentation that consumes an extra read and
replacement-character bytes in the fixture; see
[limitations](../../LIMITATIONS.md#outstanding-validation-and-defects).
This qualification does not alter the original manifest or local log.
