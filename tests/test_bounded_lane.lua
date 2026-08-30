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

local CHURCHYARD, PRACA = 16, 17

exploration.loadMap(game, loader.getMapIndex(CHURCHYARD))
check(lane.isActive(game), "the churchyard screen selects bounded_lane")
check(game.townTraversal.environment.manifest.contractVersion == 1,
    "runtime reads the environment manifest")

local state = game.townTraversal
check(state.x == 7.8, "spawn depth comes from the package anchor")
local laneCentre = (state.minY + state.maxY) / 2
check(math.abs(state.y - laneCentre) < 0.001, "spawn lands on the lane centre anchor")

local preRendered = state.environment.preRendered
check(preRendered ~= nil, "the churchyard screen is a pre-rendered package")
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
exploration.loadMap(game, loader.getMapIndex(PRACA), { arrival = "churchyard_stair" })
local praca = game.townTraversal
local stair = praca.environment.anchors["churchyard_stair"]
check(stair ~= nil, "the praca package publishes its churchyard_stair anchor")
check(math.abs(praca.y - stair.position[2]) < 0.001,
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
check(#townMaps >= 11, "the town publishes its screens (" .. #townMaps .. " found)")

local canonicalTownSpeed = townMaps[1].map.traversal.lane.speed
for _, entry in ipairs(townMaps) do
    check(entry.map.traversal.lane.speed == canonicalTownSpeed,
        "map " .. entry.map.id .. " walks at the town's shared speed")
end

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

-- Floor height varies along the lane, and does not change what the lane is.
-- The pub is the shape this exists for: a counter by the door, a short flight
-- of steps, and a lower room with the tables in it.
local floorMap = {
    id = 900,
    traversal = {
        provider = "bounded_lane",
        environmentPackage = "assets/environments/st_maria_town/pub/environment.json",
        spawnAnchor = "spawn_player",
        lane = {
            minY = 0, maxY = 10, depthX = 7.8, groundZ = -1.5, speed = 3.4,
            groundProfile = {
                { y = 0, z = -1.5 }, { y = 3.0, z = -1.5 },
                { y = 3.8, z = -2.9 }, { y = 10, z = -2.9 },
            },
        },
        blockedRanges = {},
        camera = { distance = 21.1175, fovDegrees = 28.072486935852957,
            target = { x = 7.8, y = 5, z = 0 },
            projectionFrame = { baseViewportWidth = 256 },
            tracking = { center = 5, minOffsetX = 0, maxOffsetX = 0, pixelsPerWorld = 34.6 } },
        doorways = {},
    },
    events = {},
}
local floorEnv = require("engine.environment_package").load(
    floorMap.traversal.environmentPackage)
lane.initialize(game, floorMap, floorEnv, nil)
local floor = game.townTraversal
check(math.abs(lane.groundAt(game, 1.0) - (-1.5)) < 0.001,
    "the floor by the door is the authored upper level")
check(math.abs(lane.groundAt(game, 10) - (-2.9)) < 0.001,
    "the floor at the far end is the authored lower level")
check(math.abs(lane.groundAt(game, 3.4) - (-2.2)) < 0.001,
    "the floor ramps linearly between two control points")
check(math.abs(lane.groundAt(game, -5) - (-1.5)) < 0.001,
    "before the first control point the floor holds its first height")
check(math.abs(lane.groundAt(game, 99) - (-2.9)) < 0.001,
    "past the last control point the floor holds its last height")

-- Height is drawn, never walked: the lane must be exactly as reachable as it
-- would be on flat ground, or "no logical verticality" has quietly stopped
-- being true.
floor.y = 0
for _ = 1, 400 do lane.move(game, 1) end
check(math.abs(floor.y - 10) < 0.001, "a stepped floor does not stop the walk east")
check(math.abs(floor.z - (-2.9)) < 0.001, "walking east leaves the actor on the lower floor")
for _ = 1, 400 do lane.move(game, -1) end
check(math.abs(floor.y - 0) < 0.001, "a stepped floor does not stop the walk back west")
check(math.abs(floor.z - (-1.5)) < 0.001, "walking back west returns the actor to the upper floor")

-- A screen with no authored profile is flat, which is what every existing
-- screen relies on.
exploration.loadMap(game, loader.getMapIndex(PRACA))
check(math.abs(lane.groundAt(game, 4) - game.townTraversal.groundZ) < 0.001,
    "a screen with no authored profile is flat at its groundZ")

-- An edge exit is the street continuing; a door is a thing you open. The HUD
-- tells them apart by exact position on a bound, and Market Row is the case
-- that rules out a radius test: the weaponsmith stands 0.86 from the east end
-- with a 0.9 radius, so any tolerant test would call a shop door an exit.
exploration.loadMap(game, loader.getMapIndex(18))
local market = game.townTraversal
local byAnchor = {}
for _, doorway in ipairs(market.doorways) do byAnchor[doorway.anchor] = doorway end
check(lane.isEdgeDoorway(game, byAnchor["west_quay"]),
    "Market Row continues into the Quay at its west end, silently")
check(not lane.isEdgeDoorway(game, byAnchor["smith_door"]),
    "the weaponsmith door is a door, not an edge exit")
-- A passage between the town's two levels is something the player chooses to
-- take, so it is authored just INSIDE the bound rather than on it. On the
-- bound it would be classified as the street continuing and announce nothing.
check(not lane.isEdgeDoorway(game, byAnchor["back_steps"]),
    "the stair up to the Backstreet announces itself rather than reading as the street continuing")

-- Shop arrivals are deliberately one interaction radius inside the exit.
-- Decimal 0.9 is not exactly representable, so equality at that boundary
-- needs the same tolerance as every other world-space comparison.
exploration.loadMap(game, loader.getMapIndex(27))
local arrivalExit = lane.interact(game)
check(arrivalExit and arrivalExit.instanceId == "st-maria-alicias_padaria-exit_door",
    "Up can reopen the shop exit from its arrival spawn")

-- The town mixes two ground conventions: the pre-rendered plate lanes stand at
-- groundZ -1.5 and the modelled rooms at 0.0. Market Row opens doors into both,
-- so a transit must re-derive height from the DESTINATION rather than carry the
-- departing lane's floor across, or the player arrives sunk or floating.
exploration.loadMap(game, loader.getMapIndex(18))
check(math.abs(game.townTraversal.groundZ - (-1.5)) < 0.001,
    "Market Row is a plate lane standing at -1.5")
local plateZ = game.townTraversal.z
exploration.loadMap(game, loader.getMapIndex(27), { arrival = "exit_door" })
check(math.abs(game.townTraversal.groundZ - 0.0) < 0.001,
    "arriving in the modelled bakery adopts its own 0.0 ground")
check(math.abs(game.townTraversal.z - 0.0) < 0.001,
    "and the player stands on that floor rather than 1.5m below it")
check(math.abs(plateZ - game.townTraversal.z) > 1.0,
    "the two conventions really do differ, so this transit is a real crossing")
exploration.loadMap(game, loader.getMapIndex(18), { arrival = "padaria_door" })
check(math.abs(game.townTraversal.z - (-1.5)) < 0.001,
    "and returning to the plate lane restores its floor")

-- Substituting real 3D for the plates must stay a data change, not a code
-- change. The seam is the presence of `preRendered` in the environment
-- package: with it, the flat path draws; without it, the same map falls
-- through to the ordinary 3D world path, which reads the same renderMesh and
-- the same authored camera and positions the actor from the same lane.
-- This asserts the half that is testable headlessly - that a lane is fully
-- functional with no pre-rendered block at all.
local flatEnv = require("engine.environment_package").load(
    "assets/environments/st_maria_town/quay/environment.json")
check(flatEnv.preRendered ~= nil, "the quay package is pre-rendered today")
check(flatEnv.renderMesh ~= nil and flatEnv.anchors ~= nil,
    "and it already carries the mesh and anchors a 3D scene would use")
local as3d = {}
for key, value in pairs(flatEnv) do as3d[key] = value end
as3d.preRendered = nil
local quayMap = loader.maps[loader.getMapIndex(19)]
lane.initialize(game, quayMap, as3d, nil)
check(lane.isActive(game), "a lane with no pre-rendered block still initialises")
local rx, ry, rz = lane.actorRoot(game)
check(rx == 7.8 and ry ~= nil and rz ~= nil,
    "and still publishes an actor root for the 3D path to billboard")
-- East, not west: the quay's west end is the water, and that it is a
-- genuine dead end is the point of the screen.
check(lane.edgeDoorway(game, -1) == nil,
    "the quay runs out at the water rather than looping somewhere")
check(lane.edgeDoorway(game, 1) ~= nil,
    "and its doorways still answer, because they are anchors rather than pixels")

-- The town loops. A player can leave the praca by the alley and arrive at
-- Market Row without ever walking back through the square, which is the whole
-- reason the backstreet exists; a regression that quietly dropped one of the
-- two new doors would still leave every screen reachable.
local function doorTargets(mapId)
    local map = loader.maps[loader.getMapIndex(mapId)]
    local targets = {}
    -- Following a door to where it actually goes means following the whole
    -- chain. The labyrinth door is the case that proves it: it is a
    -- CONDITIONAL_BRANCH whose accepted branch calls a common event, and the
    -- transfer lives in there. A scan of top-level commands reports the most
    -- important door in the town as leading nowhere.
    local seen = {}
    local walk
    walk = function(commands)
        for _, command in ipairs(commands or {}) do
            if command.cmd == "LOAD_MAP" then targets[command.mapId] = true end
            if command.cmd == "CALL_COMMON_EVENT" and command.commonEventId
                    and not seen[command.commonEventId] then
                seen[command.commonEventId] = true
                -- commonEvents.json is keyed by string id.
                local common = loader.commonEvents
                    and (loader.commonEvents[command.commonEventId]
                        or loader.commonEvents[tostring(command.commonEventId)])
                if common then walk(common.commands) end
            end
            walk(command.commands)
            walk(command.elseCommands)
            for _, choice in ipairs(command.choices or {}) do walk(choice.commands) end
        end
    end
    for _, event in ipairs(map.events or {}) do walk(event.commands) end
    return targets
end
check(doorTargets(17)[26], "the praca opens on to the backstreet")
check(doorTargets(26)[18], "the backstreet drops into market row")
check(doorTargets(26)[25], "the backstreet is how a player returns to the rented room")
check(doorTargets(17)[16], "the praca stair climbs to the churchyard")
check(doorTargets(16)[2], "the churchyard holds the way into the labyrinth")

-- Authored width is a design statement: the square is the widest place in the
-- town and a room is not a street. A regression that flattened every plate to
-- one width would still pass every other check in this file.
-- A town screen is presented one of two ways, and the package says which:
-- carrying a `preRendered` block means plates, and the absence of one means
-- viewport_3d renders real geometry. Both are first-class, so the corpus is
-- split here rather than assuming every screen is a plate -- which is what
-- this file assumed while every screen happened to be one.
local plateMaps, solidMaps = {}, {}
local widthOf = {}
for _, entry in ipairs(townMaps) do
    exploration.loadMap(game, entry.index)
    local environment = game.townTraversal.environment
    if environment.preRendered then
        plateMaps[#plateMaps + 1] = entry
        widthOf[entry.map.id] = environment.preRendered.imageSize[1]
    else
        solidMaps[#solidMaps + 1] = entry
    end
end

-- The baked-3D screens have to be checked for what they ARE, or dropping them
-- from the width rule above would just shrink the corpus silently.
check(#solidMaps >= 1,
    "at least one screen is presented as real geometry (" .. #solidMaps .. " found)")
for _, entry in ipairs(solidMaps) do
    exploration.loadMap(game, entry.index)
    local environment = game.townTraversal.environment
    check(type(environment.renderMesh) == "string" and environment.renderMesh ~= "",
        "map " .. entry.map.id .. " carries a render mesh instead of a plate")
    check(type(environment.textureAtlas) == "string" and environment.textureAtlas ~= "",
        "map " .. entry.map.id .. " carries a baked atlas")
    local minY, maxY = environment.bounds[2], environment.bounds[5]
    check(maxY - minY > 1,
        "map " .. entry.map.id .. " has a lane-length bounds span ("
            .. string.format("%.2f", maxY - minY) .. ")")
end
-- Width is authored per screen rather than shared, and a room is never a
-- street. Naming a specific ordering encoded one particular town shape and
-- went stale the moment the town was re-laid out; these two properties are
-- what the design actually asserts.
local exteriorWidths, roomWidths = {}, {}
for _, entry in ipairs(plateMaps) do
    local id = entry.map.id
    local isStreet = (id == 16 or id == 17 or id == 18 or id == 19 or id == 26)
    -- Two interiors are deliberately larger than a street, and both are
    -- architecturally long rather than accidentally wide: the Pub is the
    -- town's only two-level room -- low floor, a flight of steps, a raised
    -- bar -- and the Chapel is a nave with the altar at the far end. Naming
    -- the exceptions keeps the rule meaningful; widening it to swallow them
    -- would leave nothing being checked.
    local list = isStreet and exteriorWidths or roomWidths
    if id == 21 or id == 22 then list = nil end
    if list then list[#list + 1] = widthOf[id] end
end
local distinct, distinctCount = {}, 0
for _, width in ipairs(exteriorWidths) do distinct[width] = true end
for _ in pairs(distinct) do distinctCount = distinctCount + 1 end
check(distinctCount >= 3,
    "exterior widths are authored per screen rather than shared (" .. distinctCount .. " distinct)")
local narrowestExterior = math.huge
for _, width in ipairs(exteriorWidths) do narrowestExterior = math.min(narrowestExterior, width) end
local widestRoom = 0
for _, width in ipairs(roomWidths) do widestRoom = math.max(widestRoom, width) end
check(widestRoom < narrowestExterior,
    "every ordinary room is narrower than every street")
check(widthOf[21] > widestRoom and widthOf[22] > widestRoom,
    "the Pub and the Chapel are the long interiors, and every other room is smaller")

-- A blocked range must stop the walk even when ONE STEP is longer than the
-- range is wide. Testing only where a step lands lets a long step pass
-- straight through a narrow barrier, and the step length is not something an
-- author controls: it is speed times frame time, so a wall authored 0.3 wide
-- holds at 60fps and leaks the moment the machine hitches. The bug is
-- invisible in ordinary play and appears under load, which is the worst
-- combination to debug from a report.
local blockedMap = {
    id = 901,
    traversal = {
        provider = "bounded_lane",
        environmentPackage = "assets/environments/st_maria_town/pub/environment.json",
        spawnAnchor = "spawn_player",
        lane = { minY = 0, maxY = 10, depthX = 7.8, groundZ = -1.5, speed = 3.4 },
        blockedRanges = { { minY = 5.0, maxY = 5.3 } },
        camera = { distance = 21.1175, fovDegrees = 28.072486935852957,
            target = { x = 7.8, y = 5, z = 0 },
            projectionFrame = { baseViewportWidth = 256 },
            tracking = { center = 5, minOffsetX = 0, maxOffsetX = 0, pixelsPerWorld = 34.6 } },
        doorways = {},
    },
    events = {},
}
local blockedEnv = require("engine.environment_package").load(
    blockedMap.traversal.environmentPackage)
lane.initialize(game, blockedMap, blockedEnv, nil)
local blocked = game.townTraversal

-- One 1.7-unit step (0.5s at speed 3.4) clears the whole 0.3-unit barrier.
blocked.y = 4.0
lane.update(game, 0.5, 1)
check(blocked.y < 5.0,
    "a step longer than a blocked range does not tunnel through it")

-- Same hitch from the far side, because an overlap test that only looks one
-- way is half a test.
blocked.y = 6.0
lane.update(game, 0.5, -1)
check(blocked.y > 5.3,
    "a long step westward does not tunnel through a blocked range either")

-- Negative control: the barrier must not have simply frozen the lane. A step
-- that never reaches the range still moves the full distance.
blocked.y = 1.0
lane.update(game, 0.5, 1)
check(math.abs(blocked.y - 2.7) < 0.001,
    "a step clear of every blocked range still moves the authored distance")

-- And the ordinary short-step case still stops AT the barrier rather than
-- before it, so the fix did not cost the walk its reach.
blocked.y = 4.0
for _ = 1, 200 do lane.move(game, 1) end
check(blocked.y < 5.0 and blocked.y > 4.7,
    "many short steps walk up to the barrier and stop against it")

-- Report through fail_fast, which owns the run's exit code. Printing a
-- failure count and nothing else made this suite unable to fail the gate:
-- it went red twice while the runner still said ALL UNIT TESTS OK.
require("tests.fail_fast")("test_bounded_lane", failed, passed)
