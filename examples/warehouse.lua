-- Deterministic warehouse simulation for the IIgs Lua interpreter.
-- Three coroutines generate 600 text transactions. The main loop parses and
-- applies them, then independently replays the audit log and checks totals.
-- No files, modules, clock, or external input are needed.

local WAREHOUSES, SKUS, PER_PRODUCER = 6, 12, 200
local INITIAL_STOCK = 3
local EXPECTED = {
  events = 600,
  restocks = 60,
  fulfilled = 220,
  backorders = 320,
  restocked_units = 486,
  shipped_units = 499,
  backordered_units = 1122,
  digest = 32697,
}

local function mark(message)
  print(message)
  io.flush()
end

local function new_stock()
  return setmetatable({}, {__index = function() return INITIAL_STOCK end})
end

local function stock_key(warehouse, sku)
  return warehouse .. ":" .. sku
end

local function parse(line)
  local kind, id, warehouse, sku, qty =
    line:match("^([SR]),(%d+),(%d+),(%d+),(%d+)$")
  assert(kind, "bad transaction syntax")
  id, warehouse, sku, qty = tonumber(id), tonumber(warehouse),
                            tonumber(sku), tonumber(qty)
  assert(id > 0 and warehouse >= 1 and warehouse <= WAREHOUSES
    and sku >= 1 and sku <= SKUS and qty >= 1 and qty <= 10,
    "bad transaction value")
  return kind, id, warehouse, sku, qty
end

local function new_random(seed)
  return function()
    seed = (seed * 25173 + 13849) % 65536
    return seed
  end
end

local function producer(number)
  return coroutine.create(function()
    local random = new_random(number * 257 + 17)
    for i = 1, PER_PRODUCER do
      local warehouse = ((random() >> 8) % WAREHOUSES) + 1
      local sku = ((random() >> 4) % SKUS) + 1
      local qty = ((random() >> 5) % 5) + 1
      local kind = (i % 10 == 0) and "R" or "S"
      if kind == "R" then qty = qty + 5 end
      coroutine.yield(string.format("%s,%d,%d,%d,%d", kind,
        number * 1000 + i, warehouse, sku, qty))
    end
  end)
end

local stock = new_stock()
local sold = setmetatable({}, {__index = function() return 0 end})
local audit = {}
local stats = {
  events = 0, restocks = 0, fulfilled = 0, backorders = 0,
  restocked_units = 0, shipped_units = 0, backordered_units = 0,
  digest = 0,
}

local function process(line)
  local kind, id, warehouse, sku, qty = parse(line)
  local key = stock_key(warehouse, sku)
  local status
  if kind == "R" then
    stock[key] = stock[key] + qty
    stats.restocks = stats.restocks + 1
    stats.restocked_units = stats.restocked_units + qty
    status = "R"
  elseif stock[key] >= qty then
    stock[key] = stock[key] - qty
    sold[sku] = sold[sku] + qty
    stats.fulfilled = stats.fulfilled + 1
    stats.shipped_units = stats.shipped_units + qty
    status = "F"
  else
    stats.backorders = stats.backorders + 1
    stats.backordered_units = stats.backordered_units + qty
    status = "B"
  end
  stats.events = stats.events + 1
  for i = 1, #line do
    stats.digest = (stats.digest * 33 + line:byte(i)) % 65521
  end
  stats.digest = (stats.digest * 33 + status:byte()) % 65521
  audit[#audit + 1] = line .. "," .. status
end

local function total_stock(table_of_stock)
  local total = 0
  for warehouse = 1, WAREHOUSES do
    for sku = 1, SKUS do
      local amount = table_of_stock[stock_key(warehouse, sku)]
      assert(amount >= 0, "negative stock")
      total = total + amount
    end
  end
  return total
end

mark("W0 parsing and rollback checks")
assert(stock["1:1"] == INITIAL_STOCK)  -- exercise __index
assert(not pcall(process, "not a transaction"))
assert(not pcall(process, "S,9999,7,1,1"))
assert(#audit == 0 and stats.events == 0)

mark("W1 running three producers")
local workers = {producer(1), producer(2), producer(3)}
local active = #workers
while active > 0 do
  for i = 1, #workers do
    local worker = workers[i]
    if coroutine.status(worker) ~= "dead" then
      local ok, line = coroutine.resume(worker)
      assert(ok, tostring(line))
      if line then
        process(line)
        if stats.events % 100 == 0 then
          assert(total_stock(stock) ==
            WAREHOUSES * SKUS * INITIAL_STOCK +
            stats.restocked_units - stats.shipped_units)
          collectgarbage("collect")
          mark("W2 processed " .. stats.events)
        end
      else
        assert(coroutine.status(worker) == "dead")
        active = active - 1
      end
    end
  end
end

mark("W3 replaying audit log")
local replay_stock = new_stock()
local replay_sold = setmetatable({}, {__index = function() return 0 end})
local replay = {restocks = 0, fulfilled = 0, backorders = 0,
  restocked_units = 0, shipped_units = 0, backordered_units = 0}
local seen = {}
for i = 1, #audit do
  local line, recorded = audit[i]:match("^([SR],%d+,%d+,%d+,%d+),([RFB])$")
  assert(line and recorded, "bad audit row")
  local kind, id, warehouse, sku, qty = parse(line)
  assert(not seen[id], "duplicate transaction")
  seen[id] = true
  local key = stock_key(warehouse, sku)
  if kind == "R" then
    assert(recorded == "R")
    replay_stock[key] = replay_stock[key] + qty
    replay.restocks = replay.restocks + 1
    replay.restocked_units = replay.restocked_units + qty
  elseif replay_stock[key] >= qty then
    assert(recorded == "F")
    replay_stock[key] = replay_stock[key] - qty
    replay_sold[sku] = replay_sold[sku] + qty
    replay.fulfilled = replay.fulfilled + 1
    replay.shipped_units = replay.shipped_units + qty
  else
    assert(recorded == "B")
    replay.backorders = replay.backorders + 1
    replay.backordered_units = replay.backordered_units + qty
  end
end

assert(#audit == stats.events)
for name, value in pairs(replay) do assert(stats[name] == value, name) end
assert(total_stock(stock) == total_stock(replay_stock))
for warehouse = 1, WAREHOUSES do
  for sku = 1, SKUS do
    local key = stock_key(warehouse, sku)
    assert(stock[key] == replay_stock[key], "stock mismatch")
  end
end
for sku = 1, SKUS do
  assert(sold[sku] == replay_sold[sku], "sales mismatch")
end

mark("W4 ranking products")
local ranking = {}
for sku = 1, SKUS do ranking[sku] = {sku = sku, units = sold[sku]} end
table.sort(ranking, function(a, b)
  if a.units == b.units then return a.sku < b.sku end
  return a.units > b.units
end)
for i = 2, #ranking do
  assert(ranking[i - 1].units >= ranking[i].units, "sort mismatch")
end
assert(ranking[1].sku == 11 and ranking[1].units == 72)

for name, value in pairs(EXPECTED) do
  assert(stats[name] == value, name .. ": " .. stats[name] .. " != " .. value)
end
collectgarbage("collect")
mark(string.format("WAREHOUSE PASSED events=%d shipped=%d backorders=%d digest=%d top=%d",
  stats.events, stats.shipped_units, stats.backorders,
  stats.digest, ranking[1].sku))
