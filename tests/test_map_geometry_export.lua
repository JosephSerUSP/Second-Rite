local exporter = require("presentation.map_geometry_export")
local renderable = require("presentation.map_renderable_bundle")

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

local bundle = {
    version = renderable.VERSION,
    map = { id = 7, name = "Round Trip" },
    quality = { preset = "HIGH", density = 1.0 },
    materials = {
        { id = "material_001", color = { 1, 1, 1, 1 },
          albedo = { kind = "project-asset", path = "assets/tilesets/test.png" } },
    },
    surfaces = {
        {
            id = "test_group", name = "test group", material = "material_001",
            source = { kind = "cell", x = 0, y = 0, surface = "floor" },
            positions = { 0, 0, 0, 1, 0, 0, 0, 1, 0 },
            uvs = { 0, 0, 1, 0, 0, 1 },
            normals = { 0, 0, 1, 0, 0, 1, 0, 0, 1 },
            colors = { 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1 },
        },
    },
}
check(renderable.validate(bundle), "neutral renderable bundle accepts aligned triangle streams")

local invalid = {
    version = renderable.VERSION,
    materials = {},
    surfaces = {
        { id = "bad", source = { kind = "cell" }, positions = { 0, 0, 0 },
          uvs = {}, normals = {}, colors = {} },
    },
}
local validBad = pcall(renderable.validate, invalid)
check(not validBad, "bundle validation fails loudly on mismatched attribute streams")

local first, stats = exporter.serialize(bundle)
local second = exporter.serialize(bundle)

check(first == second, "serialization is deterministic")
check(stats.vertexCount == 3 and stats.triangleCount == 1 and stats.groupCount == 1,
    "serialization reports exact geometry counts")
check(first:find("g test_group", 1, true) ~= nil, "OBJ group names are sanitized deterministically")
check(first:find("vt 0.000000000 1.000000000", 1, true) ~= nil,
    "OBJ V coordinates are inverted for import round-tripping")
check(first:find("f 1/1/1 2/2/2 3/3/3", 1, true) ~= nil,
    "serialized triangles use aligned position, UV, and normal indices")
check(first:find("materials come from the authoritative renderable bundle", 1, true) ~= nil,
    "OBJ serialization declares the bundle as its material/geometry authority")

print(string.format("map geometry export tests: %d passed, %d failed", passed, failed))
if failed > 0 then error("test_map_geometry_export failed", 0) end
