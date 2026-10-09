-- Presentation policy around the reusable deform-skin consumer. No mutable
-- animation state: walking phase comes from resolved travel, idle from the
-- presentation clock, and door pose is already decorated by traversal_view.
local animation = require("presentation.character_animation")
local json = require("engine.data.json")
local actor = {}
local cache = {}
function actor.load(path)
    if cache[path] then return cache[path] end
    assert(type(path)=="string" and path:match("^assets/") and not path:find("..",1,true),
        "character bundle must be a Project asset")
    local text=assert(love.filesystem.read(path),"character bundle missing: "..path)
    local prepared=animation.prepare(json.decode(text))
    prepared.base=path:match("^(.*)/[^/]+$")
    for _,p in ipairs(prepared.asset.primitives) do
        assert(p.texture:match("^[%w_-]+%.png$"),"character texture must be a bundle-local PNG")
        assert(love.filesystem.getInfo(prepared.base.."/"..p.texture),"character texture missing: "..p.texture)
        local image=love.image.newImageData(prepared.base.."/"..p.texture)
        image:release()
    end
    cache[path]=prepared
    return prepared
end
function actor.spec(session)
    local map=session and session.currentMapData
    return map and map.traversal and map.traversal.actorAppearance or nil
end
function actor.validateSpec(spec, eventAppearance)
    assert(type(spec)=="table", "actorAppearance must be an object")
    for key in pairs(spec) do
        assert(key=="character" or key=="height" or key=="stride", "unknown actorAppearance field: "..key)
    end
    for _,key in ipairs({"height","stride"}) do
        local n=spec[key]
        if key ~= "stride" or not eventAppearance or n ~= nil then
            assert(type(n)=="number" and n==n and n>0 and n<math.huge,"actorAppearance."..key.." must be positive finite")
        end
    end
    local prepared=actor.load(spec.character)
    assert(prepared.asset.clips.idle and prepared.asset.clips.walk,"actorAppearance requires idle and walk clips")
    return prepared
end
local function sample(spec,prepared,pose,clip,time,playback)
    local duration=assert(prepared.asset.clips[clip],"character is missing semantic clip: "..tostring(clip)).duration
    local groups=animation.sample(prepared,clip,time,pose,spec.height,playback)
    for _,g in ipairs(groups) do g.texturePath=prepared.base.."/"..g.texture end
    return {groups=groups,clip=clip,time=playback=="once" and math.min(time,duration) or time%duration,character=spec.character,height=spec.height,pose=pose}
end
-- Phase selection reads the runtime owner; these clips never complete actions.
local function combatSample(session,side,spec,prepared,pose)
    local state=session.arenaEncounter
    if not state then return end
    local impact=state.impact
    local age=impact and state.elapsed-impact.time or math.huge
    local recipient=impact and ((impact.side=="player" and side=="enemy") or (impact.side=="enemy" and side=="player"))
    if recipient and not impact.miss then
        local duration=assert(prepared.asset.clips.hit,"combat character requires hit clip").duration
        if age<duration then return sample(spec,prepared,pose,"hit",age,"once") end
    end
    local action
    if side=="player" then action=state.action else action=state.enemyAction end
    local phase=action and require("engine.action_timeline").phase(action)
    if phase then
        local clip=phase.id=="windup" and "anticipation" or phase.id
        local duration=assert(prepared.asset.clips[clip],"combat character requires "..clip).duration
        return sample(spec,prepared,pose,clip,action.time/phase.duration*duration,"once")
    end
end
function actor.resolve(session,view,clock)
    local spec=actor.spec(session)
    if not spec then return nil end
    assert(view and view.actor,"animated actor requires a resolved traversal pose")
    local prepared=actor.validateSpec(spec)
    local pose=view.actor
    local clip=pose.moving and "walk" or "idle"
    local duration=prepared.asset.clips[clip].duration
    clock=session.arenaEncounter and session.arenaEncounter.elapsed or clock
    local time=pose.moving and (pose.walkDistance or 0)/spec.stride*duration or clock
    if pose.animationPhase then time=pose.animationPhase*duration end
    return require("presentation.arena_feedback").decorate(session,"player",combatSample(session,"player",spec,prepared,pose) or sample(spec,prepared,pose,clip,time))
end
-- Event roots are authored world positions; semantic clip/facing remain owned
-- by the existing Event actor. Resolving a visual never allocates actor state.
function actor.resolveEvent(session,event,presentation,clock)
    if presentation.visual ~= "character" then return nil end
    local spec=presentation.actorAppearance
    local prepared=actor.validateSpec(spec,true)
    local state=require("engine.event_actor").snapshot(session,presentation.page)
    assert(not state.overrideKind or state.overrideKind == "pose",
        "compiled Event characters currently support locomotion and held poses; one-shot playback is not authored")
    local x,y,z=require("presentation.viewport_3d").eventWorldPosition(event)
    local root=require("engine.world_event_actor").snapshot(session,event)
    if root then x,y,z=root.x,root.y,root.z end
    clock=session.arenaEncounter and session.arenaEncounter.enemyClock or clock
    if session.currentMapData.traversal and session.currentMapData.traversal.provider == "bounded_lane" then
        z=require("engine.bounded_lane").eventGroundAt(session,event,y) or z
    end
    local directions={N={0,-1},E={1,0},S={0,1},W={-1,0}}
    local facing=assert(directions[state.facing],"unknown Event facing")
    local worldHeading=root and (root.walkDistance or 0)>0
    local pose={x=x,y=y,z=z,facingX=worldHeading and root.facingX or facing[1],facingY=worldHeading and root.facingY or facing[2]}
    local animated=sample(spec,prepared,pose,state.clip,state.overrideKind == "pose" and 0 or clock)
    if session.arenaEncounter and session.arenaEncounter.event.id==event.id then
        return require("presentation.arena_feedback").decorate(session,"enemy",combatSample(session,"enemy",spec,prepared,pose) or animated)
    end
    return animated
end
function actor.clearCache() cache={} end
return actor
