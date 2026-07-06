-- Regression collateral for the IIgs savedpc const-cast fix (ldo.c
-- luaD_hookcall, ldebug.c luaG_traceexec). NOTE: the traceexec yield
-- path (savedpc--) is only reachable from a C hook calling lua_yield,
-- which pure Lua cannot do ("attempt to yield across a C-call
-- boundary"), so this exercises the luaD_hookcall ++/-- roundtrip and
-- line-info sanity inside coroutines with call/line/count hooks.
local lines, calls = 0, 0
local co = coroutine.create(function()
  local s = 0
  local function add(x) return x end
  for i = 1, 500 do s = s + add(i) end
  return s
end)
debug.sethook(co, function(ev, ln)
  if ev == "line" then
    lines = lines + 1
    assert(type(ln) == "number" and ln > 0, "bad line in hook: " .. tostring(ln))
  elseif ev == "call" or ev == "tail call" then
    calls = calls + 1
  end
end, "clr", 100)
local ok, v = coroutine.resume(co)
assert(ok, v)
assert(v == 125250, "corrupted result: " .. tostring(v))
assert(lines > 500 and calls >= 500, "hooks not firing: " .. lines .. "/" .. calls)
print("lines:", lines, "calls:", calls, "sum:", v)
print("OK")
