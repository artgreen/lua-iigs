# lua-iigs
Port of LUA to the Apple IIgs

This project aims to port the Lua programming language to the Apple IIgs platform. 

The goals of this project:
- Bring Lua scripting to the IIgs platform
    - Lua interpreter to run arbitrary Lua scripts from the command line
    - Lua REPL for testing and exploration
    - Lua library to embed Lua into arbitrary programs
    - Luac compiler to generate bytecode
    - Give back to the Apple community by bringing a powerful tool to the Apple IIgs

Demonstration of embedding Lua into a IIgs application: https://github.com/artgreen/luagsdemo

Issues

The IIgs Lua completes about 70% of the official Lua tests.  It supports enough of Lua that it is able to run a lot of Lua code pretty cleanly. Several times, I've downloaded a tool like memdump (https://github.com/changnet/lua_memdump) and used them to troubleshoot.  The C/LUA API seems to work after exercising it a little.

Tests

| Test           |     Status     | Notes                                                                                                     |
|----------------|:--------------:|-----------------------------------------------------------------------------------------------------------|
| attrib.lua     |    Failing     | cannot open file 'libs/synerr.lua'                                                                        |
| big.lua        |    Failing     | attempt to yield from outside a coroutine                                                                 |
| bitwise.lua    |    Failing     | malformed number near '0xF0.0'                                                                            |
| bwcoercion.lua |    Passing     |                                                                                                           |
| calls.lua      |      N/A       | No testC                                                                                                  |
| closure.lua    |    Passing     |                                                                                                           |
| constructs.lua |    Failing     | There is bad object type being passed to reallymarkobject() that's triggering the assert in that function. |
| coroutine.lua  |    Failing     |coroutine.lua:285: assertion failed!|
| cstack.lua     |    Failing     |02423c: BRK 00|
| debug.lua      |    Failing     |02423c: BRK 00|
| errors.lua     |    Failing     |07eba1: BRK 60|
| events.lua     |    Passing     ||
| gc.lua         |    Passing     | Minor tweaks to account for less memory                                                                   |
| Row 2 Column 1 | Row 2 Column 2 | Row 2 Column 3                                                                                            |
| Row 3 Column 1 | Row 3 Column 2 | Row 3 Column 3                                                                                            |


Powered by
- ORCA/C https://github.com/byteworksinc/ORCA-C
- GoldenGate https://juiced.gs/store/golden-gate/
- Lua https://www.lua.org
