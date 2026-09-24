-- See Copyright Notice in file all.lua.
-- Real IIgs regression: converting the minimum float returned 0x7fff0000.
print("NUMCONV 1: integer/float boundary regression")
local lo, hi = math.mininteger, math.maxinteger
local checked = 0
local function check(label, ok)
  checked = checked + 1
  assert(ok, label)
end
for _, i in ipairs({lo, lo + 1, lo + 65535, -1, 0, 1, hi - 1, hi}) do
  local f = i + 0.0
  local name = tostring(i)
  check(name .. " roundtrip", math.tointeger(f) == i)
  check(name .. " equality", f == i and i == f)
  check(name .. " ordering", f <= i and i <= f and not(f < i or i < f))
  check(name .. " bit conversion", (f | 0) == i)
  check(name .. " floor", math.floor(f) == i)
  check(name .. " ceil", math.ceil(f) == i)
  local whole, part = math.modf(f)
  check(name .. " modf", whole == i and part == 0.0)
  local t = {[i] = "integer"}
  check(name .. " table read", t[f] == "integer")
  t[f] = "float"
  check(name .. " table write", t[i] == "float")
  local key = next(t)
  check(name .. " table key", math.type(key) == "integer" and key == i
        and next(t, key) == nil)
end
local f = lo + 0.0
check("min parsed", math.tointeger(tonumber(tostring(lo) .. ".0")) == lo)
check("min fractional rejected", math.tointeger(f + 0.5) == nil)
check("min fractional floor", math.floor(f + 0.5) == lo)
check("min fractional ceil", math.ceil(f + 0.5) == lo + 1)
check("below min rejected", math.tointeger(f - 1.0) == nil)
check("below min fractional rejected", math.tointeger(f - 0.5) == nil)
check("above max rejected", math.tointeger(hi + 1.0) == nil)
check("NaN rejected", math.tointeger(0.0 / 0.0) == nil)
check("positive infinity rejected", math.tointeger(math.huge) == nil)
check("negative infinity rejected", math.tointeger(-math.huge) == nil)
print("NUMCONV PASSED checks=" .. checked)
