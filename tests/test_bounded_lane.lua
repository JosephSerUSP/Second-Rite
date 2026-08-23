-- Bounded-lane traversal is a provider capability, not a replacement Map.
--
-- St. Maria scrolls: a window moves across a plate that is wider than it, and
-- the plate's width is authored per screen. The camera eye stays fixed, so the
-- projection window never moves; the scroll is a draw offset, not a camera.
local loader = require("engine.data.loader")
local session = require("engine.session")
local exploration = require("engine.exploration")
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
local game = session.GameSession.new(loader)
game:initializeStartingParty()

local GATE, PRACA = 16, 17

exploration.loadMap(game, loader.getMapIndex(GATE))
check(lane.isActive(game), "the gate screen selects bounded_lane")
check(game.townTraversal.environment.manifest.contractVersion == 1,
    "runtime reads the environment manifest")

local state = game.townTraversal
check(state.x == 7.8, "spawn depth comes from the package anchor")
local laneCentre = (state.minY + state.maxY) / 2
check(math.abs(state.y - laneCentre) < 0.001, "spawn lands on the lane centre anchor")

local preRendered = state.environment.preRendered
check(preRendered ~= nil, "the gate screen is a pre-rendered package")
check(#preRendered.slicePositions == 1, "a flat plate needs exactly one slice")
-- Plate widths are authored per screen: a street is long, a room is not. The
-- height is fixed because the visible world is, and every plate must be at
-- least as wide as the narrowest surface profile or it cannot fill the window.
check(preRendered.imageSize[2] == 240, "plates are authored at the native height")
check(preRendered.imageSize[1] >= 256, "a plate is at least as wide as a Classic window")

-- Movement
local startY = state.y
check(lane.move(game, 1) and state.y > startY, "right movement increases lane position")
check(state.x == 7.8, "horizontal movement keeps authored depth fixed")
check(state.cameraTargetOffsetX == 0,
    "scrolling is a draw offset and never moves the projection window")

for _ = 1, 200 do lane.move(game, 1) end
check(state.y <= state.maxY + 0.001, "movement clamps at the authored east bound")
for _ = 1, 400 do lane.move(game, -1) end
check(state.y >= state.minY - 0.001, "movement clamps at the authored west bound")

-- Arrival anchors: entering a screen through a named door must land on that
-- door, not on the destination's default spawn.
exploration.loadMap(game, loader.getMapIndex(PRACA), { arrival = "west_gate" })
local praca = game.townTraversal
local westGate = praca.environment.anchors["west_gate"]
check(westGate ~= nil, "the praca package publishes its west_gate anchor")
check(math.abs(praca.y - westGate.position[2]) < 0.001,
    "arrival through a named door spawns on that door's anchor")
check(math.abs(praca.y - (praca.minY + praca.maxY) / 2) > 0.5,
    "arrival did not silently fall back to the lane centre")

exploration.loadMap(game, loader.getMapIndex(PRACA), { arrival = "no_such_anchor" })
local pracaCentre = (game.townTraversal.minY + game.townTraversal.maxY) / 2
check(math.abs(game.townTraversal.y - pracaCentre) < 0.001,
    "an unknown arrival falls back to the map's spawn anchor")

-- Structural integrity of the whole town: every doorway resolves to a real
-- anchor, and every transfer names a map that exists. A broken screen graph
-- is the failure this suite exists to catch.
local townMaps = {}
for index, map in ipairs(loader.maps) do
    if type(map.traversal) == "table" and map.traversal.provider == "bounded_lane" then
        townMaps[#townMaps + 1] = { index = index, map = map }
    end
end
check(#townMaps >= 9, "the town publishes its screens (" .. #townMaps .. " found)")

local function findEvent(map, instanceId)
    for _, event in ipairs(map.events or {}) do
        if event.instanceId == instanceId then return event end
    end
    return nil
end

for _, entry in ipairs(townMaps) do
    local map = entry.map
    local label = "map " .. tostring(map.id)
    exploration.loadMap(game, entry.index)
    local anchors = game.townTraversal.environment.anchors
    for _, doorway in ipairs(map.traversal.doorways or {}) do
        check(anchors[doorway.anchor] ~= nil,
            label .. " doorway anchor '" .. tostring(doorway.anchor) .. "' exists")
        check(findEvent(map, doorway.eventInstanceId) ~= nil,
            label .. " doorway event '" .. tostring(doorway.eventInstanceId) .. "' exists")
    end
    for _, event in ipairs(map.events or {}) do
        for _, command in ipairs(event.commands or {}) do
            if command.cmd == "LOAD_MAP" and command.mapId then
                check(loader.getMapIndex(command.mapId) ~= nil,
                    label .. " transfers to a map that exists (" .. tostring(command.mapId) .. ")")
            end
        end
        local position = event.worldPosition
        if position then
            check(position[2] >= map.traversal.lane.minY - 0.001
                    and position[2] <= map.traversal.lane.maxY + 0.001,
                label .. " event '" .. tostring(event.name) .. "' stands inside the lane")
        end
    end
end

-- An edge exit is the street continuing; a door is a thing you open. The HUD
-- tells them apart by exact position on a bound, and Market Row is the case
-- that rules out a radius test: the weaponsmith stands 0.86 from the east end
-- with a 0.9 radius, so any tolerant test would call a shop door an exit.
exploration.loadMap(game, loader.getMapIndex(18))
local market = game.townTraversal
local byAnchor = {}
for _, doorway in ipairs(market.doorways) do byAnchor[doorway.anchor] = doorway end
check(lane.isEdgeDoorway(game, byAnchor["west_praca"]),
    "the west end of Market Row is an edge exit")
check(lane.isEdgeDoorway(game, byAnchor["east_quay"]),
    "the east end of Market Row is an edge exit")
check(not lane.isEdgeDoorway(game, byAnchor["smith_door"]),
    "the weaponsmith door is a door, not an edge exit, despite standing inside a radius of one")

-- Authored width is a design statement: the square is the widest place in the
-- town and a room is not a street. A regression that flattened every plate to
-- one width would still pass every other check in this file.
local widthOf = {}
for _, entry in ipairs(townMaps) do
    exploration.loadMap(game, entry.index)
    widthOf[entry.map.id] = game.townTraversal.environment.preRendered.imageSize[1]
end
check(widthOf[17] > widthOf[16], "the praca is wider than the gate")
check(widthOf[16] > widthOf[19], "the gate is wider than the quay")
check(widthOf[19] > widthOf[22], "an exterior is wider than a room")

print(string.format("=== test_bounded_lane: %d passed, %d failed ===", passed, failed))
