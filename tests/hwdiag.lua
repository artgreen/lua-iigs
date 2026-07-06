-- hwdiag.lua -- incremental hardware diagnostic for the Apple IIgs port.
--
-- Every output line starts with a D-number and output is flushed, so if
-- the machine freezes or corrupts, the LAST VISIBLE NUMBER pinpoints the
-- failing step. Sections are ordered least- to most-dangerous, and each
-- risky step runs under pcall so one failure doesn't hide the rest.
--
-- On a failure it prints the first mismatching index and the actual
-- bytes found, which tells us *what* stomped the memory.

local function say(s)
  print(s)
  if io ~= nil and io.flush ~= nil then pcall(io.flush) end
end

local fails = 0
local function chk(id, ok, detail)
  if ok then
    say(id .. " ok")
  else
    fails = fails + 1
    say(id .. " FAIL " .. tostring(detail))
  end
end

local function memk()
  return math.floor(collectgarbage("count"))
end

say("D00 hwdiag start")
say("D01 " .. _VERSION)
-- full-width ruler: photo shows instantly whether console output is sane
say("D02 0123456789012345678901234567890123456789012345678901234567890123456789")
say("D03 mem=" .. memk() .. "K")

---------------------------------------------------------------- basics
chk("D10 integer", 2 + 2 == 4)
chk("D11 concat", ("ab" .. "cd") == "abcd")
chk("D12 format", string.format("%q", "k7") == '"k7"')
chk("D13 float", 0.5 + 0.25 == 0.75)
chk("D14 tostring", tostring(12345) == "12345")

------------------------------------------------- string interning ladder
for _, n in ipairs{100, 400, 1000, 3000} do
  local ok, err = pcall(function()
    local t = {}
    for i = 1, n do t[i] = "s" .. i end
    for i = 1, n do
      if t[i] ~= "s" .. i then error("idx " .. i .. " got " .. tostring(t[i])) end
    end
  end)
  chk("D20 intern-" .. n, ok, err)
end
say("D21 mem=" .. memk() .. "K")

------------------------------------------- constant-table compile ladder
-- (the section hwtest [1] failed on; steps find the threshold, and a
-- mismatch reports the exact index and bytes found)
local keep = nil
for _, n in ipairs{50, 200, 800, 1600, 2400, 3200} do
  local ok, err = pcall(function()
    local parts = {}
    for i = 0, n - 1 do parts[i + 1] = string.format("%q", "k" .. i) end
    local src = "return {" .. table.concat(parts, ",") .. "}"
    local f, e = load(src)
    if f == nil then error("load: " .. tostring(e)) end
    src = nil
    local t = f()
    if #t ~= n then error("len " .. tostring(#t)) end
    for i = 0, n - 1 do
      local want = "k" .. i
      local got = t[i + 1]
      if got ~= want then
        if type(got) == "string" then
          local b = {}
          for j = 1, math.min(#got, 8) do b[j] = string.byte(got, j) end
          error("idx " .. i .. " want " .. want ..
                " got len=" .. #got .. " bytes=" .. table.concat(b, ","))
        else
          error("idx " .. i .. " want " .. want .. " got " .. tostring(got))
        end
      end
    end
    if n == 50 then keep = t end
  end)
  chk("D30 const-" .. n, ok, err)
  say("D31 mem=" .. memk() .. "K")
end

------------------------------------------------------------ big tables
do
  local ok, err = pcall(function()
    local t = {}
    for i = 1, 5000 do t[i] = i end
    local s = 0
    for i = 1, 5000 do s = s + t[i] end
    if s ~= 12502500 then error("array sum " .. s) end
    local h = {}
    for i = 1, 2000 do h["key" .. i] = i end
    local hs = 0
    for i = 1, 2000 do hs = hs + h["key" .. i] end
    if hs ~= 2001000 then error("hash sum " .. hs) end
  end)
  chk("D40 tables", ok, err)
end

------------------------------------------------ string ops (luaL_Buffer)
do
  local ok, err = pcall(function()
    local s = string.rep("ab", 1000)
    if #s ~= 2000 then error("rep len " .. #s) end
    local r = s:gsub("ab", "ba")
    if #r ~= 2000 then error("gsub len " .. #r) end
    if r:sub(1, 4) ~= "baba" then error("gsub content " .. r:sub(1, 4)) end
  end)
  chk("D50 strings", ok, err)
end

--------------------------------------- GC, then re-verify old constants
do
  collectgarbage()
  collectgarbage()
  local ok = keep ~= nil
  if ok then
    for i = 0, 49 do
      if keep[i + 1] ~= "k" .. i then ok = false end
    end
  end
  chk("D60 constants-survive-GC", ok)
  say("D61 mem=" .. memk() .. "K")
end

------------------------------------------- C-stack (dangerous: run LAST)
say("D70 stack ladder begins (if output stops here, note last level)")
do
  local function pdepth(n)
    if n <= 0 then return 0 end
    local ok, v = pcall(pdepth, n - 1)
    if not ok then return 1000 end   -- overflow marker (guard fired early)
    return v + 1
  end
  for _, d in ipairs{2, 4, 6, 8} do
    say("D71 pcall-depth " .. d .. " -> " .. tostring(pdepth(d)))
  end

  say("D72 unbounded pcall recursion (guard must stop it):")
  local depth = 0
  local function deep()
    depth = depth + 1
    say("D73 level " .. depth)
    pcall(deep)
  end
  pcall(deep)
  say("D74 stopped cleanly at depth " .. depth)

  local function chain(n) return 1 + chain(n + 1) end
  local ok, msg = pcall(chain, 1)
  chk("D75 deep-chain caught", ok == false and type(msg) == "string", msg)
  say("D76 msg: " .. tostring(msg))

  -- post-overflow canaries
  local s = 0
  for i = 1, 1000 do s = s + i end
  chk("D77 arithmetic-after-overflow", s == 500500, s)
  chk("D78 constants-after-overflow", keep ~= nil and keep[50] == "k49",
      keep and keep[50])
end

say("D99 DONE fails=" .. fails)
if fails == 0 then say("ALL DIAGNOSTICS PASSED") end
