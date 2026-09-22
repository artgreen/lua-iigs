# Earlier tested baseline provenance, 2026-09-21

This LUAPATH build is the preserved earlier baseline. The
[September 22 record](../2026-09-22/README.md) identifies the subsequently
validated runtime with the public host-initialization contract. Keep this
older build as evidence, not as the default installation recommendation.

The source implementing the tested baseline was committed as
`9add073a2ea09c7a82642a08379e217b46418ba0`. It was built before that commit;
the archived executable therefore prints `IIgs b69d628-9766f6d19a8d plain`.
The prefix is the then-current HEAD, while the suffix hashes the source
snapshot, including build tooling and testing documentation.

The original manifest and SHA256SUMS are preserved here unchanged. Source
hashes for runtime code, diagnostics, and the kit builder match commit
9add073. HARDWARE_TESTING.md was updated after the build; its archived
hash intentionally differs. Rebuilding commit 9add073 produces a different
banner/digest; it must not be represented as the identical tested binary.

Archived plain executable SHA256:
`2fab7a40c79247c7fd015454fce4506d8d214fe42c6e5e7fd553fa6457d43fad`

LUAPATH.SHK SHA256:
`2aac8a8b0f26efd4e4a1af7180c297307d471127871dc0d16b10a429d462143d`

Local artifacts: `build/hardware/20260921T195254Z-isvxzp3_/`, including
`plain/build/lua`, source snapshots, logs, package images, and
`nas-transfer/LUAPATH.SHK`. These large artifacts are not tracked in Git.
NAS staging used `/Volumes/nas/LUA.20260921/`; mount availability varies.
SHA256SUMS names the original package files, not files all present in this
Git directory. Retain the archived binary for exact reproduction.

The original hwtest report said 20 passed, but one was an unsupported Lua
hook-yield case incorrectly counted as a pass. Hardware execution and clean
shell returns remain valid observations; C-hook yielding was not covered by
that run. Current test reporting distinguishes this skip explicitly.
