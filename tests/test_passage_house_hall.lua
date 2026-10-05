-- The Passage House: one building, two storeys, walked in one screen.
--
-- Map 34 (the stair hall) is a ground lane under a gallery lane, joined by a
-- stair. The player can walk the ground floor end to end, or press Up at the
-- stair foot to climb, walk the gallery to Room 3 and the Registry gate, and come
-- back down. These tests drive the shipped maps with held input, so they fail
-- if the data, the package anchors and the lane code ever stop agreeing.
local loader = require("engine.data.loader")
local session = require("engine.session")
local exploration = require("engine.exploration")
local lane = require("engine.bounded_lane")

local passed, failed = 0, 0
local function check(condition, message)
    if condition then passed = passed + 1 else
        failed = failed + 1
        print("CHECK FAILED: " .. message)
    end
end

loader.init()
local game = session.GameSession.new(loader)
game:initializeStartingParty()

local CORTICO, HALL, ROOM3 = 1001, 34, 25

local function load(mapId, arrival)
    exploration.loadMap(game, loader.getMapIndex(mapId), arrival and { arrival = arrival } or nil)
    return game.townTraversal
end

local function destinationOf(event)
    for _, command in ipairs(event and event.commands or {}) do
        if command.cmd == "LOAD_MAP" then return command.mapId, command.arrival end
    end
end

local function walkUntil(held, done, limit)
    local frames = 0
    while not done() and frames < (limit or 6000) do
        lane.update(game, 1 / 60, held)
        frames = frames + 1
    end
    return frames
end

-- The Cortico door enters the hall by its court door; Room 3 hangs off the gallery.
local cortico = load(CORTICO)
local passageDoor
for _, event in ipairs(game.currentMapData.events) do
    if event.instanceId == "core-run-court-door-passage-house" then passageDoor = event end
end
local toMap, arrival = destinationOf(passageDoor)
check(toMap == HALL and arrival == "exit_door", "the Cortico's Passage House door enters the stair hall by its court door")

local state = load(HALL, "exit_door")
check(lane.isActive(game) and state.level == "ground", "the hall is a bounded lane that starts on the ground floor")
check(state.levels.gallery ~= nil and state.links.stair ~= nil, "the hall declares a gallery level and a stair link")
check(math.abs(state.y - 20.0) < 0.001, "arriving through the great door lands at the court door")
check(state.tracking.vertical ~= nil, "the hall's camera follows the actor vertically")

-- Fork A: keep walking left along the ground floor, under the gallery, to the street door.
local passedFoot = false
walkUntil(-1, function()
    if math.abs(state.y - 15.2) < 0.05 then passedFoot = true end
    return state.y <= state.minY + 1e-6
end)
check(passedFoot, "the ground floor runs past the stair foot without climbing")
check(state.level == "ground" and state.z == 0, "the walk along the ground floor stays on the ground")
check(math.abs(state.y - state.minY) < 1e-6, "the ground floor runs to its far end")
local streetEdge = lane.edgeDoorway(game, -1)
check(streetEdge ~= nil and streetEdge.anchor == "street_door", "the ground floor's far end is the street door")
check(destinationOf(lane.eventFor(game, streetEdge)) == CORTICO, "the street door leads back out to the Cortico")
check(lane.nearDoorway(game, "UP") == nil or lane.nearDoorway(game, "UP").anchor ~= "room3_door",
    "Room 3's door above is out of reach from the ground floor")

-- Fork B: Up at the stair foot climbs.
walkUntil(1, function() return state.y >= 15.0 end)
local foot = lane.nearDoorway(game, "UP")
check(foot ~= nil and foot.link == "stair", "Up at the stair foot offers the stair")
check(lane.beginClimb(game, foot), "pressing Up starts the climb")
local previousZ, maxStep = state.z, 0
walkUntil(0, function()
    maxStep = math.max(maxStep, math.abs(state.z - previousZ)); previousZ = state.z
    return state.climb == nil
end)
check(state.level == "gallery" and math.abs(state.z - 3.2) < 1e-6, "the climb arrives on the gallery, a full storey up")
check(maxStep < 0.05, "the climb has no pops in height")
check(game.worldCameraProjectionWindowOffsetY > state.baseOffsetY + 20,
    "the camera has followed the actor up")

-- The gallery: Room 3, then the Registry gate.
walkUntil(-1, function() return state.y <= 6.0 end)
local room3Door = lane.nearDoorway(game, "UP")
check(room3Door ~= nil and room3Door.anchor == "room3_door", "Room 3's door is reachable on the gallery")
local roomMap, roomArrival = destinationOf(lane.eventFor(game, room3Door))
check(roomMap == ROOM3 and roomArrival == "exit_door", "Room 3's door leads into Room 3")

walkUntil(-1, function() return state.y <= state.minY + 1e-6 end)
local gate = lane.nearDoorway(game, "UP")
check(gate ~= nil and gate.anchor == "gate_door", "the Registry gate is at the far end of the gallery")
local gateEvent = lane.eventFor(game, gate)
local branch = gateEvent.commands[1]
check(branch.cmd == "CONDITIONAL_BRANCH" and branch.condition == "hasItem:198",
    "the gate opens for a Crossing Writ and no other key")
check(destinationOf({ commands = branch.commands }) == 33, "an opened gate leads into the Registry")
check(destinationOf({ commands = branch.elseCommands }) == nil, "a locked gate leads nowhere")

-- Through the gate, the Registry: its own gate door leads back to the gallery.
check(select(2, destinationOf({ commands = branch.commands })) == "gate_door",
    "the opened gate arrives at the Registry's gate door")
local registry = load(33, "gate_door")
check(registry.level == "ground" and math.abs(registry.y - 0.9833) < 0.001, "the Registry gate arrival is at its door")
local registryGate = lane.nearDoorway(game, "UP")
check(registryGate ~= nil and registryGate.anchor == "gate_door", "the Registry's gate door is reachable from its lane")
local backMap, backArrival = destinationOf(lane.eventFor(game, registryGate))
check(backMap == HALL and backArrival == "gate_door", "the Registry's gate leads back to the gallery")
local backInHall = load(HALL, "gate_door")
check(backInHall.level == "gallery" and math.abs(backInHall.y - 1.5) < 0.001,
    "coming back through the gate lands on the gallery at the gate")
load(HALL, "exit_door")
state = game.townTraversal
walkUntil(-1, function() return state.y <= 15.0 end)
lane.beginClimb(game, lane.nearDoorway(game, "UP"))
walkUntil(0, function() return state.climb == nil end)

-- And back down.
walkUntil(1, function() return state.y >= 9.4 end)
local top = lane.nearDoorway(game, "DOWN")
check(top ~= nil and top.anchor == "stair_top", "Down at the stair top offers the stair")
check(lane.beginClimb(game, top), "pressing Down starts the descent")
walkUntil(0, function() return state.climb == nil end)
check(state.level == "ground" and state.z == 0 and math.abs(state.y - 15.2) < 1e-6,
    "the descent arrives at the stair foot, on the ground")

-- The great door goes back out to the Cortico.
walkUntil(1, function() return state.y >= 19.9 end)
local court = lane.nearDoorway(game, "DOWN")
check(court ~= nil and court.anchor == "exit_door", "the great door is reachable at the far end")
check(destinationOf(lane.eventFor(game, court)) == CORTICO, "the great door leads out to the Cortico")

-- Room 3 is a room, and its door is the gallery.
local room = load(ROOM3)
check(lane.isActive(game) and room.level == "ground", "Room 3 is a bounded lane")
check(room.environment.preRendered == nil, "Room 3 is a real 3D room, not a flat plate")
local exitMap, exitArrival = destinationOf(lane.eventFor(game, room.doorways[1]))
check(exitMap == HALL and exitArrival == "room3_door", "Room 3's door leads out to the gallery at its own door")

-- Arriving back from Room 3 puts the player on the gallery, not on the ground.
local back = load(HALL, "room3_door")
check(back.level == "gallery" and math.abs(back.z - 3.2) < 1e-6, "coming out of Room 3 lands on the gallery")
check(math.abs(back.y - 6.0) < 0.001, "and at Room 3's door")

-- The caretaker keeps the house: the hall, not Room 3, has the porter.
load(HALL)
local hasCaretaker = false
for _, event in ipairs(game.currentMapData.events) do
    if event.instanceId == "core-run-home-caretaker" then hasCaretaker = true end
end
check(hasCaretaker, "the caretaker minds the hall")

-- Doors must not overlap: where two are in reach at once the HUD can only name one
-- of them, so the player cannot tell which an Up press will take.
for _, mapId in ipairs({ 25, 33, HALL }) do
    load(mapId)
    local doorways = game.townTraversal.doorways
    local anchors = game.townTraversal.environment.anchors
    for i = 1, #doorways do
        for j = i + 1, #doorways do
            local a, b = doorways[i], doorways[j]
            if (a.level or "ground") == (b.level or "ground") then
                local gap = math.abs(anchors[a.anchor].position[2] - anchors[b.anchor].position[2])
                check(gap >= (a.radius or 0.65) + (b.radius or 0.65) - 1e-6,
                    "map " .. mapId .. " doors '" .. a.anchor .. "' and '" .. b.anchor
                    .. "' are too close to tell apart (" .. string.format("%.2f", gap) .. ")")
            end
        end
    end
end

require("tests.fail_fast")("test_passage_house_hall", failed, passed)
