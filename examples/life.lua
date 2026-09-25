-- Conway's Life: two buffers prevent this generation changing its own inputs.
-- Fixed, empty edges. No terminal control codes or timing assumptions.
-- Comfort marker: one dot on stderr per generated generation.
local steps = tonumber(arg[1] or '6')
if not steps or steps % 1 ~= 0 or steps < 0 or steps > 100 then
  io.stderr:write('Usage: lua -E life.lua [generations 0..100]\n'); os.exit(1)
end
local width, height = 20, 10
local cells = {}
local function key(x, y) return (y - 1) * width + x end
for _, p in ipairs({{3,2}, {4,3}, {2,4}, {3,4}, {4,4}}) do
  cells[key(p[1], p[2])] = true
end
local function alive(x, y)
  return x >= 1 and x <= width and y >= 1 and y <= height and cells[key(x,y)]
end
for generation = 0, steps do
  print('Generation ' .. generation)
  local population = 0
  for y = 1, height do
    local row = {}
    for x = 1, width do
      local a = alive(x,y)
      row[x] = a and 'O' or '.'
      if a then population = population + 1 end
    end
    print(table.concat(row))
  end
  print('Population: ' .. population)
  io.flush()
  if generation < steps then
    local next_cells = {}
    for y = 1, height do
      for x = 1, width do
        local neighbors = 0
        for dy = -1, 1 do
          for dx = -1, 1 do
            if (dx ~= 0 or dy ~= 0) and alive(x+dx,y+dy) then
              neighbors = neighbors + 1
            end
          end
        end
        if neighbors == 3 or (alive(x,y) and neighbors == 2) then
          next_cells[key(x,y)] = true
        end
      end
    end
    cells = next_cells
    io.stderr:write('.')
    io.stderr:flush()
  end
end
if steps > 0 then io.stderr:write('\n') end
print('Life complete.')
