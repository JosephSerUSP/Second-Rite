-- Developer-only runtime map geometry export.
--
-- Authoritative map collection does not belong to the OBJ serializer. The
-- engine-owned `presentation.map_renderable_bundle` resolves runtime structure,
-- compiled height geometry, event models, material identity and semantic
-- provenance once; OBJ/MTL are consumers of that neutral result.
local renderable_bundle = require("presentation.map_renderable_bundle")

local exporter = {}

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

local function materialNames(renderable)
    local names = {}
    local used = {}
    for index, material in ipairs(renderable and renderable.materials or {}) do
        local id = material.id
        if type(id) ~= "string" or id == "" then
            error("renderable material needs an id", 0)
        end
        local name = safeName(id)
        if used[name] and used[name] ~= id then
            name = string.format("material_%03d_%s", index, name)
        end
        used[name] = id
        names[id] = name
    end
    return names
end

local function textureExtension(albedo)
    if albedo and albedo.kind == "embedded-png" then return ".png" end
    local extension = albedo and albedo.path and albedo.path:match("(%.[%w]+)$") or nil
    return extension and extension:lower() or ".png"
end

local function textureStem(albedo)
    if albedo and albedo.kind == "project-asset" then
        local normalized = tostring(albedo.path or ""):gsub("\\", "/")
        local basename = normalized:match("([^/]+)$") or "asset"
        local stem = basename:gsub("%.[^%.]+$", "")
        return safeName(stem)
    end
    return "embedded"
end

local function albedoIdentity(albedo, materialId)
    if albedo.kind == "project-asset" then
        if type(albedo.path) ~= "string" or albedo.path == "" then
            error("project-asset albedo for " .. tostring(materialId) .. " has no path", 0)
        end
        return "project-asset", albedo.path
    end
    if albedo.kind == "embedded-png" then
        if type(albedo.base64) ~= "string" or albedo.base64 == "" then
            error("embedded-png albedo for " .. tostring(materialId) .. " has no payload", 0)
        end
        -- Use the exact resolved payload string as the key. Lua strings are
        -- immutable/interned values here, so this avoids allocating another
        -- full-sized prefixed copy for large runtime-composed wall textures.
        return "embedded-png", albedo.base64
    end
    error(string.format("unsupported albedo payload for %s: %s",
        tostring(materialId), tostring(albedo.kind)), 0)
end

local function albedoBytes(albedo, materialId)
    if albedo.kind == "project-asset" then
        local data, readErr = love.filesystem.read(albedo.path)
        if not data then
            error(string.format("could not read albedo for %s: %s",
                tostring(materialId), tostring(readErr or albedo.path)), 0)
        end
        return data
    end
    if albedo.kind == "embedded-png" then
        if not love.data or not love.data.decode then
            error("embedded material export requires love.data.decode", 0)
        end
        local ok, decoded = pcall(love.data.decode, "string", "base64", albedo.base64 or "")
        if not ok then
            error(string.format("could not decode embedded albedo for %s: %s",
                tostring(materialId), tostring(decoded)), 0)
        end
        return decoded
    end
    error(string.format("unsupported albedo payload for %s: %s",
        tostring(materialId), tostring(albedo.kind)), 0)
end

-- Produce the portable texture layout without touching the filesystem. Texture
-- files are deduplicated by the resolved albedo payload, not by material id:
-- distinct materials may differ in tint/emission while sharing one diffuse map.
function exporter.planTextures(renderable)
    local plan = {
        byMaterial = {},
        entries = {},
        textureCount = 0,
    }
    local byKind = {
        ["project-asset"] = {},
        ["embedded-png"] = {},
    }

    for _, material in ipairs(renderable and renderable.materials or {}) do
        if material.albedo then
            local kind, identity = albedoIdentity(material.albedo, material.id)
            local entry = byKind[kind][identity]
            if not entry then
                local index = #plan.entries + 1
                local fileName = string.format("texture_%03d_%s%s",
                    index, textureStem(material.albedo), textureExtension(material.albedo))
                entry = {
                    materialId = material.id,
                    albedo = material.albedo,
                    fileName = fileName,
                    mtlPath = "textures/" .. fileName,
                }
                byKind[kind][identity] = entry
                plan.entries[#plan.entries + 1] = entry
            end
            plan.byMaterial[material.id] = entry.mtlPath
        end
    end

    plan.textureCount = #plan.entries
    return plan
end

-- Write the planned albedos under one map-local `textures/` directory. Project
-- assets are copied from the LÖVE VFS; embedded runtime-composed PNGs are decoded
-- from the bundle payload and written as actual PNG files.
function exporter.writeTextures(renderable, exportDirectory, plan)
    plan = plan or exporter.planTextures(renderable)
    if plan.textureCount == 0 then
        return plan.byMaterial, 0, plan
    end

    local textureDirectory = exportDirectory .. "/textures"
    local okDir = love.filesystem.createDirectory(textureDirectory)
    if okDir == false then error("could not create map texture export directory", 0) end

    for _, entry in ipairs(plan.entries) do
        local relativePath = exportDirectory .. "/" .. entry.mtlPath
        local bytes = albedoBytes(entry.albedo, entry.materialId)
        local ok, writeErr = love.filesystem.write(relativePath, bytes)
        if not ok then
            error("could not write map material texture: " .. tostring(writeErr), 0)
        end
    end

    return plan.byMaterial, plan.textureCount, plan
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

function exporter.collect(session)
    return renderable_bundle.collect(session)
end

local function surfaceVertex(surface, index)
    local p = (index - 1) * 3
    local t = (index - 1) * 2
    local c = (index - 1) * 4
    return {
        x = surface.positions[p + 1], y = surface.positions[p + 2], z = surface.positions[p + 3],
        u = surface.uvs[t + 1] or 0, v = surface.uvs[t + 2] or 0,
        nx = surface.normals[p + 1] or 0, ny = surface.normals[p + 2] or 0, nz = surface.normals[p + 3] or 1,
        r = surface.colors[c + 1] or 1, g = surface.colors[c + 2] or 1,
        b = surface.colors[c + 3] or 1, a = surface.colors[c + 4] or 1,
    }
end

-- OBJ currently serializes position, UV, and normal per vertex. Bundle vertex
-- colour is intentionally not part of this identity because OBJ does not emit
-- it; resolved material colour remains face-scoped through usemtl/MTL. The key
-- is built from the exact canonical numeric strings written below, so welding
-- introduces no extra tolerance: only corners that the old exporter would have
-- serialized identically can share an index.
local function serializedVertex(source)
    local x, y, z = exporter.worldToObj(source.x, source.y, source.z)
    local nx, ny, nz = exporter.normalToObj(source.nx, source.ny, source.nz)
    local values = {
        number(x), number(y), number(z),
        number(source.u), number(1 - source.v),
        number(nx), number(ny), number(nz),
    }
    return table.concat(values, "\31"), {
        "v " .. values[1] .. " " .. values[2] .. " " .. values[3],
        "vt " .. values[4] .. " " .. values[5],
        "vn " .. values[6] .. " " .. values[7] .. " " .. values[8],
    }
end

function exporter.serializeMaterials(renderable, options)
    options = options or {}
    local textureFiles = options.textureFiles or {}
    local names = materialNames(renderable)
    local lines = {
        "# Second Rite runtime map materials",
        "# material identity comes from the authoritative renderable bundle",
        "# albedo textures live under this export package's textures/ directory",
        "# map_Kd paths are relative; no source-checkout or machine-specific paths are required",
        "# emission/glow textures are not exported: Wavefront MTL has no portable emissive texture slot",
    }
    local count = 0
    for _, material in ipairs(renderable and renderable.materials or {}) do
        count = count + 1
        local color = material.color or { 1, 1, 1, 1 }
        local alpha = color[4]
        if alpha == nil then alpha = 1 end
        lines[#lines + 1] = ""
        lines[#lines + 1] = "newmtl " .. names[material.id]
        lines[#lines + 1] = "Kd " .. number(color[1] or 1) .. " "
            .. number(color[2] or 1) .. " " .. number(color[3] or 1)
        lines[#lines + 1] = "d " .. number(alpha)
        lines[#lines + 1] = "illum 1"
        if textureFiles[material.id] then
            lines[#lines + 1] = "map_Kd " .. textureFiles[material.id]
        elseif material.albedo then
            lines[#lines + 1] = "# albedo payload present but no exported texture path was supplied"
        end
        if material.emission then
            lines[#lines + 1] = "# emission/glow payload present but intentionally not serialized"
        end
    end
    lines[#lines + 1] = ""
    return table.concat(lines, "\n"), { materialCount = count }
end

function exporter.serialize(renderable, metadata)
    metadata = metadata or {}
    local surfaces = renderable and renderable.surfaces or renderable or {}
    local materials = renderable and renderable.materials or {}
    local names = materialNames(renderable)
    local map = renderable and renderable.map or {}
    local quality = renderable and renderable.quality or {}
    local mapId = metadata.mapId or map.id or "runtime"
    local mapName = metadata.mapName or map.name or ""
    local qualityLabel = metadata.quality or quality.preset or "CUSTOM"
    local density = metadata.density or quality.density or "?"
    local materialLibrary = metadata.materialLibrary
        or ("second_rite_map_" .. safeName(mapId) .. ".mtl")

    local lines = {
        "# Second Rite runtime map geometry",
        "# geometry and material identity come from the authoritative renderable bundle",
        "# material albedos are export-local and referenced through the sibling MTL",
        "# vertices share indices only when serialized position, UV, and normal are identical",
        "# map: " .. tostring(mapId) .. " " .. tostring(mapName),
        "# geometry quality: " .. tostring(qualityLabel) .. " density=" .. tostring(density),
    }
    if #materials > 0 then
        lines[#lines + 1] = "mtllib " .. materialLibrary
    end
    lines[#lines + 1] = "o second_rite_map_" .. safeName(mapId)

    local index = 0
    local sourceVertexCount = 0
    local triangles = 0
    local nonEmptySurfaces = 0
    local byVertex = {}
    for _, surface in ipairs(surfaces) do
        local vertexCount = math.floor(#(surface.positions or {}) / 3)
        if vertexCount > 0 then
            nonEmptySurfaces = nonEmptySurfaces + 1
            lines[#lines + 1] = "g " .. safeName(surface.name or surface.id)
            lines[#lines + 1] = "s off"
            if #materials > 0 then
                local materialName = names[surface.material]
                if not materialName then
                    error("renderable surface references unknown material: " .. tostring(surface.material), 0)
                end
                lines[#lines + 1] = "usemtl " .. materialName
            end

            local newVertexLines = {}
            local faceIndices = {}
            for localIndex = 1, vertexCount do
                sourceVertexCount = sourceVertexCount + 1
                local source = surfaceVertex(surface, localIndex)
                local key, vertexLines = serializedVertex(source)
                local vertexIndex = byVertex[key]
                if not vertexIndex then
                    index = index + 1
                    vertexIndex = index
                    byVertex[key] = vertexIndex
                    for _, line in ipairs(vertexLines) do
                        newVertexLines[#newVertexLines + 1] = line
                    end
                end
                faceIndices[#faceIndices + 1] = vertexIndex
            end

            for _, line in ipairs(newVertexLines) do lines[#lines + 1] = line end
            for at = 1, #faceIndices, 3 do
                if at + 2 <= #faceIndices then
                    local a, b, c = faceIndices[at], faceIndices[at + 1], faceIndices[at + 2]
                    lines[#lines + 1] = string.format("f %d/%d/%d %d/%d/%d %d/%d/%d",
                        a, a, a, b, b, b, c, c, c)
                    triangles = triangles + 1
                end
            end
        end
    end
    lines[#lines + 1] = ""
    local text = table.concat(lines, "\n")
    return text, {
        -- `vertexCount` remains the authoritative source-stream count exposed
        -- since #287/#294; emitted OBJ topology is reported separately below.
        sourceVertexCount = sourceVertexCount,
        vertexCount = sourceVertexCount,
        exportedVertexCount = index,
        uvCount = index,
        normalCount = index,
        weldedVertexCount = index,
        weldedAwayVertexCount = sourceVertexCount - index,
        triangleCount = triangles,
        faceCount = triangles,
        groupCount = nonEmptySurfaces,
        surfaceCount = nonEmptySurfaces,
        materialCount = #materials,
        objBytes = #text,
    }
end

function exporter.export(session)
    local renderable, err = exporter.collect(session)
    if not renderable then return nil, err end
    renderable_bundle.validate(renderable)

    local mapData = session.currentMapData
    local mapId = mapData.id or session.currentMapIndex or "runtime"
    local mapName = mapData.name or mapData.title or ("map_" .. tostring(mapId))

    local rootDirectory = "exports/maps"
    local baseName = safeName(mapId) .. "-" .. safeName(mapName)
    local exportDirectory = rootDirectory .. "/" .. baseName
    local okDir = love.filesystem.createDirectory(exportDirectory)
    if okDir == false then error("could not create map export directory", 0) end

    local objFileName = baseName .. ".obj"
    local mtlFileName = baseName .. ".mtl"
    local objRelativePath = exportDirectory .. "/" .. objFileName
    local mtlRelativePath = exportDirectory .. "/" .. mtlFileName

    local texturePlan = exporter.planTextures(renderable)
    local textureFiles, textureCount = exporter.writeTextures(renderable, exportDirectory, texturePlan)
    local mtlText, materialStats = exporter.serializeMaterials(renderable, {
        textureFiles = textureFiles,
    })
    local text, stats = exporter.serialize(renderable, {
        materialLibrary = mtlFileName,
    })

    local okMtl, mtlWriteErr = love.filesystem.write(mtlRelativePath, mtlText)
    if not okMtl then
        error("could not write map material export: " .. tostring(mtlWriteErr), 0)
    end
    local ok, writeErr = love.filesystem.write(objRelativePath, text)
    if not ok then
        error("could not write map geometry export: " .. tostring(writeErr), 0)
    end

    local saveDirectory = love.filesystem.getSaveDirectory()
    local exportDirectoryAbsolutePath = saveDirectory .. "/" .. exportDirectory
    local absolutePath = saveDirectory .. "/" .. objRelativePath
    local materialAbsolutePath = saveDirectory .. "/" .. mtlRelativePath
    local textureDirectoryRelativePath = exportDirectory .. "/textures"
    local textureDirectoryAbsolutePath = saveDirectory .. "/" .. textureDirectoryRelativePath

    print("[map-geometry-export] folder: " .. exportDirectoryAbsolutePath)
    print("[map-geometry-export] OBJ: " .. absolutePath)
    print("[map-geometry-export] MTL: " .. materialAbsolutePath)
    print(string.format(
        "[map-geometry-export] %d triangles, %d source vertices -> %d welded vertices, %d groups, %d materials, %d unique albedo textures",
        stats.triangleCount, stats.sourceVertexCount, stats.exportedVertexCount, stats.groupCount,
        materialStats.materialCount, textureCount))

    stats.relativePath = objRelativePath
    stats.absolutePath = absolutePath
    stats.materialRelativePath = mtlRelativePath
    stats.materialAbsolutePath = materialAbsolutePath
    stats.exportDirectoryRelativePath = exportDirectory
    stats.exportDirectoryAbsolutePath = exportDirectoryAbsolutePath
    stats.textureDirectoryRelativePath = textureDirectoryRelativePath
    stats.textureDirectoryAbsolutePath = textureDirectoryAbsolutePath
    stats.objFileName = objFileName
    stats.mtlFileName = mtlFileName
    stats.materialCount = materialStats.materialCount
    stats.textureCount = textureCount
    stats.mapId = mapId
    stats.mapName = mapName
    return stats
end

return exporter