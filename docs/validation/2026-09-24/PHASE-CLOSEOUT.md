# Published v0.2.1 validation phase complete

This phase validates the existing release and adds reusable regression kits.
It changes no interpreter, compiler, or native-host executable bytes and
does not require a new runtime release.

## Confirmed real-hardware results

The recorded system is an accelerated ROM03 Apple IIgs with 8 MB RAM.
The exact accelerator, storage device, and GS/OS version remain unconfirmed.

| Test | Result | Evidence |
| --- | --- | --- |
| Full Lua regression suite | Two completed runs, each 23 passed, zero failed, eight tests with intentional skips; both returned to `#`. The user confirmed a complete power-off/on before the second run. | [Suite hardware report](suite-hardware.json) |
| Standalone LUAC batch | Six checks passed, including debug/stripped bytecode beyond 64 KiB, expected syntax/depth rejection, and subsequent valid compilation; returned to `#`. | [Compiler hardware report](luac-hardware.json) |
| Native C host | 100 C-hook yields, successful verification and fresh-process Lua smoke, then final HOSTCHECK pass and `#`. | [Host hardware report](host-hardware.json) |

The suite incorporates large binary transfers, source/bytecode roundtrips,
and 120 file-lifetime cases. Its final table test verifies 49,152 entries;
an earlier hardware run took about 18 minutes for that test alone. There
is no measured total duration for the two full-suite runs.

The release is v0.2.1, build `e026f5b-13178cdf3c75`. Hardware records preserve
the tested archive and executable hashes, and distinguish visible banners
from artifact identities established by staging and session context.

## Reusable deliverables

- [Lua suite](../../../tests/SUITE.md): manifest, driver, named groups,
  local runner, ShrinkIt packager, and strict completion checks.
- [Standalone compiler kit](../../../tests/LUAC_TESTING.md): six-check ORCA
  EXEC batch and phase verifier using unchanged release executables.
- [Native host kit](../../../tests/HOST_TESTING.md): ORCA EXEC batch,
  exit-status/output verification, and post-host smoke.
- Regression checks for missing markers, misleading pass output,
  unexpected exit statuses, and other verifier failures.

Keep compiler and host packages in separate directories: both intentionally
use `TEST.SHK`, `TEST`, and `TEST.LUA` to minimize hardware retyping. The
suite uses `SUITE.SHK` and runs `20:luatest -E -v test.lua`. The current
hardware prefix is `20:`; generated ORCA batch files contain no semicolons.

The closeout suite archive adds `LICENSE.TXT` and updates only README.TXT.
Every executable, Lua script, and generated configuration byte matches the
hardware-tested archive. The original hardware package report is retained;
the [closeout package report](suite-closeout-package.json) records the new
archive hash and all member hashes. All members were extracted and compared,
and executable metadata was verified. No additional hardware run is claimed
for this documentation-only repackaging.

## Local verification and limits

All 22 kit/runner checks pass with real IIgs-binary fault injection. The
final local full-suite run passes 23 tests with eight skips using the
explicitly selected diagnostic GoldenGate build; see
[log](suite-closeout.log) and [report](suite-closeout-report.json).
Installed GoldenGate has different EOF/text behavior; its previously
verified supported subset is the 15-test runtime group. Emulator results
remain separate from hardware evidence.

This is a completed acceptance phase for the adapted tests on the recorded
machine, not full upstream conformance. The upstream C test harness remains
unavailable, and documented platform skips remain. Raw Memory Manager and
allocator fault-injection executables are separate coverage. Other hardware
configurations and long-duration resource-leak testing are future work.
No further hardware rerun is needed solely to close this phase.
