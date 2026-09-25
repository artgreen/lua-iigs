-- Classify five-card poker hands. Numeric ranks avoid lexical sort bugs.
-- Suits: C D H S; ranks: 2..9 T J Q K A. No betting or tie-break ranking.
local function classify(text)
  local ranks,suits,seen,counts = {},{},{},{}
  for token in text:upper():gmatch('%S+') do
    local r,s = token:match('^([2-9TJQKA])([CDHS])$')
    if not r or seen[token] then return nil,'Use five distinct cards, such as AS KD QH JC TS.' end
    seen[token] = true
    r = tonumber(r) or ({T=10,J=11,Q=12,K=13,A=14})[r]
    ranks[#ranks+1],suits[#suits+1] = r,s
    counts[r] = (counts[r] or 0)+1
  end
  if #ranks ~= 5 then return nil,'Exactly five cards are required.' end
  table.sort(ranks)
  local flush,straight,pair_count,three,four = true,true,0,false,false
  for i = 2,5 do
    if suits[i] ~= suits[1] then flush=false end
    if ranks[i] ~= ranks[1]+i-1 then straight=false end
  end
  if ranks[1]==2 and ranks[2]==3 and ranks[3]==4 and ranks[4]==5 and ranks[5]==14 then straight=true end
  for _,count in pairs(counts) do
    if count==4 then four=true elseif count==3 then three=true elseif count==2 then pair_count=pair_count+1 end
  end
  if straight and flush then return 'straight flush'
  elseif four then return 'four of a kind'
  elseif three and pair_count==1 then return 'full house'
  elseif flush then return 'flush'
  elseif straight then return 'straight'
  elseif three then return 'three of a kind'
  elseif pair_count==2 then return 'two pair'
  elseif pair_count==1 then return 'pair'
  else return 'high card' end
end
if arg[1] then
  local result,message = classify(table.concat(arg,' '))
  if not result then io.stderr:write(message,'\n'); os.exit(1) end
  print(result)
else
  for _,hand in ipairs({'AS KS QS JS TS','2C 2D 2H 2S AC','KC KD KH 3S 3D',
                       '2H 5H 8H TH KH','AS 2D 3H 4C 5S','7C 7D 7S 2H 9C',
                       'JC JD 4C 4D AH','KC KD 4H 5C 3S','2C 5D 8H JS AC'}) do
    print(hand .. ' : ' .. assert(classify(hand)))
  end
end
