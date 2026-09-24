-- NOSOURCE 1: source rejection and continued operation.
-- On a parser-free (LUA_NO_PARSER) runtime every text chunk must be refused
-- with an ordinary, catchable error, and the interpreter must keep working.
-- On a full runtime the same checks confirm that text still loads.
-- Precompile with luac for the parser-free runtime.
--   lua nosource.lua          in-process checks
--   lua nosource.lua cli N    verify a rejected command-line run (status N,
--                             output captured in source.log)
local checks = 0
local function check(cond, what)
  checks = checks + 1
  if not cond then error("NOSOURCE 1 FAILED: " .. what, 0) end
end
local REJECT = "attempt to load a text chunk %(parser not included in this build%)"

if arg and arg[1] == "cli" then
  local status = tonumber(arg[2])
  local f = assert(io.open("source.log", "r"))
  local log = f:read("a")
  f:close()
  check(status and status ~= 0, "rejected source run returned status " .. tostring(arg[2]))
  check(log:find(REJECT) ~= nil, "source.log lacks the rejection message")
  check(not log:find("SOURCE RAN"), "source text was executed")
  os.remove("source.log")
  print("NOSOURCE 1 CLI REJECTED status=" .. status)
  return
end

local f, msg = load("return 6 * 7")
local parser = f ~= nil
if parser then
  check(f() == 42, "full runtime evaluates text")
else
  check(type(msg) == "string" and msg:find(REJECT), "load(text) message: " .. tostring(msg))
  check(select("#", load("x = 1")) == 2, "load(text) returns nil plus message")
  local g, m2 = load("return 1", "=named", "t")
  check(g == nil and m2:find(REJECT), "mode 't' rejected")
end

-- Mode restrictions are enforced before any parsing, in both runtimes.
local g, m = load("return 1", "=named", "b")
check(g == nil and m:find("attempt to load a text chunk %(mode is 'b'%)"), "mode 'b' refuses text")

-- A text file on disk is refused cleanly by loadfile and dofile.
local name = "nosrc.tmp"
local out = assert(io.open(name, "w"))
out:write("return 'SOURCE RAN'\n")
out:close()
local lf, lm = loadfile(name)
if parser then
  check(lf and lf() == "SOURCE RAN", "loadfile(text) on full runtime")
else
  check(lf == nil and lm:find(REJECT), "loadfile(text) rejected")
  local ok, err = pcall(dofile, name)
  check(not ok and tostring(err):find(REJECT), "dofile(text) raises a catchable error")
end
os.remove(name)

-- require() of a text module goes through the same loader.
local modname = "nosrcmod"
out = assert(io.open(modname .. ".lua", "w"))
out:write("return 'MODULE RAN'\n")
out:close()
local savedpath = package.path
package.path = "?.lua"
local rok, rval = pcall(require, modname)
package.path, package.loaded[modname] = savedpath, nil
os.remove(modname .. ".lua")
if parser then
  check(rok and rval == "MODULE RAN", "require(text module) on full runtime")
else
  check(not rok and tostring(rval):find(REJECT), "require(text module) rejected")
end

-- Repeated rejections inside and outside coroutines leave no residue.
collectgarbage()
local before = collectgarbage("count")
for i = 1, 60 do
  local co = coroutine.wrap(function(src)
    local fn, e = load(src)
    coroutine.yield(fn ~= nil, e)
    return i
  end)
  local loaded, err = co("return " .. i)
  check(loaded == parser, "coroutine load result " .. i)
  check(co() == i, "coroutine resumes after load " .. i)
end
collectgarbage()
check(collectgarbage("count") < before + 16, "memory after repeated rejections")

-- The runtime keeps working: bytecode round trip, strings, tables, GC.
local dumped = string.dump(function(a) return a * 2, #tostring(a) end)
local h = assert(load(dumped, "=dumped", "b"))
local x, n = h(21)
check(x == 42 and n == 2, "binary chunk from string.dump")
local t = {}
for i = 1, 500 do t[i] = ("%03d"):format(i) end
check(table.concat(t, ",", 498, 500) == "498,499,500", "table/string work")
local proxy = setmetatable({}, {__index = function(_, k) return k * 3 end})
check(proxy[14] == 42 and math.maxinteger // 3 > 0, "metatables and integers")
local co = coroutine.wrap(function(a) local b = coroutine.yield(a + 1); return b * 2 end)
check(co(1) == 2 and co(5) == 10, "coroutines")
collectgarbage("collect")
check(collectgarbage("count") > 0, "collector")

print(("NOSOURCE 1 PASSED parser=%s checks=%d"):format(parser and "yes" or "no", checks))
