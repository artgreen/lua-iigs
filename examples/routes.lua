-- Dijkstra's shortest path over a small weighted graph.
-- Linear scans are easy to read and plenty for seven stations.
local names = {'Depot','Orchard','Mill','Lake','Market','Hill','Harbor'}
local edges = {
  {{2,4},{3,2}}, {{1,4},{3,1},{5,5}}, {{1,2},{2,1},{4,7}},
  {{3,7},{5,2},{6,3}}, {{2,5},{4,2},{7,4}}, {{4,3},{7,1}},
  {{5,4},{6,1}}
}
local distance, previous, done = {[1]=0}, {}, {}
for _ = 1,#names do
  local best
  for node = 1,#names do
    if not done[node] and distance[node]
       and (not best or distance[node] < distance[best]) then best=node end
  end
  if not best then break end
  done[best] = true
  for _,edge in ipairs(edges[best]) do
    local next_node,cost = edge[1],edge[2]
    local candidate = distance[best]+cost
    if not distance[next_node] or candidate < distance[next_node] then
      distance[next_node], previous[next_node] = candidate,best
    end
  end
end
for node = 1,#names do
  local path, step = {},node
  while step do table.insert(path,1,names[step]); step=previous[step] end
  print(string.format('%2d  %s',distance[node],table.concat(path,' > ')))
end
assert(distance[7] == 12)
print('Routes complete: Harbor costs 12.')
