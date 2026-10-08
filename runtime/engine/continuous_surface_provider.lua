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

local function eventPosition(event)
    if type(event) ~= "table" then return nil end
    local position = event.worldPosition or event.position
    if type(position) ~= "table" then return nil end
    local x = tonumber(position[1] or position.x)
    local y = tonumber(position[2] or position.y)
    local z = tonumber(position[3] or position.z or 0)
    if not x or not y or not z then return nil end
    if x ~= x or y ~= y or z ~= z then return nil end
    if x == math.huge or x == -math.huge
            or y == math.huge or y == -math.huge
            or z == math.huge or z == -math.huge then return nil end
    return x, y, z
end

-- Spatial authority and gameplay tuning deliberately meet only here. An
-- environment package may own the walk-region/obstacle geometry because those
-- shapes describe the physical authored room. The Map still owns locomotion
-- tuning (speed/maxStep) because that is gameplay policy. Older Projects that
-- have no package walkSurface retain their Map-authored surface unchanged.
local function semanticSpec(spec, environment)
    local tuning = spec.surface
    local authored = environment and environment.walkSurface
    if not authored then
        if type(tuning) ~= "table" then
            error("continuous surface traversal requires either environment walkSurface or Map surface", 0)
        end
        return tuning
    end

    if tuning ~= nil and type(tuning) ~= "table" then
        error("continuous surface traversal surface tuning must be an object", 0)
    end
    tuning = tuning or {}
    if tuning.regions ~= nil or tuning.obstacles ~= nil or tuning.groundZ ~= nil then
        error("continuous surface Map duplicates package-owned walk geometry; "
            .. "remove surface.regions/obstacles/groundZ", 0)
    end
    return {
        speed = tuning.speed,
        maxStep = tuning.maxStep,
        groundZ = authored.groundZ,
        regions = authored.regions,
        obstacles = authored.obstacles,
    }
end

local function initialize(session, arrival)
    local spec, map = specFor(session)
    if not spec then
        if session then session.continuousTraversal = nil end
        return nil
    end

    if type(spec.environmentPackage) ~= "string" or spec.environmentPackage == "" then
        error("continuous surface traversal requires environmentPackage", 0)
    end

    local environment = environment_package.load(spec.environmentPackage)
    local surface = semanticSpec(spec, environment)
    local spawnId = spec.spawnAnchor or "spawn_player"
    -- LOAD_MAP already owns an optional arrival string. As with bounded_lane,
    -- an arrival that names an anchor in the destination environment selects
    -- that anchor; unknown/empty arrivals retain the Map's normal spawn.
    if type(arrival) == "string" and arrival ~= ""
            and environment.anchors and environment.anchors[arrival] then
        spawnId = arrival
    end
    local spawn = anchorPosition(environment, spawnId)
    if not spawn then
        error("continuous surface spawn anchor missing: " .. tostring(spawnId), 0)
    end

    local state = semantic.new(surface, spawn)
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

function provider.isActive(session)
    local state = session and session.continuousTraversal
    local spec, map = specFor(session)
    return state ~= nil and spec ~= nil and state.mapId == map.id
end

-- Lazily establish the provider after ordinary Map loading. Keeping this in a
-- capability host rather than exploration.loadMap is intentional for the first
-- gauntlet lane: it proves that a Map can compose a traversal provider without
-- teaching the grid loader another topology. Map entry itself is now offered by
-- traversal_host so an authored LOAD_MAP arrival can initialize the same state.
function provider.ensure(session)
    local spec, map = specFor(session)
    if not spec then
        if session then session.continuousTraversal = nil end
        return nil
    end
    local existing = session.continuousTraversal
    if existing and existing.mapId == map.id then return existing end
    return initialize(session, nil)
end

-- Map-lifecycle entry point. Unlike ensure this deliberately replaces any
-- prior provider state because exploration.loadMap has just established a new
-- current Map and its authored arrival is authoritative for this entry.
function provider.enterMap(session, arrival)
    return initialize(session, arrival)
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
-- L/R are also consumed here: they are grid strafes in the legacy host and
-- must not mutate a hidden grid position underneath a continuous Map.
function provider.buttonpressed(session, button)
    if not provider.ensure(session) then return false end
    return button == "UP" or button == "DOWN" or button == "LEFT" or button == "RIGHT"
        or button == "L" or button == "R"
end

function provider.actorRoot(session)
    local state = provider.ensure(session)
    if not state then return nil end
    return state.x, state.y, state.z
end

-- Resolve the nearest ordinary Map Event authored in world space. Event
-- identity/program ownership stays with the Map; traversal supplies only the
-- proximity fact. The optional predicate belongs to the host, so page/trigger
-- semantics can filter candidates without being duplicated in traversal.
function provider.nearestEvent(session, radius, predicate)
    local state = provider.ensure(session)
    if not state then return nil end
    radius = tonumber(radius) or state.interactionRadius
    if radius <= 0 then return nil end
    local best, bestDistance2 = nil, radius * radius
    for _, event in ipairs((session.currentMapData and session.currentMapData.events) or {}) do
        if not predicate or predicate(event) then
            local x, y = eventPosition(event)
            if x and y then
                local eventRadius = tonumber(event.interactionRadius) or radius
                local dx, dy = state.x - x, state.y - y
                local distance2 = dx * dx + dy * dy
                local threshold2 = eventRadius * eventRadius
                if distance2 <= threshold2
                        and (best == nil or distance2 < bestDistance2) then
                    best, bestDistance2 = event, distance2
                end
            end
        end
    end
    return best, bestDistance2
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
    value.spawnAnchor = state.spawnAnchor
    return value
end

function provider.restore(session, saved)
    local spec, map = specFor(session)
    if not spec or type(saved) ~= "table" or saved.provider ~= "continuous_surface" then
        return nil
    end
    local environment = environment_package.load(spec.environmentPackage)
    local surface = semanticSpec(spec, environment)
    local state = semantic.restore(surface, saved)
    state.mapId = map.id
    state.environment = environment
    state.spawnAnchor = saved.spawnAnchor or spec.spawnAnchor or "spawn_player"
    state.interactionRadius = finite(spec.interactionRadius or 1.15, "interactionRadius")
    if state.interactionRadius <= 0 then
        error("continuous surface provider interactionRadius must be > 0", 0)
    end
    state.walkFrameIndex = math.floor((state.walkDistance or 0) / 0.42) % 6
    state.facing = (state.facingX or 0) < 0 and -1 or 1
    session.continuousTraversal = state
    return state
end

return provider
