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

local function geometryDirectives(text)
    local kept = {}
    for line in (text .. "\n"):gmatch("([^\n]*)\n") do
        local directive = line:match("^(%S+)")
        if directive == "o" or directive == "g" or directive == "s"
                or directive == "v" or directive == "vt" or directive == "vn"
                or directive == "f" then
            kept[#kept + 1] = line
        end
    end
    return table.concat(kept, "\n")
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

local expectedGeometry = table.concat({
    "o second_rite_map_7",
    "g test_group",
    "s off",
    "v 0.000000000 0.000000000 0.000000000",
    "vt 0.000000000 1.000000000",
    "vn 0.000000000 1.000000000 0.000000000",
    "v 1.000000000 0.000000000 0.000000000",
    "vt 1.000000000 1.000000000",
    "vn 0.000000000 1.000000000 0.000000000",
    "v 0.000000000 0.000000000 -1.000000000",
    "vt 0.000000000 0.000000000",
    "vn 0.000000000 1.000000000 0.000000000",
    "f 1/1/1 2/2/2 3/3/3",
}, "\n")
check(geometryDirectives(first) == expectedGeometry,
    "material declarations leave object/group/smoothing/vertex/UV/normal/face geometry unchanged")

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
        { id = "material_004", color = { 0.5, 1, 1, 1 },
          albedo = { kind = "project-asset", path = "assets/tilesets/a.png" } },
        { id = "material_005", color = { 1, 1, 0.5, 1 },
          albedo = { kind = "project-asset", path = "assets/models/a.png" } },
        { id = "material_006", color = { 0.75, 0.75, 1, 1 },
          albedo = { kind = "embedded-png", base64 = "fixture" } },
    },
    surfaces = {
        triangleSurface("first", "first", "material_001", 0),
        triangleSurface("second", "second", "material_002", 2),
        triangleSurface("third", "third", "material_001", 4),
        triangleSurface("fourth", "fourth", "material_004", 6),
        triangleSurface("fifth", "fifth", "material_005", 8),
        triangleSurface("sixth", "sixth", "material_006", 10),
    },
}
check(renderable.validate(materialFixture),
    "multi-material fixture satisfies the neutral renderable contract")

local texturePlan = exporter.planTextures(materialFixture)
local texturePlanAgain = exporter.planTextures(materialFixture)
check(texturePlan.textureCount == 3,
    "texture planning deduplicates shared project assets and shared embedded PNG payloads")
check(texturePlan.byMaterial.material_001 == texturePlan.byMaterial.material_004,
    "distinct resolved materials sharing one project albedo reuse one exported texture")
check(texturePlan.byMaterial.material_002 == texturePlan.byMaterial.material_006,
    "distinct resolved materials sharing one embedded albedo reuse one exported texture")
check(texturePlan.byMaterial.material_001 ~= texturePlan.byMaterial.material_005,
    "different project assets with the same basename remain distinct")
check(texturePlan.byMaterial.material_001 == "textures/texture_001_a.png"
        and texturePlan.byMaterial.material_002 == "textures/texture_002_embedded.png"
        and texturePlan.byMaterial.material_005 == "textures/texture_003_a.png",
    "texture filenames are deterministic, safe, collision-proof, and export-relative")
check(texturePlanAgain.byMaterial.material_001 == texturePlan.byMaterial.material_001
        and texturePlanAgain.byMaterial.material_005 == texturePlan.byMaterial.material_005,
    "texture planning is deterministic across repeated serialization")

local mtl, materialStats = exporter.serializeMaterials(materialFixture, {
    textureFiles = texturePlan.byMaterial,
})
local mtlAgain = exporter.serializeMaterials(materialFixture, {
    textureFiles = texturePlanAgain.byMaterial,
})
check(mtl == mtlAgain, "MTL serialization is deterministic")
check(materialStats.materialCount == 6 and countOccurrences(mtl, "newmtl ") == 6,
    "MTL emits exactly one entry per distinct bundle material")
local m1 = mtl:find("newmtl material_001", 1, true)
local m2 = mtl:find("newmtl material_002", 1, true)
local m3 = mtl:find("newmtl material_003", 1, true)
local m4 = mtl:find("newmtl material_004", 1, true)
local m5 = mtl:find("newmtl material_005", 1, true)
local m6 = mtl:find("newmtl material_006", 1, true)
check(m1 and m2 and m3 and m4 and m5 and m6
        and m1 < m2 and m2 < m3 and m3 < m4 and m4 < m5 and m5 < m6,
    "MTL preserves authoritative material ordering")
check(mtl:find("Kd 0.250000000 0.500000000 0.750000000", 1, true) ~= nil
        and mtl:find("d 0.400000000", 1, true) ~= nil,
    "MTL maps bundle color and alpha to diffuse/opacity fields")
check(mtl:find("map_Kd textures/texture_001_a.png", 1, true) ~= nil
        and mtl:find("map_Kd textures/texture_002_embedded.png", 1, true) ~= nil,
    "MTL references export-local albedo textures with portable relative paths")
check(not mtl:find("assets/tilesets/", 1, true)
        and not mtl:find("assets/models/", 1, true)
        and not mtl:find(":\\", 1, true),
    "MTL leaks no source-checkout or machine-specific absolute texture paths")
check(mtl:find("emission/glow textures are not exported", 1, true) ~= nil
        and mtl:find("emission/glow payload present but intentionally not serialized", 1, true) ~= nil,
    "MTL states the deliberate glow/emission limitation")
check(mtl:find("newmtl material_003\nKd 1.000000000 1.000000000 1.000000000\nd 1.000000000", 1, true) ~= nil,
    "materials without color or albedo serialize to an explicit opaque-white default")

local materialObj, materialObjStats = exporter.serialize(materialFixture, {
    materialLibrary = "materials.mtl",
})
check(materialObjStats.vertexCount == 18 and materialObjStats.triangleCount == 6
        and materialObjStats.groupCount == 6 and materialObjStats.materialCount == 6,
    "material directives do not change geometry counts")
check(countOccurrences(materialObj, "usemtl material_001") == 2
        and countOccurrences(materialObj, "usemtl material_002") == 1
        and countOccurrences(materialObj, "usemtl material_004") == 1,
    "shared texture files do not collapse distinct authoritative material identities")
local firstGroup = materialObj:find("g first\ns off\nusemtl material_001", 1, true)
local secondGroup = materialObj:find("g second\ns off\nusemtl material_002", 1, true)
local thirdGroup = materialObj:find("g third\ns off\nusemtl material_001", 1, true)
check(firstGroup and secondGroup and thirdGroup and firstGroup < secondGroup and secondGroup < thirdGroup,
    "surface grouping and material binding preserve bundle order")

-- Exercise actual portable texture writing for both bundle payload kinds. This
-- uses a real repository project asset plus a runtime-created PNG, then removes
-- the temporary save-directory package after byte-for-byte checks.
local embeddedImage = love.image.newImageData(2, 2)
embeddedImage:setPixel(0, 0, 1, 0, 0, 1)
embeddedImage:setPixel(1, 0, 0, 1, 0, 1)
embeddedImage:setPixel(0, 1, 0, 0, 1, 1)
embeddedImage:setPixel(1, 1, 1, 1, 1, 1)
local embeddedFileData = embeddedImage:encode("png")
local embeddedBytes = embeddedFileData:getString()
local embeddedBase64 = love.data.encode("string", "base64", embeddedFileData)
local ioFixture = {
    version = renderable.VERSION,
    materials = {
        { id = "material_001", albedo = {
            kind = "project-asset", path = "assets/tilesets/dungeon_001.png" } },
        { id = "material_002", color = { 0.5, 0.5, 0.5, 1 }, albedo = {
            kind = "project-asset", path = "assets/tilesets/dungeon_001.png" } },
        { id = "material_003", albedo = {
            kind = "embedded-png", mime = "image/png", width = 2, height = 2,
            base64 = embeddedBase64 } },
        { id = "material_004", color = { 0.5, 1, 0.5, 1 }, albedo = {
            kind = "embedded-png", mime = "image/png", width = 2, height = 2,
            base64 = embeddedBase64 } },
    },
    surfaces = {},
}
local ioDirectory = "_test_map_geometry_export_292"
local ioPlan = exporter.planTextures(ioFixture)
local ioFiles, ioCount = exporter.writeTextures(ioFixture, ioDirectory, ioPlan)
check(ioCount == 2,
    "texture writer emits one file per unique resolved albedo rather than per material")
local projectCopy = love.filesystem.read(ioDirectory .. "/" .. ioFiles.material_001)
local projectSource = love.filesystem.read("assets/tilesets/dungeon_001.png")
check(projectCopy ~= nil and projectCopy == projectSource,
    "project-asset albedo is copied byte-for-byte into the export-local textures directory")
local embeddedCopy = love.filesystem.read(ioDirectory .. "/" .. ioFiles.material_003)
check(embeddedCopy ~= nil and embeddedCopy == embeddedBytes,
    "embedded PNG material payload is decoded and written as a real export-local PNG")
check(ioFiles.material_001 == ioFiles.material_002
        and ioFiles.material_003 == ioFiles.material_004,
    "actual texture writes preserve shared-source deduplication across materials")
for _, entry in ipairs(ioPlan.entries) do
    pcall(love.filesystem.remove, ioDirectory .. "/" .. entry.mtlPath)
end
pcall(love.filesystem.remove, ioDirectory .. "/textures")
pcall(love.filesystem.remove, ioDirectory)

-- Integration gate: exercise the collector against a real loaded dungeon, not
-- only a hand-built transport fixture. dungeon_default carries a real tileset
-- height map, so a floor emitted with more than two triangles proves this path
-- reached the engine-owned displaced-surface compiler rather than a flat
-- exporter approximation.
local Session = require("engine.session")
local exploration = require("engine.exploration")
local viewport_3d = require("presentation.viewport_3d")
local loader = require("engine.data.loader")
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

    local actualPlan = exporter.planTextures(actual)
    local actualMtl = exporter.serializeMaterials(actual, { textureFiles = actualPlan.byMaterial })
    check(not actualMtl:find("assets/tilesets/", 1, true),
        "real-map MTL serialization keeps project source paths out of the portable package")

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


-- #291: consumer geometry visibility is an engine finalization policy, not a
-- renderer trick. These checks deliberately share the real #287 bundle path so
-- authoring facts cannot drift into a second JavaScript/Three.js geometry path.
print("=== Consumer Geometry Visibility Profiles (#291) ===")
local visibility = require("engine.geometry.visibility_profile")
local playProfile = visibility.resolve("play")
local overheadProfile = visibility.resolve("play-overhead")
local authoringProfile = visibility.resolve("authoring")
check(playProfile.wallTopCaps == false and playProfile.walkableCeilings == true
        and playProfile.exteriorWallFaces == false,
    "play profile preserves gameplay wall-top, ceiling, and exterior-shell semantics")
check(overheadProfile.name == "play-overhead"
        and overheadProfile.wallTopCaps == true
        and overheadProfile.walkableCeilings == false
        and overheadProfile.exteriorWallFaces == true,
    "play-overhead is a named open-top gameplay policy with caps and exterior shell")
check(overheadProfile ~= authoringProfile and overheadProfile.name ~= authoringProfile.name,
    "overhead gameplay and authoring remain separate consumer identities")
check(authoringProfile.wallTopCaps == true and authoringProfile.walkableCeilings == false
        and authoringProfile.exteriorWallFaces == true,
    "authoring profile exposes tops, omits obscuring ceilings, and retains exterior shell")

local adjacencyFixture = {
    { "#", "#", "#" },
    { "#", "+", "." },
    { "#", "#", "#" },
}
local sealedVisible, sealedReason = visibility.wallSideDecision("play", adjacencyFixture, 1, 1)
check(not sealedVisible and sealedReason == "sealed-solid",
    "sealed wall-to-wall faces remain structurally eliminated")
local openingVisible, openingReason = visibility.wallSideDecision("play", adjacencyFixture, 2, 2)
check(openingVisible and openingReason == "non-solid-neighbour",
    "openings are not mistaken for sealed wall adjacency")
local exteriorPlay, exteriorPlayReason = visibility.wallSideDecision("play", adjacencyFixture, 4, 2)
local exteriorAuthoring, exteriorAuthoringReason = visibility.wallSideDecision("authoring", adjacencyFixture, 4, 2)
local exteriorOverhead, exteriorOverheadReason = visibility.wallSideDecision("play-overhead", adjacencyFixture, 4, 2)
check(exteriorOverhead and exteriorOverheadReason == "exterior-retained",
    "overhead gameplay retains map-boundary exterior shell")
check(not exteriorPlay and exteriorPlayReason == "exterior-culled"
        and exteriorAuthoring and exteriorAuthoringReason == "exterior-retained",
    "map-boundary outward faces are omitted only for play and retained for authoring")
check(visibility.walkableCeilingVisible("play", "stone")
        and not visibility.walkableCeilingVisible("play", "sky")
        and not visibility.walkableCeilingVisible("authoring", "stone"),
    "roofed walkable cells keep gameplay ceilings while authoring omits them")
check(not visibility.walkableCeilingVisible("play-overhead", "stone")
        and visibility.wallTopVisible("play-overhead"),
    "play-overhead opens walkable ceilings while retaining wall-top caps")
check(not visibility.wallTopVisible("play") and visibility.wallTopVisible("authoring"),
    "wall top caps are authoring facts and stay absent from play")
check(not pcall(visibility.resolve, "threejsHack"),
    "unknown renderer-specific profile names fail loud")

local authoredProfileBefore = runtimeSession.currentMapData.geometryProfile
local playBundle, playBundleErr = renderable.collect(runtimeSession, "play")
local authoringBundle, authoringBundleErr = renderable.collect(runtimeSession, "authoring")
local overheadBundle, overheadBundleErr = renderable.collect(runtimeSession, "play-overhead")
check(playBundle ~= nil and authoringBundle ~= nil,
    "real map resolves both play and authoring bundles: "
        .. tostring(playBundleErr or authoringBundleErr))
if playBundle and authoringBundle then
    check(renderable.validate(playBundle) and renderable.validate(authoringBundle),
        "both consumer profiles satisfy the authoritative renderable bundle contract")
    check(playBundle.geometryProfile == "play" and authoringBundle.geometryProfile == "authoring",
        "bundle declares the semantic consumer profile that finalized it")
    local playRoles = playBundle.stats.bySurfaceRole or {}
    local authoringRoles = authoringBundle.stats.bySurfaceRole or {}
    check((playRoles.ceiling and playRoles.ceiling.surfaceCount or 0) > 0
        and (authoringRoles.ceiling and authoringRoles.ceiling.surfaceCount or 0) == 0,
        "roofed real map emits gameplay ceilings but no authoring ceilings")
    check((playRoles["wall-top"] and playRoles["wall-top"].surfaceCount or 0) == 0
        and (authoringRoles["wall-top"] and authoringRoles["wall-top"].surfaceCount or 0) > 0,
        "real authoring bundle receives readable wall top caps absent from play")
    local playVisibility = playBundle.stats.visibility or {}
    local authoringVisibility = authoringBundle.stats.visibility or {}
    check((playVisibility.culledExteriorFaces or 0) > 0
  and (authoringVisibility.culledExteriorFaces or 0) == 0
  and (authoringVisibility.emittedFaces or 0) > (playVisibility.emittedFaces or 0),
        "real exterior shell is retained for authoring and safely omitted for play")
    check((playVisibility.culledSealedFaces or 0) > 0,
        "existing sealed-solid face elimination is explicit and measured rather than re-credited")
end
check(overheadBundle ~= nil,
    "real map resolves play-overhead bundle: " .. tostring(overheadBundleErr))
if overheadBundle then
    check(renderable.validate(overheadBundle),
        "play-overhead satisfies authoritative renderable bundle contract")
    check(overheadBundle.geometryProfile == "play-overhead",
        "play-overhead bundle preserves semantic consumer identity")
    local overheadRoles = overheadBundle.stats.bySurfaceRole or {}
    check((overheadRoles.ceiling and overheadRoles.ceiling.surfaceCount or 0) == 0
            and (overheadRoles["wall-top"] and overheadRoles["wall-top"].surfaceCount or 0) > 0,
        "real play-overhead bundle opens ceilings and emits wall-top caps")
    local overheadVisibility = overheadBundle.stats.visibility or {}
    check((overheadVisibility.culledExteriorFaces or 0) == 0,
        "real play-overhead bundle retains exterior wall faces")
end
check(runtimeSession.currentMapData.geometryProfile == authoredProfileBefore,
    "profile selection never mutates authored map data")

-- #598: wall tops are authored material/geometry policy, while visibility
-- remains a consumer decision. The resolver is deterministic and an absent
-- pool preserves the historical neutral-gray cap.
local wallTopFixtureDef = { base = { wallTops = {
    { id = "cap_a", atlas = { 3, 0 }, weight = 1 },
    { id = "cap_b", atlas = { 3, 1 }, weight = 3 },
} } }
local capPickA = viewport_3d.resolveWallTopVariant(wallTopFixtureDef, 4, 7)
local capPickB = viewport_3d.resolveWallTopVariant(wallTopFixtureDef, 4, 7)
check(capPickA ~= nil and capPickA == capPickB
        and (capPickA.id == "cap_a" or capPickA.id == "cap_b"),
    "wall-top weighted resolution is deterministic per map cell")
check(viewport_3d.resolveWallTopVariant({ base = {} }, 4, 7) == nil,
    "missing wall-top pool resolves to compatibility fallback rather than another surface role")

local function materialById(value, id)
    for _, material in ipairs(value.materials or {}) do
        if material.id == id then return material end
    end
end
local fallbackCap
for _, rendered in ipairs((authoringBundle and authoringBundle.surfaces) or {}) do
    if rendered.source and rendered.source.surface == "wall-top" then
        fallbackCap = rendered
        break
    end
end
local fallbackMaterial = fallbackCap and materialById(authoringBundle, fallbackCap.material)
check(fallbackMaterial ~= nil and fallbackMaterial.albedo == nil
        and fallbackMaterial.color and fallbackMaterial.color[1] == 0.72,
    "existing tilesets without wallTops preserve the historical neutral-gray cap")

local tilesetResolver = require("engine.tileset_resolver")
local originalOverride = runtimeSession.currentMapData.tilesetOverride
local testOverride, baseOverride = {}, {}
for key, value in pairs(originalOverride or {}) do testOverride[key] = value end
for key, value in pairs(testOverride.base or {}) do baseOverride[key] = value end
baseOverride.wallTops = {
    { id = "wall_top_bundle_fixture", role = "base_wall_top", atlas = { 0, 1 }, weight = 100 },
}
testOverride.base = baseOverride
runtimeSession.currentMapData.tilesetOverride = testOverride
tilesetResolver.invalidate(runtimeSession.currentMapData)
local authoredCaps = renderable.collect(runtimeSession, "authoring")
local authoredCap
for _, rendered in ipairs((authoredCaps and authoredCaps.surfaces) or {}) do
    if rendered.source and rendered.source.surface == "wall-top" then
        authoredCap = rendered
        break
    end
end
local authoredMaterial = authoredCap and materialById(authoredCaps, authoredCap.material)
check(authoredMaterial ~= nil and authoredMaterial.albedo ~= nil
        and authoredMaterial.albedo.kind == "project-asset",
    "authored wall-top atlas variants replace the structural fallback in the neutral bundle")
runtimeSession.currentMapData.tilesetOverride = originalOverride
tilesetResolver.invalidate(runtimeSession.currentMapData)

print(string.format("map geometry export + #291 profile tests: %d passed, %d failed", passed, failed))
if failed > 0 then error("test_map_geometry_export #291 profile coverage failed", 0) end
