-- RELEASECHECK 1: published v0.2.1 bytes, renamed only to LUATEST.
local function mark(s) print(s); io.stdout:flush() end
mark("RELEASECHECK 1: published v0.2.1 acceptance")
mark("Expected -v banner: IIgs e026f5b-13178cdf3c75 plain")
mark("R1 smoke (its shell message is intermediate; more tests follow)")
dofile("hwsmoke.lua")
mark("R1 PASSED")
mark("R2 integer/float boundary regression")
dofile("numconv.lua")
mark("R2 PASSED")
mark("R3 full adapted math test")
_port=nil
_soft=nil
dofile("mathfix.lua")
mark("R3 PASSED")
collectgarbage("collect")
mark("R4 adapted file I/O and portable date/time")
mark("SKIP Unix processes, nonportable dates, large-file block")
_port=true
_soft=true
dofile("filefix.lua")
mark("R4 PASSED")
collectgarbage("collect")
mark("RELEASECHECK 1 PASSED - expect shell prompt next")
