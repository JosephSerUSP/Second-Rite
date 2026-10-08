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
function actor.validateSpec(spec)
    assert(type(spec)=="table", "actorAppearance must be an object")
    for key in pairs(spec) do
        assert(key=="character" or key=="height" or key=="stride", "unknown actorAppearance field: "..key)
    end
    for _,key in ipairs({"height","stride"}) do
        local n=spec[key]
        assert(type(n)=="number" and n==n and n>0 and n<math.huge,"actorAppearance."..key.." must be positive finite")
    end
    local prepared=actor.load(spec.character)
    assert(prepared.asset.clips.idle and prepared.asset.clips.walk,"actorAppearance requires idle and walk clips")
    return prepared
end
function actor.resolve(session,view,clock)
    local spec=actor.spec(session)
    if not spec then return nil end
    assert(view and view.actor,"animated actor requires a resolved traversal pose")
    local prepared=actor.validateSpec(spec)
    local pose=view.actor
    local clip=pose.moving and "walk" or "idle"
    local duration=prepared.asset.clips[clip].duration
    local time=pose.moving and (pose.walkDistance or 0)/spec.stride*duration or clock
    if pose.animationPhase then time=pose.animationPhase*duration end
    local groups=animation.sample(prepared,clip,time,pose,spec.height)
    for _,g in ipairs(groups) do g.texturePath=prepared.base.."/"..g.texture end
    return {groups=groups,clip=clip,time=time%duration,character=spec.character,height=spec.height}
end
function actor.clearCache() cache={} end
return actor
