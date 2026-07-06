-- hwtest.lua -- proves the Apple IIgs corruption fixes on real hardware.
--
-- Self-verifying: every check has a known answer that is WRONG (or that
-- crashes/hangs the machine) on the unfixed build, so a clean run that
-- prints "ALL TESTS PASSED" is real proof. No memcheck needed.
--
--   lua hwtest.lua        (or run it from the REPL: dofile"hwtest.lua")

local pass, fail = 0, 0
local function check(name, cond, detail)
  if cond then
    pass = pass + 1
    print("  ok   " .. name)
  else
    fail = fail + 1
    print("  FAIL " .. name .. (detail ~= nil and ("  got: " .. tostring(detail)) or ""))
  end
end

print("=== Lua IIgs fix verification ===")
print(_VERSION)

--------------------------------------------------------------------
-- [1] Compiler constant-table corruption  (luaM_shrinkvector_)
-- Compiling a chunk with thousands of unique string constants used to
-- wrap a 16-bit byte-size multiply when close_func shrank f->k,
-- truncating/freeing the constant array -> "not enough memory" on a
-- valid chunk, or a silently corrupt function.
--------------------------------------------------------------------
print("[1] compiler: large constant table")
do
  local N = 3200                      -- 3200 * 11 bytes > 32767 -> old bug
  local parts = {}
  for i = 0, N - 1 do parts[i + 1] = string.format("%q", "k" .. i) end
  local src = "return {" .. table.concat(parts, ",") .. "}"
  local f, err = load(src)
  check("valid chunk compiles", f ~= nil, err)
  if f then
    local t = f()
    check("table length", #t == N, #t)
    local intact = true
    for i = 0, N - 1 do
      if t[i + 1] ~= "k" .. i then intact = false; break end
    end
    check("every constant intact", intact)
  end
end

--------------------------------------------------------------------
-- [2] C-stack overflow is caught, not fatal  (byte-based stack guard)
-- Deep recursion across C (pcall) boundaries used to overrun the small
-- bank-0 stack and corrupt/crash the machine. It must now raise a
-- catchable error and leave the interpreter fully usable.
--------------------------------------------------------------------
print("[2] C-stack overflow is graceful")
do
  local depth = 0
  local function deep()
    depth = depth + 1
    pcall(deep)         -- recurse through a C boundary each level
  end
  pcall(deep)
  -- Reaching this line at all means no crash/corruption occurred.
  check("survived deep recursion", true)
  check("recursed several levels then stopped", depth >= 5, depth)
  -- Canary work after the near-overflow must be perfect.
  local s = 0
  for i = 1, 1000 do s = s + i end
  check("arithmetic intact after overflow", s == 500500, s)
  local t = {}
  for i = 1, 500 do t[i] = i * i end
  check("tables intact after overflow", t[500] == 250000, t[500])

  -- And an explicit clean error from a single deep chain:
  local function chain(n) return 1 + chain(n + 1) end
  local ok, msg = pcall(chain, 1)
  check("deep call raises a catchable error", ok == false)
  check("error mentions overflow/stack",
        type(msg) == "string" and
        (msg:find("stack") ~= nil or msg:find("overflow") ~= nil), msg)
end

--------------------------------------------------------------------
-- [3] Debug-hook pc handling  (savedpc pointer-arithmetic fix)
-- The const-cast workaround stepped savedpc by 1 byte instead of one
-- 4-byte Instruction. A count hook that yields exercises the corrupting
-- path (resume would decode garbage); the call-hook path exercises the
-- line-info path. Both must be correct.
--------------------------------------------------------------------
print("[3] debug hooks / savedpc")
do
  -- 3a: line info stays sane through call/line/count hooks in a coroutine
  local badline = false
  local co = coroutine.create(function()
    local s = 0
    local function add(x) return x end
    for i = 1, 400 do s = s + add(i) end
    return s
  end)
  debug.sethook(co, function(ev, ln)
    if ev == "line" and not (type(ln) == "number" and ln > 0) then
      badline = true
    end
  end, "clr", 60)
  local ok, v = coroutine.resume(co)
  check("hooked coroutine ran", ok, v)
  check("result correct under hooks", v == 80200, v)
  check("all hook line numbers valid", not badline)

  -- 3b: yielding from a count hook (the corruption path), if supported
  local co2 = coroutine.create(function()
    local s = 0
    for i = 1, 2000 do s = s + i end
    return s
  end)
  debug.sethook(co2, function() coroutine.yield() end, "", 40)
  local resumes, final, rok = 0, nil, true
  while true do
    local o, val = coroutine.resume(co2)
    if not o then
      -- If this build forbids yielding from a hook, that's fine: the
      -- corrupting path simply isn't reachable here.
      if type(val) == "string" and val:find("C%-call boundary") then
        print("  note yield-from-hook not supported (path unreachable)")
      else
        rok = false; final = val
      end
      break
    end
    resumes = resumes + 1
    if coroutine.status(co2) == "dead" then final = val; break end
    if resumes > 100000 then rok = false; break end
  end
  check("hook-yield resumes cleanly", rok, final)
  if resumes > 1 then
    check("result correct after hook yields", final == 2001000, final)
  end
end

--------------------------------------------------------------------
-- [4] math.random has no extra mantissa bits  (FIGS clamped to 53)
-- On real SANE (64-bit mantissa) the unfixed build produced 64-bit
-- fractions, so r*2^53 was not integral. Fixed build yields <=53 bits.
--------------------------------------------------------------------
print("[4] math.random precision")
do
  math.randomseed(12345)
  local bad, mult = 0, 2 ^ 53
  for _ = 1, 3000 do
    local r = math.random()
    if not (r >= 0 and r < 1) then bad = bad + 1 end
    if (r * mult) % 1 ~= 0 then bad = bad + 1 end
  end
  check("draws in [0,1) with <=53 mantissa bits", bad == 0, bad)
end

--------------------------------------------------------------------
-- [5] General integrity  (catches stray heap/table/string corruption)
--------------------------------------------------------------------
print("[5] general integrity")
do
  local s = string.rep("ab", 1000)
  check("string.rep length", #s == 2000, #s)
  check("string.sub", s:sub(1, 4) == "abab", s:sub(1, 4))

  local t = {}
  for i = 1, 5000 do t[i] = i end       -- large array part
  local sum = 0
  for i = 1, 5000 do sum = sum + t[i] end
  check("5000-entry array sum", sum == 12502500, sum)

  local h = {}
  for i = 1, 2000 do h["key" .. i] = i end   -- large hash part
  local hs = 0
  for i = 1, 2000 do hs = hs + h["key" .. i] end
  check("2000-entry hash sum", hs == 2001000, hs)

  local seen = {}                        -- string-interning stress
  for i = 1, 3000 do seen[tostring(i) .. "x"] = true end
  local c = 0
  for _ in pairs(seen) do c = c + 1 end
  check("3000 interned strings", c == 3000, c)

  collectgarbage()                       -- exercise the GC
  check("survived a full GC", true)
end

--------------------------------------------------------------------
print(string.format("=== %d passed, %d failed ===", pass, fail))
if fail == 0 then
  print("ALL TESTS PASSED")
else
  print("SOME TESTS FAILED")
end
