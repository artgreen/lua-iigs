# Reusable suite

`suite.json` defines named test groups; `suite.lua` runs and reports them.
From the repository root:

```sh
make suite GROUP=runtime
make hardware-suite BUILD=<directory> KIT=suite GROUP=full
make hardware-suite BUILD=<directory> KIT=lua GROUP=smoke
```

The full group includes adapted math and file tests and the slow table-growth
boundary test. Each test has a completion contract. Require
`SUITE COMPLETE group=<group> passed=<count> failed=0`, the batch's expected
final message, and a clean shell return. Skip counts remain part of the result.
For `KIT=lua`, the full-interpreter group is followed by the traced group;
require `[M7] state closed` on the trace run as well.

See [procedure](PROCEDURE.md) for transfer and evidence recording.
