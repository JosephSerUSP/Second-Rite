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
return owner
