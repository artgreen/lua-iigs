# Documentation map

The repository's default branch is `master`. PR #13 merged as `b911c3c`;
its runtime source was hardware-tested under the archived identifier
`IIgs 9add073-776024bcfb02 plain`. Documentation changes after that build do
not change the identity or contents of the archived executable.

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
- [September 22 LUAREVIEW record](validation/2026-09-22/README.md) identifies
  the current tested artifact, its source commit, local checks, and hardware
  follow-up.
- [September 21 LUAPATH record](validation/2026-09-21/README.md) preserves the
  earlier tested baseline and its coverage correction.
- [PR #13 review disposition](PR13-REVIEW.md) records the fixes and alternatives
  adopted during review.

Manifests and original checksums are evidence: do not regenerate them merely
because documentation changed. Binaries, disk images, SDKs, and logs under
`build/` are not included in a fresh clone. Rebuilding creates new evidence.

## Historical material

[CORRUPTION-HISTORY.md](history/CORRUPTION-HISTORY.md) is the archived July notebook;
it includes retracted hypotheses and superseded constants. It is not a
build guide or a current to-do list. The obsolete root planning pointer has
been removed; use the implementation and limitations guides for current work.
[firsttest.txt](history/firsttest.txt) is an early Lua 5.4.4 transcript, not a
result for this Lua 5.4.6 build.
