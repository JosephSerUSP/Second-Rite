-- Map/session adapter for the generic continuous_surface locomotion semantic.
--
-- `continuous_surface.lua` is deliberately host-neutral. This module is the
-- narrow Thestra Map capability that binds it to Project data, environment
-- packages and live GameSession state. It owns no camera or rendering policy.
local semantic = require("engine.continuous_surface")
local environment_package = require("engine.environment_package")

local provider = {}

local function finite(value, label)
    value = tonumber(value)
    if not value or value ~= value or value == math.huge or value == -math.huge then
        error("continuous surface provider " .. label .. " must be finite", 0)
    end
    return value
end

local function specFor(session)
    local map = session and session.currentMapData
    local spec = map and map.traversal
    if type(spec) ~= "table" or spec.provider ~= "continuous_surface" then return nil end
    return spec, map
end

local function anchorPosition(environment, id)
    local anchor = environment and environment.anchors and environment.anchors[id]
    if not anchor or type(anchor.position) ~= "table" then return nil end
    return {
        x = finite(anchor.position[1], "anchor '" .. id .. "' x"),
        y = finite(anchor.position[2], "anchor '" .. id .. "' y"),
        z = finite(anchor.position[3] or 0, "anchor '" .. id .. "' z"),
    }
end

function provider.isActive(session)
    local state = session and session.continuousTraversal
    local spec, map = specFor(session)
    return state ~= nil and spec ~= nil and state.mapId == map.id
end

-- Lazily establish the provider after ordinary Map loading. Keeping this in a
-- capability host rather than exploration.loadMap is intentional for the first
-- gauntlet lane: it proves that a Map can compose a traversal provider without
-- teaching the grid loader another topology. If the experiment survives, the
-- lifecycle seam can be promoted without changing authored Project data.
function provider.ensure(session)
    local spec, map = specFor(session)
    if not spec then
        if session then session.continuousTraversal = nil end
        return nil
    end
    local existing = session.continuousTraversal
    if existing and existing.mapId == map.id then return existing end

    if type(spec.environmentPackage) ~= "string" or spec.environmentPackage == "" then
        error("continuous surface traversal requires environmentPackage", 0)
    end
    if type(spec.surface) ~= "table" then
        error("continuous surface traversal requires a surface object", 0)
    end

    local environment = environment_package.load(spec.environmentPackage)
    local spawnId = spec.spawnAnchor or "spawn_player"
    local spawn = anchorPosition(environment, spawnId)
    if not spawn then
        error("continuous surface spawn anchor missing: " .. tostring(spawnId), 0)
    end

    local state = semantic.new(spec.surface, spawn)
    state.mapId = map.id
    state.environment = environment
    state.spawnAnchor = spawnId
    state.interactionRadius = finite(spec.interactionRadius or 1.15, "interactionRadius")
    if state.interactionRadius <= 0 then
        error("continuous surface provider interactionRadius must be > 0", 0)
    end
    state.walkFrameIndex = 0
    state.facing = 1
    session.continuousTraversal = state
    return state
end

function provider.update(session, dt, held)
    local state = provider.ensure(session)
    if not state then return false end
    held = held or {}
    local inputX = (held.right and 1 or 0) - (held.left and 1 or 0)
    local inputY = (held.down and 1 or 0) - (held.up and 1 or 0)
    local moved = semantic.update(state, dt, inputX, inputY)
    if inputX ~= 0 then state.facing = inputX < 0 and -1 or 1 end
    state.walkFrameIndex = math.floor((state.walkDistance or 0) / 0.42) % 6
    return moved > 0
end

-- Continuous movement is sampled from held logical buttons every frame. The
-- directional press edge therefore has no grid-step meaning and must stop at
-- the traversal membrane instead of falling through to main.lua's grid host.
function provider.buttonpressed(session, button)
    if not provider.ensure(session) then return false end
    return button == "UP" or button == "DOWN" or button == "LEFT" or button == "RIGHT"
end

function provider.actorRoot(session)
    local state = provider.ensure(session)
    if not state then return nil end
    return state.x, state.y, state.z
end

-- Presentation-only compatibility record for the existing world mesh path.
-- This is NOT installed into GameSession.townTraversal: continuous traversal
-- remains its own gameplay capability. The renderer may consume this ephemeral
-- view while the generic viewport is being taught a first-class traversal seam.
function provider.presentationLaneView(session)
    local state = provider.ensure(session)
    if not state then return nil end
    return {
        provider = "bounded_lane",
        environment = state.environment,
        x = state.x,
        y = state.y,
        z = state.z,
        visualX = state.x,
        visualY = state.y,
        groundZ = state.z,
        groundProfile = nil,
        baseLevel = "ground",
        level = "ground",
        levels = {
            ground = {
                minY = -100000,
                maxY = 100000,
                groundZ = state.z,
                groundProfile = nil,
                blockedRanges = {},
            },
        },
        minY = -100000,
        maxY = 100000,
        blockedRanges = {},
        moving = state.moving,
        walking = state.moving,
        walkFrameIndex = state.walkFrameIndex or 0,
        facing = state.facing or 1,
        doorways = {},
    }
end

function provider.serialize(session)
    local state = provider.ensure(session)
    if not state then return nil end
    local value = semantic.serialize(state)
    value.mapId = state.mapId
    return value
end

function provider.restore(session, saved)
    local spec, map = specFor(session)
    if not spec or type(saved) ~= "table" or saved.provider ~= "continuous_surface" then
        return nil
    end
    local environment = environment_package.load(spec.environmentPackage)
    local state = semantic.restore(spec.surface, saved)
    state.mapId = map.id
    state.environment = environment
    state.spawnAnchor = spec.spawnAnchor or "spawn_player"
    state.interactionRadius = finite(spec.interactionRadius or 1.15, "interactionRadius")
    state.walkFrameIndex = math.floor((state.walkDistance or 0) / 0.42) % 6
    state.facing = (state.facingX or 0) < 0 and -1 or 1
    session.continuousTraversal = state
    return state
end

return provider
