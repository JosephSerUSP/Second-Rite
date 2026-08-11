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

function exporter.serializeMaterials(renderable, options)
    options = options or {}
    local textureFiles = options.textureFiles or {}
    local names = materialNames(renderable)
    local lines = {
        "# Second Rite runtime map materials",
        "# material identity comes from the authoritative renderable bundle",
        "# albedo textures are copied beside the OBJ and referenced with relative map_Kd paths",
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
        "# material textures are copied beside this OBJ for portable relative map_Kd references",
        "# map: " .. tostring(mapId) .. " " .. tostring(mapName),
        "# geometry quality: " .. tostring(qualityLabel) .. " density=" .. tostring(density),
    }
    if #materials > 0 then
        lines[#lines + 1] = "mtllib " .. materialLibrary
    end
    lines[#lines + 1] = "o second_rite_map_" .. safeName(mapId)

    local index = 0
    local triangles = 0
    local nonEmptySurfaces = 0
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
            local first = index + 1
            for localIndex = 1, vertexCount do
                local source = surfaceVertex(surface, localIndex)
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
        groupCount = nonEmptySurfaces,
        materialCount = #materials,
    }
end

local function exportAlbedoTextures(renderable, directory, baseName)
    local textureFiles = {}
    local textureCount = 0
    for _, material in ipairs(renderable.materials or {}) do
        if material.albedo then
            local fileName = baseName .. "-" .. safeName(material.id) .. textureExtension(material.albedo)
            local relativePath = directory .. "/" .. fileName
            local bytes = albedoBytes(material.albedo, material.id)
            local ok, writeErr = love.filesystem.write(relativePath, bytes)
            if not ok then
                error("could not write map material texture: " .. tostring(writeErr), 0)
            end
            textureFiles[material.id] = fileName
            textureCount = textureCount + 1
        end
    end
    return textureFiles, textureCount
end

function exporter.export(session)
    local renderable, err = exporter.collect(session)
    if not renderable then return nil, err end
    renderable_bundle.validate(renderable)

    local mapData = session.currentMapData
    local mapId = mapData.id or session.currentMapIndex or "runtime"
    local mapName = mapData.name or mapData.title or ("map_" .. tostring(mapId))

    local directory = "exports/maps"
    local okDir = love.filesystem.createDirectory(directory)
    if okDir == false then error("could not create map export directory", 0) end

    local baseName = safeName(mapId) .. "-" .. safeName(mapName)
    local objFileName = baseName .. ".obj"
    local mtlFileName = baseName .. ".mtl"
    local objRelativePath = directory .. "/" .. objFileName
    local mtlRelativePath = directory .. "/" .. mtlFileName

    local textureFiles, textureCount = exportAlbedoTextures(renderable, directory, baseName)
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
    local absolutePath = saveDirectory .. "/" .. objRelativePath
    local materialAbsolutePath = saveDirectory .. "/" .. mtlRelativePath
    print(string.format(
        "[map-geometry-export] %s (%d triangles, %d vertices, %d groups, %d materials, %d textures)",
        absolutePath, stats.triangleCount, stats.vertexCount, stats.groupCount,
        materialStats.materialCount, textureCount))

    stats.relativePath = objRelativePath
    stats.absolutePath = absolutePath
    stats.materialRelativePath = mtlRelativePath
    stats.materialAbsolutePath = materialAbsolutePath
    stats.materialCount = materialStats.materialCount
    stats.textureCount = textureCount
    stats.mapId = mapId
    stats.mapName = mapName
    return stats
end

return exporter
