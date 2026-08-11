local exporter = require("presentation.map_geometry_export")
local renderable = require("presentation.map_renderable_bundle")
local visibility = require("engine.geometry.visibility_profile")

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
    geometryProfile = "play",
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

local playProfile = visibility.resolve("play")
local authoringProfile = visibility.resolve("authoring")
check(playProfile.wallTopCaps == false and playProfile.walkableCeilings == true
        and playProfile.exteriorWallFaces == false,
    "play profile formalizes the existing gameplay-camera surface policy")
check(authoringProfile.wallTopCaps == true and authoringProfile.walkableCeilings == false
        and authoringProfile.exteriorWallFaces == true,
    "authoring profile exposes outside-in/top-down structural surfaces")

local syntheticGrid = {
    { "#", "#", "#" },
    { "#", ".", "#" },
    { "#", "o", "#" },
}
local openingVisible = visibility.wallSideDecision("play", syntheticGrid, 2, 3)
local sealedVisible, sealedReason = visibility.wallSideDecision("play", syntheticGrid, 1, 1)
local exteriorPlay, exteriorPlayReason = visibility.wallSideDecision("play", syntheticGrid, 0, 2)
local exteriorAuthoring = visibility.wallSideDecision("authoring", syntheticGrid, 0, 2)
check(openingVisible == true,
    "openings/non-solid neighbours prevent incorrect structural face elimination")
check(sealedVisible == false and sealedReason == "sealed-solid",
    "sealed wall-to-wall faces remain structurally omitted")
check(exteriorPlay == false and exteriorPlayReason == "exterior-culled"
        and exteriorAuthoring == true,
    "map-exterior wall faces differ explicitly between play and authoring")
check(visibility.walkableCeilingVisible("play", "roof") == true
        and visibility.walkableCeilingVisible("authoring", "roof") == false
        and visibility.walkableCeilingVisible("play", "sky") == false,
    "walkable ceiling policy is profile-specific and still respects sky maps")
check(visibility.wallTopVisible("play") == false
        and visibility.wallTopVisible("authoring") == true,
    "wall top-cap policy is profile-specific")
check(not pcall(visibility.resolve, "threejsHack"),
    "unknown geometry visibility profiles fail loudly")

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
local authoredProfileBefore = runtimeSession.currentMapData.geometryProfile
local actual, collectErr = renderable.collect(runtimeSession, "play")
local authoring, authoringErr = renderable.collect(runtimeSession, "authoring")
check(actual ~= nil, "real loaded map produces an authoritative renderable bundle: " .. tostring(collectErr))
check(authoring ~= nil, "real loaded map produces an authoring renderable bundle: " .. tostring(authoringErr))
if actual then
    check(renderable.validate(actual), "real loaded map bundle satisfies the transport contract")
    check(actual.geometryProfile == "play",
        "game/runtime bundle declares the play visibility profile")
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
end

if actual and authoring then
    check(renderable.validate(authoring),
        "authoring bundle satisfies the same authoritative transport contract")
    check(authoring.geometryProfile == "authoring",
        "editor-facing bundle declares the authoring visibility profile")
    local playRoles = actual.stats.bySurfaceRole or {}
    local authoringRoles = authoring.stats.bySurfaceRole or {}
    check((playRoles.ceiling and playRoles.ceiling.surfaceCount or 0) > 0,
        "roofed walkable cells retain gameplay ceilings in play")
    check((authoringRoles.ceiling and authoringRoles.ceiling.surfaceCount or 0) == 0,
        "authoring omits walkable-cell ceilings that obscure the map from above")
    check((playRoles["wall-top"] and playRoles["wall-top"].surfaceCount or 0) == 0,
        "play does not add wall top caps")
    check((authoringRoles["wall-top"] and authoringRoles["wall-top"].surfaceCount or 0) > 0,
        "authoring adds readable wall top caps")
    local playVisibility = actual.stats.visibility or {}
    local authoringVisibility = authoring.stats.visibility or {}
    check((playVisibility.culledExteriorFaces or 0) > 0
            and (authoringVisibility.culledExteriorFaces or 0) == 0
            and (authoringVisibility.emittedFaces or 0) > (playVisibility.emittedFaces or 0),
        "authoring retains exterior wall faces that play safely omits")
    check((playVisibility.culledSealedFaces or 0) > 0,
        "resolved structure reports the pre-existing sealed wall-to-wall culling")
    check(runtimeSession.currentMapData.geometryProfile == authoredProfileBefore,
        "profile selection never writes consumer policy into authored map data")
end

local function printMeasurement(mapId)
    local mapIndex
    for index, map in ipairs(loader.maps or {}) do
        if tostring(map.id) == tostring(mapId) then mapIndex = index break end
    end
    if not mapIndex then error("measurement map not found: " .. tostring(mapId), 0) end
    local session = Session.GameSession.new(loader)
    session:initializeStartingParty()
    local seed = 1735689600 + tonumber(mapId)
    local savedTime = os.time
    os.time = function() return seed end
    local ok, err = pcall(exploration.loadMap, session, mapIndex, { seed = seed })
    os.time = savedTime
    if not ok then error(err, 0) end
    viewport_3d.init()
    local playBundle = assert(renderable.collect(session, "play"))
    local authoringBundle = assert(renderable.collect(session, "authoring"))
    local wall = playBundle.stats.visibility or {}
    print(string.format(
        "PROFILE MEASURE map=%d play surfaces=%d triangles=%d vertices=%d wallFaces=%d preProfileWallFaces=%d sealed=%d exteriorCulled=%d",
        mapId, playBundle.stats.surfaceCount, playBundle.stats.triangleCount,
        playBundle.stats.vertexCount, wall.emittedFaces or 0,
        wall.preProfileExposedFaces or 0, wall.culledSealedFaces or 0,
        wall.culledExteriorFaces or 0))
    print(string.format(
        "PROFILE MEASURE map=%d authoring surfaces=%d triangles=%d vertices=%d wallFaces=%d wallTops=%d ceilings=%d",
        mapId, authoringBundle.stats.surfaceCount, authoringBundle.stats.triangleCount,
        authoringBundle.stats.vertexCount,
        (authoringBundle.stats.visibility or {}).emittedFaces or 0,
        (authoringBundle.stats.bySurfaceRole["wall-top"] or {}).surfaceCount or 0,
        (authoringBundle.stats.bySurfaceRole.ceiling or {}).surfaceCount or 0))
end

if os.getenv("SECOND_RITE_PROFILE_MEASURE") == "1" then
    for _, mapIndex in ipairs({ 2, 8, 12, 14 }) do printMeasurement(mapIndex) end
end

print(string.format("map geometry export tests: %d passed, %d failed", passed, failed))
if failed > 0 then error("test_map_geometry_export failed", 0) end
