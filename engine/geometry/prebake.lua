-- Release-time deterministic geometry prebake (#161B).
--
-- This is intentionally narrow. It compiles the reusable height-authored plane
-- surfaces that a resolved tileset can ask geometry.loadAtlasSurface() for;
-- it does NOT serialize map topology, placed/world transforms, materials,
-- textures, LÖVE Mesh objects, or any GPU/driver state.
--
-- The exporter runs this against the already-materialized staging tree. That
-- means campaign overrides are visible, generated files never touch authored
-- sources, and target packagers remain ignorant of geometry compilation.
local geometry = require("engine.geometry")
local plane = require("engine.geometry.plane")
local quality = require("engine.geometry.quality")
local images = require("engine.geometry.images")
local store = require("engine.geometry.compiled_store")
local tilesetResolver = require("engine.tileset_resolver")
local json = require("data.json")

local prebake = {}
prebake.MANIFEST_VERSION = store.MANIFEST_VERSION
prebake.KIND = "tileset-height-plane"

local ATLAS_TILE = 64
local ATLAS_WALL_COLS = 4
local DEFAULT_DOOR_VARIANTS = 4

local function sortedKeys(tbl)
    local keys = {}
    for key in pairs(tbl or {}) do keys[#keys + 1] = key end
    table.sort(keys, function(a, b) return tostring(a) < tostring(b) end)
    return keys
end

local function join(root, name)
    if root:sub(-1) == "/" or root:sub(-1) == "\\" then return root .. name end
    return root .. "/" .. name
end

local function writeFile(path, contents, mode)
    local file, err = io.open(path, mode or "wb")
    if not file then error("geometry prebake cannot write " .. tostring(path) .. ": " .. tostring(err), 0) end
    local ok, writeErr = file:write(contents)
    file:close()
    if not ok then error("geometry prebake cannot write " .. tostring(path) .. ": " .. tostring(writeErr), 0) end
end

local function walkFiles(root, extension, out)
    out = out or {}
    local info = love.filesystem.getInfo(root)
    if not info then return out end
    if info.type == "file" then
        if not extension or root:sub(-#extension) == extension then out[#out + 1] = root end
        return out
    end
    local names = love.filesystem.getDirectoryItems(root)
    table.sort(names)
    for _, name in ipairs(names) do walkFiles(root .. "/" .. name, extension, out) end
    return out
end

local function addSource(set, path)
    if path and love.filesystem.getInfo(path) then set[path] = true end
end

local function heightScale(def, surface)
    local scale = def.heightMapScale
    if type(scale) == "table" then scale = scale[surface] or scale.default end
    return tonumber(scale or 0.08) or 0
end

local function specFor(def, surface, originX, originY)
    local columns = def.heightMapMeshColumns or 16
    local rows = def.heightMapMeshRows or 16
    return {
        id = "tileset_height_" .. surface .. "_" .. originX .. "_" .. originY,
        label = "tileset height map '" .. tostring(def.heightMap) .. "' " .. surface,
        topology = "plane",
        role = "surfaceFixture",
        surface = surface,
        heightOperation = def.heightMapOperation or "add",
        heightScale = heightScale(def, surface),
        meshColumns = columns,
        meshRows = rows,
        sampleColumns = def.heightMapSampleColumns or math.min(48, columns * 4),
        sampleRows = def.heightMapSampleRows or math.min(48, rows * 4),
        triangleBudget = def.heightMapTriangleBudget or 64,
        offset = def.heightMapOffset or 0.004,
        sealPerimeter = true,
    }
end

function prebake.runtimeKey(heightMapPath, surface, originX, originY, flipU, compilerVersion, qualityKey)
    local base = tostring(heightMapPath) .. ":" .. tostring(surface) .. ":"
        .. tostring(originX) .. "," .. tostring(originY) .. ":" .. tostring(flipU == true)
    return "atlas:v" .. tostring(compilerVersion or geometry.COMPILER_VERSION) .. ":" .. base
        .. "|" .. tostring(qualityKey or quality.key())
end

local imageDataCache = {}
local function imageData(path)
    if imageDataCache[path] then return imageDataCache[path] end
    local ok, data = pcall(love.image.newImageData, path)
    if not ok then error("geometry prebake cannot decode " .. tostring(path) .. ": " .. tostring(data), 0) end
    imageDataCache[path] = data
    return data
end

local function cropHeightTile(source, x, y, width, height)
    if source:getWidth() == width and source:getHeight() == height then return source end
    if x < 0 or y < 0 or x + width > source:getWidth() or y + height > source:getHeight() then
        error(string.format("geometry prebake atlas tile %d,%d %dx%d is outside %dx%d",
            x, y, width, height, source:getWidth(), source:getHeight()), 0)
    end
    local tile = love.image.newImageData(width, height)
    for row = 0, height - 1 do
        for column = 0, width - 1 do
            tile:setPixel(column, row, source:getPixel(x + column, y + row))
        end
    end
    return tile
end

local function sourceInfo(def)
    local id = def.id or "dungeon_default"
    local texturePath = def.texture or ("assets/tilesets/" .. id .. ".png")
    local heightPath = def.heightMap
    if not heightPath then return nil end
    if not love.filesystem.getInfo(texturePath) then
        error("geometry prebake tileset texture missing: " .. tostring(texturePath), 0)
    end
    if not love.filesystem.getInfo(heightPath) then
        error("geometry prebake tileset height map missing: " .. tostring(heightPath), 0)
    end
    local textureData = imageData(texturePath)
    local heightData = imageData(heightPath)
    local tileWidth = def.tileWidth or ATLAS_TILE
    local tileHeight = def.tileHeight or ATLAS_TILE
    local mode
    if heightData:getWidth() == textureData:getWidth() and heightData:getHeight() == textureData:getHeight() then
        mode = "atlas"
    elseif heightData:getWidth() == tileWidth and heightData:getHeight() == tileHeight then
        mode = "tile"
    else
        error("geometry prebake height map must match its texture atlas or one tile: "
            .. tostring(heightPath), 0)
    end
    return {
        texturePath = texturePath,
        heightPath = heightPath,
        textureWidth = textureData:getWidth(),
        textureHeight = textureData:getHeight(),
        heightData = heightData,
        mode = mode,
        tileWidth = tileWidth,
        tileHeight = tileHeight,
    }
end

local function descriptor(def, surface, variant, originX, originY, flipU, context)
    if not def.heightMap or not variant or variant.geometry or heightScale(def, surface) <= 0 then return nil end
    return {
        def = def,
        surface = surface,
        variant = variant,
        originX = originX,
        originY = originY,
        flipU = flipU == true,
        context = context,
    }
end

local function appendDescriptor(out, value)
    if value then out[#out + 1] = value end
end

local function wallRows(def)
    if type(def.wallRows) == "table" and #def.wallRows > 0 then return def.wallRows end
    local rows = {}
    for _, wall in ipairs(def.base and def.base.walls or {}) do
        if wall.middle and wall.middle[1] ~= nil then rows[#rows + 1] = wall.middle[1] end
    end
    if #rows == 0 then rows[1] = 1 end
    return rows
end

-- Enumerate exactly the atlas coordinates the current renderer can feed to
-- atlasHeightSurface for one resolved tileset. Both wall orientations matter:
-- west/south flip the height field as well as U, so they are distinct neutral
-- models. Door atlas cells use the selected base-wall height semantics.
local function descriptorsForResolvedTileset(def, context)
    local out = {}
    if not def or not def.heightMap then return out end
    local base = def.base or {}
    local walls = base.walls or {}

    for _, wall in ipairs(walls) do
        if not wall.geometry then
            if wall.middle then
                local ox, oy = (wall.middle[2] or 0) * ATLAS_TILE, (wall.middle[1] or 0) * ATLAS_TILE
                appendDescriptor(out, descriptor(def, "wall", wall, ox, oy, false, context))
                appendDescriptor(out, descriptor(def, "wall", wall, ox, oy, true, context))
            elseif wall.atlas then
                local ox, oy = (wall.atlas[2] or 0) * ATLAS_TILE, (wall.atlas[1] or 0) * ATLAS_TILE
                appendDescriptor(out, descriptor(def, "wall", wall, ox, oy, false, context))
                appendDescriptor(out, descriptor(def, "wall", wall, ox, oy, true, context))
            else
                for _, row in ipairs(wallRows(def)) do
                    for column = 0, ATLAS_WALL_COLS - 1 do
                        local ox, oy = column * ATLAS_TILE, row * ATLAS_TILE
                        appendDescriptor(out, descriptor(def, "wall", wall, ox, oy, false, context))
                        appendDescriptor(out, descriptor(def, "wall", wall, ox, oy, true, context))
                    end
                end
            end
        end
    end

    -- An atlas-only door still builds a wall relief at the door tile's origin;
    -- model/geometry-backed doors bypass atlasHeightSurface entirely.
    if #walls > 0 then
        for _, door in ipairs(def.doors or {}) do
            if not door.geometry and not door.model and door.atlas then
                for _, wall in ipairs(walls) do
                    if not wall.geometry then
                        local ox, oy = (door.atlas[2] or 0) * ATLAS_TILE, (door.atlas[1] or 0) * ATLAS_TILE
                        appendDescriptor(out, descriptor(def, "wall", wall, ox, oy, false, context))
                        appendDescriptor(out, descriptor(def, "wall", wall, ox, oy, true, context))
                    end
                end
            end
        end
        if #(def.doors or {}) == 0 and def.doorRow ~= nil then
            for _, wall in ipairs(walls) do
                if not wall.geometry then
                    for column = 0, DEFAULT_DOOR_VARIANTS - 1 do
                        local ox, oy = column * ATLAS_TILE, def.doorRow * ATLAS_TILE
                        appendDescriptor(out, descriptor(def, "wall", wall, ox, oy, false, context))
                        appendDescriptor(out, descriptor(def, "wall", wall, ox, oy, true, context))
                    end
                end
            end
        end
    end

    for _, floor in ipairs(base.floors or {}) do
        if not floor.geometry then
            local ox = floor.atlas and (floor.atlas[2] or 0) * ATLAS_TILE or 0
            local oy = floor.atlas and (floor.atlas[1] or 0) * ATLAS_TILE or 0
            appendDescriptor(out, descriptor(def, "floor", floor, ox, oy, false, context))
        end
    end
    for _, ceiling in ipairs(base.ceilings or {}) do
        if not ceiling.geometry then
            local ox = ceiling.atlas and (ceiling.atlas[2] or 0) * ATLAS_TILE or 0
            local oy = ceiling.atlas and (ceiling.atlas[1] or 0) * ATLAS_TILE or 0
            appendDescriptor(out, descriptor(def, "ceiling", ceiling, ox, oy, false, context))
        end
    end
    return out
end

local function compileDescriptor(item)
    local def = item.def
    local info = sourceInfo(def)
    local data = info.mode == "atlas"
        and cropHeightTile(info.heightData, item.originX, item.originY, info.tileWidth, info.tileHeight)
        or info.heightData
    if item.flipU then data = images.flipX(data) end
    local spec = specFor(def, item.surface, item.originX, item.originY)
    local function uv(u, v)
        local px = item.originX + 0.5 + u * (info.tileWidth - 1)
        local py = item.originY + 0.5 + v * (info.tileHeight - 1)
        if item.flipU then
            px = item.originX + info.tileWidth - 0.5 - u * (info.tileWidth - 1)
        end
        return px / info.textureWidth, py / info.textureHeight
    end
    local layers = { {
        data = data,
        scale = spec.heightScale,
        operation = spec.heightOperation,
    } }
    local model = plane.build(spec, layers, uv)
    local key = prebake.runtimeKey(info.heightPath, item.surface, item.originX, item.originY, item.flipU)
    return key, model, info, spec
end

local function canonicalSources(loader, referenced)
    local set = {}
    for _, path in ipairs(walkFiles(loader.root, ".json")) do set[path] = true end
    -- Compiler implementation is provenance too. COMPILER_VERSION is the API
    -- identifier; source hashes additionally make a forgotten version bump
    -- fail safe rather than silently accepting old geometry.
    for _, path in ipairs(walkFiles("engine/geometry", ".lua")) do set[path] = true end
    for path in pairs(referenced) do addSource(set, path) end

    local files = {}
    for _, path in ipairs(sortedKeys(set)) do
        local value = store.fileDigest(path)
        if not value then error("geometry prebake source became unreadable: " .. tostring(path), 0) end
        files[#files + 1] = { path = path, digest = value }
    end
    return files
end

local function q(value)
    return json.encode(value)
end

local function manifestJson(manifest)
    local lines = {
        "{",
        "  \"version\": " .. tostring(manifest.version) .. ",",
        "  \"formatVersion\": " .. tostring(manifest.formatVersion) .. ",",
        "  \"compilerVersion\": " .. tostring(manifest.compilerVersion) .. ",",
        "  \"quality\": " .. q(manifest.quality) .. ",",
        "  \"geometryClass\": " .. q(manifest.geometryClass) .. ",",
        "  \"sourceFiles\": [",
    }
    for index, source in ipairs(manifest.sourceFiles) do
        lines[#lines + 1] = "    {\"path\": " .. q(source.path) .. ", \"digest\": " .. q(source.digest) .. "}"
            .. (index < #manifest.sourceFiles and "," or "")
    end
    lines[#lines + 1] = "  ],"
    lines[#lines + 1] = "  \"entries\": ["
    for index, entry in ipairs(manifest.entries) do
        lines[#lines + 1] = "    {\"key\": " .. q(entry.key)
            .. ", \"file\": " .. q(entry.file)
            .. ", \"kind\": " .. q(entry.kind)
            .. ", \"label\": " .. q(entry.label) .. "}"
            .. (index < #manifest.entries and "," or "")
    end
    lines[#lines + 1] = "  ]"
    lines[#lines + 1] = "}"
    lines[#lines + 1] = ""
    return table.concat(lines, "\n")
end

function prebake.build(loader)
    if type(loader) ~= "table" or type(loader.maps) ~= "table" then
        error("geometry prebake requires an initialized data loader", 0)
    end
    local descriptors = {}
    for _, mapData in ipairs(loader.maps) do
        local def = tilesetResolver.resolve(loader, mapData)
        if def and def.heightMap then
            local context = "map " .. tostring(mapData.id) .. " / tileset "
                .. tostring((mapData and mapData.tileset) or def.id or "dungeon_default")
            local list = descriptorsForResolvedTileset(def, context)
            for _, item in ipairs(list) do descriptors[#descriptors + 1] = item end
        end
    end

    local byKey, byFile, referenced = {}, {}, {}
    for _, item in ipairs(descriptors) do
        local key, model, info, spec = compileDescriptor(item)
        referenced[info.heightPath] = true
        referenced[info.texturePath] = true
        local blob = store.encode(model, key)
        local existing = byKey[key]
        if existing then
            if existing.blob ~= blob then
                error("geometry prebake found one runtime cache key producing different neutral geometry: "
                    .. key .. " (" .. tostring(existing.context) .. " vs " .. tostring(item.context)
                    .. "). The runtime identity is insufficient; do not ship an ambiguous prebake.", 0)
            end
        else
            local file = store.artifactName(key)
            if byFile[file] and byFile[file] ~= key then
                error("geometry prebake artifact hash collision between distinct identities", 0)
            end
            byFile[file] = key
            byKey[key] = {
                key = key,
                file = file,
                blob = blob,
                context = item.context,
                label = spec.label .. " @ " .. item.originX .. "," .. item.originY
                    .. (item.flipU and " flipped" or ""),
            }
        end
    end

    local entries = {}
    for _, key in ipairs(sortedKeys(byKey)) do
        local entry = byKey[key]
        entries[#entries + 1] = {
            key = entry.key,
            file = entry.file,
            kind = prebake.KIND,
            label = entry.label,
            _blob = entry.blob,
        }
    end
    return {
        version = prebake.MANIFEST_VERSION,
        formatVersion = store.FORMAT_VERSION,
        compilerVersion = geometry.COMPILER_VERSION,
        quality = quality.key(),
        geometryClass = prebake.KIND,
        sourceFiles = canonicalSources(loader, referenced),
        entries = entries,
    }
end

function prebake.run(outputDir, loader)
    if type(outputDir) ~= "string" or outputDir == "" then
        error("geometry prebake requires an existing output directory", 0)
    end
    if not io or not io.open then error("geometry prebake needs io.open for the staging transform", 0) end
    local manifest = prebake.build(loader)
    for _, entry in ipairs(manifest.entries) do
        writeFile(join(outputDir, entry.file), entry._blob, "wb")
    end
    -- `_blob` is build memory only and must never appear in manifest metadata.
    for _, entry in ipairs(manifest.entries) do entry._blob = nil end
    writeFile(join(outputDir, "manifest.json"), manifestJson(manifest), "wb")
    return manifest
end

return prebake
