-- Levels and links: a building's storeys on a bounded lane.
--
-- A lane is one line, but a house has a ground floor and a gallery above it. A
-- map declares extra `levels` (each a lane of its own) and `links` between them;
-- the player walks one level at a time and takes a link by pressing UP/DOWN at a
-- doorway that names it. The camera may follow the actor's height, as far as the
-- authored room goes. These tests use inline map data, so they pin the primitive
-- rather than any one Project's building.
local loader = require("engine.data.loader")
local session = require("engine.session")
local lane = require("engine.bounded_lane")

local passed, failed = 0, 0
local function check(condition, message)
    if condition then
        passed = passed + 1
    else
        failed = failed + 1
        print("CHECK FAILED: " .. message)
    end
end

loader.init()

local GALLERY_Z = 3.2

-- A hall: a ground lane 0.3..21 with a gallery lane 1..10.6 one storey up, joined
-- by a stair whose foot is at 15.2 and whose top is at 10.4. Ground and gallery
-- OVERLAP in Y, which is the point: the same Y is two different places.
local function spec(overrides)
    local value = {
        provider = "bounded_lane",
        environmentPackage = "inline",
        spawnAnchor = "spawn_player",
        lane = { minY = 0.3, maxY = 21.0, depthX = 0, groundZ = 0, speed = 3.4 },
        levels = { gallery = { minY = 1.0, maxY = 10.6, groundZ = GALLERY_Z } },
        links = { { id = "stair", x = 1.8,
            from = { level = "ground", y = 15.2 }, to = { level = "gallery", y = 10.4 } } },
        doorways = {
            { anchor = "stair_foot", eventInstanceId = "foot", radius = 0.9, link = "stair" },
            { anchor = "stair_top", eventInstanceId = "top", radius = 0.9, level = "gallery",
              link = "stair" },
            { anchor = "street_door", eventInstanceId = "street", radius = 0.9 },
            { anchor = "room_door", eventInstanceId = "room", radius = 0.9, level = "gallery" },
        },
        camera = {
            profile = "town_sideview", distance = 14, yawDegrees = 12, pitchDegrees = -17.5,
            eyeHeight = -1.4583333333, fovDegrees = 36.87,
            projectionScale = { x = 0.94079629, y = 0.9116197588 },
            projectionWindowOffsetY = -70.47,
            target = { x = 0, y = 11, z = 2.2604 },
            projectionFrame = { compositionWidth = 256, canonicalCenterX = 128, canonicalHorizonY = 66 },
            tracking = { axis = "y", center = 11, minOffsetX = -156, maxOffsetX = 156,
                vertical = { minOffsetY = -120, maxOffsetY = 0 } },
        },
    }
    for key, patch in pairs(overrides or {}) do value[key] = patch end
    return value
end

local function mapData(traversal)
    return {
        id = 9999, title = "inline hall", traversal = traversal,
        events = {
            { instanceId = "foot", name = "Stair", direction = "away", worldPosition = { 0, 15.2, 0 } },
            { instanceId = "top", name = "Stair down", direction = "toward",
              worldPosition = { 0, 10.4, GALLERY_Z }, level = "gallery" },
            { instanceId = "street", name = "Street", direction = "left", worldPosition = { 0, 0.3, 0 } },
            { instanceId = "room", name = "Room", direction = "away",
              worldPosition = { 0, 6.0, GALLERY_Z }, level = "gallery" },
        },
    }
end

local environment = { anchors = {
    spawn_player = { position = { 0, 19.0, 0 } },
    stair_foot = { position = { 0, 15.2, 0 } },
    stair_top = { position = { 0, 10.4, GALLERY_Z } },
    street_door = { position = { 0, 0.3, 0 } },
    room_door = { position = { 0, 6.0, GALLERY_Z } },
    gallery_spawn = { position = { 0, 6.0, GALLERY_Z } },
} }

local function open(overrides, arrival)
    local game = session.GameSession.new(loader)
    game:initializeStartingParty()
    local data = mapData(spec(overrides))
    game.currentMapData = data
    lane.initialize(game, data, environment, arrival)
    return game, game.townTraversal
end

local game, state = open()
check(lane.isActive(game), "an inline map selects bounded_lane")
check(state.level == "ground" and state.baseLevel == "ground", "the base lane is the ground level")
check(state.levels.gallery ~= nil and state.links.stair ~= nil, "levels and links are read")
check(state.z == 0, "the ground level's floor is where the actor starts")

-- Arriving at an anchor on the gallery puts the actor on the gallery.
local arrived, arrivedState = open(nil, "gallery_spawn")
check(arrivedState.level == "gallery", "an anchor at gallery height arrives on the gallery")
check(math.abs(arrivedState.z - GALLERY_Z) < 1e-6, "the gallery floor height applies on arrival")
check(arrivedState.minY == 1.0 and arrivedState.maxY == 10.6, "the gallery's own bounds apply")

-- Each level has its own bounds and floor.
for _ = 1, 400 do lane.update(game, 1 / 60, -1) end
check(math.abs(state.y - 0.3) < 1e-6, "walking left stops at the ground level's own west bound")
for _ = 1, 600 do lane.update(game, 1 / 60, 1) end
check(math.abs(state.y - 21.0) < 1e-6, "walking right stops at the ground level's east bound")
check(lane.groundAt(game, 5) == 0, "ground floor height on the ground level")
check(lane.groundAt(game, 5, "gallery") == GALLERY_Z, "another level's floor can be asked for by name")
check(lane.groundAt(game, 5, "nowhere") == nil, "an unknown level has no floor")

-- Doorways belong to a level: the room door above is not in reach from below.
lane.place(game, "ground", 6.0)
check(lane.nearDoorway(game, "UP") == nil, "a door on the gallery is out of reach from beneath it")
lane.place(game, "gallery", 6.0)
check(lane.nearDoorway(game, "UP") ~= nil and lane.nearDoorway(game, "UP").anchor == "room_door",
    "the same lane Y on the gallery reaches that door")
check(lane.place(game, "gallery", 99) and state.y == 10.6, "place clamps to the level's bounds")

-- Events carry their level: models and prompts follow the event, not the actor.
lane.place(game, "ground", 6.0)
check(lane.onLevel(game, { name = "plain" }), "an event with no level is on the base lane")
check(not lane.onLevel(game, game.currentMapData.events[4]), "a gallery event is not on the ground level")
check(lane.eventGroundAt(game, game.currentMapData.events[4], 6.0) == GALLERY_Z,
    "a gallery event stands on the gallery floor even while the actor is below")
check(lane.eventGroundAt(game, game.currentMapData.events[3], 6.0) == 0, "a ground event stands on the ground")

-- The stair: UP at the foot climbs, and the actor arrives on the gallery.
lane.place(game, "ground", 15.0)
local foot = lane.nearDoorway(game, "UP")
check(foot ~= nil and foot.link == "stair", "the stair foot is reachable with UP")
check(lane.nearDoorway(game, "DOWN") == nil, "the foot is not a DOWN doorway")
check(lane.beginClimb(game, foot), "pressing up at the foot begins a climb")
check(state.climb ~= nil, "the actor is climbing")
check(lane.nearDoorway(game) == nil and lane.edgeDoorway(game, -1) == nil,
    "nothing can be interacted with mid-climb")
check(not lane.beginClimb(game, foot), "a climb cannot be started during a climb")

local previousZ, maxStep, steps = state.z, 0, 0
local sawDepth = false
while state.climb and steps < 2000 do
    lane.update(game, 1 / 60, 1)      -- held input is ignored while climbing
    maxStep = math.max(maxStep, math.abs(state.z - previousZ))
    previousZ = state.z
    if state.x > 1.0 then sawDepth = true end
    steps = steps + 1
end
check(state.climb == nil, "the climb ends")
check(state.level == "gallery", "the actor arrives on the gallery")
check(math.abs(state.y - 10.4) < 1e-6 and math.abs(state.z - GALLERY_Z) < 1e-6,
    "the actor arrives at the top of the stair, at gallery height")
check(state.x == 0, "the actor steps back onto the lane's depth at the top")
check(sawDepth, "the actor walked in to the stair's own depth while climbing")
check(maxStep < 0.05, "the climb has no pops in height (largest frame step " .. string.format("%.3f", maxStep) .. ")")
check(steps > 60 and steps < 400, "a storey takes a believable time to climb (" .. steps .. " frames)")
check(state.minY == 1.0, "the gallery's bounds apply after the climb")

-- And DOWN at the top comes back down.
local top = lane.nearDoorway(game, "DOWN")
check(top ~= nil and top.anchor == "stair_top", "the stair top is reachable with DOWN")
check(lane.nearDoorway(game, "UP") == nil or lane.nearDoorway(game, "UP").anchor ~= "stair_top",
    "the top is not an UP doorway")
check(lane.beginClimb(game, top), "pressing down at the top begins the descent")
steps = 0
while state.climb and steps < 2000 do lane.update(game, 1 / 60, 0); steps = steps + 1 end
check(state.level == "ground" and math.abs(state.y - 15.2) < 1e-6 and state.z == 0,
    "the descent arrives at the foot, on the ground")

-- A climb from the wrong place does nothing.
lane.place(game, "gallery", 3.0)
check(not lane.beginClimb(game, { anchor = "x", link = "missing" }), "an unknown link does not climb")

-- Vertical follow: the camera slides with the actor's height, inside its bounds.
local ground = open()
lane.place(ground, "ground", 12.0)
check(ground.worldCameraProjectionWindowOffsetY == -70.47,
    "on the reference floor the camera sits at its authored vertical offset")
local up, upState = open()
lane.place(up, "gallery", 6.0)
check(up.worldCameraProjectionWindowOffsetY < -70.47 - 20,
    "on the gallery the camera has slid up to follow (offset " .. tostring(up.worldCameraProjectionWindowOffsetY) .. ")")
check(upState.cameraFollowOffsetY >= -120 and upState.cameraFollowOffsetY <= 0,
    "the follow stays inside the authored vertical bounds")

-- The follow keeps the actor at the same screen height: project the feet.
local world_view = require("engine.generated.world-view")
local function footScreenY(g, s)
    local camera = world_view.resolveTownCamera(setmetatable(
        { projectionWindowOffsetY = g.worldCameraProjectionWindowOffsetY }, { __index = s.camera }))
    return world_view.projectPerspective(camera, 256, 240, s.depthX, s.y, s.z).y
end
lane.place(ground, "ground", 6.0)
local groundFeet = footScreenY(ground, ground.townTraversal)
lane.place(up, "gallery", 6.0)
check(math.abs(footScreenY(up, upState) - groundFeet) < 0.5,
    "an actor on the gallery keeps the screen height they have on the ground")

-- Clamped by the room that exists: a tight bound stops the camera short.
local tight, tightState = open({ camera = (function()
    local c = spec().camera
    c.tracking.vertical = { minOffsetY = -10, maxOffsetY = 0 }
    return c
end)() })
lane.place(tight, "gallery", 6.0)
check(tightState.cameraFollowOffsetY == -10, "the follow stops at the authored room's edge")

-- No vertical tracking declared: the camera does not move vertically at all.
local flat, flatState = open({ camera = (function()
    local c = spec().camera
    c.tracking.vertical = nil
    return c
end)() })
lane.place(flat, "gallery", 6.0)
check(flat.worldCameraProjectionWindowOffsetY == nil and flatState.cameraFollowOffsetY == nil,
    "a map that does not ask for vertical follow keeps its fixed vertical window")

-- Authoring mistakes fail loudly rather than doing nothing.
local function failsWith(overrides, fragment, message)
    local ok, err = pcall(open, overrides)
    check(not ok and tostring(err):find(fragment, 1, true) ~= nil,
        message .. " (got " .. tostring(err) .. ")")
end
failsWith({ links = { { id = "s", from = { level = "ground", y = 15 }, to = { level = "attic", y = 5 } } } },
    "names no level", "a link to an unknown level fails")
failsWith({ links = { { id = "s", from = { level = "ground", y = 15 }, to = { level = "ground", y = 5 } } } },
    "two different levels", "a link within one level fails")
failsWith({ links = { { id = "s", from = { level = "ground", y = 15 }, to = { level = "gallery", y = 50 } } } },
    "outside level", "a link end outside its level fails")
failsWith({ doorways = { { anchor = "stair_foot", eventInstanceId = "foot", link = "nope" } } },
    "does not touch level", "a doorway naming an unknown link fails")
failsWith({ doorways = { { anchor = "stair_top", eventInstanceId = "top", level = "attic" } } },
    "names no level", "a doorway naming an unknown level fails")
failsWith({ levels = { ground = { minY = 0, maxY = 1 } } },
    "unique non-empty string", "a level cannot reuse the base lane's name")
failsWith({ levels = { gallery = { minY = 5, maxY = 1, groundZ = 3 } } },
    "minY < maxY", "a level with inverted bounds fails")

require("tests.fail_fast")("test_bounded_lane_levels", failed, passed)
