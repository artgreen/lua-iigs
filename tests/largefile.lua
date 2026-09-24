-- Binary file offsets beyond 16 bits, using small transfers and one handle.
-- Temporary file only; no simultaneous reader/writer sharing is required.
local function mark(s) print(s); io.stdout:flush() end
mark("LARGEFILE 1: binary offsets through 256 KiB")
local chunk = 4096
local initial = 262143  -- append will cross the 256 KiB boundary
local tail = "\0\255APPEND\r\n0123456789"
local total = initial + #tail
local bytes = {}
for i = 0, 255 do bytes[#bytes + 1] = string.char(i) end
-- Period 257 makes a 64 KiB offset error change the expected bytes.
local pattern = string.rep(table.concat(bytes) .. "!", 17)
local patches = {
  {65532, "\0\255PATCH64\r\n"},
  {131068, "\255\0PATCH128\n"},
  {196604, "\0\255PATCH192\r"},
}
local function original(offset, count)
  local first = offset % 257 + 1
  return pattern:sub(first, first + count - 1)
end
local function expected(offset, count, changed)
  local n = math.min(count, math.max(0, initial - offset))
  local data = original(offset, n)
  if count > n then
    local start = offset + n - initial + 1
    data = data .. tail:sub(start, start + count - n - 1)
  end
  if changed then
    for _, patch in ipairs(patches) do
      local first = math.max(offset, patch[1])
      local last = math.min(offset + count, patch[1] + #patch[2])
      if first < last then
        data = data:sub(1, first - offset) ..
               patch[2]:sub(first - patch[1] + 1, last - patch[1]) ..
               data:sub(last - offset + 1)
      end
    end
  end
  return data
end
local path = os.tmpname()
os.remove(path)  -- recreate as binary even if tmpname created a text file
local function verify(size, changed)
  local f <close> = assert(io.open(path, "rb"))
  assert(f:seek("end") == size, "file size mismatch")
  assert(f:seek("set", 0) == 0)
  local offset = 0
  while offset < size do
    local n = math.min(chunk, size - offset)
    local data = assert(f:read(n))
    assert(data == expected(offset, n, changed),
           "byte mismatch at chunk offset " .. offset)
    offset = offset + n
    assert(f:seek() == offset, "read position mismatch")
    if offset % 32768 == 0 or offset == size then
      mark("verified " .. offset .. "/" .. size)
    end
  end
  assert(f:read(1) == nil, "expected EOF")
  assert(f:seek("end", -16) == size - 16, "end-relative seek")
  assert(f:read(16) == expected(size - 16, 16, changed), "end-relative data")
  assert(f:close())
end
local ok, err = pcall(function()
  mark("L1 write 262143 bytes in small blocks")
  do
    local f <close> = assert(io.open(path, "wb"))
    local offset = 0
    while offset < initial do
      local n = math.min(chunk, initial - offset)
      assert(f:write(original(offset, n)))
      offset = offset + n
      assert(f:seek() == offset, "write position mismatch")
      if offset % 32768 == 0 or offset == initial then
        mark("written " .. offset .. "/" .. initial)
      end
    end
    assert(f:flush())
    assert(f:close())
  end
  mark("L2 reopen and verify every original byte")
  verify(initial, false)
  mark("L3 set/cur/end seeks near boundaries")
  do
    local f <close> = assert(io.open(path, "rb"))
    for _, offset in ipairs({32767, 32768, 65532, 65535, 65536,
                            131068, 131071, 131072,
                            196604, 196607, 196608, 262127}) do
      local n = math.min(32, initial - offset)
      assert(f:seek("set", offset) == offset, "absolute seek")
      assert(f:read(n) == original(offset, n), "absolute seek data")
      assert(f:seek("cur", -n) == offset, "backward relative seek")
      assert(f:seek("cur", 1) == offset + 1, "forward relative seek")
      assert(f:read(n - 1) == original(offset + 1, n - 1), "relative seek data")
      mark("seek OK " .. offset)
    end
    assert(f:close())
  end
  mark("L4 update across 64/128/192 KiB boundaries")
  do
    local f <close> = assert(io.open(path, "r+b"))
    for _, patch in ipairs(patches) do
      assert(f:seek("set", patch[1]) == patch[1])
      assert(f:write(patch[2]))
      assert(f:flush())
    end
    assert(f:close())
  end
  mark("L5 append across 256 KiB boundary")
  do
    local f <close> = assert(io.open(path, "ab"))
    assert(f:write(tail))
    assert(f:flush())
    assert(f:seek("end") == total, "append size mismatch")
    assert(f:close())
  end
  mark("L6 reopen and verify every updated byte")
  verify(total, true)
  mark("L7 truncate, reopen, and verify no stale tail")
  local short = "TRUNCATED\0\255\n"
  do
    local f <close> = assert(io.open(path, "wb"))
    assert(f:write(short))
    assert(f:close())
  end
  do
    local f <close> = assert(io.open(path, "rb"))
    assert(f:seek("end") == #short, "truncate size mismatch")
    assert(f:seek("set", 0) == 0)
    assert(f:read(#short) == short, "truncate data mismatch")
    assert(f:read(1) == nil, "stale data after truncation")
    assert(f:close())
  end
end)
local removed, remove_error = os.remove(path)
if not ok then
  mark("LARGEFILE 1 FAILED: " .. tostring(err))
  error(err, 0)
end
assert(removed, remove_error)
mark("LARGEFILE 1 PASSED bytes=" .. total .. " - expect shell prompt next")
