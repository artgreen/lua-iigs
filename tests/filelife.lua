-- Repeat file cleanup through normal return, errors, coroutines, loops, GC.
local function mark(s) print(s); io.stdout:flush() end
mark("FILELIFE 1: repeated file cleanup and recovery")
local path = os.tmpname()
os.remove(path)
local cases = 0
local function verify(expected)
  local f <close> = assert(io.open(path, "rb"))
  assert(f:read("a") == expected, "data after automatic close mismatch")
  assert(f:close())
  assert(os.remove(path), "temporary file cleanup failed")
  cases = cases + 1
end
local function normal(data)
  local f <close> = assert(io.open(path, "wb"))
  assert(f:setvbuf("full", 2000))
  assert(f:write(data))
  return f  -- retain the userdata to check that scope exit closed it
end
local previous = collectgarbage("incremental")
local ok, err = pcall(function()
  for _, mode in ipairs({"incremental", "generational"}) do
    collectgarbage(mode)
    mark("GC mode " .. mode)
    for round = 1, 12 do
      local data = "round=" .. round .. ":" .. mode .. "\0\255\r\n"
      mark("round " .. round .. " normal return")
      local closed = normal(data)
      assert(io.type(closed) == "closed file", "normal return leaked handle")
      verify(data)

      mark("round " .. round .. " error unwind")
      local held
      local success, reason = pcall(function()
        local f <close> = assert(io.open(path, "wb"))
        held = f
        assert(f:setvbuf("full", 2000))
        assert(f:write(data))
        error("FILELIFE intentional error", 0)
      end)
      assert(not success and reason == "FILELIFE intentional error")
      assert(io.type(held) == "closed file", "error unwind leaked handle")
      held = nil
      verify(data)

      mark("round " .. round .. " coroutine close")
      local co = coroutine.create(function()
        local f <close> = assert(io.open(path, "wb"))
        assert(f:setvbuf("full", 2000))
        assert(f:write(data))
        coroutine.yield(f)
        error("cancelled coroutine continued")
      end)
      local resumed, handle = coroutine.resume(co)
      assert(resumed and io.type(handle) == "file")
      assert(coroutine.status(co) == "suspended")
      assert(coroutine.close(co))
      assert(coroutine.status(co) == "dead")
      assert(io.type(handle) == "closed file", "coroutine close leaked handle")
      verify(data)

      mark("round " .. round .. " early loop exit")
      normal("first\nsecond\n")
      local iterator, state, control, closing = io.lines(path)
      assert(io.type(closing) == "file")
      local seen = 0
      for line in iterator, state, control, closing do
        assert(line == "first")
        seen = seen + 1
        break
      end
      assert(seen == 1 and io.type(closing) == "closed file",
             "early loop exit leaked handle")
      verify("first\nsecond\n")

      mark("round " .. round .. " garbage-collected writer")
      local weak = setmetatable({}, {__mode = "v"})
      do
        local orphan = assert(io.open(path, "wb"))
        assert(orphan:setvbuf("full", 2000))
        assert(orphan:write(data))
        weak[1] = orphan
        orphan = nil  -- deliberately no explicit close or <close> variable
      end
      collectgarbage("collect")
      collectgarbage("collect")
      assert(weak[1] == nil, "orphaned file remains reachable")
      verify(data)
      mark(mode .. " round " .. round .. " PASSED cases=" .. cases)
    end
  end
end)
collectgarbage(previous)
collectgarbage("collect")
collectgarbage("collect")
if not ok then
  os.remove(path)
  mark("FILELIFE 1 FAILED after cases=" .. cases .. ": " .. tostring(err))
  error(err, 0)
end
assert(cases == 120)
mark("FILELIFE 1 PASSED cases=120 - expect shell prompt next")
