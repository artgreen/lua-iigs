-- stack calibration: recurse via pcall to a fixed depth
-- run at several depths and compare memcheck "Stack Usage" high-water marks
local depth = tonumber(...) or 20
local function f(n)
  if n <= 0 then return 0 end
  local ok, v = pcall(f, n - 1)
  if not ok then return -1 end
  return v + 1
end
print("requested depth:", depth, "reached:", f(depth))
