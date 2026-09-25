# Validation status

## Established baseline

The runtime sources are preserved from development commit
`614a65bd7f3b6fdee297b57ceafd16b80a5ba697`. [BASELINE.json](BASELINE.json)
records their hashes, upstream provenance, and executable identities.
The complete earlier history, release assets, and hardware evidence are
preserved in the maintainer's local recovery archive.

Reported hardware is an accelerated ROM 03 IIgs with 8 MB RAM.
OS/shell versions and accelerator model/speed are incompletely recorded.

| Artifact | Recorded hardware evidence |
| --- | --- |
| Published 0.2.1 LUA | Full adapted suite reported passing twice; includes numeric conversions and adapted file I/O. Binary offsets through 262,163 bytes also checked with small transfers. |
| 0.2.1 LUAC and IIGSHOST | Standalone compiler and native embedding/C-hook batches passed, returning to the shell. |
| Build 63eca55c48e5 LUASMALL | Revised compact kit passed in one warm run, with chunks compiled on the IIgs by LUAC. Final stripped completion was photographed; prior phases are inferred from the stop-on-failure batch. No cold repeat. |
| Build 63eca55c48e5 LUA and LUATRACE | Reduced smoke/trace batch reported passing in one warm run. A progress photo supports intermediate steps; final completion was user-reported. Full-suite coverage was not repeated for these banner-changed bytes. |

Upstream-suite adaptations and skipped coverage are described in
[compatibility](COMPATIBILITY.md) and [tests](../tests/README.md).
No complete upstream test-suite percentage is claimed.

## Distribution 0.3.0

The reorganization changes paths, tooling, documentation, and packaging.
It intentionally leaves runtime source bytes and compile/link settings intact.
Local builds, test reports, and package manifests are generated from the
candidate and kept beside its artifacts. Byte comparisons establish whether
those binaries match a baseline; source equality alone does not establish it.

On September 25, 2026, the maintainer reported that acceptance testing worked
and approved publication. [ACCEPTANCE.json](ACCEPTANCE.json) records that report,
the accepted candidate's source commit and manifest hash, and its executable
hashes. Individual kit results, machine details, and a new hardware transcript
were not supplied with that approval; no additional per-kit coverage is inferred.

The release retains those accepted executable bytes. Final publication changes
update documentation and acceptance records. GoldenGate checks remain separate
from the maintainer's hardware report. See the
[hardware procedure](../tests/hardware/PROCEDURE.md) for recording future runs.
