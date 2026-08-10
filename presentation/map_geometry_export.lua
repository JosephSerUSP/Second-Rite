-- Developer-only runtime map geometry export.
--
-- Authoritative map collection no longer belongs to the OBJ serializer. The
-- engine-owned `presentation.map_renderable_bundle` resolves runtime structure,
-- compiled height geometry, event models, material identity and semantic
-- provenance once; OBJ is one consumer of that neutral result. A later MTL /
-- texture serializer can therefore add texture export without re-deriving the
-- world or creating a second geometry path.
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

function exporter.serialize(renderable, metadata)
    metadata = metadata or {}
    local surfaces = renderable and renderable.surfaces or renderable or {}
    local map = renderable and renderable.map or {}
    local quality = renderable and renderable.quality or {}
    local mapId = metadata.mapId or map.id or "runtime"
    local mapName = metadata.mapName or map.name or ""
    local qualityLabel = metadata.quality or quality.preset or "CUSTOM"
    local density = metadata.density or quality.density or "?"

    local lines = {
        "# Second Rite runtime map geometry",
        "# geometry-only OBJ; materials come from the authoritative renderable bundle",
        "# map: " .. tostring(mapId) .. " " .. tostring(mapName),
        "# geometry quality: " .. tostring(qualityLabel) .. " density=" .. tostring(density),
        "o second_rite_map_" .. safeName(mapId),
    }
    local index = 0
    local triangles = 0
    local nonEmptySurfaces = 0
    for _, surface in ipairs(surfaces) do
        local vertexCount = math.floor(#(surface.positions or {}) / 3)
        if vertexCount > 0 then
            nonEmptySurfaces = nonEmptySurfaces + 1
            lines[#lines + 1] = "g " .. safeName(surface.name or surface.id)
            lines[#lines + 1] = "s off"
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
    }
end

function exporter.export(session)
    local renderable, err = exporter.collect(session)
    if not renderable then return nil, err end

    local mapData = session.currentMapData
    local mapId = mapData.id or session.currentMapIndex or "runtime"
    local mapName = mapData.name or mapData.title or ("map_" .. tostring(mapId))
    local text, stats = exporter.serialize(renderable)

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
