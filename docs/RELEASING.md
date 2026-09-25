# Preparing a release

`VERSION` is the distribution version; the Lua language version remains
5.4.6. Update `CHANGELOG.md` and the download catalog with each release.

1. Finish and commit the source tree. Run `make doctor` and `make test-build`.
2. Run `make identify` and keep the printed build directory.
3. Run all checks against that exact directory:

```sh
make test BUILD=<directory> CHECKS="unit targeted luac compact hosts trace"
make release BUILD=<directory> REPORT=<printed-report.json>
```

The release command requires every check exactly once in all groups, matching
executable hashes and the current test inputs. It refuses uncommitted source
changes or a build whose runtime/host sources differ from the committed tree.
It assembles packages without recompiling executables.
The hardware-only `memfree` tool is recorded as built, not run, and excluded
from the executed pass count. Assembly happens under `build/release-staging/`;
only a completed, verified candidate moves into `dist/`. Failed staging
directories remain available for diagnosis.

The result is a new directory under `dist/` containing standard and compact
`.SHK` / `.po` pairs, SDK and diagnostics ZIPs, a source ZIP, manifests,
the cited report, and `SHA256SUMS`. The SDK contains separate full/compact
containers, plus a metadata-preserving embedding source container. Both ZIP
bundles include the guides, with external source links pinned to the commit.
Diagnostics contain the `suite`, `lua`, `small`, `luac`, and `host` kits.
The traced interpreter ships separately as `LUATRACE.SHK` / `luatrace.po`
and is also included in the `lua` kit. Unzip those outer bundles on the
transfer computer, then use their `.SHK` or `.po` containers on the IIgs.

The source ZIP includes a source manifest with originating commit and hashes.
Validate it in a fresh directory without Git using an explicitly selected SDK.
Local preflight results are emulator checks; hardware status starts pending.

4. Run the supplied acceptance kits on real hardware. Record configuration,
   exact executable hashes, completion markers, shell return, and any skips.
   Keep the reports with the candidate. Do not silently replace artifacts
   after hardware acceptance; new bytes need their own validation.
5. Review the source tree, downloads, checksums, release notes, and hardware
   record. Tag and upload the reviewed artifacts only after approval.

There is no automatic publishing command. GitHub uploads, tags, branch
replacement, and cleanup of old releases are separate maintainer actions.
The first clean-history release is 0.3.0; earlier tags are not reused.
