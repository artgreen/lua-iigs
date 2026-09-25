-- A small, no-betting blackjack game. Dealer stands on soft 17.
-- A natural blackjack beats a three-card 21; equal hands are a push.
local seed = tonumber(arg[1] or '42')
if not seed or seed % 1 ~= 0 or seed < 0 or seed > 65535 then
  io.stderr:write('Usage: lua -E blackjack.lua [seed 0..65535]\n'); os.exit(1)
end
local function random(n)
  seed = (seed * 25173 + 13849) % 65536
  return (seed >> 8) % n+1
end
local function score(hand)
  local total,aces = 0,0
  for _,card in ipairs(hand) do
    local rank = (card-1)%13+1
    if rank==1 then total,aces=total+11,aces+1
    else total=total+math.min(rank,10) end
  end
  while total>21 and aces>0 do total,aces=total-10,aces-1 end
  return total
end
local function show(hand)
  local labels = {'A','2','3','4','5','6','7','8','9','10','J','Q','K'}
  local suits = {'C','D','H','S'}
  local text = {}
  for i,card in ipairs(hand) do text[i]=labels[(card-1)%13+1]..suits[(card-1)//13+1] end
  return table.concat(text,' ')
end
local function ask(prompt)
  io.write(prompt); io.flush()
  local line=io.read('*l')
  return line and line:lower():match('^%s*(.-)%s*$') or 'q'
end
local wins,losses,pushes = 0,0,0
print('Blackjack. h: hit, s: stand, q: quit. Dealer stands on 17.')
print('Shuffle seed: '..seed)
while true do
  local deck = {}
  for card=1,52 do deck[card]=card end
  for i=52,2,-1 do local j=random(i); deck[i],deck[j]=deck[j],deck[i] end
  local function draw(hand) hand[#hand+1]=assert(table.remove(deck)) end
  local player,dealer = {},{}
  draw(player); draw(dealer); draw(player); draw(dealer)
  print('You: '..show(player)..' = '..score(player))
  print('Dealer shows: '..show({dealer[1]}))
  local quit=false
  while score(player)<21 and score(dealer)~=21 do
    local answer=ask('Hit, stand, or quit? ')
    if answer=='q' then quit=true; break
    elseif answer=='s' then break
    elseif answer=='h' then draw(player); print('You: '..show(player)..' = '..score(player))
    else print('Please enter h, s, or q.') end
  end
  if quit then break end
  if score(player)<=21 and not (#player==2 and score(player)==21) then
    while score(dealer)<17 do draw(dealer) end
  end
  local p,d = score(player),score(dealer)
  local pn,dn = p==21 and #player==2,d==21 and #dealer==2
  print('Dealer: '..show(dealer)..' = '..d)
  if p>21 or (dn and not pn) or (not pn and d<=21 and d>p) then
    losses=losses+1; print('Dealer wins.')
  elseif d>21 or (pn and not dn) or p>d then
    wins=wins+1; print(pn and 'Blackjack! You win.' or 'You win.')
  else pushes=pushes+1; print('Push: a tie.') end
  local answer
  repeat answer=ask('Another hand? y/n: ') until answer=='y' or answer=='n' or answer=='q'
  if answer~='y' then break end
end
print(string.format('Score: %d wins, %d losses, %d pushes',wins,losses,pushes))
print('Thanks for playing Blackjack!')
