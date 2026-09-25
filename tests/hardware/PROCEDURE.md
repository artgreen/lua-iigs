# Hardware acceptance

Create a kit from an identified build, or use the release diagnostics bundle:

```sh
make hardware-suite BUILD=<directory> KIT=suite
```

Transfer `TEST.SHK` as binary and extract it into a dedicated writable directory.
With YankIt and the established shell prefix:

```text
yankit xvf /nas/lua.test/test.shk
20:test
```

The batch is an ORCA EXEC file. Prefix `20:` is the tested configuration;
use `PREFIX=none` or the appropriate prefix when generating a kit for another
shell setup. Each kit uses the same `TEST` name, so keep kits in separate
directories. The full suite includes a table-growth test that took about
18 minutes silently on the established machine; the whole run took nearly
40 minutes. A quiet screen alone is not a hang.

| Kit | Coverage |
| --- | --- |
| `suite` | Full interpreter, reusable suite (`GROUP=full` default) |
| `lua` | Full interpreter and Memory Manager traced interpreter |
| `small` | On-device compilation, compact debug/stripped chunks, source rejection |
| `luac` | Standalone compiler and bytecode checks |
| `host` | Native embedding and C-hook yields |

The suite's local preflight defaults to `runtime`, because stock GoldenGate
cannot pass the complete I/O group. Preflight is not a hardware result.
The compact kit compiles test chunks on the IIgs to avoid emulator-folded
floating-point constants. The batch stops on failure.

Record the kit manifest/hash, observed build banner, machine ROM/RAM,
accelerator, OS/shell, warm or cold start, final completion markers, skips,
and return to the shell. For tracing also record the allocator armed and
`[M7] state closed`. Preserve failures and incomplete runs explicitly.
A photograph of an intermediate line does not establish later completion;
distinguish photographs, logs, and user-reported outcomes.

See the adjacent guides for each kit's expected markers. Status for the
current distribution is in [validation](../../docs/VALIDATION.md).
