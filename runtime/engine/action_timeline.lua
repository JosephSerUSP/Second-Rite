-- Runtime-owned ordered phases. Splits large dt at boundaries; each exit runs
-- once, independently of drawing, input repeat, or animation availability.
local timeline = {}
function timeline.new(phases)
    assert(type(phases)=="table" and #phases>0,"timeline requires phases")
    for _,phase in ipairs(phases) do
        assert(type(phase.id)=="string" and type(phase.duration)=="number"
            and phase.duration>0 and phase.duration<math.huge,"invalid timeline phase")
    end
    return {phases=phases,index=1,time=0,done=false}
end
function timeline.phase(state)
    return not state.done and state.phases[state.index] or nil
end
function timeline.advance(state,dt,onStep,onExit)
    assert(type(dt)=="number" and dt>=0 and dt<math.huge,"invalid timeline dt")
    while not state.done and dt>0 do
        local phase=state.phases[state.index]
        local slice=math.min(dt,phase.duration-state.time)
        if onStep then onStep(phase.id,slice) end
        state.time=state.time+slice;dt=dt-slice
        if state.time>=phase.duration then
            state.index=state.index+1;state.time=0
            state.done=state.index>#state.phases
            if onExit then onExit(phase.id) end
        end
    end
    return dt
end
return timeline
