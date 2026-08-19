-- Authoritative, renderer-neutral snapshot of the static world surfaces that
-- Second Rite actually compiled for a loaded map.
--
-- This module owns no camera and performs no editor interaction. It asks the
-- runtime resolver/geometry compiler for the same surfaces the world renderer
-- uses, preserves semantic provenance, and packages the result into plain Lua
-- tables suitable for JSON transport or external-format serializers.
local viewport_3d = require("presentation.viewport_3d")
local obj_model = require("presentation.obj_model")
local mesh = require("presentation.mesh")
local geometry = require("engine.geometry")
local geometry_images = require("engine.geometry.images")
local geometry_visibility = require("engine.geometry.visibility_profile")
local tileset_resolver = require("engine.tileset_resolver")
local quality = require("engine.geometry.quality")
local instance_transport = require("presentation.renderable_instance_transport")

local bundle = {}
bundle.VERSION = 1

local ATLAS_TILE = 64

local function safeName(value)
    local name = tostring(value or "unnamed")
        :gsub("[%c%s]+", "_")
        :gsub("[^%w_%-%.]", "_")
        :gsub("_+", "_")
        :gsub("^_+", "")
        :gsub("_+$", "")
    return name ~= "" and name or "unnamed"
end

local function newSurface(surfaces, name, source, material)
    local surface = {
        id = safeName(name),
        name = safeName(name),
        source = source,
        material = material,
        positions = {},
        uvs = {},
        normals = {},
        colors = {},
    }
    surfaces[#surfaces + 1] = surface
    return surface
end

local function pushVertex(surface, value)
    local positions, uvs = surface.positions, surface.uvs
    local normals, colors = surface.normals, surface.colors
    positions[#positions + 1] = value[1]
    positions[#positions + 1] = value[2]
    positions[#positions + 1] = value[3]
    uvs[#uvs + 1] = value[4] or 0
    uvs[#uvs + 1] = value[5] or 0
    normals[#normals + 1] = value[6] or 0
    normals[#normals + 1] = value[7] or 0
    normals[#normals + 1] = value[8] or 1
    colors[#colors + 1] = value[9] or 1
    colors[#colors + 1] = value[10] or 1
    colors[#colors + 1] = value[11] or 1
    colors[#colors + 1] = value[12] or 1
end

local function vertex(x, y, z, u, v, nx, ny, nz, r, g, b, a)
    return { x, y, z, u or 0, v or 0, nx or 0, ny or 0, nz or 1,
        r or 1, g or 1, b or 1, a or 1 }
end

local function addQuad(surface, a, b, c, d, uv, normal)
    uv = uv or { 0, 0, 1, 1 }
    normal = normal or { 0, 0, 1 }
    local function at(point, u, v)
        return vertex(point.x, point.y, point.z, u, v,
            normal[1], normal[2], normal[3])
    end
    pushVertex(surface, at(a, uv[1], uv[2]))
    pushVertex(surface, at(b, uv[3], uv[2]))
    pushVertex(surface, at(c, uv[3], uv[4]))
    pushVertex(surface, at(a, uv[1], uv[2]))
    pushVertex(surface, at(c, uv[3], uv[4]))
    pushVertex(surface, at(d, uv[1], uv[4]))
end

local function atlasUV(originX, originY, width, height, texW, texH, flipU)
    local u0 = (originX + 0.5) / texW
    local u1 = (originX + width - 0.5) / texW
    local v0 = (originY + 0.5) / texH
    local v1 = (originY + height - 0.5) / texH
    if flipU then u0, u1 = u1, u0 end
    return { u0, v0, u1, v1 }
end

local function cellSource(x, y, surface, extra)
    local source = {
        kind = "cell",
        -- Runtime map-grid coordinates are one-based; authored map/event
        -- coordinates are zero-based. Preserve both rather than making a
        -- consumer infer which convention a mesh placement used.
        x = x - 1,
        y = y - 1,
        runtimeX = x,
        runtimeY = y,
        surface = surface,
    }
    for key, value in pairs(extra or {}) do source[key] = value end
    return source
end

local function imagePayloadFromData(data)
    local png = data:encode("png")
    return {
        kind = "embedded-png",
        mime = "image/png",
        width = data:getWidth(),
        height = data:getHeight(),
        base64 = love.data.encode("string", "base64", png),
    }
end

local function imagePayloadFromCanvas(canvas)
    return imagePayloadFromData(canvas:newImageData())
end

local function assetPayload(path)
    if not path then return nil end
    return { kind = "project-asset", path = path }
end

local function newMaterialRegistry()
    return {
        list = {},
        byKey = {},
        byDrawable = setmetatable({}, { __mode = "k" }),
        composedAlbedo = {},
    }
end

local function registerMaterial(registry, key, spec)
    if key and registry.byKey[key] then return registry.byKey[key] end
    local id = string.format("material_%03d", #registry.list + 1)
    local material = {
        id = id,
        color = spec.color or { 1, 1, 1, 1 },
        albedo = spec.albedo,
        emission = spec.emission,
    }
    registry.list[#registry.list + 1] = material
    if key then registry.byKey[key] = id end
    return id
end

local function registerAssetMaterial(registry, path, glowPath, color)
    local key = "asset:" .. tostring(path or "") .. "|glow:" .. tostring(glowPath or "")
    return registerMaterial(registry, key, {
        color = color,
        albedo = assetPayload(path),
        emission = assetPayload(glowPath),
    })
end

local function registerCanvasMaterial(registry, texture, glowTexture, color)
    if not texture then
        return registerMaterial(registry, "flat:" .. table.concat(color or { 1, 1, 1, 1 }, ","), {
            color = color,
        })
    end
    local byTexture = registry.byDrawable[texture]
    if byTexture and (not glowTexture or byTexture.glow == glowTexture) then
        return byTexture.id
    end
    if not (texture.typeOf and texture:typeOf("Canvas")) then
        error("renderable material has a runtime image but no project source path", 0)
    end
    local spec = { color = color, albedo = imagePayloadFromCanvas(texture) }
    if glowTexture then
        if not (glowTexture.typeOf and glowTexture:typeOf("Canvas")) then
            error("renderable emission map has no project source path", 0)
        end
        spec.emission = imagePayloadFromCanvas(glowTexture)
    end
    local id = registerMaterial(registry, nil, spec)
    registry.byDrawable[texture] = { id = id, glow = glowTexture }
    return id
end

local function registerWallMaterial(registry, face, atlas)
    if not face.texture then
        return registerMaterial(registry, "flat-wall", { color = { 1, 1, 1, 1 } })
    end
    if face.texture.typeOf and face.texture:typeOf("Canvas") then
        return registerCanvasMaterial(registry, face.texture, face.glowTexture, { 1, 1, 1, 1 })
    end
    if atlas and atlas.texturePath then
        return registerAssetMaterial(registry, atlas.texturePath,
            face.glowTexture and atlas.glowPath or nil, { 1, 1, 1, 1 })
    end
    return registerMaterial(registry, "flat-wall", { color = { 1, 1, 1, 1 } })
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
        texturePath = texturePath,
        glowPath = tilesetDef.glowMap,
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
    error("map renderable placement has no mesh source", 0)
end

local function modelMaterial(registry, model, modelGroup, context)
    local color = modelGroup.color or { 1, 1, 1, 1 }
    if modelGroup.texturePath then
        return registerAssetMaterial(registry, modelGroup.texturePath, nil, color)
    end
    if context and context.texturePath and modelGroup.texture then
        return registerAssetMaterial(registry, context.texturePath, context.glowPath, color)
    end
    if model.assetPaths and #model.assetPaths > 1 and modelGroup.texture then
        local key = table.concat(model.assetPaths, "\n")
        local cached = registry.composedAlbedo[key]
        if not cached then
            local albedo = geometry.debugFields(model.assetPaths)
            cached = imagePayloadFromData(albedo)
            registry.composedAlbedo[key] = cached
        end
        return registerMaterial(registry, "geometry-composite:" .. key, {
            color = color,
            albedo = cached,
        })
    end
    if modelGroup.texture then
        error("compiled model texture has no reproducible material source", 0)
    end
    return registerMaterial(registry,
        "flat-model:" .. tostring(modelGroup.material or "") .. ":" .. table.concat(color, ","),
        { color = color })
end

local function orientPlacedXY(x, y, axis, normalX, normalY)
    if normalX or normalY then
        return viewport_3d.wallModelFrame(x, y, normalX, normalY)
    elseif axis == "y" then
        return -y, x
    end
    return x, y
end

local function placedTransform(originX, originY, axis, normalX, normalY)
    local xx, xy = orientPlacedXY(1, 0, axis, normalX, normalY)
    local yx, yy = orientPlacedXY(0, 1, axis, normalX, normalY)
    return {
        translation = { originX, originY, 0 },
        -- Row-major 2x2 matrix. Consumers apply this exact runtime-authored
        -- orientation to local positions and normals; they do not infer wall or
        -- opening semantics from `source`.
        matrix2d = { xx, yx, xy, yy },
    }
end

local function addPlacedModel(surfaces, registry, name, source, spec,
        originX, originY, axis, normalX, normalY, materialContext)
    local model = modelFor(spec)
    for groupIndex, modelGroup in ipairs(model.groups or {}) do
        local materialName = modelGroup.material
        local suffix = (materialName and materialName ~= "") and materialName or ("part_" .. groupIndex)
        local surface = newSurface(surfaces, name .. "_" .. suffix, source,
            modelMaterial(registry, model, modelGroup, materialContext))
        if instance_transport.capturing() then
            surface._instanceTransport = instance_transport.capture(
                model, groupIndex, modelGroup,
                placedTransform(originX, originY, axis, normalX, normalY))
        end
        for _, sourceVertex in ipairs(modelGroup.vertices or {}) do
            local lx, ly, lz = sourceVertex[1], sourceVertex[2], sourceVertex[3]
            local nx, ny, nz = sourceVertex[6] or 0, sourceVertex[7] or 0, sourceVertex[8] or 1
            lx, ly = orientPlacedXY(lx, ly, axis, normalX, normalY)
            nx, ny = orientPlacedXY(nx, ny, axis, normalX, normalY)
            pushVertex(surface, vertex(
                originX + lx, originY + ly, lz,
                sourceVertex[4], sourceVertex[5], nx, ny, nz,
                sourceVertex[9], sourceVertex[10], sourceVertex[11], sourceVertex[12]))
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

local function addOpeningQuad(surface, x, y, axis, lo, hi, bottom, top, uv)
    if axis == "x" then
        local wx = x + 0.5
        addQuad(surface,
            { x = wx, y = y + lo, z = bottom },
            { x = wx, y = y + hi, z = bottom },
            { x = wx, y = y + hi, z = top },
            { x = wx, y = y + lo, z = top },
            uv, { 1, 0, 0 })
    else
        local wy = y + 0.5
        addQuad(surface,
            { x = x + hi, y = wy, z = bottom },
            { x = x + lo, y = wy, z = bottom },
            { x = x + lo, y = wy, z = top },
            { x = x + hi, y = wy, z = top },
            uv, { 0, 1, 0 })
    end
end

function bundle.validate(value)
    if type(value) ~= "table" or value.version ~= bundle.VERSION then
        error("renderable bundle version mismatch", 0)
    end
    local materialIds = {}
    for _, material in ipairs(value.materials or {}) do
        if type(material.id) ~= "string" or material.id == "" then
            error("renderable material needs an id", 0)
        end
        if materialIds[material.id] then
            error("duplicate renderable material id: " .. material.id, 0)
        end
        materialIds[material.id] = true
    end
    for _, surface in ipairs(value.surfaces or {}) do
        local positions = surface.positions or {}
        local vertexCount = #positions / 3
        if vertexCount ~= math.floor(vertexCount) or vertexCount % 3 ~= 0 then
            error("renderable surface '" .. tostring(surface.id) .. "' is not a triangle list", 0)
        end
        if #(surface.uvs or {}) ~= vertexCount * 2
                or #(surface.normals or {}) ~= vertexCount * 3
                or #(surface.colors or {}) ~= vertexCount * 4 then
            error("renderable surface '" .. tostring(surface.id)
                .. "' attribute streams have different vertex counts", 0)
        end
        if surface.material and not materialIds[surface.material] then
            error("renderable surface '" .. tostring(surface.id)
                .. "' references unknown material '" .. tostring(surface.material) .. "'", 0)
        end
        if type(surface.source) ~= "table" or not surface.source.kind then
            error("renderable surface '" .. tostring(surface.id) .. "' has no semantic source", 0)
        end
    end
    return true
end

local function summarize(surfaces, materials)
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
        viewport_3d.prepareResolvedStructure(session, profile.name)
    if not structure then return nil, "No runtime map geometry is available." end
    local mapData = session.currentMapData
    local atlas = atlasInfo(session)
    local tilesetDef = atlas and atlas.definition or nil
    local surfaces = {}
    local registry = newMaterialRegistry()
    local atlasMaterial = atlas and registerAssetMaterial(registry,
        atlas.texturePath, atlas.glowPath, { 1, 1, 1, 1 }) or nil

    for _, cell in ipairs(structure.floorCells or {}) do
        local x, y = cell.x, cell.y
        local floorSource = cellSource(x, y, "floor")
        local floorSpec = atlas and viewport_3d.resolveWeightedVariant(
            tilesetDef.base and tilesetDef.base.floors,
            x, y, 961748927, 982451653) or nil
        local floorOriginX, floorOriginY = variantAtlasOrigin(atlas, "floor", floorSpec)
        local floorHeight = floorSpec and not floorSpec.geometry
            and atlasHeightSurface(atlas, "floor", floorSpec,
                floorOriginX, floorOriginY, false) or nil
        if floorHeight then
            addPlacedModel(surfaces, registry, "floor_" .. x .. "_" .. y,
                floorSource, floorHeight, x + 0.5, y + 0.5, "x", nil, nil,
                { texturePath = atlas.texturePath, glowPath = atlas.glowPath })
        elseif floorSpec and floorSpec.geometry then
            addPlacedModel(surfaces, registry, "floor_" .. x .. "_" .. y,
                floorSource, { geometry = floorSpec.geometry }, x + 0.5, y + 0.5, "x")
        else
            local surface = newSurface(surfaces, "floor_" .. x .. "_" .. y,
                floorSource, atlasMaterial)
            addQuad(surface,
                { x = x, y = y, z = 0 }, { x = x + 1, y = y, z = 0 },
                { x = x + 1, y = y + 1, z = 0 }, { x = x, y = y + 1, z = 0 },
                surfaceUV(atlas, "floor", floorSpec), { 0, 0, 1 })
        end

        local featureId = structure.materialLookup[x .. "," .. y]
        local feature = atlas and atlas.features[featureId or ""] or nil
        if feature and feature.role == "floor_feature" then
            local source = cellSource(x, y, "floor-feature", { featureId = feature.id })
            if viewport_3d.meshSource(feature) then
                addPlacedModel(surfaces, registry, "floor_feature_" .. x .. "_" .. y,
                    source, feature, x + 0.5, y + 0.5, "x")
            end
            if feature.atlas then
                local surface = newSurface(surfaces, "floor_feature_atlas_" .. x .. "_" .. y,
                    source, atlasMaterial)
                addQuad(surface,
                    { x = x, y = y, z = 0.002 }, { x = x + 1, y = y, z = 0.002 },
                    { x = x + 1, y = y + 1, z = 0.002 }, { x = x, y = y + 1, z = 0.002 },
                    atlasUV(feature.atlas[2] * ATLAS_TILE, feature.atlas[1] * ATLAS_TILE,
                        ATLAS_TILE, ATLAS_TILE, atlas.w, atlas.h, false),
                    { 0, 0, 1 })
            end
        end

        if geometry_visibility.walkableCeilingVisible(
                profile.name, mapData.ceilingStyle) then
            local ceilingSource = cellSource(x, y, "ceiling")
            local ceilingSpec = atlas and viewport_3d.resolveWeightedVariant(
                tilesetDef.base and tilesetDef.base.ceilings,
                x, y, 15485863, 32452843) or nil
            local ceilingOriginX, ceilingOriginY = variantAtlasOrigin(atlas, "ceiling", ceilingSpec)
            local ceilingHeight = ceilingSpec and not ceilingSpec.geometry
                and atlasHeightSurface(atlas, "ceiling", ceilingSpec,
                    ceilingOriginX, ceilingOriginY, false) or nil
            if ceilingHeight then
                addPlacedModel(surfaces, registry, "ceiling_" .. x .. "_" .. y,
                    ceilingSource, ceilingHeight, x + 0.5, y + 0.5, "x", nil, nil,
                    { texturePath = atlas.texturePath, glowPath = atlas.glowPath })
            elseif ceilingSpec and ceilingSpec.geometry then
                addPlacedModel(surfaces, registry, "ceiling_" .. x .. "_" .. y,
                    ceilingSource, { geometry = ceilingSpec.geometry }, x + 0.5, y + 0.5, "x")
            else
                local surface = newSurface(surfaces, "ceiling_" .. x .. "_" .. y,
                    ceilingSource, atlasMaterial)
                addQuad(surface,
                    { x = x, y = y + 1, z = 1 }, { x = x + 1, y = y + 1, z = 1 },
                    { x = x + 1, y = y, z = 1 }, { x = x, y = y, z = 1 },
                    surfaceUV(atlas, "ceiling", ceilingSpec), { 0, 0, -1 })
            end
        end
    end

    if geometry_visibility.wallTopVisible(profile.name) then
        local fallbackWallTopMaterial
        for _, cell in ipairs(structure.wallCells or {}) do
            local x, y = cell.x, cell.y
            local source = cellSource(x, y, "wall-top")
            local wallTopSpec = atlas and viewport_3d.resolveWallTopVariant(tilesetDef, x, y) or nil
            if wallTopSpec then
                local originX, originY = variantAtlasOrigin(atlas, "wallTop", wallTopSpec)
                local heightSpec = not wallTopSpec.geometry
                    and atlasHeightSurface(atlas, "wallTop", wallTopSpec, originX, originY, false) or nil
                if heightSpec then
                    addPlacedModel(surfaces, registry, "wall_top_" .. x .. "_" .. y,
                        source, heightSpec, x + 0.5, y + 0.5, "x", nil, nil,
                        { texturePath = atlas.texturePath, glowPath = atlas.glowPath })
                elseif wallTopSpec.geometry then
                    addPlacedModel(surfaces, registry, "wall_top_" .. x .. "_" .. y,
                        source, { geometry = wallTopSpec.geometry }, x + 0.5, y + 0.5, "x")
                else
                    local surface = newSurface(surfaces, "wall_top_" .. x .. "_" .. y,
                        source, atlasMaterial)
                    addQuad(surface,
                        { x = x, y = y, z = 1 }, { x = x + 1, y = y, z = 1 },
                        { x = x + 1, y = y + 1, z = 1 }, { x = x, y = y + 1, z = 1 },
                        surfaceUV(atlas, "wallTop", wallTopSpec), { 0, 0, 1 })
                end
            else
                if not fallbackWallTopMaterial then
                    fallbackWallTopMaterial = registerMaterial(registry, "structural:wall-top", {
                        color = { 0.72, 0.72, 0.72, 1 },
                    })
                end
                local surface = newSurface(surfaces, "wall_top_" .. x .. "_" .. y,
                    source, fallbackWallTopMaterial)
                addQuad(surface,
                    { x = x, y = y, z = 1 }, { x = x + 1, y = y, z = 1 },
                    { x = x + 1, y = y + 1, z = 1 }, { x = x, y = y + 1, z = 1 },
                    { 0, 0, 1, 1 }, { 0, 0, 1 })
            end
        end
    end

    for _, face in ipairs(faces or {}) do
        local direction = wallDirection(face)
        local baseName = "wall_" .. face.mapX .. "_" .. face.mapY .. "_" .. direction
        local source = cellSource(face.mapX, face.mapY, direction .. "-wall")
        if not (face.meshSpec and face.meshSpec.coversFace) then
            local surface = newSurface(surfaces, baseName, source,
                registerWallMaterial(registry, face, atlas))
            addQuad(surface,
                { x = face.p1.x, y = face.p1.y, z = 0 },
                { x = face.p2.x, y = face.p2.y, z = 0 },
                { x = face.p2.x, y = face.p2.y, z = 1 },
                { x = face.p1.x, y = face.p1.y, z = 1 },
                face.uv, { face.normalX, face.normalY, 0 })
        end
        if face.meshSpec then
            addPlacedModel(surfaces, registry, baseName .. "_geometry", source,
                face.meshSpec,
                face.centerX + face.normalX * 0.002,
                face.centerY + face.normalY * 0.002,
                nil, face.normalX, face.normalY,
                face.meshSpec.runtimeSurface and atlas and {
                    texturePath = atlas.texturePath, glowPath = atlas.glowPath,
                } or nil)
        end
    end

    if atlas then
        local function mix(a, b, t) return a + (b - a) * t end
        for _, cell in ipairs(structure.openingCells or {}) do
            local x, y, axis = cell.x, cell.y, cell.axis
            local source = cellSource(x, y, "opening", { axis = axis })
            local doorSpec = viewport_3d.resolveWeightedVariant(
                tilesetDef.doors, x, y, 83492791, 39916801)
            if doorSpec and viewport_3d.meshSource(doorSpec) then
                addPlacedModel(surfaces, registry, "opening_" .. x .. "_" .. y,
                    source, doorSpec, x + 0.5, y + 0.5, axis)
            else
                local originX = doorSpec and doorSpec.atlas
                    and doorSpec.atlas[2] * ATLAS_TILE or 0
                local originY = doorSpec and doorSpec.atlas
                    and doorSpec.atlas[1] * ATLAS_TILE
                    or ((tilesetDef.doorRow or 2) * ATLAS_TILE)
                local doorUV = atlasUV(originX, originY, ATLAS_TILE, ATLAS_TILE,
                    atlas.w, atlas.h, false)
                local u0, v0, u1, v1 = doorUV[1], doorUV[2], doorUV[3], doorUV[4]
                local surface = newSurface(surfaces, "opening_" .. x .. "_" .. y,
                    source, atlasMaterial)
                addOpeningQuad(surface, x, y, axis, 0, 0.18, 0, 1,
                    { u0, v0, mix(u0, u1, 0.18), v1 })
                addOpeningQuad(surface, x, y, axis, 0.82, 1, 0, 1,
                    { mix(u0, u1, 0.82), v0, u1, v1 })
                addOpeningQuad(surface, x, y, axis, 0.18, 0.82, 0.82, 1,
                    { mix(u0, u1, 0.18), v0,
                        mix(u0, u1, 0.82), mix(v0, v1, 0.18) })
            end
        end
    end

    for index, placement in ipairs(viewport_3d.collectEventModelPlacements(session)) do
        local id = placement.event and placement.event.id or index
        addPlacedModel(surfaces, registry, "event_" .. tostring(id),
            { kind = "event", id = id },
            { model = placement.model }, placement.x, placement.y, "x")
    end

    local mapId = mapData.id or session.currentMapIndex or "runtime"
    local mapName = mapData.name or mapData.title or ("map_" .. tostring(mapId))
    local stats = summarize(surfaces, registry.list)
    stats.visibility = visibilityStats
    local result = {
        version = bundle.VERSION,
        geometryProfile = profile.name,
        map = { id = mapId, name = mapName },
        coordinateSystem = {
            handedness = "right",
            up = "z",
            unit = "map-cell",
            runtimeGridOrigin = { x = 1, y = 1 },
            authoredGridOrigin = { x = 0, y = 0 },
            uvOrigin = "top-left",
        },
        quality = {
            preset = quality.presetLabel(),
            density = quality.density(),
        },
        materials = registry.list,
        surfaces = surfaces,
        stats = stats,
    }
    bundle.validate(result)
    return result
end

return bundle
