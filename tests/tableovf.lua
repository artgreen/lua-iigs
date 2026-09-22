-- Reach the 16-bit table limits and check recovery and existing entries.
if _VERSION ~= "Lua (IIgs) 5.4" then
  print("TABLEOVF SKIPPED (requires IIgs limits)")
  return
end
local t, last = {}, 0
local ok, err = pcall(function()
  for i = 1, 65536 do
    t[i] = i
    last = i
  end
end)
assert(not ok and type(err) == "string" and err:find("table overflow", 1, true), err)
assert(last >= 32768, "did not exercise widened rehash counter")
for i = 1, last do assert(t[i] == i, "entry damaged: " .. i) end
collectgarbage()
for i = 1, last do assert(t[i] == i, "entry damaged after GC: " .. i) end
print("TABLEOVF PASSED entries=" .. last)
