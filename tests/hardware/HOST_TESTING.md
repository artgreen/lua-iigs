# Native C-host hardware check

HOSTCHECK 1 runs the published `IIGSHOST` executable, verifies its status and
output, then launches a fresh Lua process for the smoke test. It supplements
the Lua-only suite and standalone LUAC batch. It does not use the unavailable
upstream `T` test harness or rebuild the release binaries.

From the dedicated writable test directory:

```text
yankit xvf /nas/lua.test/test.shk
20:test
```

The names and `20:` prefix are the same as the preceding compiler batch.
Extraction replaces `TEST` and `TEST.LUA` with the host-check versions.
`TEST` is an ORCA EXEC file (SRC `$B0`, auxiliary `$0006`); `IIGSHOST` and
`LUATEST` are EXE `$B5` / auxiliary `$0000`.

The native host checks:

- State creation is refused before the required stack initializer.
- After initialization, deep Lua-stack recursion is caught and Lua still works.
- Oversized vector and array requests are rejected with the expected errors.
- Existing table data survives the rejected resize and garbage collection.
- A native C count hook yields repeatedly; the embedding program resumes
  the coroutine, verifies its final result (2,001,000), and closes the state.

The host runs quietly until it exits. Its stdout/stderr are captured, then
printed by the verifier. There is no established hardware duration for this
exact batch. Both local preflight and one photographed hardware run report
`IIGSHOST PASSED yields=100`; the hardware run also completed the post-host
smoke test and returned to the shell after the final HOSTCHECK pass marker.
The verifier requires one completion line, a yield count within the native
test's accepted range, zero process status, and no recognized failure or
corruption output. A missing marker or an error after a marker cannot pass.

The subsequent smoke test exercises arithmetic/strings, loading,
coroutine continuations, tables and GC in a fresh interpreter process.
Require the **final** marker and shell return:

```text
HOSTCHECK 1 PASSED - expect shell prompt next
#
```

Earlier `SMOKE DONE` and `IIGSHOST PASSED` lines are intermediate. On failure,
retain the last screen and `host.out`/`host.err` for diagnosis. The batch
replaces those filenames plus `host.state` in its working directory, and
removes them after success. Rerunning the same command provides another warm
launch, but a single pass does not establish resource-leak freedom or
cold-start repeatability. Allocator fault injection and the raw Memory
Manager probe remain separate tests.

## Reproduce and verify

```sh
make hardware-suite KIT=host RELEASE=/path/to/release
make hardware-suite KIT=host BUILD=<build id>
TEST_LUA=build/dev/lua/out/lua python3 -m unittest discover -s tests/tooling -p 'test_*checks.py'
```

A release directory must contain `RELEASE-MANIFEST.json` and its referenced
containers. Executable bytes are extracted and checked against the manifest.

The tool runs each native process separately under GoldenGate with memory
checks, including the Lua log verifier and subsequent smoke test. This does
not execute the ORCA shell batch locally. The numeric prefix is configurable;
an empty prefix requests normal shell lookup. Batch comments contain no
semicolon command separators.

Outputs under `build/hardware-suites/<utc>-host-<id>/` include preflight
output, `KIT-MANIFEST.json` (provenance and checksums), and a verified
`TEST.SHK` plus 800 KB ProDOS image.  Every archive member is extracted and compared with
its input. The packager does not stage to the NAS or publish a release.
See the [validation status](../../docs/VALIDATION.md)
for the exact executable identities and current hardware status.
