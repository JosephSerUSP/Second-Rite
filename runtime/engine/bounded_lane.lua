-- A deliberately small traversal capability for authored side-view proof maps.
-- It owns continuous horizontal position, bounds and doorway proximity; it is
-- not a general physics or Map replacement.
--
-- LEVELS AND LINKS. A lane is one line, but a building has storeys. A map may
-- declare extra `levels` (each a lane of its own: bounds, floor height, optional
-- ground profile) beside the base lane, and `links` between them (a stair). The
-- player is on exactly one level at a time, walks it with LEFT/RIGHT, and takes a
-- link by pressing UP/DOWN at a doorway that names it: the actor then climbs the
-- link's path on its own and arrives on the other level. Nothing here is a
-- second movement system; every level is the same lane, switched.
local bounded_lane = {}
local world_view = require("engine.generated.world-view")

-- How far from a bound a doorway may sit and still be that edge's exit
-- when no doorway sits on the bound itself. Wide enough for a door
-- painted just inside a room's wall, short enough that it cannot reach
-- a door belonging to the middle of a street.
local EDGE_REACH = 2.5

-- Door radii are authored in decimal world units, often exactly one spawn
-- offset away. Binary floating point can put 0.9 a hair above 0.9, which made
-- the intended Up interaction miss at the shop entrance.
local PROXIMITY_EPSILON = 1e-6

-- The name of the lane every map has. Extra levels are named by the author.
local DEFAULT_LEVEL = "ground"

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
    return world_view.groundHeight(state.groundProfile, state.groundZ, y)
end

-- Floor height at lane position `y`, on the current level or on a named one.
function bounded_lane.groundAt(session, y, level)
    local state = session and session.townTraversal
    if not state then return nil end
    if level ~= nil and level ~= state.level then
        local other = state.levels and state.levels[level]
        if not other then return nil end
        return world_view.groundHeight(other.groundProfile, other.groundZ, tonumber(y) or state.y)
    end
    return groundAt(state, tonumber(y) or state.y)
end

-- The level an Event or doorway belongs to: the one it names, else the base lane.
local function levelOf(state, thing)
    return (type(thing) == "table" and thing.level) or state.baseLevel
end

-- Is this Event on the level the actor is walking? A shop door on the upper floor
-- is not in reach of someone passing beneath it, whatever their lane Y.
function bounded_lane.onLevel(session, event)
    local state = session and session.townTraversal
    if not state then return false end
    return levelOf(state, event) == state.level
end

-- Where an Event's models stand: on its own level's floor, not the actor's.
function bounded_lane.eventGroundAt(session, event, y)
    local state = session and session.townTraversal
    if not state then return nil end
    return bounded_lane.groundAt(session, y, levelOf(state, event))
end

-- Does the closed span [from, to] touch a blocked range?
--
-- The SPAN, not the destination. Testing only where a step lands lets a step
-- longer than a blocked range pass straight through it: at speed 3.4 a 0.5s
-- frame hitch covers 1.7 world units, so any barrier narrower than that is
-- porous exactly when the machine is struggling. An author asked for a wall,
-- and a wall that only stops you at 60fps is not one.
local function inBlockedRange(state, from, to)
    if to == nil then to = from end
    local lo, hi = from, to
    if lo > hi then lo, hi = hi, lo end
    for _, range in ipairs(state.blockedRanges or {}) do
        local rangeLo = number(range.minY, "blocked minY")
        local rangeHi = number(range.maxY, "blocked maxY")
        -- Overlap rather than containment: either endpoint may sit outside
        -- the range while the step crosses it entirely.
        if hi >= rangeLo and lo <= rangeHi then return true end
    end
    return false
end

local function clamp(value, minimum, maximum)
    return math.max(minimum, math.min(maximum, value))
end

local function parseGroundProfile(authored)
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
end

-- Everything that makes one level a lane. The state keeps the CURRENT level's
-- values in its own fields so movement, blocking and floor height stay the single
-- code path they always were.
local function buildLevel(def, label, fallbackBlocked)
    local level = {
        minY = number(def.minY, label .. " minY"),
        maxY = number(def.maxY, label .. " maxY"),
        groundZ = number(def.groundZ or 0, label .. " groundZ"),
        groundProfile = parseGroundProfile(def.groundProfile),
        blockedRanges = def.blockedRanges or fallbackBlocked or {},
    }
    if level.minY >= level.maxY then error("bounded lane " .. label .. " must have minY < maxY", 0) end
    return level
end

local function levelGround(level, y)
    return world_view.groundHeight(level.groundProfile, level.groundZ, y)
end

local function applyLevel(state, id)
    local level = state.levels[id]
    if not level then error("bounded lane has no level '" .. tostring(id) .. "'", 0) end
    state.level = id
    state.minY, state.maxY = level.minY, level.maxY
    state.groundZ = level.groundZ
    state.groundProfile = level.groundProfile
    state.blockedRanges = level.blockedRanges
end

-- Which level an anchor stands on, from where it is rather than from a second
-- authored field: the level whose floor at the anchor's Y is nearest the
-- anchor's height. The base lane wins a tie.
local function levelAtAnchor(state, position)
    local y, z = tonumber(position[2]) or 0, tonumber(position[3])
    local best, bestGap = state.baseLevel, nil
    if z == nil then return best end
    local ids = { state.baseLevel }
    for id in pairs(state.levels) do
        if id ~= state.baseLevel then ids[#ids + 1] = id end
    end
    table.sort(ids, function(a, b)
        if a == state.baseLevel then return b ~= state.baseLevel end
        if b == state.baseLevel then return false end
        return a < b
    end)
    for _, id in ipairs(ids) do
        local level = state.levels[id]
        if y >= level.minY - 0.01 and y <= level.maxY + 0.01 then
            local gap = math.abs((levelGround(level, y) or 0) - z)
            if bestGap == nil or gap < bestGap - 1e-6 then best, bestGap = id, gap end
        end
    end
    return best
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

-- Vertical follow. A map's height is not limited: where the author declares
-- `camera.tracking.vertical`, the window slides up and down so the actor keeps
-- the screen height they have on the reference floor, as far as the authored
-- room goes (`minOffsetY`/`maxOffsetY` are the bounds of the geometry that
-- exists). The slide is whatever it takes to cancel the actor's rise in the
-- real camera, measured with the real projection, so it is exact at any camera.
local function projectZ(camera, state, z)
    return world_view.projectPerspective(camera, 256, 240, state.depthX, state.y, z).y
end

local function verticalFollowOffset(state)
    local vertical = state.tracking.vertical
    if not vertical then return nil end
    local camera = world_view.resolveTownCamera(state.camera)
    local reference = projectZ(camera, state, vertical.referenceZ)
    local actual = projectZ(camera, state, state.z)
    local wanted = -(reference - actual) * vertical.factor
    return clamp(wanted, vertical.minOffsetY, vertical.maxOffsetY)
end

local function updateProjectionWindow(session, state)
    local tracking = state.tracking
    local target = world_view.trackedProjectionOffset(state.y, tracking.center,
        tracking.pixelsPerWorld, tracking.minOffsetX, tracking.maxOffsetX)
    state.cameraTargetOffsetX = target
    if state.cameraOffsetX == nil then state.cameraOffsetX = target end
    state.camera.projectionWindowOffsetX = state.cameraOffsetX
    session.worldCameraProjectionWindowOffsetX = state.cameraOffsetX
    local follow = verticalFollowOffset(state)
    if follow ~= nil then
        state.cameraFollowOffsetY = follow
        session.worldCameraProjectionWindowOffsetY = state.baseOffsetY + follow
    end
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
        groundProfile = parseGroundProfile(lane.groundProfile),
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
            vertical = (function()
                local authored = trackingSpec.vertical
                if authored == nil then return nil end
                if type(authored) ~= "table" then
                    error("bounded lane tracking.vertical must be a table", 0)
                end
                local result = {
                    minOffsetY = number(authored.minOffsetY, "tracking.vertical minOffsetY"),
                    maxOffsetY = number(authored.maxOffsetY, "tracking.vertical maxOffsetY"),
                    factor = number(authored.factor or 1, "tracking.vertical factor"),
                    referenceZ = number(authored.referenceZ or lane.groundZ or position[3] or 0,
                        "tracking.vertical referenceZ"),
                }
                if result.minOffsetY > result.maxOffsetY then
                    error("bounded lane tracking.vertical minOffsetY exceeds maxOffsetY", 0)
                end
                return result
            end)(),
        },
    }
    state.baseOffsetY = tonumber(camera.projectionWindowOffsetY
        or camera.projectionOffsetY) or 0
    state.x = state.depthX
    state.baseLevel = lane.id or DEFAULT_LEVEL
    state.levels = { [state.baseLevel] = buildLevel(
        { minY = state.minY, maxY = state.maxY, groundZ = state.groundZ,
          groundProfile = lane.groundProfile }, "lane", state.blockedRanges) }
    for id, def in pairs(spec.levels or {}) do
        if type(id) ~= "string" or id == "" or id == state.baseLevel then
            error("bounded lane level id '" .. tostring(id) .. "' must be a unique non-empty string", 0)
        end
        state.levels[id] = buildLevel(def, "level '" .. id .. "'")
    end
    state.links = {}
    for index, link in ipairs(spec.links or {}) do
        local label = "link #" .. index
        if type(link.id) ~= "string" or link.id == "" or state.links[link.id] then
            error("bounded lane " .. label .. " needs a unique string id", 0)
        end
        local ends = {}
        for _, key in ipairs({ "from", "to" }) do
            local point = link[key]
            if type(point) ~= "table" or not state.levels[point.level] then
                error("bounded lane link '" .. link.id .. "' " .. key .. ".level names no level", 0)
            end
            local level = state.levels[point.level]
            local y = number(point.y, "link '" .. link.id .. "' " .. key .. ".y")
            if y < level.minY or y > level.maxY then
                error("bounded lane link '" .. link.id .. "' " .. key
                    .. ".y lies outside level '" .. point.level .. "'", 0)
            end
            ends[key] = { level = point.level, y = y }
        end
        if ends.from.level == ends.to.level then
            error("bounded lane link '" .. link.id .. "' must join two different levels", 0)
        end
        state.links[link.id] = { id = link.id, from = ends.from, to = ends.to,
            x = number(link.x or state.depthX, "link '" .. link.id .. "' x") }
    end
    for _, doorway in ipairs(state.doorways) do
        if doorway.level ~= nil and not state.levels[doorway.level] then
            error("bounded lane doorway '" .. tostring(doorway.anchor) .. "' names no level '"
                .. tostring(doorway.level) .. "'", 0)
        end
        if doorway.link ~= nil then
            local link = state.links[doorway.link]
            local at = doorway.level or state.baseLevel
            if not link or (link.from.level ~= at and link.to.level ~= at) then
                error("bounded lane doorway '" .. tostring(doorway.anchor)
                    .. "' names link '" .. tostring(doorway.link)
                    .. "' that does not touch level '" .. at .. "'", 0)
            end
        end
    end
    applyLevel(state, levelAtAnchor(state, position))
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

-- Side-view town menus intentionally live as modal modes inside the map scene
-- so the world remains visible underneath them. Continuous traversal is polled
-- every frame rather than arriving through the scene's directional hooks, so
-- it must honor that same modal ownership explicitly or a held direction leaks
-- through the menu. Keep the policy here at the traversal boundary so every
-- bounded-lane map inherits it instead of each authored menu disabling walking.
local function mapModalOwnsInput()
    local scene_host = require("engine.scene_host")
    if scene_host.getCurrent() ~= "map" then return false end
    local sceneState = scene_host.getCurrentState()
    local mode = sceneState and sceneState.v and tonumber(sceneState.v.mode)
    return mode ~= nil and mode ~= 0
end

-- The one place lane position changes. Continuous walking and the discrete
-- nudge used by harnesses both go through it, so bounds and blocked ranges
-- cannot drift apart between them.
local function advance(session, state, direction, distance)
    -- A climb owns the actor until it arrives; walking input is not read.
    if state.climb then return false end
    state.facing = direction
    local nextY = state.y + direction * distance
    local limited = clamp(nextY, state.minY, state.maxY)
    if inBlockedRange(state, state.y, limited) then
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

-- The path a climb follows, as {x, y, z} waypoints: from where the actor stands to
-- the link's foot, along the flight, and out onto the far level at its own depth.
local function climbPath(state, link, up)
    local source, target = up and link.from or link.to, up and link.to or link.from
    local sourceZ = levelGround(state.levels[source.level], source.y)
    local targetZ = levelGround(state.levels[target.level], target.y)
    local raw = {
        { state.x, state.y, state.z },
        { link.x, source.y, sourceZ },
        { link.x, target.y, targetZ },
        { state.depthX, target.y, targetZ },
    }
    local path, length = { raw[1] }, 0
    for index = 2, #raw do
        local previous, point = path[#path], raw[index]
        local dx, dy, dz = point[1] - previous[1], point[2] - previous[2], point[3] - previous[3]
        local segment = math.sqrt(dx * dx + dy * dy + dz * dz)
        if segment > 1e-6 then
            path[#path + 1] = point
            length = length + segment
        end
    end
    return path, length, target
end

local function pointAlong(path, travelled)
    local remaining = travelled
    for index = 2, #path do
        local a, b = path[index - 1], path[index]
        local dx, dy, dz = b[1] - a[1], b[2] - a[2], b[3] - a[3]
        local segment = math.sqrt(dx * dx + dy * dy + dz * dz)
        if remaining <= segment or index == #path then
            local t = segment > 0 and math.min(1, remaining / segment) or 1
            return a[1] + dx * t, a[2] + dy * t, a[3] + dz * t
        end
        remaining = remaining - segment
    end
    local last = path[#path]
    return last[1], last[2], last[3]
end

-- Take the link a doorway names. The doorway supplies the proximity and the
-- direction (its Event's authored direction picks UP or DOWN); the link supplies
-- the flight. Returns true if a climb began.
function bounded_lane.beginClimb(session, doorway)
    local state = session and session.townTraversal
    if not state or state.climb or not doorway or not doorway.link then return false end
    local link = state.links[doorway.link]
    if not link then return false end
    local up
    if state.level == link.from.level then up = true
    elseif state.level == link.to.level then up = false
    else return false end
    local path, length, target = climbPath(state, link, up)
    if length <= 0 then return false end
    state.climb = { link = link, path = path, length = length, travelled = 0,
        target = target, direction = up and 1 or -1 }
    state.atBound = 0
    return true
end

local function finishClimb(session, state)
    local climb = state.climb
    applyLevel(state, climb.target.level)
    state.x = state.depthX
    state.y = climb.target.y
    state.z = groundAt(state, state.y)
    state.climb = nil
    state.moving = false
    state.atBound = 0
end

local function advanceClimb(session, state, distance)
    local climb = state.climb
    local before = climb.travelled
    climb.travelled = math.min(climb.length, climb.travelled + distance)
    local x, y, z = pointAlong(climb.path, climb.travelled)
    if y ~= state.y then state.facing = y > state.y and 1 or -1 end
    state.x, state.y, state.z = x, y, z
    state.moving = true
    state.walkDistance = (state.walkDistance or 0) + (climb.travelled - before)
    if climb.travelled >= climb.length then finishClimb(session, state) end
end

-- Put the actor on a level at a lane position. For harnesses and tests that need
-- a deterministic place to stand; play moves by walking and climbing.
function bounded_lane.place(session, level, y)
    local state = session and session.townTraversal
    if not state then return false end
    applyLevel(state, level or state.level)
    state.climb = nil
    state.x = state.depthX
    state.y = clamp(tonumber(y) or state.y, state.minY, state.maxY)
    state.z = groundAt(state, state.y)
    state.moving = false
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
    if held ~= 0 and mapModalOwnsInput() then held = 0 end
    if dt == nil then
        state.walking = false
        state.walkFrameIndex = 0
        state.atBound = 0
    elseif dt < 0 then
        error("bounded lane update dt must be non-negative", 0)
    else
        if state.climb then
            advanceClimb(session, state, state.speed * dt)
        elseif held ~= 0 then
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

-- Event.direction is the same authored axis used by the transfer marker.
function bounded_lane.doorwayButton(session, doorway)
    local event = bounded_lane.eventFor(session, doorway)
    if not event then return nil end
    local axis = world_view.transitionArrowAxis(event.direction)
    if axis.x > 0 then return "UP" end
    if axis.x < 0 then return "DOWN" end
    return axis.y < 0 and "LEFT" or "RIGHT"
end

function bounded_lane.nearDoorway(session, button)
    local state = session and session.townTraversal
    if not state or state.climb then return nil end
    local nearest, distance
    for _, doorway in ipairs(state.doorways) do
        local anchor = state.environment and state.environment.anchors[doorway.anchor]
        if anchor and levelOf(state, doorway) == state.level
                and (not button or bounded_lane.doorwayButton(session, doorway) == button) then
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
    if not state or state.climb then return nil end
    local bound = direction < 0 and state.minY or state.maxY
    local best, bestDistance
    local fallback, fallbackDistance
    for _, doorway in ipairs(state.doorways) do
        local anchor = state.environment and state.environment.anchors[doorway.anchor]
        if anchor and levelOf(state, doorway) == state.level
                and bounded_lane.doorwayButton(session, doorway)
                == (direction < 0 and "LEFT" or "RIGHT") then
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
    if not anchor or levelOf(state, doorway) ~= state.level then return false end
    local y = tonumber(anchor.position[2]) or 0
    local button = bounded_lane.doorwayButton(session, doorway)
    return (button == "LEFT" and math.abs(y - state.minY) < 0.01)
        or (button == "RIGHT" and math.abs(y - state.maxY) < 0.01)
end

-- Resolve a doorway to the ordinary Map event that carries its commands.
-- Gameplay meaning stays in Event data; the doorway supplies only proximity.
function bounded_lane.eventFor(session, doorway)
    if not doorway then return nil end
    for _, event in ipairs((session.currentMapData and session.currentMapData.events) or {}) do
        if (doorway.eventInstanceId ~= nil and event.instanceId == doorway.eventInstanceId)
                or (doorway.eventId ~= nil and event.id == doorway.eventId) then
            return event
        end
    end
    return nil
end

function bounded_lane.interact(session, button)
    return bounded_lane.eventFor(session, bounded_lane.nearDoorway(session, button))
end

-- Street names appear before reaching a bound, giving time to read them.
function bounded_lane.promptDoorway(session)
    local near = bounded_lane.nearDoorway(session)
    if near then return near end
    local state = session and session.townTraversal
    if not state then return nil end
    local best, distance
    for _, direction in ipairs({-1, 1}) do
        local doorway = bounded_lane.edgeDoorway(session, direction)
        local anchor = doorway and state.environment.anchors[doorway.anchor]
        if anchor then
            local d = math.abs(state.y - anchor.position[2])
            if d <= EDGE_REACH and (not distance or d < distance) then
                best, distance = doorway, d
            end
        end
    end
    return best
end

return bounded_lane