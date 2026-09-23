# Current IIgs corruption protections

The merged runtime has targeted and repeatability passes on the accelerated
ROM 03 / 8 MB IIgs. The exact tested artifact is identified in the
[September 22 validation record](validation/2026-09-22/README.md); an arbitrary
rebuild is not the same binary. The earlier
[September 21 baseline](validation/2026-09-21/README.md) is also preserved.
See [hardware results](validation/HARDWARE_RESULTS.md) for observed scope and
[embedding](EMBEDDING.md) for a complete host example.

| Setting | Current value | Defined in |
| --- | --- | --- |
| Bank-0 stack request | 24,832 bytes | `LUA_IIGS_STACK_SIZE`, luaconf.h |
| Startup allowance | 1,024 bytes | `LUA_IIGS_STACK_SLACK`, luaconf.h |
| Usable size for anchor calculation | 23,808 bytes | derived from the two settings |
| Soft floor | estimated base + 7,168 | lstate.c |
| Hard floor | estimated base + 4,096 | lstate.c |
| C-call counter | 200 (upstream Lua 5.4 value; formerly 128 in this port) | llimits.h |
| MM allocation cutoff | 16,384 bytes (conservative) | lauxlib.c |
| C-heap fallback maximum | strictly less than 30,000 payload bytes | lauxlib.c |

## Stack protection and host contract

The byte probe is necessary because C frames vary greatly in size. The
counter cannot protect the IIgs bank-0 stack by itself. Coroutine
continuation resumes also need a check: they bypass the ordinary C-call
entry point. The hard floor remains active during soft-error handling.
The startup allowance and floors are empirically chosen; the initializer
cannot discover or enlarge the actual stack segment.

Every IIgs executable using lua.lib must include lua.h, request
`#pragma stacksize LUA_IIGS_STACK_SIZE`, and call
`lua_iigs_initstack(&anchor)` with a local `char anchor` in main before
creating any Lua state. The anchor frame must outlive all Lua calls.
The guard and error-grace flag are shared by every state in the process.
Do not initialize from a nested frame or move states to another native
stack. An uninitialized host now gets NULL from lua_newstate/luaL_newstate.
Interpreter, compiler, and bridge follow this contract; the C host test
checks refusal before initialization and recovery after Lua-stack overflow.
This is a required initialization change for existing library clients.

## Allocation and 16-bit arithmetic

The hybrid allocator keeps small blocks on the C heap and directs larger
blocks to raw Memory Manager handles. The 16KB cutoff is conservative;
the historical large-block failure region was around 32KB, not a precisely
characterized universal threshold. The small startup probe checks handle
attributes, placement, and a few sentinel writes. It does not certify all
allocation sizes. `mmalloc.lua` checks complete payloads above 32KB and
across banks while retaining other live blocks.

A failed startup probe prints one warning, remembers the last probe failure
reason, and allows only bounded C-heap fallback. Requests of 30,000 bytes
or more fail cleanly when the MM path is unavailable. A small C-heap failure
can initiate the MM probe; a transient MM failure can use the bounded
fallback. Allocation/growth failures retain the old block. Shrink failure
retains a physically larger block (Lua's requested-size accounting can
understate physical use); trace builds report this. An invalid handle is
not disposed because doing so could damage unrelated memory; at most three
probe allocations can be retained after CheckHandle rejection.

`luaL_iigsmmstatus()` reports untested/ok/degraded/disabled without running
a probe. `lua -v` prints this status at the time it is called; untested is
normal before a large allocation. `ok` describes the startup probe only.

The other protections widen allocation arithmetic before multiplication,
limit table sizes that overflow 16-bit calculations, and update saved-PC
pointers by sizeof(Instruction), not one byte. Table append overflow and
direct oversized-array resize have separate tests. A C-host test also
checks vector growth at INT_MAX and the resulting error message. C-hook yielding is now
tested in an actual C host; a Lua debug hook cannot exercise that branch.

## Remaining work

- Isolate the historical files.lua failure, including its input-consuming
  diagnostic read and fixture encoding, before attributing it to runtime
  text translation. See [limitations](LIMITATIONS.md).
- The upstream T C API harness is still unavailable. The focused C host
  adds coverage but does not replace that full harness.
- Confirm OS/shell version, accelerator model/speed, and storage device.
- Broader coverage and other hardware configurations remain open; the
  additional mixed-script session was reported without individual script names.

For the detailed experiments, measurements, and superseded theories, see
[the archived notebook](history/CORRUPTION-HISTORY.md). Hardware observations take
precedence over its historical emulator-only conclusions.
