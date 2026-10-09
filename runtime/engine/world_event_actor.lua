local provider = require("engine.continuous_surface_provider")
local semantic = require("engine.continuous_surface")
local owner = {}
local function key(session, event)
    return tostring(session.currentMapIndex)..":"..tostring(event.id)
end
function owner.snapshot(session, event)
    return session.worldEventActors and session.worldEventActors[key(session,event)] or nil
end
function owner.create(session, event)
    assert(not owner.snapshot(session,event), "world Event actor already exists")
    local state = provider.createActor(session,event)
    session.worldEventActors = session.worldEventActors or {}
    session.worldEventActors[key(session,event)] = state
    return state
end
function owner.move(session,event,dt,dx,dy)
    local state = assert(owner.snapshot(session,event), "world Event actor missing")
    semantic.update(state,dt,dx,dy)
    require("engine.event_actor").setLocomotion(session,event,state.moving and "moving" or "idle")
    return state
end
function owner.remove(session,event)
    if session.worldEventActors then session.worldEventActors[key(session,event)]=nil end
    require("engine.event_actor").setLocomotion(session,event,"idle")
end
function owner.moveToward(session,event,dt,x,y,speed)
    local root=assert(owner.snapshot(session,event),"world Event actor missing")
    assert(speed>0 and speed<=root._compiled.speed,"world actor speed exceeds movement contract")
    local dx,dy=x-root.x,y-root.y
    local distance=math.sqrt(dx*dx+dy*dy)
    if distance==0 then return owner.move(session,event,dt,0,0) end
    local magnitude=math.min(speed,distance/math.max(dt,1e-12))/root._compiled.speed
    return owner.move(session,event,dt,dx/distance*magnitude,dy/distance*magnitude)
end
return owner
