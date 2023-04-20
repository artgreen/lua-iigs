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

Powered by
- ORCA/C https://github.com/byteworksinc/ORCA-C
- GoldenGate https://juiced.gs/store/golden-gate/
- Lua https://www.lua.org
