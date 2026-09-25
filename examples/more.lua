-- A line-at-a-time pager; Enter continues, q or EOF stops cleanly.
local filename = arg[1]
if not filename then
  io.write('File to read: '); io.flush(); filename=io.read('*l')
end
if not filename or filename == '' then print('No file selected.'); return end
local file,message = io.open(filename,'r')
if not file then io.stderr:write(tostring(message),'\n'); os.exit(1) end
local lines = 0
while true do
  local line,read_error = file:read('*l')
  if not line then
    file:close()
    if read_error then io.stderr:write(read_error,'\n'); os.exit(1) end
    print('End of file.'); break
  end
  print(line); lines=lines+1
  if lines % 20 == 0 then
    io.write('Enter: more, q: quit > '); io.flush()
    local answer = io.read('*l')
    if not answer or answer:lower():match('^%s*q') then
      file:close(); print('\nPager closed.'); break
    end
  end
end
