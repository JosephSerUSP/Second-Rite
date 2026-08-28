-- The G5 UI backdrop is a frozen fixture, not a second copy of shipping
-- content. This suite guards the boundary that makes UI diffs attributable:
-- town edits must not move the camera, add gameplay, or change the material
-- photographed behind the windows.

local loader = require("engine.data.loader")
local cli = require("engine.cli_tools")

local passed, failed = 0, 0
local function check(label, fn)
    local ok, err = pcall(fn)
    if ok then
        passed = passed + 1
        print("  [PASS] " .. label)
    else
        failed = failed + 1
        print("  [FAIL] " .. label .. ": " .. tostring(err))
    end
end

print("[TEST] Starting frozen G5 backdrop tests...")

local backdropId = cli.GATE_BACKDROP_MAP_ID
local mapIndex = loader.getMapIndex(backdropId)
local map = mapIndex and loader.maps[mapIndex]

check("harness backdrop resolves to a map with its private tileset", function()
    assert(map, "the G5 harness needs its frozen backdrop map so UI frames do not depend on shipping map layout")
    assert(map.tileset == "_gate_room",
        "the G5 backdrop must pin _gate_room so a shipping tileset edit cannot recouple UI frames to authoring content")
end)

check("backdrop declares a complete floor spawn", function()
    assert(map, "cannot verify the authored G5 standpoint while the frozen backdrop map is missing")
    local spawn = map.spawn
    assert(type(spawn) == "table" and type(spawn.x) == "number"
        and type(spawn.y) == "number" and type(spawn.dir) == "string"
        and spawn.dir ~= "",
        "the G5 backdrop needs an authored x/y/dir spawn; deriving it from corridors lets layout edits teleport the camera")
    local row = map.layout and map.layout[spawn.y]
    assert(type(row) == "string" and row:sub(spawn.x, spawn.x) == ".",
        "the authored G5 spawn must remain on floor so the frozen standpoint cannot become invalid")
end)

for _, field in ipairs({ "events", "encounters", "recruits", "treasures" }) do
    check("backdrop has no " .. field, function()
        assert(map, "the G5 backdrop must exist before its fixture-only fields can be checked")
        assert(type(map[field]) == "table" and #map[field] == 0,
            "the G5 backdrop is a fixture, so it must not carry " .. field
                .. "; gameplay there would make UI captures depend on content")
    end)
end

local tileset = loader.getTileset("_gate_room")
local function checkFrozenAsset(field)
    check("_gate_room " .. field .. " stays under the frozen asset directory", function()
        assert(tileset, "the G5 backdrop needs its private tileset definition")
        local path = tileset[field]
        assert(type(path) == "string" and path:sub(1, #"assets/tilesets/_gate/")
            == "assets/tilesets/_gate/",
            "_gate_room " .. field
                .. " must stay under assets/tilesets/_gate/ so shared material edits cannot alter G5")
        local info = love.filesystem.getInfo(path)
        assert(info and info.type == "file",
            "_gate_room " .. field .. " points at a missing frozen G5 asset: " .. tostring(path))
    end)
end
checkFrozenAsset("texture")
checkFrozenAsset("heightMap")

for _, field in ipairs({ "features", "fixturePrefabs" }) do
    check("_gate_room has no probabilistic " .. field, function()
        assert(tileset, "the G5 backdrop needs its private tileset definition")
        assert(type(tileset[field]) == "table" and #tileset[field] == 0,
            "the G5 backdrop must not inject " .. field
                .. "; randomness would make identical UI captures unstable")
    end)
end

print("=== Frozen G5 Backdrop Tests: " .. passed .. " passed, " .. failed .. " failed ===")
assert(failed == 0, "frozen G5 backdrop tests had failures")
