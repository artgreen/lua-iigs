-- sieve.lua -- minimal reproducer for the chained-coroutine C-stack
-- corruption (the bug behind coroutine.lua's on-hardware crashes).
--
--   lua sieve.lua [N]      -- N = target chain depth (default 40)
--
-- Builds a prime sieve as a chain of coroutine.wrap filters: every prime
-- found appends another filter, and pulling one value cascades a RESUME
-- through the whole chain at once. Coroutine CONTINUATION resumes run via
-- unroll(), which bypassed the ccall byte-guard, so a deep chain overran
-- the 24.8KB bank-0 stack segment into other bank-0 memory (text page
-- included). Before the lua_resume guard fix, this printed
-- "MemCheck: memory altered at ..." under GoldenGate at chain depths as
-- low as ~6, and crashed real hardware. After the fix it stops with a
-- clean, catchable "C stack overflow" once the chain hits the platform's
-- ~5-level limit -- no memory is corrupted.

local N = tonumber(...) or 40
local function gen (n)
  return coroutine.wrap(function () for i = 2, n do coroutine.yield(i) end end)
end
local function filter (p, g)
  return coroutine.wrap(function ()
    while 1 do
      local n = g()
      if n == nil then return end
      if n % p ~= 0 then coroutine.yield(n) end
    end
  end)
end

local x = gen(1000)
local a = {}
local ok, err = pcall(function ()
  while 1 do
    local n = x(); if n == nil then break end
    a[#a + 1] = n
    if #a >= N then break end
    x = filter(n, x)
  end
end)
print("chain=" .. N, "primes=" .. #a, ok and "OK" or ("caught: " .. tostring(err)))
