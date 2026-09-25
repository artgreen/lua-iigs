# Compact runtime testing

```sh
make lua-small
make test CONFIG=lua-small
make hardware-suite BUILD=<directory> KIT=small
```

`compact.json` defines debug and stripped local acceptance groups. The hardware
kit includes LUAC and compiles its test chunks on the IIgs, then checks text
source rejection, the compact group, and the stripped group. Its small driver
and configuration contain no floating-point constants when compiled locally.

Require `NOSOURCE 1 CLI REJECTED`, successful compact and stripped suite
completion, and a clean shell return. The batch stops on failure.
The established compact-kit run passed on the accelerated ROM 03/8 MB machine;
it was one warm run, not a cold-start repeat. See [validation](../../docs/VALIDATION.md).

GoldenGate-compiled floating constants can differ from IIgs runtime arithmetic.
This affects full and compact runtimes equally; see
[compatibility](../../docs/COMPATIBILITY.md).
