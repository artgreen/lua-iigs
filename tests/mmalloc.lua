-- Allocation boundary and aliasing checks; keep several live blocks.
-- The startup MM probe only validates attributes on a small block.
local blocks = {}
local function verify(s, n, unit)
  assert(#s == n, "allocation length")
  for start = 1, n, #unit do
    local count = math.min(#unit, n - start + 1)
    assert(s:sub(start, start + count - 1) == unit:sub(1, count),
           "allocation data mismatch at " .. start)
  end
end
for index, n in ipairs({16384, 28000, 33000, 40960, 65536, 131072}) do
  -- Distinct patterns detect aliasing even at aligned block offsets.
  local unit = string.rep(string.char(64 + index) .. "123456789abcdef", 256)
  local s = unit
  while #s < n do s = s .. s end
  s = s:sub(1, n)
  blocks[#blocks + 1] = {s, n, unit}
  collectgarbage()
  for _, live in ipairs(blocks) do verify(live[1], live[2], live[3]) end
  print("MM allocation intact " .. n)
end
print("MMALLOC PASSED")
