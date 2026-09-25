-- Cooperative scheduling: coroutines yield delays in virtual ticks.
-- No threads, sleeps, wall clock, busy waiting, or external dependencies.
local jobs = {}
local function add(name, repeats, delay)
  jobs[#jobs+1] = {name=name, wake=0, task=coroutine.create(function()
    for i = 1,repeats do
      print(name .. ' step ' .. i)
      if i < repeats then coroutine.yield(delay) end
    end
  end)}
end
add('Loader',3,2); add('Printer',4,1); add('Backup',2,3)
local completed = 0
while completed < #jobs do
  local next_tick
  for _,job in ipairs(jobs) do
    if not job.done and (not next_tick or job.wake < next_tick) then next_tick=job.wake end
  end
  print('Tick ' .. next_tick)
  for _,job in ipairs(jobs) do
    if not job.done and job.wake == next_tick then
      local ok,delay = coroutine.resume(job.task)
      assert(ok, tostring(delay))
      if coroutine.status(job.task) == 'dead' then
        job.done,completed = true,completed+1
      else
        assert(math.type(delay)=='integer' and delay>0,'invalid task delay')
        job.wake = next_tick+delay
      end
    end
  end
end
print('Workers complete: 3 jobs, 9 steps.')
