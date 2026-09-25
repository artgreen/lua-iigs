-- Streaming word counts, with deterministic sorting for ties.
-- ASCII letters only; at most 512 distinct words to keep the demo bounded.
local counts, distinct, total = {}, 0, 0
local function consume(line)
  for word in line:lower():gmatch('[a-z]+') do
    if not counts[word] then
      if distinct == 512 then return nil, 'More than 512 distinct words.' end
      distinct = distinct + 1
      counts[word] = 0
    end
    counts[word], total = counts[word]+1,total+1
  end
  return true
end
if arg[1] then
  local file, message = io.open(arg[1], 'r')
  if not file then io.stderr:write(tostring(message), '\n'); os.exit(1) end
  while true do
    local line, read_error = file:read('*l')
    if not line then
      file:close()
      if read_error then io.stderr:write(read_error, '\n'); os.exit(1) end
      break
    end
    local ok, why = consume(line)
    if not ok then file:close(); io.stderr:write(why, '\n'); os.exit(1) end
  end
else
  consume('Lua on the Apple IIgs. Small machine, big ideas!')
  consume('Lua tables count words. Lua makes small tools.')
end
local ranking = {}
for word,count in pairs(counts) do ranking[#ranking+1] = {word=word,count=count} end
table.sort(ranking, function(a,b)
  if a.count == b.count then return a.word < b.word end
  return a.count > b.count
end)
print(string.format('Words: %d total, %d distinct',total,distinct))
for i = 1, math.min(12,#ranking) do
  print(string.format('%4d  %s',ranking[i].count,ranking[i].word))
end
