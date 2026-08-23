-- A deliberately small traversal capability for authored side-view proof maps.
-- It owns continuous horizontal position, bounds and doorway proximity; it is
-- not a general physics or Map replacement.
local bounded_lane = {}

-- How far from a bound a doorway may sit and still be that edge's exit
-- when no doorway sits on the bound itself. Wide enough for a door
-- painted just inside a room's wall, short enough that it cannot reach
-- a door belonging to the middle of a street.
local EDGE_REACH = 2.5

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
    state.z = state.groundZ
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

function bounded_lane.move(session, direction)
    local state = session and session.townTraversal
    if not state or state.provider ~= "bounded_lane" then return false end
    direction = direction < 0 and -1 or 1
    local nextY = state.y + direction * state.speed
    if nextY < state.minY or nextY > state.maxY or inBlockedRange(state, nextY) then
        state.moving = false
        return false
    end
    state.y = nextY
    state.facing = direction
    state.moving = true
    updateProjectionWindow(session, state)
    return true
end

function bounded_lane.update(session, dt)
    local state = session and session.townTraversal
    if state then
        updateProjectionWindow(session, state)
        if dt == nil then
            state.cameraOffsetX = state.cameraTargetOffsetX
            state.visualX, state.visualY = state.x, state.y
            state.walking = false
            state.walkFrameIndex = 0
        elseif dt < 0 then
            error("bounded lane update dt must be non-negative", 0)
        else
            local alpha = 1 - math.exp(-state.tracking.interpolationSpeed * dt)
            state.cameraOffsetX = state.cameraOffsetX
                + (state.cameraTargetOffsetX - state.cameraOffsetX) * alpha
            local movementAlpha = 1 - math.exp(-state.tracking.movementInterpolationSpeed * dt)
            state.visualX = state.visualX
                + (state.x - state.visualX) * movementAlpha
            state.visualY = state.visualY
                + (state.y - state.visualY) * movementAlpha
            local remaining = math.abs(state.x - state.visualX)
                + math.abs(state.y - state.visualY)
            state.walking = state.moving or remaining > 0.001
            if state.walking then
                state.walkAnimationTime = state.walkAnimationTime + dt
                state.walkFrameIndex = math.floor(
                    state.walkAnimationTime * state.tracking.animationFps) % 6
            else
                state.walkAnimationTime = 0
                state.walkFrameIndex = 0
            end
        end
        state.camera.projectionWindowOffsetX = state.cameraOffsetX
        session.worldCameraProjectionWindowOffsetX = state.cameraOffsetX
        state.moving = false
    end
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
