-- Headless characterization of the current Map Instance boundaries.
--
-- This suite deliberately adds no Map fields or lifecycle hooks. It drives the
-- existing exploration, Scene, savegame, and input seams and records the facts
-- future Map Event Program hosts must not infer from one another.
package.path = package.path .. ";./?.lua;./engine/?.lua"

local loader = require("data.loader")
local sessionModule = require("engine.session")
local exploration = require("engine.exploration")
local sceneHost = require("engine.scene_host")
local savegame = require("engine.savegame")
local flow = require("engine.flow")

loader.init()

local passed, failed = 0, 0
local function check(condition, message)
    if condition then
        passed = passed + 1
        print("  [PASS] " .. message)
    else
        failed = failed + 1
        print("  [FAIL] " .. message)
    end
end

local function newSession()
    local s = sessionModule.GameSession.new(loader)
    s:initializeStartingParty()
    return s
end

local function context(s)
    return { session = s, loader = loader, party = s.party }
end

local function sameSequence(actual, expected)
    if #actual ~= #expected then return false end
    for i, value in ipairs(expected) do
        if actual[i] ~= value then return false end
    end
    return true
end

print("[TEST] Starting Map Instance lifecycle characterization...")

-- Fixture A: Scene displacement does not leave or recreate the playable Map.
do
    local s = newSession()
    exploration.loadMap(s, 1)
    local mapData, grid, mapIndex = s.currentMapData, s.mapGrid, s.currentMapIndex
    local ctx = context(s)

    sceneHost.init("map", ctx)
    check(sceneHost.getCurrent() == "map", "Map Scene is initially current")

    sceneHost.goto_scene("dialogue", ctx)
    check(sceneHost.getCurrent() == "dialogue"
            and s.currentMapData == mapData and s.mapGrid == grid
            and s.currentMapIndex == mapIndex,
        "Dialogue displacement leaves the same Map Instance current and resident")

    sceneHost.goto_scene("map", ctx)
    check(sceneHost.getCurrent() == "map"
            and s.currentMapData == mapData and s.mapGrid == grid,
        "closing Dialogue returns to the same Map Instance")

    sceneHost.goto_scene("battle", ctx)
    check(sceneHost.getCurrent() == "battle"
            and s.currentMapData == mapData and s.mapGrid == grid
            and s.currentMapIndex == mapIndex,
        "Battle displacement leaves the same Map Instance current and resident")

    -- This is the same real Scene transition used by battle resolution paths.
    sceneHost.goto_scene("map", ctx)
    check(sceneHost.getCurrent() == "map"
            and s.currentMapData == mapData and s.mapGrid == grid,
        "Battle Scene completion returns to the same Map Instance")

    sceneHost.init(nil)
end

-- Fixture B: loadMap is the current Map replacement authority. The old
-- dangerous instance is cached before currentMapIndex/currentMapData switch.
do
    local s = newSession()
    exploration.loadMap(s, 2, { seed = 1735689608 })
    local mapAData, mapAGrid = s.currentMapData, s.mapGrid
    local departureX, departureY = s.playerX, s.playerY

    exploration.loadMap(s, 3, { seed = 1735689609 })
    check(s.currentMapIndex == 3 and s.currentMapData ~= mapAData
            and s.mapGrid ~= mapAGrid,
        "transfer makes Map B the authoritative current Map")
    check(s.mapStates[2] ~= nil and s.mapStates[2].mapGrid == mapAGrid
            and s.mapStates[2].playerX == departureX
            and s.mapStates[2].playerY == departureY,
        "transfer caches Map A's dangerous runtime state before replacement")
    check(s.currentMapIndex == 3 and s.currentMapData.id == 3
            and s.currentMapData ~= loader.maps[3],
        "Map B activation completes with a resolved runtime Map copy")

    exploration.loadMap(s, 2, { arrival = "resume" })
    check(s.currentMapIndex == 2 and s.currentMapData ~= mapAData
            and s.mapGrid == mapAGrid
            and s.playerX == departureX and s.playerY == departureY,
        "resume transfer restores Map A's cached grid and arrival position")
end

-- Fixture C: generated creation and cached revisit are distinguished today by
-- the presence of session.mapStates[mapIndex], not by an instance identity.
do
    local s = newSession()
    exploration.loadMap(s, 2, { seed = 1735689608 })
    local firstGrid = s.mapGrid
    local firstEvents = s.currentMapData.events
    local firstFeatures = s.generatedFeatures
    check(s.mapStates[2] == nil,
        "first generated load has no cached Map Instance record yet")

    exploration.loadMap(s, 3, { seed = 1735689609 })
    check(s.mapStates[2] ~= nil and s.mapStates[2].mapGrid == firstGrid
            and s.mapStates[2].events == firstEvents
            and s.mapStates[2].generatedFeatures == firstFeatures,
        "leaving the generated Map creates the current cache record")

    exploration.loadMap(s, 2, { arrival = "resume" })
    check(s.mapGrid == firstGrid and s.currentMapData.events == firstEvents
            and s.generatedFeatures == firstFeatures,
        "cached return restores the generated runtime collections by reference")
    check(s.currentMapData.instanceId == nil and s.mapStates[2].instanceId == nil,
        "no explicit Map Instance identity field distinguishes creation from revisit")
end

-- Fixture D: save restoration creates a new GameSession and restores Map data
-- directly; it does not call ordinary exploration.loadMap activation.
do
    local source = newSession()
    exploration.loadMap(source, 2, { seed = 1735689608 })
    exploration.loadMap(source, 3, { seed = 1735689609 })
    local slot = "map_instance_lifecycle_characterization"
    local oldLoadMap = exploration.loadMap
    local saveOk = pcall(savegame.save, source, loader, "map", slot)
    local raw = savegame.load(slot, loader)
    local restored
    local restoreOk

    exploration.loadMap = function()
        error("save restore unexpectedly called exploration.loadMap")
    end
    if raw then
        restoreOk, restored = pcall(savegame.deserialize, raw, loader)
    else
        restoreOk = false
    end
    exploration.loadMap = oldLoadMap
    savegame.delete(slot)

    check(saveOk and raw and raw.scene == "map",
        "a standing-on-Map save records the resumable Map scene and state")
    check(restoreOk and restored and restored ~= source
            and restored.currentMapIndex == source.currentMapIndex
            and restored.playerX == source.playerX
            and restored.playerY == source.playerY,
        "save restore builds a new runtime host around restored Map state")
    check(restoreOk and restored and restored.currentMapData ~= source.currentMapData
            and restored.mapStates[2] ~= nil,
        "save restore reconstructs authored Map data and resident cache data without loadMap")
end

-- Fixture E: drive the real love.keypressed path. The flow wrapper is an
-- observation seam, while the step Event uses the real interpreter command.
-- A press is now an honest device edge: every independent probe releases the
-- physical key before the next press instead of relying on OS-repeat behavior.
do
    local s = newSession()
    exploration.loadMap(s, 2, { seed = 1735689608 })
    s.currentMapData.events = {}

    local function findCell(predicate)
        for y, row in ipairs(s.mapGrid) do
            for x, tile in ipairs(row) do
                if tile ~= "#" and predicate(x, y, row) then return x, y end
            end
        end
    end

    local blockedX, blockedY = findCell(function(x, y)
        return not (s.mapGrid[y - 1] and s.mapGrid[y - 1][x]
            and s.mapGrid[y - 1][x] ~= "#")
    end)
    local stepX, stepY = findCell(function(x, y, row)
        return row[x + 1] and row[x + 1] ~= "#"
    end)
    local oldActiveSession = _G.activeSession
    local oldRun = flow.run
    local calls = {}
    flow.run = function(phase, ctx)
        calls[#calls + 1] = phase
        if phase == "battle.encounter_check" then
            return { { type = "characterization_probe" } }
        end
        return oldRun(phase, ctx)
    end

    _G.activeSession = s
    local ctx = context(s)
    sceneHost.init("map", ctx)

    local function pressAndRelease(key)
        love.keypressed(key)
        love.keyreleased(key)
    end

    s.playerX, s.playerY, s.playerDir = blockedX, blockedY, "N"
    s.transitionTimer, s.bumpCooldowns = 0, {}
    calls = {}
    pressAndRelease("up")
    check(s.playerX == blockedX and s.playerY == blockedY and #calls == 0,
        "blocked movement commits no coordinate and runs no step or encounter phase")

    s.playerX, s.playerY, s.playerDir = stepX, stepY, "E"
    s.transitionTimer, s.bumpCooldowns = 0, {}
    calls = {}
    pressAndRelease("up")
    check(s.playerX == stepX + 1 and s.playerY == stepY
            and sameSequence(calls, { "exploration.step", "battle.encounter_check" }),
        "successful movement commits coordinates, then runs step Flow, then encounter check")

    s.playerX, s.playerY, s.playerDir = stepX, stepY, "E"
    s.transitionTimer, s.bumpCooldowns = 0, {}
    s.flags.step_event_probe = nil
    s.currentMapData.events = {
        {
            id = "step_event_probe",
            x = stepX,
            y = stepY - 1,
            trigger = "step",
            commands = {
                { cmd = "SET_FLAG", flag = "step_event_probe", value = true },
            },
        },
    }
    calls = {}
    pressAndRelease("up")
    check(s.playerX == stepX + 1 and s.playerY == stepY
            and s.flags.step_event_probe == true
            and sameSequence(calls, { "exploration.step" }),
        "a committed step Event runs after the step Flow and suppresses encounter processing")

    flow.run = oldRun
    sceneHost.init(nil)
    _G.activeSession = oldActiveSession
end

print(string.format("=== Map Instance Lifecycle: %d passed, %d failed ===", passed, failed))
if failed > 0 then
    require("tests.fail_fast")("Map Instance lifecycle characterization failed", failed)
end
