# lua-iigs
Port of LUA to the Apple IIgs

**Hardware status (September 2026):** a working baseline is established on
the user's accelerated ROM 03 IIgs with 8 MB RAM. Keep the `LUAPATH` build
identified as `IIgs b69d628-9766f6d19a8d plain`. It completed seven consecutive
coroutine/allocation test pairs (14 launches), then both tests again after
a full power cycle, with success messages and clean shell returns.

The targeted hardware checks also cover stack overflow recovery, pattern
matching, constants, and garbage collection. The IIgs module search path
now supports bare relative filenames without a command-line workaround.
This establishes a tested baseline for these workloads on this machine;
the historical file-I/O failure and unavailable C API test harness remain
outside the completed validation. See [HARDWARE_RESULTS.md](HARDWARE_RESULTS.md)
for the evidence and [HARDWARE_TESTING.md](HARDWARE_TESTING.md) for rebuilding
and reproducing the checks.

The original project description and issue notes below are historical;
they do not describe the current validation status.

This project is a port the Lua programming language to the Apple IIgs platform. 

Currently, Lua version 5.4.6 has been ported to the IIgs using ORCA-C.  Greater than 95% of the Lua 5.4.6 test suite
passes, with minor changes to account for the smaller memory size of the platform.

Issues
- There are two places in the Lua source where the field of a union/structure is declared as **const**.  In several 
places, this field is changed; usually to increment or decrement the field.  These modifications of the const fields 
results in a compiler error in the ORCA_C compiler.  Removing the const declaration appears to solve the errors.
- There is at least one function in the Lua source that assumes that a **short** is always smaller than 
an **int**.  I plan on hunting for more instances of similar assumptions.
- String catalog corruption.  In researching this project, I read about other porting projects running into
  unexplained string catalog corruption. I seem to have the same issue.  So far, the corruption seems to be limited to 
program termination when the string catalog is emptied.


The goals of this project:
- Bring Lua scripting to the IIgs platform
    - Lua interpreter to run arbitrary Lua scripts from the command line
    - Lua REPL for testing and exploration
    - Lua library to embed Lua into arbitrary programs
    - Luac compiler to generate bytecode
    - Give back to the Apple community by bringing a powerful tool to the Apple IIgs
- Stretch goal 1: Create a system tool set implementing (at least a portion of) the Lua VM.
- Stretch goal 2: Create a NDA acting as a CLI for the tool set


Powered by
- ORCA/C https://github.com/byteworksinc/ORCA-C
- GoldenGate https://juiced.gs/store/golden-gate/
- Lua https://www.lua.org
