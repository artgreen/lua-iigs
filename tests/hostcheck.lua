-- Verify a separate native IIGSHOST process, then exercise Lua afterward.
local function mark(s) print(s); io.stdout:flush() end
local function read(path)
  local f <close> = assert(io.open(path, "rb"))
  return assert(f:read("a"))
end
local function write(path, bytes)
  local f <close> = assert(io.open(path, "wb"))
  assert(f:write(bytes)); assert(f:close())
end
local phase = assert(arg[1], "HOSTCHECK needs a phase")
local files = {"host.out", "host.err", "host.state"}
mark("HOSTCHECK 1 phase=" .. phase)
if phase == "prepare" then
  for _, path in ipairs(files) do
    local f = io.open(path, "rb")
    if f then assert(f:close()); assert(os.remove(path)) end
  end
  write("host.state", "prepared")
  mark("HOSTCHECK 1 PREPARED")
elseif phase == "verify" then
  assert(read("host.state") == "prepared", "missing host preparation")
  local stdout, stderr = read("host.out"), read("host.err")
  mark(stdout)
  if #stderr > 0 then mark(stderr) end
  local status = assert(tonumber(arg[2]), "missing native host status")
  assert(status == 0, "native host returned nonzero status")
  local text = stdout .. "\n" .. stderr
  assert(not text:match("%f[%a]FAIL%f[%A]") and not text:match("%f[%a]FAILED%f[%A]")
         and not text:find("MemCheck:", 1, true) and not text:match("%f[%a]BRK%f[%A]")
         and not text:find("mm=degraded", 1, true), "native host reported failure/corruption")
  local matches, yields = 0, nil
  for line in (stdout:gsub("\r\n", "\n"):gsub("\r", "\n") .. "\n"):gmatch("([^\n]*)\n") do
    local n = line:match("^IIGSHOST PASSED yields=(%d+)$")
    if n then matches = matches + 1; yields = tonumber(n) end
  end
  assert(matches == 1 and yields >= 2 and yields <= 10000, "missing/invalid native C-hook completion")
  write("host.state", "verified")
  mark("HOSTCHECK 1 HOST VERIFIED yields=" .. yields)
elseif phase == "finish" then
  assert(read("host.state") == "verified", "native host has not been verified")
  mark("HOSTCHECK 1 post-host Lua smoke")
  local smoke = assert(loadfile("hwsmoke.lua"))
  smoke()
  for _, path in ipairs(files) do assert(os.remove(path), "cleanup failed: " .. path) end
  mark("HOSTCHECK 1 PASSED - expect shell prompt next")
else
  error("unknown host-check phase: " .. phase)
end
