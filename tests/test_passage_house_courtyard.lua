-- Shipping Passage House transfers/profile through the actual runtime unit harness.
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
load(1001, "door-passage-house")
local entryY, entryZ = game.townTraversal.y, game.townTraversal.z
useDoor("core-run-court-door-passage-house")
check(game.currentMapData.id == 34, "Cortico enters the Passage House stair hall")
useDoor("st-maria-passage-hall-exit_door")
check(game.currentMapData.id == 1001 and math.abs(game.townTraversal.y-entryY)<1e-6
    and math.abs(game.townTraversal.z-entryZ)<1e-6, "return preserves physical doorstep and elevation")
local state = game.townTraversal
state.y = state.minY
for _, direction in ipairs({1,-1}) do
    local previousZ = lane.groundAt(game, state.y)
    for _ = 1, 1200 do
        lane.update(game, 1/60, direction)
        check(math.abs(state.z-lane.groundAt(game,state.y))<1e-6, "walking feet follow graded court")
        check(direction*(state.z-previousZ)>=-1e-6, "continuous monotone grade")
        previousZ=state.z
    end
    check(math.abs(state.y-(direction>0 and state.maxY or state.minY))<1e-6, "whole court remains traversable")
end
load(25,nil)
check(game.currentMapData.id==25,"introduction can still arrive directly in lodging")
require("tests.fail_fast")("passage_house_courtyard",failed,passed)
