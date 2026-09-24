-- Reusable IIgs regression driver. suitecfg.lua is generated from suite.json.
-- Run in a dedicated writable directory; test scripts create temporary files.
local config = dofile("suitecfg.lua")
local group = (arg and arg[1]) or "full"
local selected = assert(config.groups[group], "unknown suite group: " .. group)
local out, stdout, fmt = print, io.stdout, string.format
local pairs, type, tostring, select = pairs, type, tostring, select
local loadfile, error, assert = loadfile, error, assert
local gc, hook, rawset = collectgarbage, debug.sethook, rawset
local concat, match, lower = table.concat, string.match, string.lower
local globals, setmeta, getmeta = _G, setmetatable, getmetatable
local input, output, stdin = io.input, io.output, io.stdin
-- tracegc can leave a dot without a newline; suite records always start a line.
local function mark(s) out("\n" .. s); stdout:flush() end
local function snapshot(t)
  local copy = {}
  for k, v in pairs(t) do copy[k] = v end
  return copy
end
local function restore(t, copy)
  for k in pairs(t) do rawset(t, k, nil) end
  for k, v in pairs(copy) do rawset(t, k, v) end
end
local baseline = snapshot(globals)
local meta = getmeta(globals)
local libs = {io, os, math, string, table, coroutine, debug, package, package.loaded}
local saved = {}
for i, lib in ipairs(libs) do saved[i] = snapshot(lib) end
local passed, partial = 0, 0
mark("IIGS SUITE 1 group=" .. group .. " tests=" .. #selected)
mark("Intermediate 'expect shell prompt' messages belong to individual tests.")
mark("Require SUITE COMPLETE and then the shell prompt. Stops on first failure.")
for index, name in ipairs(selected) do
  local spec = config.tests[name]
  local complete, bad, skipped = false, nil, false
  mark(fmt("SUITE START %d/%d %s", index, #selected, name))
  if spec.notice then mark(spec.notice) end
  if name == "files" then skipped = true end
  -- Observe only primitive arguments; do not invoke __tostring twice.
  globals.print = function(...)
    local words = {}
    for i = 1, select("#", ...) do
      local v = select(i, ...)
      words[i] = (type(v) == "string" or type(v) == "number") and tostring(v) or "?"
    end
    local line = concat(words, "\t")
    if match(line, spec.marker) or (spec.alternate and match(line, spec.alternate)) then
      complete = true
    end
    if match(line, "%f[%a]FAIL%f[%A]") or match(line, "%f[%a]FAILED%f[%A]")
        or match(line, "cleanup err=") then bad = line end
    if match(lower(line), "%f[%a]skip[%a]*%f[%A]") then skipped = true end
    if match(line, "skipping file tests") then bad = line end
    out(...)
  end
  globals.arg = {[0] = name .. ".lua"}
  globals._port, globals._soft = nil, nil
  globals.Message = nil
  globals.package.path = "?.lua"
  if name == "files" then globals._port, globals._soft = true, true end
  -- Call directly in the Lua VM. pcall/dofile wrappers consume scarce native
  -- stack and can make otherwise valid tests fail. Uncaught errors abort the
  -- process without SUITE COMPLETE, which is always a failed run.
  local chunk = assert(loadfile(name .. ".lua"))
  chunk()
  hook()
  local tracer = globals.package.loaded.tracegc
  if tracer then tracer.stop() end
  for i, lib in ipairs(libs) do restore(lib, saved[i]) end
  restore(globals, baseline)
  setmeta(globals, meta)
  input(stdin); output(stdout)
  gc("restart"); gc("incremental"); gc("collect")
  if bad or not complete then
    mark("SUITE FAIL " .. name .. ": " .. tostring(bad or "missing completion marker"))
    error("SUITE FAILED (remaining tests not run)", 0)
  end
  passed = passed + 1
  if skipped then partial = partial + 1 end
  mark("SUITE PASS " .. name .. (skipped and " WITH SKIPS" or ""))
end
mark(fmt("SUITE COMPLETE group=%s passed=%d failed=0 with_skips=%d", group, passed, partial))
mark("Expect shell prompt next")
