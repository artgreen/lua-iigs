-- See Copyright Notice in file all.lua.
-- Observe binary integrity, text newline handling, and repeated EOF reads.
print("IOPROBE 1: file bytes, text modes, and EOF")
io.stdout:flush()
local path = os.tmpname()
local checks, failures = 0, 0
local function check(name, ok)
  checks = checks + 1
  if not ok then
    failures = failures + 1
    print("FAIL " .. name)
  end
end
local function hex(s)
  if s == nil then return "nil" end
  local t = {}
  for i = 1, #s do t[i] = string.format("%02X", string.byte(s, i)) end
  return table.concat(t, " ")
end
local function write(mode, data)
  -- Recreate truncated files: GS/OS file type can survive reopening with
  -- a different mode, so reusing a BIN file would hide TXT behavior.
  if mode == "w" or mode == "wb" then os.remove(path) end
  local f <close> = assert(io.open(path, mode))
  assert(f:write(data))
  assert(f:close())
end
local function read(mode, format)
  local f <close> = assert(io.open(path, mode))
  return f:read(format)
end
local function phase(name, fn)
  print(name)
  io.stdout:flush()
  local ok, err = pcall(fn)
  check(name .. " completed", ok)
  if not ok then print(tostring(err)) end
  io.stdout:flush()
end

phase("I1 binary roundtrip/seek/append", function()
  local bytes = {}
  for i = 0, 255 do bytes[#bytes + 1] = string.char(i) end
  local data = string.rep(table.concat(bytes), 17)
  write("wb", data)
  check("binary all 4352 bytes", read("rb", "a") == data)
  local f <close> = assert(io.open(path, "rb"))
  check("binary first bytes", f:read(256) == data:sub(1, 256))
  check("binary seek", f:seek("set", 1023) == 1023)
  check("binary boundary bytes", f:read(258) == data:sub(1024, 1281))
  assert(f:close())
  write("ab", "\0\xFF\r\n")
  check("binary append", read("rb", "a") == data .. "\0\xFF\r\n")
end)

phase("I2 restored upstream byte fixture", function()
  write("w", '"\xE1lo"{a}\n\xE7fourth_line\n')
  local f <close> = assert(io.open(path, "r"))
  local first, rest = f:read(5, "l")
  check("fixture first five bytes", first == '"\xE1lo"')
  check("fixture remainder", rest == "{a}")
  check("fixture single high byte", f:read(1) == "\xE7")
  check("fixture second line", f:read("l") == "fourth_line")
end)

phase("I3 text newline comparison", function()
  local text = "A\nB\n"
  write("w", text)
  local raw = read("rb", "a")
  local all = read("r", "a")
  local counted = read("r", #text)
  local f <close> = assert(io.open(path, "r"))
  local lines = assert(f:read("L")) .. assert(f:read("L"))
  print("expected : " .. hex(text))
  print("disk rb/a: " .. hex(raw))
  print("text r/a : " .. hex(all))
  print("text r/4 : " .. hex(counted))
  print("text r/L : " .. hex(lines))
  check("text all logical newlines", all == text)
  check("text counted logical newlines", counted == text)
  check("text lines logical newlines", lines == text)
  assert(f:close())
  local mixed <close> = assert(io.open(path, "r"))
  assert(mixed:read("l") == "A")
  local afterline = mixed:read("a")
  print("line then a: " .. hex(afterline))
  check("text all after line", afterline == "B\n")
  assert(mixed:close())
  local countedmix <close> = assert(io.open(path, "r"))
  assert(countedmix:read("l") == "A")
  local aftercount = countedmix:read(2)
  print("line then 2: " .. hex(aftercount))
  check("text count after line", aftercount == "B\n")
end)

phase("I4 repeated reads at EOF", function()
  write("wb", "x")
  local f <close> = assert(io.open(path, "rb"))
  check("EOF initial byte", f:read(1) == "x")
  for i = 1, 8 do
    check("EOF byte " .. i, f:read(1) == nil)
    check("EOF line " .. i, f:read("l") == nil)
  end
  check("EOF all empty", f:read("a") == "")
  check("EOF seek resets", f:seek("set", 0) == 0 and f:read(1) == "x")
end)

check("temporary file removed", os.remove(path) ~= nil)
print("IOPROBE 1 DONE checks=" .. checks .. " failures=" .. failures)
print("Expect shell prompt next")
io.stdout:flush()
