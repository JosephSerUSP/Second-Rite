-- A deliberately small traversal capability for authored side-view proof maps.
-- It owns continuous horizontal position, bounds and doorway proximity; it is
-- not a general physics or Map replacement.
local bounded_lane = {}

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
    local offset = -(state.y - tracking.center) * tracking.pixelsPerWorld
    offset = clamp(offset, tracking.minOffsetX, tracking.maxOffsetX)
    state.camera.projectionWindowOffsetX = offset
    session.worldCameraProjectionWindowOffsetX = offset
    return offset
end

function bounded_lane.initialize(session, mapData, environment)
    local spec = mapData.traversal
    if type(spec) ~= "table" or spec.provider ~= "bounded_lane" then
        return nil
    end
    local lane = spec.lane or {}
    local camera = copy(spec.camera or {})
    local trackingSpec = camera.tracking or {}
    local spawnAnchor = spec.spawnAnchor or "spawn_player"
    local anchor = environment and environment.anchors and environment.anchors[spawnAnchor]
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
        },
    }
    state.x = state.depthX
    state.y = clamp(state.y, state.minY, state.maxY)
    state.z = state.groundZ
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

function bounded_lane.update(session)
    local state = session and session.townTraversal
    if state then
        state.moving = false
        updateProjectionWindow(session, state)
    end
end

function bounded_lane.actorRoot(session)
    local state = session and session.townTraversal
    if not state then return nil end
    return state.x, state.y, state.z
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

function bounded_lane.interact(session)
    local doorway = bounded_lane.nearDoorway(session)
    if not doorway then return nil end
    for _, event in ipairs((session.currentMapData and session.currentMapData.events) or {}) do
        if event.instanceId == doorway.eventInstanceId or event.id == doorway.eventId then
            return event
        end
    end
    return nil
end

return bounded_lane
