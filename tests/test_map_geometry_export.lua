local exporter = require("presentation.map_geometry_export")

local passed, failed = 0, 0
local function check(condition, message)
    if condition then
        passed = passed + 1
    else
        failed = failed + 1
        print("FAIL: " .. message)
    end
end

local ox, oy, oz = exporter.worldToObj(2, 3, 4)
check(ox == 2 and oy == 4 and oz == -3,
    "world coordinates use the inverse of the runtime OBJ import transform")

local nx, ny, nz = exporter.normalToObj(-1, 0.5, 0.25)
check(nx == -1 and ny == 0.25 and nz == -0.5,
    "normal coordinates use the same axis transform")

local groups = {
    {
        name = "test group",
        vertices = {
            { x = 0, y = 0, z = 0, u = 0, v = 0, nx = 0, ny = 0, nz = 1 },
            { x = 1, y = 0, z = 0, u = 1, v = 0, nx = 0, ny = 0, nz = 1 },
            { x = 0, y = 1, z = 0, u = 0, v = 1, nx = 0, ny = 0, nz = 1 },
        },
    },
}
local metadata = { mapId = 7, mapName = "Round Trip", quality = "HIGH", density = "1.00" }
local first, stats = exporter.serialize(groups, metadata)
local second = exporter.serialize(groups, metadata)

check(first == second, "serialization is deterministic")
check(stats.vertexCount == 3 and stats.triangleCount == 1 and stats.groupCount == 1,
    "serialization reports exact geometry counts")
check(first:find("g test_group", 1, true) ~= nil, "OBJ group names are sanitized deterministically")
check(first:find("vt 0.000000000 1.000000000", 1, true) ~= nil,
    "OBJ V coordinates are inverted for import round-tripping")
check(first:find("f 1/1/1 2/2/2 3/3/3", 1, true) ~= nil,
    "serialized triangles use aligned position, UV, and normal indices")

print(string.format("map geometry export tests: %d passed, %d failed", passed, failed))
if failed > 0 then error("test_map_geometry_export failed", 0) end
