-- A deliberately small traversal capability for authored side-view proof maps.
-- It owns continuous horizontal position, bounds and doorway proximity; it is
-- not a general physics or Map replacement.
local bounded_lane = {}

-- How far from a bound a doorway may sit and still be that edge's exit
-- when no doorway sits on the bound itself. Wide enough for a door
-- painted just inside a room's wall, short enough that it cannot reach
-- a door belonging to the middle of a street.
local EDGE_REACH = 2.5

-- Door radii are authored in decimal world units, often exactly one spawn
-- offset away. Binary floating point can put 0.9 a hair above 0.9, which made
-- the intended Up interaction miss at the shop entrance.
local PROXIMITY_EPSILON = 1e-6

-- How far one discrete `move` nudge carries, expressed as seconds of walking
-- so it stays in step with continuous movement if the speed changes.
local NUDGE_SECONDS = 0.22

-- World units walked per frame of the six-frame cycle. Animation is driven by
-- distance rather than by a clock, which is what stops the feet sliding: the
-- character cannot take a step without covering ground.
local STRIDE_PER_FRAME = 0.42

local function copy(value)
    if type(value) ~= "table" then return value end
    local result = {}
    for key, child in pairs(value) do result[key] = copy(child) end
    return result
end

local function number(value, label)
    value = tonumber(value)
    if not value or value ~= value or value == math.huge or value == -math.huge then
        error("bounded lane " .. label .. " must be finite", 0)
    end
    return value
end

-- Authored floor height along the lane.
--
-- The lane stays strictly one-dimensional: this changes where the actor's
-- feet are DRAWN, never what they can reach. A flight of steps in a pub is
-- two floor heights and a short ramp between them, and the player crosses it
-- by walking, exactly as they cross flat ground. Control points are
-- {y, z} pairs in world units, piecewise-linear between them, so an author
-- picks the ramp length and gets a step, a slope or a hill from one shape.
--
-- Authored in WORLD units rather than plate pixels on purpose: a real 3D
-- scene substituted for the plate has a floor at a world height, and this
-- profile is then a description of it rather than a picture-space fudge.
local function groundAt(state, y)
    local profile = state.groundProfile
    if not profile or #profile == 0 then return state.groundZ end
    if y <= profile[1].y then return profile[1].z end
    for index = 2, #profile do
        local previous, current = profile[index - 1], profile[index]
        if y <= current.y then
            local span = current.y - previous.y
            if span <= 0 then return current.z end
            local t = (y - previous.y) / span
            return previous.z + (current.z - previous.z) * t
        end
    end
    return profile[#profile].z
end

function bounded_lane.groundAt(session, y)
    local state = session and session.townTraversal
    if not state then return nil end
    return groundAt(state, tonumber(y) or state.y)
end

local function inBlockedRange(state, y)
    for _, range in ipairs(state.blockedRanges or {}) do
        local lo = number(range.minY, "blocked minY")
        local hi = number(range.maxY, "blocked maxY")
        if y >= lo and y <= hi then return true end
    end
    return false
end

local function clamp(value, minimum, maximum)
    return math.max(minimum, math.min(maximum, value))
end

local function pixelsPerWorldUnit(camera, distance)
    local projectionFrame = camera.projectionFrame or {}
    local scale = camera.projectionScale or {}
    local fovHalf = math.tan(math.rad(number(camera.fovDegrees, "camera fovDegrees")) * 0.5)
    local baseWidth = number(projectionFrame.baseViewportWidth or 256,
        "camera baseViewportWidth")
    return baseWidth * 0.5 * number(scale.x or 1, "camera projectionScale.x")
        / (fovHalf * distance)
end

local function updateProjectionWindow(session, state)
    local tracking = state.tracking
    local target = -(state.y - tracking.center) * tracking.pixelsPerWorld
    target = clamp(target, tracking.minOffsetX, tracking.maxOffsetX)
    state.cameraTargetOffsetX = target
    if state.cameraOffsetX == nil then state.cameraOffsetX = target end
    state.camera.projectionWindowOffsetX = state.cameraOffsetX
    session.worldCameraProjectionWindowOffsetX = state.cameraOffsetX
    return target
end

-- `arrival` is the string the transfer command already carries. A screen with
-- more than one door cannot return the player to the door they used if every
-- entry lands on the map's single spawn anchor, so an arrival that names an
-- anchor in the destination package selects it. The door event is therefore
-- also the spawn point, and no new authored object type appears.
function bounded_lane.initialize(session, mapData, environment, arrival)
    local spec = mapData.traversal
    if type(spec) ~= "table" or spec.provider ~= "bounded_lane" then
        return nil
    end
    local lane = spec.lane or {}
    local camera = copy(spec.camera or {})
    local trackingSpec = camera.tracking or {}
    local spawnAnchor = spec.spawnAnchor or "spawn_player"
    local anchors = environment and environment.anchors or {}
    local anchor = nil
    if type(arrival) == "string" and arrival ~= "" and anchors[arrival] then
        anchor = anchors[arrival]
        spawnAnchor = arrival
    else
        anchor = anchors[spawnAnchor]
    end
    if not anchor then error("bounded lane spawn anchor missing: " .. tostring(spawnAnchor), 0) end
    local position = anchor.position
    if trackingSpec.axis and trackingSpec.axis ~= "y" then
        error("bounded lane currently requires camera-right horizontal axis 'y'", 0)
    end
    local distance = number(camera.distance, "camera distance")
    local state = {
        provider = "bounded_lane",
        environment = environment,
        camera = camera,
        minY = number(lane.minY, "lane minY"),
        maxY = number(lane.maxY, "lane maxY"),
        depthX = number(lane.depthX, "lane depthX"),
        groundZ = number(lane.groundZ or position[3], "lane groundZ"),
        speed = number(lane.speed or 0.8, "lane speed"),
        blockedRanges = spec.blockedRanges or {},
        groundProfile = (function()
            local authored = lane.groundProfile
            if type(authored) ~= "table" or #authored == 0 then return nil end
            local points = {}
            for index, point in ipairs(authored) do
                points[index] = {
                    y = number(point.y or point[1], "ground profile y"),
                    z = number(point.z or point[2], "ground profile z"),
                }
                if index > 1 and points[index].y < points[index - 1].y then
                    error("bounded lane ground profile must run west to east", 0)
                end
            end
            return points
        end)(),
        doorways = spec.doorways or {},
        x = number(position[1], "spawn x"),
        y = number(position[2], "spawn y"),
        z = number(position[3], "spawn z"),
        facing = 1,
        moving = false,
        tracking = {
            center = number(trackingSpec.center or camera.target.y, "tracking center"),
            minOffsetX = number(trackingSpec.minOffsetX or -96, "tracking minOffsetX"),
            maxOffsetX = number(trackingSpec.maxOffsetX or 96, "tracking maxOffsetX"),
            pixelsPerWorld = number(trackingSpec.pixelsPerWorld
                or pixelsPerWorldUnit(camera, distance), "tracking pixelsPerWorld"),
            interpolationSpeed = number(trackingSpec.interpolationSpeed or 12,
                "tracking interpolationSpeed"),
            movementInterpolationSpeed = number(
                trackingSpec.movementInterpolationSpeed or 14,
                "tracking movementInterpolationSpeed"),
            animationFps = number(trackingSpec.animationFps or 8,
                "tracking animationFps"),
        },
    }
    state.x = state.depthX
    state.y = clamp(state.y, state.minY, state.maxY)
    state.z = groundAt(state, state.y)
    state.visualX, state.visualY = state.x, state.y
    state.walkAnimationTime = 0
    state.walkFrameIndex = 0
    state.walking = false
    session.townTraversal = state
    updateProjectionWindow(session, state)
    -- Existing grid consumers still receive a harmless one-cell position; the
    -- provider is the authority for movement and actor roots on this map.
    session.playerX, session.playerY, session.playerDir = 1, 1, "E"
    return state
end

function bounded_lane.isActive(session)
    return session and session.townTraversal and session.townTraversal.provider == "bounded_lane"
end

-- The one place lane position changes. Continuous walking and the discrete
-- nudge used by harnesses both go through it, so bounds and blocked ranges
-- cannot drift apart between them.
local function advance(session, state, direction, distance)
    state.facing = direction
    local nextY = state.y + direction * distance
    local limited = clamp(nextY, state.minY, state.maxY)
    if inBlockedRange(state, limited) then
        state.moving = false
        state.atBound = direction
        return false
    end
    -- Reaching the end of the lane is not a failure to move: the actor walks
    -- up to the bound and stops there, and `atBound` records that it is
    -- leaning on that edge so a doorway there can answer.
    state.atBound = (limited ~= nextY) and direction or 0
    if limited == state.y then
        state.moving = false
        return false
    end
    state.walkDistance = (state.walkDistance or 0) + math.abs(limited - state.y)
    state.y = limited
    state.z = groundAt(state, state.y)
    state.moving = true
    updateProjectionWindow(session, state)
    return true
end

-- A single discrete nudge, for tests and the walkthrough harness. Play uses
-- `update` with a held direction; this exists so a harness can step the world
-- deterministically without pretending to hold a key for a while.
function bounded_lane.move(session, direction)
    local state = session and session.townTraversal
    if not state or state.provider ~= "bounded_lane" then return false end
    return advance(session, state, direction < 0 and -1 or 1, state.speed * NUDGE_SECONDS)
end

-- `held` is -1, 0 or 1: the direction the player is currently holding. Walking
-- is continuous and frame-rate independent, and the drawn position is the real
-- position - there is no separate visual that lags behind it, because a sprite
-- that trails the position it is being tested against reads as broken.
function bounded_lane.update(session, dt, held)
    local state = session and session.townTraversal
    if not state then return end
    held = tonumber(held) or 0
    if dt == nil then
        state.walking = false
        state.walkFrameIndex = 0
        state.atBound = 0
    elseif dt < 0 then
        error("bounded lane update dt must be non-negative", 0)
    else
        if held ~= 0 then
            advance(session, state, held < 0 and -1 or 1, state.speed * dt)
        else
            state.moving = false
            state.atBound = 0
        end
        state.walking = state.moving
        if state.walking then
            state.walkFrameIndex =
                math.floor((state.walkDistance or 0) / STRIDE_PER_FRAME) % 6
        else
            state.walkFrameIndex = 0
        end
    end
    -- Nothing chases anything: the camera reads the actor's real position, so
    -- the projection window is exact rather than settling towards exact.
    updateProjectionWindow(session, state)
    state.visualX, state.visualY = state.x, state.y
    state.cameraOffsetX = state.cameraTargetOffsetX
    state.camera.projectionWindowOffsetX = state.cameraOffsetX
    session.worldCameraProjectionWindowOffsetX = state.cameraOffsetX
end

function bounded_lane.actorRoot(session)
    local state = session and session.townTraversal
    if not state then return nil end
    return state.visualX or state.x, state.visualY or state.y, state.z
end

function bounded_lane.nearDoorway(session)
    local state = session and session.townTraversal
    if not state then return nil end
    local nearest, distance
    for _, doorway in ipairs(state.doorways) do
        local anchor = state.environment and state.environment.anchors[doorway.anchor]
        if anchor then
            local dx = state.x - anchor.position[1]
            local dy = state.y - anchor.position[2]
            local d = math.sqrt(dx * dx + dy * dy)
            if d <= number(doorway.radius or 0.65, "doorway radius")
                    + PROXIMITY_EPSILON
                    and (not distance or d < distance) then
                nearest, distance = doorway, d
            end
        end
    end
    return nearest, distance
end

-- The doorway that leaving by this edge should use.
--
-- `nearDoorway` answers "what is closest to the player", which is right for a
-- deliberate press but wrong at a bound: a shop door authored a little way in
-- from the west end is nearer than the west exit itself, so walking west would
-- open the shop instead of leaving. This asks the other question - which
-- doorway belongs to *this edge* - and lets interior doors be reached by the
-- door verb instead.
function bounded_lane.edgeDoorway(session, direction)
    local state = session and session.townTraversal
    if not state then return nil end
    local bound = direction < 0 and state.minY or state.maxY
    local best, bestDistance
    local fallback, fallbackDistance
    for _, doorway in ipairs(state.doorways) do
        local anchor = state.environment and state.environment.anchors[doorway.anchor]
        if anchor then
            local d = math.abs(anchor.position[2] - bound)
            if d <= number(doorway.radius or 0.65, "doorway radius")
                    and (not bestDistance or d < bestDistance) then
                best, bestDistance = doorway, d
            end
            if not fallbackDistance or d < fallbackDistance then
                fallback, fallbackDistance = doorway, d
            end
        end
    end
    -- A room's door is painted where the artist put it, which is usually a
    -- little way in from the wall rather than exactly at the bound. If nothing
    -- sits on the bound itself, the nearest door to it still counts as this
    -- edge's way out - otherwise walking into the wall does nothing and the
    -- room reads as a dead end.
    if not best and fallbackDistance and fallbackDistance <= EDGE_REACH then
        best = fallback
    end
    return best
end

-- Is this doorway the end of the street rather than a door?
--
-- An edge exit is authored exactly ON a bound, because that is what makes
-- walking off the screen work. A real door is painted somewhere along the
-- wall, so it is never exactly on one. The distinction matters to the HUD:
-- continuing along a street is not an interaction and should not be announced
-- like one. The test is exact rather than radius-based on purpose - the
-- weaponsmith's door sits 0.86 from Market Row's east end, well inside a
-- 0.9 radius, and is emphatically still a door.
function bounded_lane.isEdgeDoorway(session, doorway)
    local state = session and session.townTraversal
    if not state or not doorway then return false end
    local anchor = state.environment and state.environment.anchors[doorway.anchor]
    if not anchor then return false end
    local y = tonumber(anchor.position[2]) or 0
    return math.abs(y - state.minY) < 0.01 or math.abs(y - state.maxY) < 0.01
end

-- Resolve a doorway to the ordinary Map event that carries its commands.
-- Gameplay meaning stays in Event data; the doorway supplies only proximity.
function bounded_lane.eventFor(session, doorway)
    if not doorway then return nil end
    for _, event in ipairs((session.currentMapData and session.currentMapData.events) or {}) do
        if event.instanceId == doorway.eventInstanceId or event.id == doorway.eventId then
            return event
        end
    end
    return nil
end

function bounded_lane.interact(session)
    return bounded_lane.eventFor(session, bounded_lane.nearDoorway(session))
end

return bounded_lane
