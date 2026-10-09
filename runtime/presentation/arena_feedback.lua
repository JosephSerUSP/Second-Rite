-- Projections of committed contact facts. No damage, timing or root mutation.
local feedback = {}
function feedback.decorate(session,side,animated)
    local state=session.arenaEncounter
    if not state then return animated end
    local impact=state.impact
    local age=impact and state.elapsed-impact.time or 999
    local hit=impact and not impact.miss and ((impact.side=="player" and side=="enemy")
        or (impact.side=="enemy" and side=="player")) and age<0.18
    local fading=state.mode=="aftermath" and ((state.result=="victory" and side=="enemy")
        or (state.result=="defeat" and side=="player"))
    local opacity=fading and 1-state.terminal.time/state.spec.terminalSeconds or 1
    for _,group in ipairs(animated.groups) do
        for _,v in ipairs(group.vertices) do
            v[12]=v[12]*opacity
            if hit then v[9],v[10],v[11]=1,impact.side=="enemy" and 0.2 or 1,impact.side=="enemy" and 0.15 or 1 end
        end
    end
    return animated
end
function feedback.drawLabel(state,project,scale)
    if not state or not state.impact then return end
    local hit=state.impact
    local age=state.elapsed-hit.time
    if age<0 or age>0.85 then return end
    local point=project(hit.x,hit.y,hit.z+1.3)
    if point.depth<=0 then return end
    local ui=require("presentation.ui")
    love.graphics.push("all")
    love.graphics.scale(scale,scale)
    ui.drawString(hit.miss and "MISS" or tostring(hit.amount),point.x/scale-24,
        point.y/scale-28*age+24*age*age,{1,0.95,0.7,math.min(1,(0.85-age)*5)},"center",48)
    love.graphics.pop()
end
return feedback
