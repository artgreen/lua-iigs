-- See Copyright Notice in file all.lua.
-- Distinguish deferred file creation, second-open restrictions, and buffering.
print("BUFPROBE 3: creation, second opens, and flush")
print("R0=before write Rw=after write Rf=after flush Rc=after close")
io.stdout:flush()
local failed = 0
local function visible(path, mode)
  local f <close>, message, code = io.open(path, mode)
  if not f then return "open-err:" .. tostring(code) end
  local data, message, code = f:read("a")
  if data == nil then return "read-err:" .. tostring(code) end
  return string.format("%q", data)
end
local function create(path, data)
  local f <close> = assert(io.open(path, "wb"))
  assert(f:write(data))
  assert(f:close())
end
local function trial(label, seed, mode, buffering)
  print(label)
  io.stdout:flush()
  local path = os.tmpname()
  os.remove(path)
  local ok, err = pcall(function()
    if seed ~= nil then create(path, seed) end
    local f <close> = assert(io.open(path, mode))
    local readmode = mode:find("b", 1, true) and "rb" or "r"
    local before = visible(path, readmode)  -- match FILECHECK before setvbuf
    assert(f:setvbuf(buffering, 2000))
    assert(f:write("x"))
    local written = visible(path, readmode)
    assert(f:flush())
    local flushed = visible(path, readmode)
    assert(f:close())
    local closed = visible(path, readmode)
    print("R0=" .. before .. " Rw=" .. written .. " Rf=" .. flushed .. " Rc=" .. closed)
    assert(closed == string.format("%q", seed == "seed" and "xeed" or "x"),
           "wrong data after close")
  end)
  if not ok then
    failed = failed + 1
    print("FAIL " .. tostring(err))
  end
  local removed, message, code = os.remove(path)
  if not removed then print("cleanup err=" .. tostring(code)) end
  io.stdout:flush()
end
trial("B1 new file, w/full", nil, "w", "full")
trial("B2 existing empty file, w/full", "", "w", "full")
trial("B3 existing data, r+/full", "seed", "r+", "full")
trial("B4 new file, wb/full", nil, "wb", "full")
trial("B5 new file, w/no buffering", nil, "w", "no")
-- Reader-only sharing, independent of an open writer.
do
  print("B6 two simultaneous readers")
  local path = os.tmpname()
  local ok, err = pcall(function()
    create(path, "seed")
    local first <close> = assert(io.open(path, "rb"))
    local second = visible(path, "rb")
    print("second=" .. second)
    assert(second == '"seed"' and first:read("a") == "seed")
  end)
  if not ok then failed = failed + 1; print("FAIL " .. tostring(err)) end
  os.remove(path)
end
print("BUFPROBE 3 DONE cases=6 errors=" .. failed)
print("Report R0/Rw/Rf/Rc even when errors=0; expect shell prompt next")
io.stdout:flush()
