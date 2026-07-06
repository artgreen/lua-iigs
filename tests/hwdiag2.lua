-- hwdiag2.lua -- isolates the >32KB allocation aliasing seen on real
-- hardware (hwdiag const-3200: slot 472 contained an internal 'proto'
-- TValue => two live objects overlapping; threshold between 26,400 and
-- 35,200 byte allocations).
--
-- Decision tree:
--   E10 fails  -> plain malloc of big blocks is bad (fresh-alloc path)
--   E10 ok, E20 fails -> realloc/table-growth path is bad
--   E10+E20 ok, E30 fails -> compile/Proto-shrink path is bad
-- Mismatch reports include a count and the first 3 defects, which
-- distinguishes one aliased region from a truncated/shifted copy.

local function say(s)
  print(s)
  if io ~= nil and io.flush ~= nil then pcall(io.flush) end
end
local fails = 0
local function chk(id, ok, detail)
  if ok then say(id .. " ok")
  else fails = fails + 1; say(id .. " FAIL " .. tostring(detail)) end
end
local function memk() return math.floor(collectgarbage("count")) end

say("E00 hwdiag2 start " .. _VERSION .. " mem=" .. memk() .. "K")

---------------------------------------------------------------- E10
-- Big strings built by doubling concat: each doubling is a fresh
-- allocation (luaS_createlngstrobj -> malloc) plus a full copy.
-- Byte at position p must equal PAT[(p-1)%10+1]; sampled every 997
-- bytes so shifts, truncation, and aliasing all show up.
do
  local PAT = "ABCDEFGHIJ"
  local sizes = {16000, 28000, 33000, 40000, 65000, 131000}
  for _, want in ipairs(sizes) do
    local ok, err = pcall(function()
      local s = string.rep(PAT, 100)          -- 1000 bytes (rep is capped
      while #s < want do                       -- at 32767, so double up)
        local h = s .. s
        s = h
      end
      -- trim to exact size via sub (another big fresh allocation)
      s = s:sub(1, want)
      if #s ~= want then error("len " .. #s) end
      local bad, first = 0, nil
      for p = 1, want, 997 do
        local c = s:byte(p)
        local e = PAT:byte((p - 1) % 10 + 1)
        if c ~= e then
          bad = bad + 1
          if first == nil then first = "p=" .. p .. " got=" .. tostring(c) .. " want=" .. e end
        end
      end
      -- and the very end
      local e = PAT:byte((want - 1) % 10 + 1)
      if s:byte(want) ~= e then bad = bad + 1; first = first or ("tail got=" .. tostring(s:byte(want))) end
      if bad > 0 then error(bad .. " bad samples; first: " .. first) end
    end)
    chk("E10 string-" .. want, ok, err)
  end
  collectgarbage()
  say("E11 mem=" .. memk() .. "K")
end

---------------------------------------------------------------- E20
-- Big table arrays built by plain appends: growth reallocs the array
-- through power-of-two doubling (2048 -> 4096 slots = 45,056 bytes),
-- with NO parser and NO Proto shrink involved.
do
  local sizes = {1000, 2400, 3000, 3200, 4096, 5000}
  for _, n in ipairs(sizes) do
    local ok, err = pcall(function()
      local t = {}
      for i = 1, n do t[i] = "k" .. (i - 1) end
      local bad, first = 0, {}
      for i = 1, n do
        if t[i] ~= "k" .. (i - 1) then
          bad = bad + 1
          if #first < 3 then
            local g = t[i]
            first[#first + 1] = "idx" .. (i - 1) .. "=" ..
              (type(g) == "string" and ("str/" .. #g) or tostring(g))
          end
        end
      end
      if bad > 0 then error(bad .. " bad: " .. table.concat(first, " ")) end
    end)
    chk("E20 table-" .. n, ok, err)
    say("E21 mem=" .. memk() .. "K")
  end
end

---------------------------------------------------------------- E30
-- The original failing path: load() of a big constant table. Ladder
-- brackets the 32KB line (2900*11=31,900 < 32,768 < 3000*11=33,000)
-- and reports mismatch count + first 3 (not just the first).
do
  local sizes = {2400, 2900, 3000, 3200}
  for _, n in ipairs(sizes) do
    local ok, err = pcall(function()
      local parts = {}
      for i = 0, n - 1 do parts[i + 1] = string.format("%q", "k" .. i) end
      local src = "return {" .. table.concat(parts, ",") .. "}"
      local f, e = load(src)
      if f == nil then error("load: " .. tostring(e)) end
      src = nil; parts = nil
      local t = f()
      if #t ~= n then error("len " .. tostring(#t)) end
      local bad, first = 0, {}
      for i = 0, n - 1 do
        if t[i + 1] ~= "k" .. i then
          bad = bad + 1
          if #first < 3 then
            local g = t[i + 1]
            first[#first + 1] = "idx" .. i .. "=" ..
              (type(g) == "string" and ("str/" .. #g) or tostring(g))
          end
        end
      end
      if bad > 0 then error(bad .. " bad: " .. table.concat(first, " ")) end
    end)
    chk("E30 const-" .. n, ok, err)
    say("E31 mem=" .. memk() .. "K")
  end
end

---------------------------------------------------------------- E70
-- The other open question from hwtest: does the stack guard hold on
-- hardware? Per-level prints so a freeze reports its depth.
say("E70 stack test (per-level prints; if this freezes, note the level)")
do
  local depth = 0
  local function deep()
    depth = depth + 1
    say("E71 level " .. depth)
    pcall(deep)
  end
  pcall(deep)
  say("E72 stopped cleanly at depth " .. depth)
  local function chain(n) return 1 + chain(n + 1) end
  local ok, msg = pcall(chain, 1)
  chk("E73 chain caught", ok == false, msg)
end

say("E99 DONE fails=" .. fails)
if fails == 0 then say("ALL DIAGNOSTICS PASSED") end
