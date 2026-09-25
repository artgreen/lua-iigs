-- Backtracking with tables: count N-queens solutions and show the first.
-- At most eight nested calls; deliberately modest for the IIgs native stack.
local n = tonumber(arg[1] or '8')
if not n or n % 1 ~= 0 or n < 1 or n > 8 then
  io.stderr:write('Usage: lua -E queens.lua [board size 1..8]\n'); os.exit(1)
end
local columns, rising, falling, board, first = {}, {}, {}, {}, nil
local count = 0
local function place(row)
  if row > n then
    count = count + 1
    if not first then
      first = {}
      for r = 1, n do first[r] = board[r] end
    end
    return
  end
  for col = 1, n do
    if not columns[col] and not rising[row+col] and not falling[row-col] then
      board[row], columns[col], rising[row+col], falling[row-col] = col, true, true, true
      place(row+1)
      columns[col], rising[row+col], falling[row-col] = nil, nil, nil
    end
  end
end
print('Searching ' .. n .. ' x ' .. n .. ' board...'); io.flush()
place(1)
if first then
  for row = 1, n do
    local line = {}
    for col = 1, n do line[col] = first[row] == col and 'Q' or '.' end
    print(table.concat(line, ' '))
  end
end
print(string.format('Queens: n=%d solutions=%d', n, count))
