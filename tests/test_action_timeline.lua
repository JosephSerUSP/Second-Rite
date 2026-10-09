local timeline=require("engine.action_timeline")
local function run(steps)
    local state=timeline.new({{id="anticipation",duration=.25},{id="recovery",duration=.5}})
    local elapsed,exits=0,{}
    for _,dt in ipairs(steps) do
        timeline.advance(state,dt,function(_,slice) elapsed=elapsed+slice end,
            function(id) exits[#exits+1]={id,elapsed} end)
    end
    assert(state.done and #exits==2,"timeline must finish each phase once")
    assert(exits[1][1]=="anticipation" and math.abs(exits[1][2]-.25)<1e-9,"contact crossed at wrong time")
    assert(exits[2][1]=="recovery" and math.abs(exits[2][2]-.75)<1e-9,"recovery crossed at wrong time")
    timeline.advance(state,10,nil,function() error("completed timeline replayed") end)
end
run({1});run({.1,.1,.1,.1,.1,.1,.1,.1})
assert(not pcall(timeline.new,{{id="bad",duration=0}}))
assert(not pcall(timeline.new,{{id="bad",duration=0/0}}))
local held=timeline.new({{id="held",duration=1}})
timeline.advance(held,0,nil,function() error("zero dt crossed phase") end)
assert(held.time==0 and not held.done)
assert(not pcall(timeline.advance,held,-1))
print("ACTION TIMELINE TESTS OK")
