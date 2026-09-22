-- cobisect.lua -- localize which coroutine operation corrupts memory on
-- real hardware. coroutine.lua reproduces the null-byte text-page sweep;
-- this runs each coroutine-operation CLASS in isolation, announcing the
-- class BEFORE running it (flushed), with a known-answer check after. If
-- the machine crashes/garbles, the last "Cn trying ..." line names the
-- culprit; if it survives, "Cn ok" confirms that class is clean.
--
-- Classes escalate least- to most-suspect. C4 (deep recursion inside a
-- coroutine, riding the C-stack guard) is the prime suspect.

local function say(s)
  print(s)
  if io ~= nil and io.flush ~= nil then pcall(io.flush) end
end

local fails = 0
local function chk(id, ok, detail)
  if ok then say(id .. " ok")
  else fails = fails + 1; say(id .. " FAIL " .. tostring(detail)) end
end

say("COBISECT start " .. _VERSION)

-- C1: basic create / resume / yield, many iterations -----------------
say("C1 trying basic resume/yield x500")
do
  local sum = 0
  for i = 1, 500 do
    local co = coroutine.create(function(a)
      local b = coroutine.yield(a + 1)
      return b + 1
    end)
    local _, v1 = coroutine.resume(co, i)
    local _, v2 = coroutine.resume(co, v1)
    sum = sum + v2
  end
  chk("C1 basic", sum == (500*501/2) + 500*2, sum)
end

-- C2: coroutine.wrap -------------------------------------------------
say("C2 trying wrap x500")
do
  local sum = 0
  for i = 1, 500 do
    local gen = coroutine.wrap(function() for j = 1, 3 do coroutine.yield(j) end end)
    sum = sum + gen() + gen() + gen()
  end
  chk("C2 wrap", sum == 500 * 6, sum)
end

-- C3: moderate recursion inside a coroutine (no overflow) -------------
say("C3 trying moderate recursion in coroutine")
do
  local function rec(n) if n <= 0 then return 0 end return 1 + rec(n - 1) end
  local co = coroutine.create(function() return rec(15) end)
  local ok, v = coroutine.resume(co)
  chk("C3 recursion", ok and v == 15, v)
end

-- C4: PRIME SUSPECT -- deep recursion inside a coroutine that rides the
-- C-stack guard until "C stack overflow" is caught -------------------
say("C4 trying guard-riding deep recursion in coroutine")
do
  local co = coroutine.create(function()
    local function deep(n) return 1 + deep(n + 1) end
    local ok, msg = pcall(deep, 1)
    return ok, msg
  end)
  local rok, pok, msg = coroutine.resume(co)
  chk("C4 guard-ride", rok and pok == false and
      type(msg) == "string" and (msg:find("stack") or msg:find("overflow")), msg)
  -- canary after the ride
  local s = 0; for i = 1, 500 do s = s + i end
  chk("C4 canary", s == 125250, s)
end

-- C5: nested coroutines (coroutine resuming a coroutine, several deep) -
-- depth 4 keeps well inside the ~14KB hardware stack; the point is that
-- nesting WORKS, not that it overflows
say("C5 trying nested coroutines depth 4")
do
  local function make(depth)
    return coroutine.wrap(function()
      if depth <= 0 then coroutine.yield(0)
      else coroutine.yield(make(depth - 1)() + 1) end
    end)
  end
  local ok, v = pcall(function() return make(4)() end)
  chk("C5 nested", ok and v == 4, v)
end

-- C6: coroutine.close on a suspended coroutine -----------------------
say("C6 trying coroutine.close x200")
do
  local closed = 0
  for i = 1, 200 do
    local co = coroutine.create(function()
      local x <close> = setmetatable({}, {__close = function() closed = closed + 1 end})
      coroutine.yield()
    end)
    coroutine.resume(co)
    coroutine.close(co)
  end
  chk("C6 close", closed == 200, closed)
end

-- C7: error thrown inside a coroutine --------------------------------
say("C7 trying error-in-coroutine x300")
do
  local caught = 0
  for i = 1, 300 do
    local co = coroutine.create(function() error("boom") end)
    local ok, msg = coroutine.resume(co)
    if not ok and tostring(msg):find("boom") then caught = caught + 1 end
  end
  chk("C7 error", caught == 300, caught)
end

-- C8: debug hook that yields (savedpc path) --------------------------
say("C8 trying hook-yield")
do
  local co = coroutine.create(function()
    local s = 0
    for i = 1, 1000 do s = s + i end
    return s
  end)
  local supported = true
  debug.sethook(co, function()
    if coroutine.isyieldable() then coroutine.yield() end
  end, "", 50)
  local resumes, final = 0, nil
  while true do
    local ok, v = coroutine.resume(co)
    if not ok then
      if tostring(v):find("C%-call boundary") then supported = false end
      final = v; break
    end
    resumes = resumes + 1
    if coroutine.status(co) == "dead" then final = v; break end
    if resumes > 100000 then break end
  end
  if supported and resumes > 0 then
    chk("C8 hook-yield", final == 500500, final)
  else
    say("C8 hook-yield skipped (not supported here)")
  end
end

-- C9: churn -- create and abandon many coroutines (GC + allocator) ----
say("C9 trying coroutine churn x2000 + GC")
do
  for i = 1, 2000 do
    local co = coroutine.create(function() coroutine.yield() end)
    coroutine.resume(co)
    if i % 200 == 0 then collectgarbage() end
  end
  collectgarbage()
  chk("C9 churn", true)
end

say("COBISECT DONE fails=" .. fails)
if fails == 0 then say("ALL COROUTINE CLASSES PASSED") end
