# Examples

These scripts are demonstrations, not the regression suite. They are not
included in the packages or hardware kits; transfer desired scripts as
text separately. Run them with the interpreter from a working directory
where they and any input files can be found. Commands below assume the
interpreter is named `lua`.

| Script | Use |
| --- | --- |
| `blackjack.lua` | Interactive card game; answers are read from the console |
| `more.lua` | Prompts for a filename and pages through it, 23 lines at a time |
| `replcli.lua` | Small demonstration command loop with `cat`, `echo`, and `exit` |
| `warehouse.lua` | Self-checking warehouse simulation with three coroutines and 600 transactions |

```text
lua -E blackjack.lua
lua -E more.lua
lua -E replcli.lua
lua -E -v warehouse.lua
```

`warehouse.lua` needs no input files or modules. It generates a deterministic
stream of sales and restocks, parses the text records, checks stock conservation
during the run, replays an audit log, sorts product totals, and forces garbage
collection. The program prints progress at every 100 records so a slow run is
visibly active. Its final line must be:

```text
WAREHOUSE PASSED events=600 shipped=499 backorders=320 digest=32697 top=11
```

Require a clean return to the shell prompt as well as that line. The expected
figures were calculated independently and the program passed locally under
GoldenGate with memory checking; it has not yet been run on real IIgs hardware.

The demo command loop is not Lua's own REPL or a replacement system shell.
It splits input on whitespace and does not implement shell quoting. Its
blank-input, EOF, and some flag-handling paths are incomplete; use it as
example code rather than as validation of the interpreter. For Lua's actual
interactive prompt, run `lua -E -i` and leave with `os.exit()`.

The root-level `poker.lua`, `test.lua`, and `test2.lua` are older standalone
examples/manual checks. Their output is not an automated regression contract.
The early [firsttest.txt](../docs/history/firsttest.txt) transcript is
historical Lua 5.4.4 output, not current test evidence.

`bridge.lua` requires a statically registered C module and runs through the
`bridge` executable, not the ordinary interpreter. See the
[embedding guide](../docs/EMBEDDING.md) for build commands and the demo's limits.

These examples have not each received separately recorded hardware testing.
The maintained validation commands are in [the test guide](../tests/README.md)
and [hardware procedure](../HARDWARE_TESTING.md).
