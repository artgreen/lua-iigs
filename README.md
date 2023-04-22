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

The port supports enough of Lua that it is able to run a lot of Lua code pretty cleanly. Several times, I've downloaded a tool like memdump (https://github.com/changnet/lua_memdump) and used them to troubleshoot.  The C/LUA API seems to work after exercising it a little.

Tests

| Test           | Status  | Notes                                                                                                      |
|----------------|:-------:|------------------------------------------------------------------------------------------------------------|
| attrib.lua     | Failing | cannot open file 'libs/synerr.lua'                                                                         |
| big.lua        | Failing | attempt to yield from outside a coroutine                                                                  |
| bitwise.lua    | Failing | malformed number near '0xF0.0'                                                                             |
| bwcoercion.lua | Passing |                                                                                                            |
| calls.lua      |   N/A   | No testC                                                                                                   |
| closure.lua    | Passing |                                                                                                            |
| constructs.lua | Failing | There is bad object type being passed to reallymarkobject() that's triggering the assert in that function. |
| coroutine.lua  | Failing | coroutine.lua:285: assertion failed!                                                                       |
| cstack.lua     | Failing | 02423c: BRK 00                                                                                             |
| debug.lua      | Failing | 02423c: BRK 00                                                                                             |
| errors.lua     | Failing | 07eba1: BRK 60                                                                                             |
| events.lua     | Passing |                                                                                                            |
| files.lua      | Failing | files.lua:150: malformed number near '0xABCp-3'                                                            |
| gc.lua         | Passing | Minor tweaks to account for less memory                                                                    |
| gengc.lua      | Failing | 111608: BRK 00                                                                                             |
| goto.lua       | Passing |                                                                                                            |
| heavy.lua      | Failing | 000002: BRK 00                                                                                             |
| literals.lua   | Failing | literals.lua:299: malformed number near '0X0.41'                                                           |
| locals.lua     | Failing | 02423c: BRK 00                                                                                             |
| main.lua       | Failing | main.lua:14: assertion failed!                                                                             |
| math.lua       | Failing | math.lua:435: malformed number near '0x7.4'                                                                |
| nextvar.lua    | Failing | Never returns. Probably memory corruption causing next() to go into a loop                                 |
| pm.lua         | Failing | pm.lua:83: assertion failed!                                                                               |
| sort.lua       | Failing | 02423c: BRK 00                                                                                             |
| strings.lua    | Failing | strings.lua:220: assertion failed!                                                                         |
| tpack.lua      | Passing |                                                                                                            |
| vararg.lua     | Passing |                                                                                                            |
| verybig.lua    | Failing | file lgc.c, line 535, function traversestrongtable; assertion: !(keytt(n) == LUA_TNIL)                     |


Powered by
- ORCA/C https://github.com/byteworksinc/ORCA-C
- GoldenGate https://juiced.gs/store/golden-gate/
- Lua https://www.lua.org
