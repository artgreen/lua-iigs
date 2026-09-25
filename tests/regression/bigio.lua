-- Large single binary transfers; separate from large offsets/small chunks.
local function mark(s) print(s); io.stdout:flush() end
mark("BIGIO 1: single transfers around 32/64/128 KiB")
local sizes = {32767, 32768, 65535, 65536, 65537, 131072, 131073}
local bytes = {}
for i = 0, 255 do bytes[#bytes + 1] = string.char(i) end
local pattern = table.concat(bytes) .. "!"  -- period 257, includes NUL/FF/CR/LF
local function payload(n)
  -- string.rep has a separate INT_MAX limit in this port. Concatenation
  -- builds the input without making that unrelated API the test's gate.
  local s = pattern
  while #s < n do s = s .. s end
  return s:sub(1, n)
end
local path = os.tmpname()
os.remove(path)  -- ensure the recreated file is binary
local passed = 0
local ok, err = pcall(function()
  for _, n in ipairs(sizes) do
    collectgarbage("collect")
    mark("B1 build payload bytes=" .. n)
    local data = payload(n)
    assert(#data == n, "payload length mismatch")
    mark("B2 single write bytes=" .. n)
    do
      local f <close> = assert(io.open(path, "wb"))
      assert(f:write(data) == f, "single write failed")
      assert(f:flush())
      assert(f:seek() == n, "write position mismatch")
      assert(f:close())
    end
    mark("B3 single counted read bytes=" .. n)
    do
      local f <close> = assert(io.open(path, "rb"))
      assert(f:seek("end") == n, "file size mismatch")
      assert(f:seek("set", 0) == 0)
      local got = assert(f:read(n))
      assert(#got == n, "counted read length mismatch")
      assert(got == data, "counted read byte mismatch")
      assert(f:seek() == n, "counted read position mismatch")
      assert(f:read(1) == nil, "expected EOF after counted read")
      assert(f:close())
    end
    mark("B4 read all bytes=" .. n)
    do
      local f <close> = assert(io.open(path, "rb"))
      local got = assert(f:read("a"))
      assert(#got == n and got == data, "read-all mismatch")
      assert(f:seek() == n, "read-all position mismatch")
      assert(f:close())
    end
    mark("B5 counted read past EOF request=" .. (n + 17))
    do
      local f <close> = assert(io.open(path, "rb"))
      local got = assert(f:read(n + 17))
      assert(#got == n and got == data, "partial EOF read mismatch")
      assert(f:seek() == n, "partial EOF read position mismatch")
      assert(f:read(1) == nil, "expected EOF after partial read")
      assert(f:close())
    end
    assert(os.remove(path))
    passed = passed + 1
    mark("B6 PASS bytes=" .. n)
  end
end)
if not ok then
  os.remove(path)  -- temporary file only; all scoped handles have closed
  mark("BIGIO 1 FAILED after cases=" .. passed .. ": " .. tostring(err))
  error(err, 0)
end
collectgarbage("collect")
mark("BIGIO 1 PASSED cases=" .. passed .. " - expect shell prompt next")
