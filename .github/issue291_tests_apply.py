from pathlib import Path


def replace_once(path, old, new):
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one match, found {count}: {old[:100]!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    "presentation/editor_renderable_bridge.lua",
    '            local result, collectErr = renderables.collect(vSession)',
    '            local result, collectErr = renderables.collect(vSession, "authoring")',
)

replace_once(
    "tests/test_map_geometry_export.lua",
    'local exporter = require("presentation.map_geometry_export")\nlocal renderable = require("presentation.map_renderable_bundle")',
    'local exporter = require("presentation.map_geometry_export")\nlocal renderable = require("presentation.map_renderable_bundle")\nlocal visibility = require("engine.geometry.visibility_profile")',
)

replace_once(
    "tests/test_map_geometry_export.lua",
    '''local bundle = {
    version = renderable.VERSION,
    map = { id = 7, name = "Round Trip" },''',
    '''local bundle = {
    version = renderable.VERSION,
    geometryProfile = "play",
    map = { id = 7, name = "Round Trip" },''',
)

replace_once(
    "tests/test_map_geometry_export.lua",
    '''check(first:find("materials come from the authoritative renderable bundle", 1, true) ~= nil,
    "OBJ serialization declares the bundle as its material/geometry authority")

-- Integration gate:''',
    '''check(first:find("materials come from the authoritative renderable bundle", 1, true) ~= nil,
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

-- Integration gate:''',
)

replace_once(
    "tests/test_map_geometry_export.lua",
    '''local actual, collectErr = renderable.collect(runtimeSession)
check(actual ~= nil, "real loaded map produces an authoritative renderable bundle: " .. tostring(collectErr))
if actual then
    check(renderable.validate(actual), "real loaded map bundle satisfies the transport contract")''',
    '''local authoredProfileBefore = runtimeSession.currentMapData.geometryProfile
local actual, collectErr = renderable.collect(runtimeSession, "play")
local authoring, authoringErr = renderable.collect(runtimeSession, "authoring")
check(actual ~= nil, "real loaded map produces an authoritative renderable bundle: " .. tostring(collectErr))
check(authoring ~= nil, "real loaded map produces an authoring renderable bundle: " .. tostring(authoringErr))
if actual then
    check(renderable.validate(actual), "real loaded map bundle satisfies the transport contract")
    check(actual.geometryProfile == "play",
        "game/runtime bundle declares the play visibility profile")''',
)

replace_once(
    "tests/test_map_geometry_export.lua",
    '''    check(hasProjectMaterial,
        "real bundle preserves the authoritative tileset texture as a project material reference")
end

print(string.format("map geometry export tests: %d passed, %d failed", passed, failed))''',
    '''    check(hasProjectMaterial,
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

local function printMeasurement(mapIndex)
    local session = Session.GameSession.new(loader)
    session:initializeStartingParty()
    local savedTime = os.time
    os.time = function() return 1735689600 + mapIndex end
    local ok, err = pcall(exploration.loadMap, session, mapIndex,
        { seed = 1735689600 + mapIndex })
    os.time = savedTime
    if not ok then error(err, 0) end
    viewport_3d.init()
    local playBundle = assert(renderable.collect(session, "play"))
    local authoringBundle = assert(renderable.collect(session, "authoring"))
    local wall = playBundle.stats.visibility or {}
    print(string.format(
        "PROFILE MEASURE map=%d play surfaces=%d triangles=%d vertices=%d wallFaces=%d preProfileWallFaces=%d sealed=%d exteriorCulled=%d",
        mapIndex, playBundle.stats.surfaceCount, playBundle.stats.triangleCount,
        playBundle.stats.vertexCount, wall.emittedFaces or 0,
        wall.preProfileExposedFaces or 0, wall.culledSealedFaces or 0,
        wall.culledExteriorFaces or 0))
    print(string.format(
        "PROFILE MEASURE map=%d authoring surfaces=%d triangles=%d vertices=%d wallFaces=%d wallTops=%d ceilings=%d",
        mapIndex, authoringBundle.stats.surfaceCount, authoringBundle.stats.triangleCount,
        authoringBundle.stats.vertexCount,
        (authoringBundle.stats.visibility or {}).emittedFaces or 0,
        (authoringBundle.stats.bySurfaceRole["wall-top"] or {}).surfaceCount or 0,
        (authoringBundle.stats.bySurfaceRole.ceiling or {}).surfaceCount or 0))
end

if os.getenv("SECOND_RITE_PROFILE_MEASURE") == "1" then
    for _, mapIndex in ipairs({ 2, 8, 12, 14 }) do printMeasurement(mapIndex) end
end

print(string.format("map geometry export tests: %d passed, %d failed", passed, failed))''',
)

print("issue291 bridge/test replacements completed")
