# Examples

These scripts are demonstrations, not the regression suite. They are not
included in the current hardware-kit images; transfer desired scripts as
text separately. Run them with the interpreter from a working directory
where they and any input files can be found. Commands below assume the
interpreter is named `lua`.

| Script | Use |
| --- | --- |
| `blackjack.lua` | Interactive card game; answers are read from the console |
| `more.lua` | Prompts for a filename and pages through it, 23 lines at a time |
| `replcli.lua` | Small demonstration command loop with `cat`, `echo`, and `exit` |

```text
lua -E blackjack.lua
lua -E more.lua
lua -E replcli.lua
```

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
