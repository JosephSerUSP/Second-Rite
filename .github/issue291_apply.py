from pathlib import Path


def replace_once(path, old, new):
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one match, found {count}: {old[:100]!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    "presentation/viewport_3d.lua",
    'local geometryImages = require("engine.geometry.images")\nlocal small_battlers',
    'local geometryImages = require("engine.geometry.images")\nlocal geometryVisibility = require("engine.geometry.visibility_profile")\nlocal small_battlers',
)

replace_once(
    "presentation/viewport_3d.lua",
    '''    for _, faces in pairs((prepared and prepared.resolvedWallFaces) or {}) do
        for _, face in ipairs(faces) do
            releaseMeshTree(face.meshTree)
            face.meshTree = nil
        end
    end''',
    '''    for _, byProfile in pairs((prepared and prepared.resolvedWallFaces) or {}) do
        for _, resolved in pairs(byProfile) do
            for _, face in ipairs(resolved.faces or {}) do
                releaseMeshTree(face.meshTree)
                face.meshTree = nil
            end
        end
    end''',
)

replace_once(
    "presentation/viewport_3d.lua",
    '''local function prepareResolvedWallFaces(structure, atlas)
    structure.resolvedWallFaces = structure.resolvedWallFaces or {}
    local cacheKey = atlas or NO_ATLAS_CACHE_KEY
    if structure.resolvedWallFaces[cacheKey] then
        return structure.resolvedWallFaces[cacheKey]
    end
    local grid, faces = structure.grid, {}
    local function addFace(mapX, mapY, kind, p1, p2, nx, ny)
        if wallCell(grid, nx, ny) then return end''',
    '''local function prepareResolvedWallFaces(structure, atlas, profileName)
    local profile = geometryVisibility.resolve(profileName)
    structure.resolvedWallFaces = structure.resolvedWallFaces or {}
    local cacheKey = atlas or NO_ATLAS_CACHE_KEY
    local byProfile = structure.resolvedWallFaces[cacheKey]
    if not byProfile then
        byProfile = {}
        structure.resolvedWallFaces[cacheKey] = byProfile
    end
    if byProfile[profile.name] then
        local resolved = byProfile[profile.name]
        return resolved.faces, resolved.stats
    end
    local grid, faces = structure.grid, {}
    local stats = {
        profile = profile.name,
        candidateFaces = #(structure.wallCells or {}) * 4,
        emittedFaces = 0,
        culledSealedFaces = 0,
        culledExteriorFaces = 0,
    }
    local function addFace(mapX, mapY, kind, p1, p2, nx, ny)
        local visible, reason = geometryVisibility.wallSideDecision(
            profile.name, grid, nx, ny)
        if not visible then
            if reason == "sealed-solid" then
                stats.culledSealedFaces = stats.culledSealedFaces + 1
            elseif reason == "exterior-culled" then
                stats.culledExteriorFaces = stats.culledExteriorFaces + 1
            end
            return
        end''',
)

replace_once(
    "presentation/viewport_3d.lua",
    '''            mapX = mapX, mapY = mapY,
        })
    end
    for _, cell in ipairs(structure.wallCells) do''',
    '''            mapX = mapX, mapY = mapY,
        })
        stats.emittedFaces = stats.emittedFaces + 1
    end
    for _, cell in ipairs(structure.wallCells) do''',
)

replace_once(
    "presentation/viewport_3d.lua",
    '''    structure.resolvedWallFaces[cacheKey] = faces
    return faces
end

function viewport_3d.prepareResolvedStructure(session)
    local structure = viewport_3d.prepareStructure(session)
    if not structure then return nil, nil end
    local atlas = resolveTileset(session.currentMapData, session)
    return structure, prepareResolvedWallFaces(structure, atlas)
end''',
    '''    stats.preProfileExposedFaces = stats.candidateFaces - stats.culledSealedFaces
    stats.profileReductionFaces = stats.preProfileExposedFaces - stats.emittedFaces
    buildProfiler.set("materialize.wallFaces." .. profile.name .. ".candidates",
        stats.candidateFaces)
    buildProfiler.set("materialize.wallFaces." .. profile.name .. ".emitted",
        stats.emittedFaces)
    buildProfiler.set("materialize.wallFaces." .. profile.name .. ".culledSealed",
        stats.culledSealedFaces)
    buildProfiler.set("materialize.wallFaces." .. profile.name .. ".culledExterior",
        stats.culledExteriorFaces)
    byProfile[profile.name] = { faces = faces, stats = stats }
    return faces, stats
end

function viewport_3d.prepareResolvedStructure(session, profileName)
    local profile = geometryVisibility.resolve(profileName)
    local structure = viewport_3d.prepareStructure(session)
    if not structure then return nil, nil, nil end
    local atlas = resolveTileset(session.currentMapData, session)
    local faces, stats = prepareResolvedWallFaces(structure, atlas, profile.name)
    return structure, faces, stats
end''',
)

replace_once(
    "presentation/viewport_3d.lua",
    '''    for _, face in ipairs(prepareResolvedWallFaces(structure, atlas)) do''',
    '''    for _, face in ipairs(prepareResolvedWallFaces(structure, atlas, "play")) do''',
)

replace_once(
    "presentation/map_renderable_bundle.lua",
    '''local geometry_images = require("engine.geometry.images")
local tileset_resolver''',
    '''local geometry_images = require("engine.geometry.images")
local geometry_visibility = require("engine.geometry.visibility_profile")
local tileset_resolver''',
)

replace_once(
    "presentation/map_renderable_bundle.lua",
    '''local function summarize(surfaces, materials)
    local vertices = 0
    for _, surface in ipairs(surfaces) do vertices = vertices + math.floor(#surface.positions / 3) end
    return {
        surfaceCount = #surfaces,
        materialCount = #materials,
        vertexCount = vertices,
        triangleCount = math.floor(vertices / 3),
    }
end

function bundle.collect(session)
    if not (session and session.currentMapData and session.mapGrid) then
        return nil, "No runtime map is loaded."
    end

    local structure, faces = viewport_3d.prepareResolvedStructure(session)''',
    '''local function summarize(surfaces, materials)
    local vertices = 0
    local bySurfaceRole = {}
    for _, surface in ipairs(surfaces) do
        local count = math.floor(#surface.positions / 3)
        vertices = vertices + count
        local role = surface.source and surface.source.surface or nil
        if role then
            local entry = bySurfaceRole[role]
            if not entry then
                entry = { surfaceCount = 0, vertexCount = 0, triangleCount = 0 }
                bySurfaceRole[role] = entry
            end
            entry.surfaceCount = entry.surfaceCount + 1
            entry.vertexCount = entry.vertexCount + count
            entry.triangleCount = entry.triangleCount + math.floor(count / 3)
        end
    end
    return {
        surfaceCount = #surfaces,
        materialCount = #materials,
        vertexCount = vertices,
        triangleCount = math.floor(vertices / 3),
        bySurfaceRole = bySurfaceRole,
    }
end

function bundle.collect(session, profileName)
    if not (session and session.currentMapData and session.mapGrid) then
        return nil, "No runtime map is loaded."
    end

    local profile = geometry_visibility.resolve(profileName)
    local structure, faces, visibilityStats =
        viewport_3d.prepareResolvedStructure(session, profile.name)''',
)

replace_once(
    "presentation/map_renderable_bundle.lua",
    '''        if mapData.ceilingStyle ~= "sky" then''',
    '''        if geometry_visibility.walkableCeilingVisible(
                profile.name, mapData.ceilingStyle) then''',
)

replace_once(
    "presentation/map_renderable_bundle.lua",
    '''    end

    for _, face in ipairs(faces or {}) do
        local direction = wallDirection(face)''',
    '''    end

    if geometry_visibility.wallTopVisible(profile.name) then
        local wallTopMaterial = registerMaterial(registry, "structural:wall-top", {
            color = { 0.72, 0.72, 0.72, 1 },
        })
        for _, cell in ipairs(structure.wallCells or {}) do
            local x, y = cell.x, cell.y
            local source = cellSource(x, y, "wall-top")
            local surface = newSurface(surfaces, "wall_top_" .. x .. "_" .. y,
                source, wallTopMaterial)
            addQuad(surface,
                { x = x, y = y, z = 1 }, { x = x + 1, y = y, z = 1 },
                { x = x + 1, y = y + 1, z = 1 }, { x = x, y = y + 1, z = 1 },
                { 0, 0, 1, 1 }, { 0, 0, 1 })
        end
    end

    for _, face in ipairs(faces or {}) do
        local direction = wallDirection(face)''',
)

replace_once(
    "presentation/map_renderable_bundle.lua",
    '''    local result = {
        version = bundle.VERSION,
        map = { id = mapId, name = mapName },''',
    '''    local stats = summarize(surfaces, registry.list)
    stats.visibility = visibilityStats
    local result = {
        version = bundle.VERSION,
        geometryProfile = profile.name,
        map = { id = mapId, name = mapName },''',
)

replace_once(
    "presentation/map_renderable_bundle.lua",
    '''        materials = registry.list,
        surfaces = surfaces,
        stats = summarize(surfaces, registry.list),
    }''',
    '''        materials = registry.list,
        surfaces = surfaces,
        stats = stats,
    }''',
)

print("issue291 implementation replacements completed")
