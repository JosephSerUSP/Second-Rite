-- Developer-only runtime map geometry export.
--
-- The renderer owns the authoritative world placement rules, while the static
-- mesh compiler owns the source triangle representation. This module stays on
-- that CPU/world side of the seam: it never reads the current camera, clipped
-- stream meshes, fog, lighting, billboards, particles, or UI state.
--
-- OBJ is intentionally geometry-only for the first pass. UVs and normals are
-- preserved so a later texture-export follow-up can add MTL/baked images without
-- changing the mesh contract.
local viewport_3d = require("presentation.viewport_3d")
local obj_model = require("presentation.obj_model")
local mesh = require("presentation.mesh")
local geometry = require("engine.geometry")
local geometry_images = require("engine.geometry.images")
local tileset_resolver = require("engine.tileset_resolver")
local quality = require("engine.geometry.quality")

local exporter = {}

local ATLAS_TILE = 64

local function cleanZero(value)
    return math.abs(value) < 0.0000000005 and 0 or value
end

local function number(value)
    return string.format("%.9f", cleanZero(value or 0))
end

local function safeName(value)
    local name = tostring(value or "unnamed")
        :gsub("[%c%s]+", "_")
        :gsub("[^%w_%-%.]", "_")
        :gsub("_+", "_")
        :gsub("^_+", "")
        :gsub("_+$", "")
    return name ~= "" and name or "unnamed"
end

-- Second Rite world space is Z-up. Its OBJ loader converts the usual external
-- Y-up coordinates with (x, y, z) -> (x, -z, y), so export uses the exact
-- inverse. This makes an exported OBJ round-trip through obj_model.parse().
function exporter.worldToObj(x, y, z)
    return x, z, -y
end

function exporter.normalToObj(x, y, z)
    return x, z, -y
end

local function newGroup(groups, name)
    local group = { name = safeName(name), vertices = {} }
    groups[#groups + 1] = group
    return group
end

local function vertex(x, y, z, u, v, nx, ny, nz)
    return {
        x = x, y = y, z = z,
        u = u or 0, v = v or 0,
        nx = nx or 0, ny = ny or 0, nz = nz or 1,
    }
end

local function pushVertex(group, value)
    group.vertices[#group.vertices + 1] = value
end

local function addQuad(group, a, b, c, d, uv, normal)
    uv = uv or { 0, 0, 1, 1 }
    normal = normal or { 0, 0, 1 }
    local function at(point, u, v)
        return vertex(point.x, point.y, point.z, u, v,
            normal[1], normal[2], normal[3])
    end
    pushVertex(group, at(a, uv[1], uv[2]))
    pushVertex(group, at(b, uv[3], uv[2]))
    pushVertex(group, at(c, uv[3], uv[4]))
    pushVertex(group, at(a, uv[1], uv[2]))
    pushVertex(group, at(c, uv[3], uv[4]))
    pushVertex(group, at(d, uv[1], uv[4]))
end

local function atlasUV(originX, originY, width, height, texW, texH, flipU)
    local u0 = (originX + 0.5) / texW
    local u1 = (originX + width - 0.5) / texW
    local v0 = (originY + 0.5) / texH
    local v1 = (originY + height - 0.5) / texH
    if flipU then u0, u1 = u1, u0 end
    return { u0, v0, u1, v1 }
end

local function cropHeightTile(source, x, y, width, height)
    if source:getWidth() == width and source:getHeight() == height then return source end
    local tile = love.image.newImageData(width, height)
    for row = 0, height - 1 do
        for column = 0, width - 1 do
            tile:setPixel(column, row, source:getPixel(x + column, y + row))
        end
    end
    return tile
end

local function atlasInfo(session)
    local mapData = session.currentMapData
    local loader = session.loader
    local tilesetDef, cacheKey = tileset_resolver.resolve(loader, mapData)
    if not tilesetDef then return nil end

    local id = tilesetDef.id or (mapData and mapData.tileset) or "dungeon_default"
    local texturePath = tilesetDef.texture or ("assets/tilesets/" .. id .. ".png")
    local texture = tilesetDef.textureImage
    if not texture then
        if not love.filesystem.getInfo(texturePath) then return nil end
        texture = mesh.texture(texturePath)
    end

    local tileWidth = tilesetDef.tileWidth or ATLAS_TILE
    local tileHeight = tilesetDef.tileHeight or ATLAS_TILE
    local heightData, heightMode
    if tilesetDef.heightMap then
        local heightPath = tilesetDef.heightMap
        if not love.filesystem.getInfo(heightPath) then
            error("tileset height map missing: " .. tostring(heightPath), 0)
        end
        local ok, data = pcall(love.image.newImageData, heightPath)
        if not ok then error("tileset height map unreadable: " .. tostring(heightPath), 0) end
        if data:getWidth() == texture:getWidth() and data:getHeight() == texture:getHeight() then
            heightMode = "atlas"
        elseif data:getWidth() == tileWidth and data:getHeight() == tileHeight then
            heightMode = "tile"
        else
            error("tileset height map must match the texture atlas or one tile: "
                .. data:getWidth() .. "x" .. data:getHeight(), 0)
        end
        heightData = data
    end

    local features = {}
    for _, feature in ipairs(tilesetDef.features or {}) do
        if feature.id then features[feature.id] = feature end
    end

    local floorRow, floorCol = tilesetDef.floorRow, tilesetDef.floorCol
    if floorRow == nil and tilesetDef.base and tilesetDef.base.floors
            and tilesetDef.base.floors[1] and tilesetDef.base.floors[1].atlas then
        floorRow = tilesetDef.base.floors[1].atlas[1]
        floorCol = tilesetDef.base.floors[1].atlas[2]
    end
    local ceilingRow, ceilingCol = tilesetDef.ceilingRow, tilesetDef.ceilingCol
    if ceilingRow == nil and tilesetDef.base and tilesetDef.base.ceilings
            and tilesetDef.base.ceilings[1] and tilesetDef.base.ceilings[1].atlas then
        ceilingRow = tilesetDef.base.ceilings[1].atlas[1]
        ceilingCol = tilesetDef.base.ceilings[1].atlas[2]
    end

    return {
        id = id,
        cacheKey = cacheKey or id,
        definition = tilesetDef,
        texture = texture,
        w = texture:getWidth(), h = texture:getHeight(),
        tileWidth = tileWidth, tileHeight = tileHeight,
        heightData = heightData, heightMode = heightMode,
        heightMapPath = tilesetDef.heightMap,
        heightMapScale = tilesetDef.heightMapScale,
        heightMapOperation = tilesetDef.heightMapOperation or "add",
        heightMapMeshColumns = tilesetDef.heightMapMeshColumns or 16,
        heightMapMeshRows = tilesetDef.heightMapMeshRows or 16,
        heightMapSampleColumns = tilesetDef.heightMapSampleColumns,
        heightMapSampleRows = tilesetDef.heightMapSampleRows,
        heightMapTriangleBudget = tilesetDef.heightMapTriangleBudget or 64,
        heightMapOffset = tilesetDef.heightMapOffset or 0.004,
        floorRow = floorRow, floorCol = floorCol,
        ceilingRow = ceilingRow, ceilingCol = ceilingCol,
        features = features,
        heightTileCache = {},
    }
end

local function heightScaleFor(atlas, surface)
    local scale = atlas.heightMapScale
    if type(scale) == "table" then scale = scale[surface] or scale.default end
    return tonumber(scale or 0.08) or 0
end

-- Mirrors viewport_3d's tileset-level height-surface adapter. The compiler is
-- still the source of truth; this only gives it the same cropped field and UV
-- mapping the renderer supplies for a floor/ceiling placement.
local function atlasHeightSurface(atlas, surface, variant, originX, originY, flipU)
    if not atlas or not atlas.heightData or not variant then return nil end
    local scale = heightScaleFor(atlas, surface)
    if scale <= 0 then return nil end

    local tileKey = originX .. "," .. originY .. ":" .. tostring(flipU == true)
    local data = atlas.heightTileCache[tileKey]
    if not data then
        data = atlas.heightMode == "atlas"
            and cropHeightTile(atlas.heightData, originX, originY,
                atlas.tileWidth, atlas.tileHeight)
            or atlas.heightData
        if flipU then data = geometry_images.flipX(data) end
        atlas.heightTileCache[tileKey] = data
    end

    local spec = {
        id = "tileset_height_" .. surface .. "_" .. originX .. "_" .. originY,
        label = "tileset height map '" .. tostring(atlas.heightMapPath) .. "' " .. surface,
        topology = "plane", role = "surfaceFixture", surface = surface,
        heightOperation = atlas.heightMapOperation, heightScale = scale,
        meshColumns = atlas.heightMapMeshColumns, meshRows = atlas.heightMapMeshRows,
        sampleColumns = atlas.heightMapSampleColumns
            or math.min(48, atlas.heightMapMeshColumns * 4),
        sampleRows = atlas.heightMapSampleRows
            or math.min(48, atlas.heightMapMeshRows * 4),
        triangleBudget = atlas.heightMapTriangleBudget,
        offset = atlas.heightMapOffset,
        sealPerimeter = true,
    }
    local function uv(u, v)
        local px = originX + 0.5 + u * (atlas.tileWidth - 1)
        local py = originY + 0.5 + v * (atlas.tileHeight - 1)
        if flipU then
            px = originX + atlas.tileWidth - 0.5 - u * (atlas.tileWidth - 1)
        end
        return px / atlas.w, py / atlas.h
    end
    return {
        runtimeSurface = {
            cacheKey = tostring(atlas.heightMapPath) .. ":" .. surface .. ":"
                .. originX .. "," .. originY .. ":" .. tostring(flipU == true),
            spec = spec,
            heightData = data,
            texture = atlas.texture,
            uv = uv,
        },
        coversFace = true,
    }
end

local function modelFor(spec)
    if spec.runtimeSurface then
        local runtime = spec.runtimeSurface
        return geometry.loadAtlasSurface(runtime.cacheKey, runtime.spec,
            runtime.heightData, runtime.texture, runtime.uv)
    elseif spec.geometry then
        return geometry.load(spec.geometry)
    elseif spec.model then
        return obj_model.load(spec.model)
    end
    error("map geometry placement has no mesh source", 0)
end

local function addPlacedModel(groups, name, spec, originX, originY, axis, normalX, normalY)
    local model = modelFor(spec)
    for groupIndex, modelGroup in ipairs(model.groups or {}) do
        local material = modelGroup.material
        local suffix = (material and material ~= "") and material or ("part_" .. groupIndex)
        local group = newGroup(groups, name .. "_" .. suffix)
        for _, source in ipairs(modelGroup.vertices or {}) do
            local lx, ly, lz = source[1], source[2], source[3]
            local nx, ny, nz = source[6] or 0, source[7] or 0, source[8] or 1
            if normalX or normalY then
                lx, ly = viewport_3d.wallModelFrame(lx, ly, normalX, normalY)
                nx, ny = viewport_3d.wallModelFrame(nx, ny, normalX, normalY)
            elseif axis == "y" then
                lx, ly = -ly, lx
                nx, ny = -ny, nx
            end
            pushVertex(group, vertex(
                originX + lx, originY + ly, lz,
                source[4], source[5], nx, ny, nz))
        end
    end
end

local function defaultSurfaceAtlas(atlas, surface)
    if not atlas then return 0, 0 end
    if surface == "floor" then
        return (atlas.floorCol or 0) * ATLAS_TILE, (atlas.floorRow or 3) * ATLAS_TILE
    end
    return (atlas.ceilingCol or 0) * ATLAS_TILE, (atlas.ceilingRow or 0) * ATLAS_TILE
end

local function variantAtlasOrigin(atlas, surface, variant)
    if variant and variant.atlas then
        return variant.atlas[2] * ATLAS_TILE, variant.atlas[1] * ATLAS_TILE
    end
    return defaultSurfaceAtlas(atlas, surface)
end

local function surfaceUV(atlas, surface, variant)
    if not atlas then return { 0, 0, 1, 1 } end
    local ox, oy = variantAtlasOrigin(atlas, surface, variant)
    return atlasUV(ox, oy, ATLAS_TILE, ATLAS_TILE, atlas.w, atlas.h, false)
end

local function wallDirection(face)
    if face.normalY == -1 then return "north" end
    if face.normalY == 1 then return "south" end
    if face.normalX == -1 then return "west" end
    return "east"
end

local function addOpeningQuad(group, x, y, axis, lo, hi, bottom, top, uv)
    if axis == "x" then
        local wx = x + 0.5
        addQuad(group,
            { x = wx, y = y + lo, z = bottom },
            { x = wx, y = y + hi, z = bottom },
            { x = wx, y = y + hi, z = top },
            { x = wx, y = y + lo, z = top },
            uv, { 1, 0, 0 })
    else
        local wy = y + 0.5
        addQuad(group,
            { x = x + hi, y = wy, z = bottom },
            { x = x + lo, y = wy, z = bottom },
            { x = x + lo, y = wy, z = top },
            { x = x + hi, y = wy, z = top },
            uv, { 0, 1, 0 })
    end
end

function exporter.collect(session)
    if not (session and session.currentMapData and session.mapGrid) then
        return nil, "No runtime map is loaded."
    end

    local structure, faces = viewport_3d.prepareResolvedStructure(session)
    if not structure then return nil, "No runtime map geometry is available." end
    local mapData = session.currentMapData
    local atlas = atlasInfo(session)
    local tilesetDef = atlas and atlas.definition or nil
    local groups = {}

    -- Floors and ceilings are materialized for every open runtime cell, not
    -- merely the cells the camera happened to see in the last frame.
    for _, cell in ipairs(structure.floorCells or {}) do
        local x, y = cell.x, cell.y
        local floorSpec = atlas and viewport_3d.resolveWeightedVariant(
            tilesetDef.base and tilesetDef.base.floors,
            x, y, 961748927, 982451653) or nil
        local floorOriginX, floorOriginY = variantAtlasOrigin(atlas, "floor", floorSpec)
        local floorHeight = floorSpec and not floorSpec.geometry
            and atlasHeightSurface(atlas, "floor", floorSpec,
                floorOriginX, floorOriginY, false) or nil
        if floorHeight then
            addPlacedModel(groups, "floor_" .. x .. "_" .. y,
                floorHeight, x + 0.5, y + 0.5, "x")
        elseif floorSpec and floorSpec.geometry then
            addPlacedModel(groups, "floor_" .. x .. "_" .. y,
                { geometry = floorSpec.geometry }, x + 0.5, y + 0.5, "x")
        else
            local group = newGroup(groups, "floor_" .. x .. "_" .. y)
            addQuad(group,
                { x = x, y = y, z = 0 }, { x = x + 1, y = y, z = 0 },
                { x = x + 1, y = y + 1, z = 0 }, { x = x, y = y + 1, z = 0 },
                surfaceUV(atlas, "floor", floorSpec), { 0, 0, 1 })
        end

        local feature = atlas and atlas.features[structure.materialLookup[x .. "," .. y] or ""] or nil
        if feature and feature.role == "floor_feature" then
            if viewport_3d.meshSource(feature) then
                addPlacedModel(groups, "floor_feature_" .. x .. "_" .. y,
                    feature, x + 0.5, y + 0.5, "x")
            end
            if feature.atlas then
                local group = newGroup(groups, "floor_feature_atlas_" .. x .. "_" .. y)
                addQuad(group,
                    { x = x, y = y, z = 0.002 }, { x = x + 1, y = y, z = 0.002 },
                    { x = x + 1, y = y + 1, z = 0.002 }, { x = x, y = y + 1, z = 0.002 },
                    atlasUV(feature.atlas[2] * ATLAS_TILE, feature.atlas[1] * ATLAS_TILE,
                        ATLAS_TILE, ATLAS_TILE, atlas.w, atlas.h, false),
                    { 0, 0, 1 })
            end
        end

        if not (mapData.ceilingStyle == "sky") then
            local ceilingSpec = atlas and viewport_3d.resolveWeightedVariant(
                tilesetDef.base and tilesetDef.base.ceilings,
                x, y, 15485863, 32452843) or nil
            local ceilingOriginX, ceilingOriginY = variantAtlasOrigin(atlas, "ceiling", ceilingSpec)
            local ceilingHeight = ceilingSpec and not ceilingSpec.geometry
                and atlasHeightSurface(atlas, "ceiling", ceilingSpec,
                    ceilingOriginX, ceilingOriginY, false) or nil
            if ceilingHeight then
                addPlacedModel(groups, "ceiling_" .. x .. "_" .. y,
                    ceilingHeight, x + 0.5, y + 0.5, "x")
            elseif ceilingSpec and ceilingSpec.geometry then
                addPlacedModel(groups, "ceiling_" .. x .. "_" .. y,
                    { geometry = ceilingSpec.geometry }, x + 0.5, y + 0.5, "x")
            else
                local group = newGroup(groups, "ceiling_" .. x .. "_" .. y)
                addQuad(group,
                    { x = x, y = y + 1, z = 1 }, { x = x + 1, y = y + 1, z = 1 },
                    { x = x + 1, y = y, z = 1 }, { x = x, y = y, z = 1 },
                    surfaceUV(atlas, "ceiling", ceilingSpec), { 0, 0, -1 })
            end
        end
    end

    -- prepareResolvedStructure() resolves every exposed wall face independent
    -- of camera visibility, including composed image-authored wall geometry.
    for _, face in ipairs(faces or {}) do
        local baseName = "wall_" .. face.mapX .. "_" .. face.mapY .. "_" .. wallDirection(face)
        if not (face.meshSpec and face.meshSpec.coversFace) then
            local group = newGroup(groups, baseName)
            addQuad(group,
                { x = face.p1.x, y = face.p1.y, z = 0 },
                { x = face.p2.x, y = face.p2.y, z = 0 },
                { x = face.p2.x, y = face.p2.y, z = 1 },
                { x = face.p1.x, y = face.p1.y, z = 1 },
                face.uv, { face.normalX, face.normalY, 0 })
        end
        if face.meshSpec then
            addPlacedModel(groups, baseName .. "_geometry", face.meshSpec,
                face.centerX + face.normalX * 0.002,
                face.centerY + face.normalY * 0.002,
                nil, face.normalX, face.normalY)
        end
    end

    -- Structural openings are real geometry too: either a door kit mesh or the
    -- renderer's temporary two-jamb + lintel silhouette.
    if atlas then
        local function mix(a, b, t) return a + (b - a) * t end
        for _, cell in ipairs(structure.openingCells or {}) do
            local x, y, axis = cell.x, cell.y, cell.axis
            local doorSpec = viewport_3d.resolveWeightedVariant(
                tilesetDef.doors, x, y, 83492791, 39916801)
            if doorSpec and viewport_3d.meshSource(doorSpec) then
                addPlacedModel(groups, "opening_" .. x .. "_" .. y,
                    doorSpec, x + 0.5, y + 0.5, axis)
            else
                local originX = doorSpec and doorSpec.atlas
                    and doorSpec.atlas[2] * ATLAS_TILE or 0
                local originY = doorSpec and doorSpec.atlas
                    and doorSpec.atlas[1] * ATLAS_TILE
                    or ((tilesetDef.doorRow or 2) * ATLAS_TILE)
                local doorUV = atlasUV(originX, originY, ATLAS_TILE, ATLAS_TILE,
                    atlas.w, atlas.h, false)
                local u0, v0, u1, v1 = doorUV[1], doorUV[2], doorUV[3], doorUV[4]
                local group = newGroup(groups, "opening_" .. x .. "_" .. y)
                addOpeningQuad(group, x, y, axis, 0, 0.18, 0, 1,
                    { u0, v0, mix(u0, u1, 0.18), v1 })
                addOpeningQuad(group, x, y, axis, 0.82, 1, 0, 1,
                    { mix(u0, u1, 0.82), v0, u1, v1 })
                addOpeningQuad(group, x, y, axis, 0.18, 0.82, 0.82, 1,
                    { mix(u0, u1, 0.18), v0,
                        mix(u0, u1, 0.82), mix(v0, v1, 0.18) })
            end
        end
    end

    -- Runtime event pages decide whether an event currently presents as a 3D
    -- model or a billboard. Only the former is geometry and enters the OBJ.
    for index, placement in ipairs(viewport_3d.collectEventModelPlacements(session)) do
        local id = placement.event and placement.event.id or index
        addPlacedModel(groups, "event_" .. tostring(id),
            { model = placement.model }, placement.x, placement.y, "x")
    end

    return groups
end

function exporter.serialize(groups, metadata)
    metadata = metadata or {}
    local lines = {
        "# Second Rite runtime map geometry",
        "# geometry-only OBJ; textures/MTL intentionally deferred",
        "# map: " .. tostring(metadata.mapId or "runtime") .. " " .. tostring(metadata.mapName or ""),
        "# geometry quality: " .. tostring(metadata.quality or "CUSTOM")
            .. " density=" .. tostring(metadata.density or "?"),
        "o second_rite_map_" .. safeName(metadata.mapId or "runtime"),
    }
    local index = 0
    local triangles = 0
    for _, group in ipairs(groups or {}) do
        if #group.vertices > 0 then
            lines[#lines + 1] = "g " .. safeName(group.name)
            lines[#lines + 1] = "s off"
            local first = index + 1
            for _, source in ipairs(group.vertices) do
                local x, y, z = exporter.worldToObj(source.x, source.y, source.z)
                local nx, ny, nz = exporter.normalToObj(source.nx, source.ny, source.nz)
                lines[#lines + 1] = "v " .. number(x) .. " " .. number(y) .. " " .. number(z)
                -- obj_model.parse() flips OBJ V on import; invert here so an
                -- export/import round trip preserves the engine UV exactly.
                lines[#lines + 1] = "vt " .. number(source.u) .. " " .. number(1 - source.v)
                lines[#lines + 1] = "vn " .. number(nx) .. " " .. number(ny) .. " " .. number(nz)
                index = index + 1
            end
            for at = first, index, 3 do
                if at + 2 <= index then
                    lines[#lines + 1] = string.format("f %d/%d/%d %d/%d/%d %d/%d/%d",
                        at, at, at, at + 1, at + 1, at + 1, at + 2, at + 2, at + 2)
                    triangles = triangles + 1
                end
            end
        end
    end
    lines[#lines + 1] = ""
    return table.concat(lines, "\n"), {
        vertexCount = index,
        triangleCount = triangles,
        groupCount = #(groups or {}),
    }
end

function exporter.export(session)
    local groups, err = exporter.collect(session)
    if not groups then return nil, err end

    local mapData = session.currentMapData
    local mapId = mapData.id or session.currentMapIndex or "runtime"
    local mapName = mapData.name or ("map_" .. tostring(mapId))
    local text, stats = exporter.serialize(groups, {
        mapId = mapId,
        mapName = mapName,
        quality = quality.presetLabel(),
        density = string.format("%.2f", quality.density()),
    })

    local directory = "exports/maps"
    local okDir = love.filesystem.createDirectory(directory)
    if okDir == false then error("could not create map export directory", 0) end
    local relativePath = directory .. "/" .. safeName(mapId) .. "-" .. safeName(mapName) .. ".obj"
    local ok, writeErr = love.filesystem.write(relativePath, text)
    if not ok then
        error("could not write map geometry export: " .. tostring(writeErr), 0)
    end
    local absolutePath = love.filesystem.getSaveDirectory() .. "/" .. relativePath
    print(string.format("[map-geometry-export] %s (%d triangles, %d vertices, %d groups)",
        absolutePath, stats.triangleCount, stats.vertexCount, stats.groupCount))

    stats.relativePath = relativePath
    stats.absolutePath = absolutePath
    stats.mapId = mapId
    stats.mapName = mapName
    return stats
end

return exporter
