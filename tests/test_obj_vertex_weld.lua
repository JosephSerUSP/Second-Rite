-- Export-only OBJ vertex welding (#302).
--
-- Runtime/renderable geometry intentionally stays a flat triangle stream. These
-- tests pin the serializer seam instead: only attribute tuples that resolve to
-- identical OBJ position/UV/normal text may share an index.
local M = {}

local exporter = require("presentation.map_geometry_export")
local obj_model = require("presentation.obj_model")
local renderable = require("presentation.map_renderable_bundle")

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

local function countOccurrences(text, needle)
    local count, start = 0, 1
    while true do
        local at = text:find(needle, start, true)
        if not at then return count end
        count = count + 1
        start = at + #needle
    end
end

local function appendVertex(surface, vertex)
    for i = 1, 3 do surface.positions[#surface.positions + 1] = vertex[i] end
    for i = 4, 5 do surface.uvs[#surface.uvs + 1] = vertex[i] end
    for i = 6, 8 do surface.normals[#surface.normals + 1] = vertex[i] end
    for i = 9, 12 do surface.colors[#surface.colors + 1] = vertex[i] or 1 end
end

local function surface(id, material, vertices)
    local result = {
        id = id,
        name = id,
        material = material,
        source = { kind = "cell", x = 0, y = 0, surface = "floor" },
        positions = {}, uvs = {}, normals = {}, colors = {},
    }
    for _, vertex in ipairs(vertices) do appendVertex(result, vertex) end
    return result
end

local function bundle(surfaces, materials)
    return {
        version = renderable.VERSION,
        map = { id = 302, name = "OBJ Weld" },
        quality = { preset = "HIGH", density = 1 },
        materials = materials or {
            { id = "material_001", color = { 1, 1, 1, 1 } },
        },
        surfaces = surfaces,
    }
end

local function v(x, y, z, u, texV, nx, ny, nz, r, g, b, a)
    return { x, y, z, u, texV, nx, ny, nz,
        r or 1, g or 1, b or 1, a or 1 }
end

local function legacySerialize(value, metadata)
    -- Test-only copy of #294's pre-weld OBJ geometry shape. It exists only so
    -- the round-trip assertion can compare the old triangle soup with the new
    -- indexed serialization at the OBJ consumer boundary.
    metadata = metadata or {}
    local surfaces = value.surfaces or value or {}
    local materials = value.materials or {}
    local map = value.map or {}
    local quality = value.quality or {}
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
        "# map: " .. tostring(mapId) .. " " .. tostring(mapName),
        "# geometry quality: " .. tostring(qualityLabel) .. " density=" .. tostring(density),
    }
    if #materials > 0 then lines[#lines + 1] = "mtllib " .. materialLibrary end
    lines[#lines + 1] = "o second_rite_map_" .. safeName(mapId)

    local index = 0
    for _, s in ipairs(surfaces) do
        local vertexCount = math.floor(#(s.positions or {}) / 3)
        if vertexCount > 0 then
            lines[#lines + 1] = "g " .. safeName(s.name or s.id)
            lines[#lines + 1] = "s off"
            if #materials > 0 then lines[#lines + 1] = "usemtl " .. tostring(s.material) end
            local first = index + 1
            for localIndex = 1, vertexCount do
                local p, t = (localIndex - 1) * 3, (localIndex - 1) * 2
                local x, y, z = exporter.worldToObj(
                    s.positions[p + 1], s.positions[p + 2], s.positions[p + 3])
                local nx, ny, nz = exporter.normalToObj(
                    s.normals[p + 1] or 0, s.normals[p + 2] or 0, s.normals[p + 3] or 1)
                lines[#lines + 1] = "v " .. number(x) .. " " .. number(y) .. " " .. number(z)
                lines[#lines + 1] = "vt " .. number(s.uvs[t + 1] or 0)
                    .. " " .. number(1 - (s.uvs[t + 2] or 0))
                lines[#lines + 1] = "vn " .. number(nx) .. " " .. number(ny) .. " " .. number(nz)
                index = index + 1
            end
            for at = first, index, 3 do
                if at + 2 <= index then
                    lines[#lines + 1] = string.format("f %d/%d/%d %d/%d/%d %d/%d/%d",
                        at, at, at, at + 1, at + 1, at + 1, at + 2, at + 2, at + 2)
                end
            end
        end
    end
    lines[#lines + 1] = ""
    return table.concat(lines, "\n")
end

local function parsedSemanticSignature(parsed)
    local out = {}
    for _, group in ipairs(parsed.groups or {}) do
        out[#out + 1] = "material=" .. tostring(group.material or "")
        for _, vertex in ipairs(group.vertices or {}) do
            local fields = {}
            for i = 1, 8 do fields[i] = number(vertex[i]) end
            out[#out + 1] = table.concat(fields, ",")
        end
    end
    return table.concat(out, "\n")
end

local function unsafePositionOnlySerialize(value)
    -- Deliberately wrong planted control: a repeated position reuses the first
    -- UV/normal tuple. The semantic round-trip comparison below must detect it.
    local positions, lines, faces = {}, { "o unsafe_position_weld" }, {}
    local nextIndex = 0
    for _, s in ipairs(value.surfaces or {}) do
        local face = {}
        local vertexCount = math.floor(#(s.positions or {}) / 3)
        for localIndex = 1, vertexCount do
            local p, t = (localIndex - 1) * 3, (localIndex - 1) * 2
            local x, y, z = exporter.worldToObj(
                s.positions[p + 1], s.positions[p + 2], s.positions[p + 3])
            local positionKey = number(x) .. "," .. number(y) .. "," .. number(z)
            local index = positions[positionKey]
            if not index then
                nextIndex = nextIndex + 1
                index = nextIndex
                positions[positionKey] = index
                local nx, ny, nz = exporter.normalToObj(
                    s.normals[p + 1] or 0, s.normals[p + 2] or 0, s.normals[p + 3] or 1)
                lines[#lines + 1] = "v " .. number(x) .. " " .. number(y) .. " " .. number(z)
                lines[#lines + 1] = "vt " .. number(s.uvs[t + 1] or 0)
                    .. " " .. number(1 - (s.uvs[t + 2] or 0))
                lines[#lines + 1] = "vn " .. number(nx) .. " " .. number(ny) .. " " .. number(nz)
            end
            face[#face + 1] = index
            if #face == 3 then
                faces[#faces + 1] = string.format("f %d/%d/%d %d/%d/%d %d/%d/%d",
                    face[1], face[1], face[1], face[2], face[2], face[2], face[3], face[3], face[3])
                face = {}
            end
        end
    end
    for _, face in ipairs(faces) do lines[#lines + 1] = face end
    lines[#lines + 1] = ""
    return table.concat(lines, "\n")
end

local function legacySerializedSize(value, metadata)
    -- Exact byte count of #294's old serialization without allocating the full
    -- pre-weld map-8 OBJ alongside the new one.
    metadata = metadata or {}
    local surfaces = value.surfaces or value or {}
    local materials = value.materials or {}
    local map = value.map or {}
    local quality = value.quality or {}
    local mapId = metadata.mapId or map.id or "runtime"
    local mapName = metadata.mapName or map.name or ""
    local qualityLabel = metadata.quality or quality.preset or "CUSTOM"
    local density = metadata.density or quality.density or "?"
    local materialLibrary = metadata.materialLibrary
        or ("second_rite_map_" .. safeName(mapId) .. ".mtl")
    local bytes = 0
    local function add(line) bytes = bytes + #line + 1 end
    add("# Second Rite runtime map geometry")
    add("# geometry and material identity come from the authoritative renderable bundle")
    add("# material albedos are export-local and referenced through the sibling MTL")
    add("# map: " .. tostring(mapId) .. " " .. tostring(mapName))
    add("# geometry quality: " .. tostring(qualityLabel) .. " density=" .. tostring(density))
    if #materials > 0 then add("mtllib " .. materialLibrary) end
    add("o second_rite_map_" .. safeName(mapId))

    local index = 0
    for _, s in ipairs(surfaces) do
        local vertexCount = math.floor(#(s.positions or {}) / 3)
        if vertexCount > 0 then
            add("g " .. safeName(s.name or s.id))
            add("s off")
            if #materials > 0 then add("usemtl " .. tostring(s.material)) end
            local first = index + 1
            for localIndex = 1, vertexCount do
                local p, t = (localIndex - 1) * 3, (localIndex - 1) * 2
                local x, y, z = exporter.worldToObj(
                    s.positions[p + 1], s.positions[p + 2], s.positions[p + 3])
                local nx, ny, nz = exporter.normalToObj(
                    s.normals[p + 1] or 0, s.normals[p + 2] or 0, s.normals[p + 3] or 1)
                add("v " .. number(x) .. " " .. number(y) .. " " .. number(z))
                add("vt " .. number(s.uvs[t + 1] or 0)
                    .. " " .. number(1 - (s.uvs[t + 2] or 0)))
                add("vn " .. number(nx) .. " " .. number(ny) .. " " .. number(nz))
                index = index + 1
            end
            for at = first, index, 3 do
                if at + 2 <= index then
                    add(string.format("f %d/%d/%d %d/%d/%d %d/%d/%d",
                        at, at, at, at + 1, at + 1, at + 1, at + 2, at + 2, at + 2))
                end
            end
        end
    end
    return bytes
end

function M.run()
    print("=== OBJ Export Vertex Welding (#302) ===")
    local passed, failed = 0, 0
    local function check(condition, message)
        if condition then
            passed = passed + 1
            print("  [PASS] " .. message)
        else
            failed = failed + 1
            print("  [FAIL] " .. message)
        end
    end

    local n = { 0, 0, 1 }
    local quad = bundle({ surface("quad", "material_001", {
        v(0, 0, 0, 0, 0, n[1], n[2], n[3]),
        v(1, 0, 0, 1, 0, n[1], n[2], n[3]),
        v(1, 1, 0, 1, 1, n[1], n[2], n[3]),
        v(0, 0, 0, 0, 0, n[1], n[2], n[3]),
        v(1, 1, 0, 1, 1, n[1], n[2], n[3]),
        v(0, 1, 0, 0, 1, n[1], n[2], n[3]),
    }) })
    check(renderable.validate(quad), "ordinary quad fixture satisfies the renderable contract")
    local quadObj, quadStats = exporter.serialize(quad, { materialLibrary = "quad.mtl" })
    check(quadStats.sourceVertexCount == 6 and quadStats.exportedVertexCount == 4
            and quadStats.weldedAwayVertexCount == 2,
        "two triangles of one ordinary quad reuse the two duplicated corner indices")
    check(countOccurrences(quadObj, "\nv ") == 4
            and countOccurrences(quadObj, "\nvt ") == 4
            and countOccurrences(quadObj, "\nvn ") == 4,
        "OBJ emits one aligned v/vt/vn record per distinct export tuple")
    check(quadObj:find("f 1/1/1 2/2/2 3/3/3", 1, true) ~= nil
            and quadObj:find("f 1/1/1 3/3/3 4/4/4", 1, true) ~= nil,
        "ordinary quad faces actually reference shared corner indices")
    check(quadStats.triangleCount == 2 and quadStats.faceCount == 2,
        "welding leaves triangle/face count unchanged")

    local identicalAcrossSurfaces = bundle({
        surface("a", "material_001", {
            v(0, 0, 0, 0, 0, 0, 0, 1), v(1, 0, 0, 1, 0, 0, 0, 1), v(0, 1, 0, 0, 1, 0, 0, 1),
        }),
        surface("b", "material_001", {
            v(0, 0, 0, 0, 0, 0, 0, 1), v(-1, 0, 0, 1, 0, 0, 0, 1), v(0, -1, 0, 0, 1, 0, 0, 1),
        }),
    })
    local identicalObj, identicalStats = exporter.serialize(identicalAcrossSurfaces)
    check(identicalStats.sourceVertexCount == 6 and identicalStats.exportedVertexCount == 5,
        "identical full serialized tuples weld even across surface/group boundaries")
    check(countOccurrences(identicalObj, "\nf ") == 2,
        "cross-surface tuple reuse does not collapse faces")

    local uvSplit = bundle({ surface("uv_split", "material_001", {
        v(0, 0, 0, 0, 0, 0, 0, 1), v(1, 0, 0, 1, 0, 0, 0, 1), v(0, 1, 0, 0, 1, 0, 0, 1),
        v(0, 0, 0, 0.5, 0, 0, 0, 1), v(0, 1, 0, 0, 1, 0, 0, 1), v(-1, 0, 0, 1, 0, 0, 0, 1),
    }) })
    local uvObj, uvStats = exporter.serialize(uvSplit)
    check(uvStats.exportedVertexCount == 5,
        "same position with a different UV remains an intentional split")

    local normalSplit = bundle({ surface("normal_split", "material_001", {
        v(0, 0, 0, 0, 0, 0, 0, 1), v(1, 0, 0, 1, 0, 0, 0, 1), v(0, 1, 0, 0, 1, 0, 0, 1),
        v(0, 0, 0, 0, 0, 0, 1, 0), v(0, 1, 0, 0, 1, 0, 0, 1), v(-1, 0, 0, 1, 0, 0, 1, 0),
    }) })
    local _, normalStats = exporter.serialize(normalSplit)
    check(normalStats.exportedVertexCount == 6,
        "same position/UV with a different normal remains an intentional split")

    local colourOnly = bundle({ surface("colour_only", "material_001", {
        v(0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1),
        v(1, 0, 0, 1, 0, 0, 0, 1), v(0, 1, 0, 0, 1, 0, 0, 1),
        v(0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1),
        v(0, 1, 0, 0, 1, 0, 0, 1), v(-1, 0, 0, 1, 0, 0, 0, 1),
    }) })
    local colourObj, colourStats = exporter.serialize(colourOnly)
    check(colourStats.exportedVertexCount == 5
            and not colourObj:find("1.000000000 0.000000000 0.000000000 1.000000000", 1, true),
        "bundle vertex colour is not treated as an OBJ discontinuity because current OBJ never serializes it")

    local materialColour = bundle({
        surface("red_face", "material_001", {
            v(0, 0, 0, 0, 0, 0, 0, 1), v(1, 0, 0, 1, 0, 0, 0, 1), v(0, 1, 0, 0, 1, 0, 0, 1),
        }),
        surface("green_face", "material_002", {
            v(0, 0, 0, 0, 0, 0, 0, 1), v(-1, 0, 0, 1, 0, 0, 0, 1), v(0, -1, 0, 0, 1, 0, 0, 1),
        }),
    }, {
        { id = "material_001", color = { 1, 0, 0, 1 } },
        { id = "material_002", color = { 0, 1, 0, 0.5 } },
    })
    local materialObj, materialStats = exporter.serialize(materialColour)
    local materialMtl = exporter.serializeMaterials(materialColour)
    check(materialStats.exportedVertexCount == 5
            and materialObj:find("usemtl material_001", 1, true)
            and materialObj:find("usemtl material_002", 1, true)
            and materialMtl:find("Kd 1.000000000 0.000000000 0.000000000", 1, true)
            and materialMtl:find("Kd 0.000000000 1.000000000 0.000000000", 1, true)
            and materialMtl:find("d 0.500000000", 1, true),
        "export-relevant colour/alpha discontinuity remains face-scoped through material assignment")
    local oldMaterialDirectives = legacySerialize(materialColour)
    local function assignments(text)
        local kept = {}
        for line in (text .. "\n"):gmatch("([^\n]*)\n") do
            local op = line:match("^(%S+)")
            if op == "g" or op == "usemtl" or op == "f" then kept[#kept + 1] = line end
        end
        return table.concat(kept, "\n")
    end
    check(assignments(oldMaterialDirectives) == assignments(materialObj),
        "surface/group material assignments are unchanged by welding")

    local quadAgain = exporter.serialize(quad, { materialLibrary = "quad.mtl" })
    check(quadObj == quadAgain, "welded OBJ serialization is deterministic")
    check(quadStats.exportedVertexCount < quadStats.sourceVertexCount,
        "representative geometry has fewer exported vertices after welding")

    local legacyQuad = legacySerialize(quad, { materialLibrary = "quad.mtl" })
    local parsedBefore = obj_model.parse(legacyQuad, "#302 legacy quad")
    local parsedAfter = obj_model.parse(quadObj, "#302 welded quad")
    check(parsedSemanticSignature(parsedBefore) == parsedSemanticSignature(parsedAfter),
        "OBJ round-trip preserves the pre-weld resolved triangle position/UV/normal/material stream")

    local legacyUv = legacySerialize(uvSplit)
    local unsafeUv = unsafePositionOnlySerialize(uvSplit)
    check(parsedSemanticSignature(obj_model.parse(legacyUv, "#302 UV baseline"))
            ~= parsedSemanticSignature(obj_model.parse(unsafeUv, "#302 unsafe position weld")),
        "negative control detects the semantic damage from an unsafe position-only weld")
    check(parsedSemanticSignature(obj_model.parse(legacyUv, "#302 UV baseline repeat"))
            == parsedSemanticSignature(obj_model.parse(uvObj, "#302 safe UV weld")),
        "safe full-tuple welding preserves the UV-seam fixture that the negative control breaks")

    -- Real-map verification: map 8 is the substantial multi-material export the
    -- owner used to discover #302. We serialize only the post-weld OBJ; the old
    -- byte count is computed from the exact #294 line shape to avoid retaining a
    -- second triangle-soup-sized string in memory.
    local Session = require("engine.session")
    local exploration = require("engine.exploration")
    local viewport_3d = require("presentation.viewport_3d")
    local loader = require("data.loader")
    local runtimeSession = Session.GameSession.new(loader)
    runtimeSession:initializeStartingParty()
    local originalTime = os.time
    os.time = function() return 1735689600 end
    local loaded, loadErr = pcall(exploration.loadMap, runtimeSession, 8, { seed = 1735689608 })
    os.time = originalTime
    if not loaded then error(loadErr, 0) end
    viewport_3d.init()
    local actual, collectErr = renderable.collect(runtimeSession)
    check(actual ~= nil, "map 8 produces an authoritative renderable bundle: " .. tostring(collectErr))
    if actual then
        check(renderable.validate(actual), "map 8 bundle satisfies the renderable contract")
        local mapObj, mapStats = exporter.serialize(actual, { materialLibrary = "map8.mtl" })
        local beforeBytes = legacySerializedSize(actual, { materialLibrary = "map8.mtl" })
        local nonEmptySurfaces = 0
        for _, s in ipairs(actual.surfaces or {}) do
            if #(s.positions or {}) > 0 then nonEmptySurfaces = nonEmptySurfaces + 1 end
        end
        print(string.format(
            "[OBJ WELD MAP 8] before v=%d vt=%d vn=%d f=%d bytes=%d surfaces=%d materials=%d | after v=%d vt=%d vn=%d f=%d bytes=%d surfaces=%d materials=%d",
            mapStats.sourceVertexCount, mapStats.sourceVertexCount, mapStats.sourceVertexCount,
            mapStats.triangleCount, beforeBytes, nonEmptySurfaces, #(actual.materials or {}),
            mapStats.exportedVertexCount, mapStats.uvCount, mapStats.normalCount,
            mapStats.faceCount, #mapObj, mapStats.surfaceCount, mapStats.materialCount))
        check(mapStats.vertexCount == actual.stats.vertexCount
                and mapStats.triangleCount == actual.stats.triangleCount,
            "map 8 keeps authoritative source vertex and triangle counts unchanged")
        check(mapStats.exportedVertexCount < mapStats.sourceVertexCount,
            "map 8 exported OBJ vertex count drops after exact-tuple welding")
        check(mapStats.uvCount == mapStats.exportedVertexCount
                and mapStats.normalCount == mapStats.exportedVertexCount,
            "map 8 retains aligned position/UV/normal index tables")
        check(mapStats.faceCount == actual.stats.triangleCount
                and mapStats.surfaceCount == nonEmptySurfaces
                and mapStats.materialCount == #(actual.materials or {}),
            "map 8 face, surface, and material counts are unchanged")
        check(#mapObj < beforeBytes,
            "map 8 OBJ byte size drops despite the explicit weld metadata comment")
    end

    require("tests.fail_fast")("test_obj_vertex_weld", failed, passed)
end

return M
