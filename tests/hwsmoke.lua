-- Short hardware acceptance test. Each marker is flushed before work.
-- Use -v when invoking Lua to include the interpreter's build identifier.
io.stdout:setvbuf("no")
local function mark(s) print(s); io.flush() end
mark("S0 smoke entered")
assert(_VERSION == "Lua (IIgs) 5.4")
mark("S1 arithmetic and strings")
local sum = 0
for i = 1, 1000 do sum = sum + i end
assert(sum == 500500)
assert(string.rep("abc", 100):sub(-6) == "abcabc")
mark("S2 source and bytecode loading")
local f = assert(load("local x = ...; return x * x + 1"))
assert(f(12) == 145)
assert(assert(load(string.dump(f)))(12) == 145)
mark("S3 coroutine continuations")
local co = coroutine.create(function()
  for i = 1, 100 do coroutine.yield(i) end
  return "finished"
end)
for i = 1, 100 do
  local ok, value = coroutine.resume(co)
  assert(ok and value == i)
end
local ok, value = coroutine.resume(co)
assert(ok and value == "finished" and coroutine.status(co) == "dead")
mark("S4 tables and garbage collection")
do
  local t = {}
  for i = 1, 1000 do t[i] = "item" .. i end
  collectgarbage("collect")
  for i = 1, 1000 do assert(t[i] == "item" .. i) end
end
collectgarbage("collect")
mark("SMOKE DONE - expect shell prompt next")
