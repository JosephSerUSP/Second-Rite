package.path = package.path .. ";./?.lua;./engine/?.lua"

local json = require("engine.data.json")
local loader = require("engine.data.loader")
local mapInspection = require("engine.map_inspection")
local savegame = require("engine.savegame")
local sessionModule = require("engine.session")

loader.init()

local function deepEqual(a, b)
    if type(a) ~= type(b) then return false end
    if type(a) ~= "table" then return a == b end
    for key, value in pairs(a) do
        if not deepEqual(value, b[key]) then return false end
    end
    for key in pairs(b) do
        if a[key] == nil then return false end
    end
    return true
end

local source = loader.maps[2]
local snapshot = json.decode(json.encode(source))
local before = json.encode(source)
local runtimeSession = sessionModule.GameSession.new(loader)
local runtimeSaveBefore = savegame.serialize(runtimeSession, loader, "map")
runtimeSaveBefore.savedAt = nil
local activeSessionBefore = sessionModule.activeSession
local runtimeMapBefore = runtimeSession.currentMapData
local runtimeGridBefore = runtimeSession.mapGrid
local first = mapInspection.resolve(loader, 2, snapshot, 424242)
local second = mapInspection.resolve(loader, 2, json.decode(json.encode(source)), 424242)
local changed = mapInspection.resolve(loader, 2, json.decode(json.encode(source)), 424243)
local modifiedSnapshot = json.decode(json.encode(source))
modifiedSnapshot.width = source.width + 1
local modified = mapInspection.resolve(loader, 2, modifiedSnapshot, 424242)

assert(first.kind == "generated-map-inspection", "inspection identifies its semantic payload")
assert(first.request.transient and first.request.previewInstance
        and first.request.saveMutation == false and first.request.seed == 424242,
    "inspection is an isolated preview instance with an explicit seed")
assert(first.scope.id == "map:2:generated"
        and first.scope.kind == "current-single-generated-scope",
    "inspection uses a provisional current-scope identity without an Area schema")
assert(#first.generated.rooms > 0 and #first.generated.corridors > 0,
    "inspection reports rooms and the exact corridor links produced by generation")
assert(#first.generated.zones > 0 and first.generated.entrance.x ~= nil
        and first.generated.exit.x ~= nil,
    "inspection reports generated zone tags and both staircase landmarks")
assert(first.resolved.tileset.resolvedId ~= nil,
    "inspection reports the real resolved tileset identity")
assert(deepEqual(first.generated, second.generated),
    "the same Map snapshot and seed resolve to identical generated facts")
assert(deepEqual(first, second),
    "the complete semantic preview payload is stable for the same seed")
assert(not deepEqual(first.generated, changed.generated),
    "a reseed intentionally changes the generated result")
assert(modified.map.width == source.width + 1
        and #modified.generated.grid[1] == source.width + 1
        and not deepEqual(first.generated, modified.generated),
    "the same seed resolves the current unsaved Map snapshot, including a transient dimension change")
assert(json.encode(source) == before,
    "transient inspection does not mutate the authored loader Map")
assert(loader.maps[2] == source and loader.mapsById["2"] == 2
        and json.encode(loader.maps[2]) == before,
    "the canonical loader Map and its id index remain unchanged after transient inspection")
local runtimeSaveAfter = savegame.serialize(runtimeSession, loader, "map")
runtimeSaveAfter.savedAt = nil
assert(json.encode(runtimeSaveBefore) == json.encode(runtimeSaveAfter)
        and runtimeSession.currentMapData == runtimeMapBefore
        and runtimeSession.mapGrid == runtimeGridBefore
        and sessionModule.activeSession == activeSessionBefore,
    "inspection does not mutate gameplay runtime or serialized save state")

print("test_map_inspection: OK")
