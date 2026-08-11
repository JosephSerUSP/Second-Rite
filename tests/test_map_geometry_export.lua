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

local function countOccurrences(text, needle)
    local count = 0
    local start = 1
    while true do
        local at = text:find(needle, start, true)
        if not at then return count end
        count = count + 1
        start = at + #needle
    end
end

local function triangleSurface(id, name, material, offset)
    offset = offset or 0
    return {
        id = id, name = name, material = material,
        source = { kind = "cell", x = offset, y = 0, surface = "floor" },
        positions = { offset, 0, 0, offset + 1, 0, 0, offset, 1, 0 },
        uvs = { 0, 0, 1, 0, 0, 1 },
        normals = { 0, 0, 1, 0, 0, 1, 0, 0, 1 },
        colors = { 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1 },
    }
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
        triangleSurface("test_group", "test group", "material_001", 0),
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

local first, stats = exporter.serialize(bundle, { materialLibrary = "round-trip.mtl" })
local second = exporter.serialize(bundle, { materialLibrary = "round-trip.mtl" })

check(first == second, "serialization is deterministic")
check(stats.vertexCount == 3 and stats.triangleCount == 1 and stats.groupCount == 1,
    "serialization reports exact geometry counts")
check(first:find("g test_group", 1, true) ~= nil, "OBJ group names are sanitized deterministically")
check(first:find("vt 0.000000000 1.000000000", 1, true) ~= nil,
    "OBJ V coordinates are inverted for import round-tripping")
check(first:find("f 1/1/1 2/2/2 3/3/3", 1, true) ~= nil,
    "serialized triangles use aligned position, UV, and normal indices")
check(first:find("authoritative renderable bundle", 1, true) ~= nil,
    "OBJ serialization declares the bundle as its material/geometry authority")
check(first:find("mtllib round-trip.mtl", 1, true) ~= nil,
    "OBJ references its sibling material library")
check(first:find("usemtl material_001", 1, true) ~= nil,
    "OBJ binds each surface to the bundle material identity")

local materialFixture = {
    version = renderable.VERSION,
    map = { id = 8, name = "Materials" },
    quality = { preset = "HIGH", density = 1.0 },
    materials = {
        { id = "material_001", color = { 0.25, 0.5, 0.75, 0.4 },
          albedo = { kind = "project-asset", path = "assets/tilesets/a.png" },
          emission = { kind = "project-asset", path = "assets/tilesets/a_glow.png" } },
        { id = "material_002", color = { 1, 0.5, 0.25, 1 },
          albedo = { kind = "embedded-png", base64 = "fixture" } },
        { id = "material_003" },
    },
    surfaces = {
        triangleSurface("first", "first", "material_001", 0),
        triangleSurface("second", "second", "material_002", 2),
        triangleSurface("third", "third", "material_001", 4),
    },
}
check(renderable.validate(materialFixture),
    "multi-material fixture satisfies the neutral renderable contract")

local mtl, materialStats = exporter.serializeMaterials(materialFixture, {
    textureFiles = {
        material_001 = "materials-material_001.png",
        material_002 = "materials-material_002.png",
    },
})
local mtlAgain = exporter.serializeMaterials(materialFixture, {
    textureFiles = {
        material_001 = "materials-material_001.png",
        material_002 = "materials-material_002.png",
    },
})
check(mtl == mtlAgain, "MTL serialization is deterministic")
check(materialStats.materialCount == 3 and countOccurrences(mtl, "newmtl ") == 3,
    "MTL emits exactly one entry per distinct bundle material")
local m1 = mtl:find("newmtl material_001", 1, true)
local m2 = mtl:find("newmtl material_002", 1, true)
local m3 = mtl:find("newmtl material_003", 1, true)
check(m1 and m2 and m3 and m1 < m2 and m2 < m3,
    "MTL preserves authoritative material ordering")
check(mtl:find("Kd 0.250000000 0.500000000 0.750000000", 1, true) ~= nil
        and mtl:find("d 0.400000000", 1, true) ~= nil,
    "MTL maps bundle color and alpha to diffuse/opacity fields")
check(mtl:find("map_Kd materials-material_001.png", 1, true) ~= nil
        and mtl:find("map_Kd materials-material_002.png", 1, true) ~= nil,
    "MTL references exported albedo textures with relative paths")
check(mtl:find("emission/glow textures are not exported", 1, true) ~= nil
        and mtl:find("emission/glow payload present but intentionally not serialized", 1, true) ~= nil,
    "MTL states the deliberate glow/emission limitation")
check(mtl:find("newmtl material_003\nKd 1.000000000 1.000000000 1.000000000\nd 1.000000000", 1, true) ~= nil,
    "materials without color or albedo serialize to an explicit opaque-white default")

local materialObj, materialObjStats = exporter.serialize(materialFixture, {
    materialLibrary = "materials.mtl",
})
check(materialObjStats.vertexCount == 9 and materialObjStats.triangleCount == 3
        and materialObjStats.groupCount == 3 and materialObjStats.materialCount == 3,
    "material directives do not change geometry counts")
check(countOccurrences(materialObj, "usemtl material_001") == 2
        and countOccurrences(materialObj, "usemtl material_002") == 1,
    "shared materials are reused across multiple surface boundaries")
local firstGroup = materialObj:find("g first\ns off\nusemtl material_001", 1, true)
local secondGroup = materialObj:find("g second\ns off\nusemtl material_002", 1, true)
local thirdGroup = materialObj:find("g third\ns off\nusemtl material_001", 1, true)
check(firstGroup and secondGroup and thirdGroup and firstGroup < secondGroup and secondGroup < thirdGroup,
    "surface grouping and material binding preserve bundle order")

-- Integration gate: exercise the collector against a real loaded dungeon, not
-- only a hand-built transport fixture. dungeon_default carries a real tileset
-- height map, so a floor emitted with more than two triangles proves this path
-- reached the engine-owned displaced-surface compiler rather than a flat
-- exporter approximation.
local Session = require("engine.session")
local exploration = require("engine.exploration")
local viewport_3d = require("presentation.viewport_3d")
local loader = require("data.loader")
local runtimeSession = Session.GameSession.new(loader)
runtimeSession:initializeStartingParty()
local originalTime = os.time
os.time = function() return 1735689600 end
local loaded, loadErr = pcall(exploration.loadMap, runtimeSession, 2, { seed = 1735689602 })
os.time = originalTime
if not loaded then error(loadErr, 0) end
viewport_3d.init()
local actual, collectErr = renderable.collect(runtimeSession)
check(actual ~= nil, "real loaded map produces an authoritative renderable bundle: " .. tostring(collectErr))
if actual then
    check(renderable.validate(actual), "real loaded map bundle satisfies the transport contract")
    check(actual.stats and actual.stats.vertexCount > 0 and actual.stats.triangleCount > 0,
        "real loaded map bundle contains compiled world triangles")

    local hasCellProvenance = false
    local hasCompiledFloor = false
    for _, surface in ipairs(actual.surfaces or {}) do
        if surface.source and surface.source.kind == "cell"
                and surface.source.x ~= nil and surface.source.runtimeX ~= nil then
            hasCellProvenance = true
        end
        if surface.source and surface.source.surface == "floor"
                and #(surface.positions or {}) > 18 then
            hasCompiledFloor = true
        end
    end
    check(hasCellProvenance,
        "real surfaces preserve authored and runtime cell provenance")
    check(hasCompiledFloor,
        "dungeon_default floor uses compiled height-field geometry rather than a flat quad")

    local hasProjectMaterial = false
    for _, material in ipairs(actual.materials or {}) do
        if material.albedo and material.albedo.kind == "project-asset"
                and material.albedo.path == "assets/tilesets/dungeon_001.png" then
            hasProjectMaterial = true
            break
        end
    end
    check(hasProjectMaterial,
        "real bundle preserves the authoritative tileset texture as a project material reference")

    local actualObj, actualStats = exporter.serialize(actual, { materialLibrary = "actual.mtl" })
    check(actualObj:find("mtllib actual.mtl", 1, true) ~= nil
            and actualObj:find("usemtl ", 1, true) ~= nil,
        "real collected geometry serializes material bindings without a second collection path")
    check(actualStats.vertexCount == actual.stats.vertexCount
            and actualStats.triangleCount == actual.stats.triangleCount,
        "real material serialization preserves authoritative geometry counts")
end

print(string.format("map geometry export tests: %d passed, %d failed", passed, failed))
if failed > 0 then error("test_map_geometry_export failed", 0) end
