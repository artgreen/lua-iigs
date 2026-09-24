-- Compile, dump, save, reload, and execute a chunk whose code exceeds 64 KiB.
local function mark(s) print(s); io.stdout:flush() end
mark("BYTEFILE 1: source and bytecode roundtrip beyond 64 KiB")
local count = 9000
local source_path, binary_path = os.tmpname(), os.tmpname()
os.remove(source_path)
os.remove(binary_path)
local function write(path, bytes)
  local f <close> = assert(io.open(path, "wb"))
  assert(f:write(bytes))
  assert(f:close())
end
local function verify(f)
  for _, seed in ipairs({0, 17, -1234}) do
    local result, bytes, nested = f(seed)
    assert(result == seed + count, "compiled result mismatch")
    assert(bytes == "\0\255BYTECODE\r\n", "binary constant mismatch")
    assert(type(nested) == "function", "nested prototype missing")
    collectgarbage("collect")
    assert(nested(23) == seed + count + 23, "nested upvalue mismatch")
  end
end
local ok, err = pcall(function()
  mark("P1 generate source with 9000 arithmetic statements")
  local block = string.rep("x=x+1 -- pad\n", 1000)
  local blocks = {"local x=...\n"}
  for i = 1, 9 do blocks[#blocks + 1] = block end
  blocks[#blocks + 1] =
    'return x, "\\0\\255BYTECODE\\r\\n", function(step) return x+step end\n'
  local source = table.concat(blocks)
  assert(#source > 65536, "source did not cross target boundary")
  mark("source bytes=" .. #source)
  write(source_path, source)
  source, blocks, block = nil, nil, nil
  collectgarbage("collect")
  mark("P2 load source file and execute")
  local f = assert(loadfile(source_path, "t"))
  verify(f)
  for _, strip in ipairs({false, true}) do
    local mode = strip and "stripped" or "debug"
    mark("P3 dump " .. mode)
    local dump = string.dump(f, strip)
    mark(mode .. " bytecode bytes=" .. #dump)
    assert(#dump > 65536, "bytecode did not cross target boundary")
    mark("P4 load from memory " .. mode)
    verify(assert(load(dump, "@bytefile-memory", "b")))
    mark("P5 save/reopen/compare " .. mode)
    write(binary_path, dump)
    do
      local file <close> = assert(io.open(binary_path, "rb"))
      assert(file:read("a") == dump, "saved bytecode mismatch")
      assert(file:close())
    end
    mark("P6 load binary file and execute " .. mode)
    verify(assert(loadfile(binary_path, "b")))
    mark("P7 reject wrong mode and truncated input " .. mode)
    local rejected, message = load(dump, "@bytefile-text-only", "t")
    assert(rejected == nil and type(message) == "string", "binary accepted as text")
    -- Truncate a known-valid chunk; do not execute corrupted bytecode.
    rejected, message = load(dump:sub(1, #dump - 1), "@bytefile-truncated", "b")
    assert(rejected == nil and type(message) == "string", "truncated chunk accepted")
    local text <close> = assert(io.open(source_path, "rb"))
    rejected, message = load(text:read("a"), "@bytefile-binary-only", "b")
    assert(rejected == nil and type(message) == "string", "source accepted as binary")
    assert(text:close())
    mark("P8 reload valid file after errors " .. mode)
    verify(assert(loadfile(binary_path, "b")))
    mark(mode .. " PASSED")
  end
end)
local source_removed, source_error = os.remove(source_path)
local binary_removed, binary_error = os.remove(binary_path)
if not ok then
  mark("BYTEFILE 1 FAILED: " .. tostring(err))
  error(err, 0)
end
assert(source_removed, source_error)
assert(binary_removed, binary_error)
collectgarbage("collect")
mark("BYTEFILE 1 PASSED variants=2 - expect shell prompt next")
