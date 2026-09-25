-- Iterative depth-first search carves a perfect maze (exactly one route
-- between cells). An explicit stack avoids deep native recursion.
local seed = tonumber(arg[1] or '42')
if not seed or seed % 1 ~= 0 or seed < 0 or seed > 65535
   or (arg[2] and arg[2] ~= 'solve') then
  io.stderr:write('Usage: lua -E maze.lua [seed 0..65535] [solve]\n'); os.exit(1)
end
local original_seed = seed
local function choose(n)
  seed = (seed * 25173 + 13849) % 65536 -- fits a signed 32-bit Lua integer
  return (seed >> 8) % n + 1
end
local w, h, grid, seen, parent, stack = 12, 8, {}, {}, {}, {1}
local function xy(cell) return (cell-1) % w+1, (cell-1)//w+1 end
for y = 1, 2*h+1 do
  grid[y] = {}
  for x = 1, 2*w+1 do grid[y][x] = '#' end
end
seen[1], grid[2][2] = true, ' '
while #stack > 0 do
  local cell = stack[#stack]
  local x,y = xy(cell)
  local candidates = {}
  for _, d in ipairs({{0,-1}, {1,0}, {0,1}, {-1,0}}) do
    local nx,ny = x+d[1],y+d[2]
    local next_cell = (ny-1)*w+nx
    if nx>=1 and nx<=w and ny>=1 and ny<=h and not seen[next_cell] then
      candidates[#candidates+1] = {next_cell,nx,ny}
    end
  end
  if #candidates == 0 then
    stack[#stack] = nil
  else
    local next_cell,nx,ny = table.unpack(candidates[choose(#candidates)])
    grid[y+ny][x+nx], grid[ny*2][nx*2] = ' ', ' '
    seen[next_cell], parent[next_cell] = true,cell
    stack[#stack+1] = next_cell
  end
end
if arg[2] == 'solve' then
  local cell = w*h
  while cell ~= 1 do
    local x,y = xy(cell)
    local px,py = xy(parent[cell])
    grid[y*2][x*2], grid[y+py][x+px] = '.', '.'
    cell = parent[cell]
  end
end
grid[2][2], grid[2*h][2*w] = 'S','E'
print('Maze seed=' .. original_seed .. ' (S to E)')
for _,row in ipairs(grid) do print(table.concat(row)) end
print('Maze complete: 96 connected cells.')
