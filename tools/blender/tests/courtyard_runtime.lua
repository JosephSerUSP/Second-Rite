-- Runs only in a candidate stage, through the actual runtime unit harness.
local loader = require("engine.data.loader")
local session = require("engine.session")
local exploration = require("engine.exploration")
local lane = require("engine.bounded_lane")
local interpreter = require("engine.interpreter")
local game = session.GameSession.new(loader)
game:initializeStartingParty()
local passed, failed = 0, 0
local function check(condition, label)
    if condition then passed = passed + 1 else failed = failed + 1; print("COURTYARD FAIL: " .. label) end
end
local function load(id, arrival)
    exploration.loadMap(game, loader.getMapIndex(id), {arrival = arrival})
end
local function useDoor(instance)
    local doorway = lane.nearDoorway(game)
    local event = lane.eventFor(game, doorway)
    check(event and event.instanceId == instance, "actual nearest doorway is " .. instance)
    interpreter.runImmediate(event.commands, {session = game, loader = loader})
end
load(26, "lodging_door")
local entryY, entryZ = game.townTraversal.y, game.townTraversal.z
useDoor("st-maria-cortico-lodging_door")
check(game.currentMapData.id == 32, "Cortico enters candidate court")
check(math.abs(game.townTraversal.y - 0.5) < 1e-6 and game.townTraversal.z == 0, "entry lands on lower landing")
for _, direction in ipairs({1,-1}) do
    local previousZ = game.townTraversal.z
    for _ = 1, 240 do
        lane.update(game, 1/60, direction)
        local state = game.townTraversal
        check(math.abs(state.z - lane.groundAt(game, state.y)) < 1e-6, "walk feet follow profile")
        check(direction * (state.z - previousZ) >= -1e-6, "continuous monotone climb/descent")
        previousZ = state.z
    end
    check(math.abs(game.townTraversal.z - (direction > 0 and 0.3 or 0)) < 1e-6, "slope endpoint")
end
load(32,"lodging_entry")
check(math.abs(game.townTraversal.z-0.3)<1e-6,"upper doorway arrival")
useDoor("st-maria-passage-court-lodging_entry")
check(game.currentMapData.id==25,"upper doorway reaches lodging")
useDoor("st-maria-lodging-exit_door")
check(game.currentMapData.id==32 and math.abs(game.townTraversal.y-11.5)<1e-6,"lodging returns to upper landing")
load(32,"cortico_entry")
useDoor("st-maria-passage-court-cortico_entry")
check(game.currentMapData.id==26 and math.abs(game.townTraversal.y-entryY)<1e-6
    and math.abs(game.townTraversal.z-entryZ)<1e-6,"return preserves Cortico doorway position and elevation")
load(25,nil)
check(game.currentMapData.id==25,"introduction can still arrive directly in lodging")
require("tests.fail_fast")("courtyard_candidate",failed,passed)
