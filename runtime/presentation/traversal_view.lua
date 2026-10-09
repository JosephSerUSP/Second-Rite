-- Provider-neutral traversal presentation facts.
--
-- Gameplay traversal providers expose only the environment + raw actor pose they
-- own. This presentation-side resolver decorates those facts with transient
-- visual pose (door approach, animation state) and adapts the legacy bounded
-- lane until it joins the provider registry. Consumers should depend on this
-- record rather than on `session.townTraversal` unless they are implementing a
-- genuinely bounded-lane-only feature (for example layered town prerenders).
local traversal_host = require("engine.traversal_host")

local traversal_view = {}

local function copyActor(actor)
    if type(actor) ~= "table" then return nil end
    return {
        x = tonumber(actor.x) or 0,
        y = tonumber(actor.y) or 0,
        z = tonumber(actor.z) or 0,
        frame = tonumber(actor.frame) or 0,
        facing = tonumber(actor.facing) or 1,
        moving = actor.moving == true,
        facingX = actor.facingX,
        facingY = actor.facingY,
        walkDistance = actor.walkDistance,
    }
end

local function decorateActor(actor)
    actor = copyActor(actor)
    if not actor then return nil end
    local pose = require("presentation.door_transition").actorPose()
    if pose then
        actor.x = actor.x + (tonumber(pose.x) or 0)
        actor.y = actor.y + (tonumber(pose.y) or 0)
        if pose.frame ~= nil then actor.frame = tonumber(pose.frame) or actor.frame end
        actor.moving = true
        actor.animationPhase = actor.frame / 6
        local dx, dy = tonumber(pose.x) or 0, tonumber(pose.y) or 0
        if dx ~= 0 or dy ~= 0 then
            local length = math.sqrt(dx^2 + dy^2)
            actor.facingX, actor.facingY = dx / length, dy / length
        end
    end
    return actor
end

local function hosted(session)
    local raw = traversal_host.presentationView(session)
    if not raw then return nil end
    return {
        provider = raw.provider,
        environment = raw.environment,
        actor = decorateActor(raw.actor),
        camera = raw.camera,
        -- Package-backed traversal actors historically render against the
        -- authored/baked environment appearance rather than receiving the grid
        -- light sampler a second time. State that presentation policy directly.
        unlitActors = true,
    }
end

local function bounded(session)
    local state = session and session.townTraversal
    if not state then return nil end
    local x, y, z = require("engine.bounded_lane").actorRoot(session)
    local rawActor = {
        x = x,
        y = y,
        z = z,
        frame = state.walkFrameIndex or 0,
        facing = state.facing or 1,
        moving = state.moving == true or state.walking == true,
        facingX = 0,
        facingY = state.facing or 1,
        walkDistance = state.walkDistance or 0,
    }
    return {
        provider = "bounded_lane",
        environment = state.environment,
        actor = decorateActor(rawActor),
        camera = state.camera,
        unlitActors = true,
        -- Explicit escape hatch for the still-specialized layered-town path.
        -- Generic world consumers must not inspect this field.
        boundedLane = state,
    }
end

function traversal_view.resolve(session)
    return hosted(session) or bounded(session)
end

function traversal_view.environment(session)
    local view = traversal_view.resolve(session)
    return view and view.environment or nil
end

function traversal_view.actor(session)
    local view = traversal_view.resolve(session)
    return view and view.actor or nil
end

return traversal_view
