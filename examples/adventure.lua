-- A tiny table-driven adventure. Explore, find the key, light the beacon.
local rooms = {
  dock={text='The dock. A path leads north to a shed.', exits={north='shed'}},
  shed={text='A tool shed. Paths lead south and east.', exits={south='dock',east='hill'}, item='key'},
  hill={text='A hill below the lighthouse. West: shed. North: tower.', exits={west='shed',north='tower'}},
  tower={text='The beacon is dark. A locked cabinet holds its switch.', exits={south='hill'}},
}
local room,inventory = 'dock',{}
local function look()
  print(rooms[room].text)
  if rooms[room].item then print('You see a ' .. rooms[room].item .. '.') end
end
print('BEACON: a small island adventure')
print('Commands: look, north/south/east/west, take key, use key, inventory, quit')
look()
while true do
  io.write('> '); io.flush()
  local line = io.read('*l')
  if not line then print('\nGoodbye.'); break end
  local command = line:lower():match('^%s*(.-)%s*$')
  if command == 'quit' or command == 'q' then print('Goodbye.'); break
  elseif command == 'look' then look()
  elseif command == 'inventory' then print(inventory.key and 'Carrying: key' or 'Carrying: nothing')
  elseif command == 'take key' then
    if rooms[room].item == 'key' then
      rooms[room].item,inventory.key = nil,true; print('Taken.')
    else print('No key here.') end
  elseif command == 'use key' then
    if not inventory.key then print('You need a key.')
    elseif room ~= 'tower' then print('Nothing here needs unlocking.')
    else print('The beacon shines. Ships can find the harbor!'); print('Adventure complete.'); break end
  elseif rooms[room].exits[command] then room=rooms[room].exits[command]; look()
  elseif command ~= '' then print('Try look, a direction, take key, use key, inventory, or quit.') end
end
