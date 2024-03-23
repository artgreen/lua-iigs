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

Another interesting discovery is that the Lua developers appear to have assumed that a type short is always smaller than a type int.
At least one part of the code makes this assumption. I'll need to verify this and sort it out.
- Caveat: Numbers in hexadecimal ('0X0.41') are not supported by ORCA-C's implementation of strtod()
- Bug: String catalog corruption.  In researching this project, I read about other porting projects running into unexplained string catalog corruption. I seem to have the same issue.  So far, the corruption seems to be limited to program termination when the string catalog is emptied.

Tests - 5.4.6

| Test           | Status  | Notes                                                                                                      |
|----------------|:-------:|------------------------------------------------------------------------------------------------------------|
| api.lua        | Passing |                                                                                                            |
| attrib.lua     | Passing |                                                                                                            |
| big.lua        | Failing | lua: attempt to yield from outside a coroutine big.lua:56                                                  |
| bitwise.lua    | Passing | See note 1                                                                                                 |
| bwcoercion.lua | Passing |                                                                                                            |
| calls.lua      | Failing | 000acd: BRK 00                                                                                             |
| closure.lua    | Passing |                                                                                                            |
| code.lua       | Passing | See note 1                                                                                                 |
| constructs.lua | Passing | There is bad object type being passed to reallymarkobject() that's triggering the assert in that function. |
| coroutine.lua  | Failing | Needed to remove infinite coroutine recursion test                                                         |
| cstack.lua     | Failing | Timeout                                                                                                    |
| db.lua         | Failing | lua: db.lua:599: assertion failed!                                                                         |
| debug.lua      |   N/A   | Removed from tests 5.4.6                                                                                   |
| errors.lua     | Failing | C stack overflow not detected; Errors in recursion fails; MemCheck: memory altered at 009112               |
| events.lua     | Passing |                                                                                                            |
| files.lua      | Failing | files.lua:8: assertion failed!; fixed hex formatted numbers                                                |
| gc.lua         | Passing |                                                                                                            |
| gengc.lua      | Failing | e11607: BRK 00                                                                                             |
| goto.lua       | Passing |                                                                                                            |
| heavy.lua      | Passing |                                                                                                            |
| literals.lua   | Passing | See note 1                                                                                                 |
| locals.lua     | Passing |                                                                                                            |
| main.lua       |   N/A   | We aren't spawning subshells on the IIgs                                                                   |
| math.lua       | Failing | lua: math.lua:557: assertion failed!                                                                       |
| nextvar.lua    | Passing |                                                                                                            |
| pm.lua         | Passing | See note 2                                                                                                 |
| sort.lua       | Passing |                                                                                                            |
| strings.lua    | Passing |                                                                                                            |
| tpack.lua      | Passing |                                                                                                            |
| vararg.lua     | Passing |                                                                                                            |
| verybig.lua    | Failing | lua: table overflow                                                                                        |

Note 1: Removed hex numbers representing floating point numbers which are not supported by strtold()

Note 2: Removed tests with strings containing certain characters. Suspect a locale issue with string.find()

Powered by
- ORCA/C https://github.com/byteworksinc/ORCA-C
- GoldenGate https://juiced.gs/store/golden-gate/
- Lua https://www.lua.org
