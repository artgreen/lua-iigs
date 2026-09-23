# Documentation map

The repository's default branch is `master`. The
[v0.2.1 release](https://github.com/artgreen/lua-iigs/releases/tag/v0.2.1)
includes PR #15's hardware-validated minimum-integer fix. Its binaries were
rebuilt from merged commit `e026f5b`; the same source inputs passed hardware
math testing as `IIgs aa385d7-13178cdf3c75 plain`. Rebuilds retain their own
identities and do not replace the archived hardware-tested bytes.

## Current guidance

| Task | Guide |
| --- | --- |
| Understand the project and run Lua | [Project README](../README.md) |
| Build, package, and verify artifacts | [Building](BUILDING.md) |
| Transfer files and validate a new build on hardware | [Hardware testing](../HARDWARE_TESTING.md) |
| Run local regression checks and interpret coverage | [Tests](../tests/README.md) |
| Embed Lua or register a C module | [Embedding](EMBEDDING.md) |
| Try the bundled demonstrations | [Examples](../examples/README.md) |
| Check platform limits and outstanding work | [Limitations](LIMITATIONS.md) |
| Understand stack and allocator protections | [Implementation notes](CORRUPTION-ANALYSIS.md) |

## Evidence and provenance

- [Hardware results](validation/HARDWARE_RESULTS.md) is chronological. Early pending
  items and unsuccessful runs are preserved; the latest summary describes
  current status. User reports and photographs are distinguished from logs.
- [I/O investigation](validation/IO_INVESTIGATION.md) separates fixture
  defects, the emulator EOF guard, and the pending hardware text-mode probe.
- [September 22 LUAREVIEW record](validation/2026-09-22/README.md) identifies
  an earlier tested artifact, its source commit, local checks, and hardware
  follow-up.
- [September 21 LUAPATH record](validation/2026-09-21/README.md) preserves the
  earlier tested baseline and its coverage correction.
- [PR #13 review disposition](PR13-REVIEW.md) records the fixes and alternatives
  adopted during review.

The public manifest copies redact a local SDK path; original checksums remain
as evidence for the preserved packages. Do not regenerate those checksums
merely because documentation changed. Binaries, disk images, SDKs, and logs
under `build/` are not included in a fresh clone. Rebuilding creates new evidence.

## Historical material

[CORRUPTION-HISTORY.md](history/CORRUPTION-HISTORY.md) is the archived July notebook;
it includes retracted hypotheses and superseded constants. It is not a
build guide or a current to-do list. The obsolete root planning pointer has
been removed; use the implementation and limitations guides for current work.
[firsttest.txt](history/firsttest.txt) is an early Lua 5.4.4 transcript, not a
result for this Lua 5.4.6 build.
