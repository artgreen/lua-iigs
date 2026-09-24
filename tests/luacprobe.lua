-- Companion to the standalone LUAC batch test. Each phase is a fresh process.
local phase = assert(arg[1], "LUACPROBE needs a phase")
local function mark(s) print(s); io.stdout:flush() end
local function read(path)
  local f <close> = assert(io.open(path, "rb"))
  return assert(f:read("a"))
end
local function write(path, bytes)
  local f <close> = assert(io.open(path, "wb"))
  assert(f:write(bytes)); assert(f:close())
end
local paths = {"lc.small.lua", "lc.big.lua", "lc.bad.lua", "lc.deep.lua",
               "lc.small.out", "lc.debug.out", "lc.strip.out", "lc.again.out",
               "lc.bad.log", "lc.deep.log", "lc.state"}
local function advance(previous, nextstage)
  assert(read("lc.state") == previous, "missing/out-of-order compiler phase")
  write("lc.state", nextstage)
end
local function execute(path, increment, large)
  local bytes = read(path)
  assert(bytes:sub(1, 4) == "\27Lua", "not a Lua binary chunk")
  if large then assert(#bytes > 65536, "bytecode did not exceed 64 KiB") end
  local fn = assert(loadfile(path, "b"))
  for _, seed in ipairs({0, 17, -1234}) do
    local value, binary, nested = fn(seed)
    assert(value == seed + increment, "wrong compiled arithmetic result")
    assert(binary == "\0\255LUAC\r\n", "binary constant damaged")
    assert(type(nested) == "function", "nested function missing")
    collectgarbage("collect")
    assert(nested(23) == value + 23, "nested closure/upvalue damaged")
  end
  mark(path .. " verified bytes=" .. #bytes)
  return #bytes
end
local function rejected(logpath, sourcepath, fragment)
  local status = assert(tonumber(arg[2]), "missing compiler exit status")
  assert(status ~= 0, "compiler unexpectedly accepted invalid source")
  local text = read(logpath)
  mark(text)
  assert((not sourcepath or text:find(sourcepath, 1, true)) and text:find(fragment, 1, true),
         "wrong compiler error; inspect diagnostic above")
  assert(not text:find("MemCheck:", 1, true) and not text:match("%f[%a]BRK%f[%A]"),
         "corruption while rejecting source")
end

mark("LUACPROBE 1 phase=" .. phase)
if phase == "prepare" then
  -- These names belong exclusively to this probe in its dedicated directory.
  -- Clear stale outputs so a failed compile cannot reuse a previous result.
  for _, path in ipairs(paths) do
    local f = io.open(path, "rb")
    if f then assert(f:close()); assert(os.remove(path)) end
  end
  local tail = 'return x, "\\0\\255LUAC\\r\\n", function(step) return x+step end\n'
  write("lc.small.lua", "local x=(...)+42\n" .. tail)
  local block = string.rep("x=x+1 -- pad\n", 1000)
  local parts = {"local x=...\n"}
  for i = 1, 9 do parts[#parts + 1] = block end
  parts[#parts + 1] = tail
  local source = table.concat(parts)
  assert(#source > 65536)
  write("lc.big.lua", source)
  write("lc.bad.lua", "local =\n")
  write("lc.deep.lua", "return " .. string.rep("(", 500) .. "1" .. string.rep(")", 500) .. "\n")
  write("lc.state", "prepared")
  mark("prepared large source bytes=" .. #source)
elseif phase == "small" then
  execute("lc.small.out", 42, false)
  advance("prepared", "small")
elseif phase == "debug" then
  execute("lc.debug.out", 9000, true)
  advance("small", "debug")
elseif phase == "stripped" then
  local length = execute("lc.strip.out", 9000, true)
  assert(length < #read("lc.debug.out"), "stripping did not reduce bytecode size")
  advance("debug", "stripped")
elseif phase == "syntax" then
  rejected("lc.bad.log", "lc.bad.lua", "expected")
  advance("stripped", "syntax")
elseif phase == "depth" then
  -- The native stack guard raises before the parser adds a source location.
  rejected("lc.deep.log", nil, "luactest: C stack overflow")
  advance("syntax", "depth")
elseif phase == "recovery" then
  execute("lc.again.out", 42, false)
  advance("depth", "recovery")
elseif phase == "finish" then
  assert(read("lc.state") == "recovery", "compiler test did not finish every phase")
  for _, path in ipairs(paths) do assert(os.remove(path), "cleanup failed: " .. path) end
  mark("LUACPROBE 1 PASSED checks=6 - expect shell prompt next")
else
  error("unknown compiler-test phase: " .. phase)
end
if phase ~= "finish" then mark("LUACPROBE 1 PHASE PASSED " .. phase) end
