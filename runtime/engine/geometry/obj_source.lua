-- Pure Wavefront source adapter shared by native acquisition and Model compilation.
-- Preserve authored CPU precision; GPU conversion belongs to each renderer.
local model = require("engine.geometry.model")
local source = {}

local function resolveIndex(value, count, label)
    local index = tonumber(value)
    if not index or index == 0 or index ~= math.floor(index) then
        error("OBJ " .. label .. " index is invalid: " .. tostring(value), 0)
    end
    if index < 0 then index = count + index + 1 end
    if index < 1 or index > count then
        error("OBJ " .. label .. " index out of range: " .. tostring(value), 0)
    end
    return index
end

local function objToWorld(x, y, z)
    -- OBJ exporters such as Blender's default preset write Y-up with forward
    -- along -Z. The dungeon world is Z-up with forward in its XY plane.
    return x, -z, y
end

function source.parse(text, label)
    local positions, colors, uvs, normals = {}, {}, {}, {}
    local builder = model.newBuilder(label or "OBJ")
    local mtllib = nil
    local lineNumber = 0
    for raw in (text .. "\n"):gmatch("([^\r\n]*)[\r\n]+") do
        lineNumber = lineNumber + 1
        local line = raw:gsub("#.*$", ""):match("^%s*(.-)%s*$")
        local op, rest = line:match("^(%S+)%s*(.*)$")
        if op == "v" then
            local x, y, z = rest:match("^(%S+)%s+(%S+)%s+(%S+)")
            if not x then error((label or "OBJ") .. ":" .. lineNumber .. " malformed vertex", 0) end
            x, y, z = objToWorld(assert(tonumber(x)), assert(tonumber(y)), assert(tonumber(z)))
            positions[#positions + 1] = { x, y, z }
            local values = {}
            for token in rest:gmatch("%S+") do values[#values + 1] = token end
            if #values == 6 then
                -- Retain the RGB vertex extension already supported by the
                -- static Model importer; the neutral builder owns its storage.
                colors[#positions] = { assert(tonumber(values[4])),
                    assert(tonumber(values[5])), assert(tonumber(values[6])), 1 }
            elseif #values ~= 3 and #values ~= 4 then
                error((label or "OBJ") .. ":" .. lineNumber .. " vertex requires XYZ, optional W, or XYZ RGB", 0)
            end
        elseif op == "vt" then
            local u, v = rest:match("^(%S+)%s+(%S+)")
            if not u then error((label or "OBJ") .. ":" .. lineNumber .. " malformed UV", 0) end
            uvs[#uvs + 1] = { assert(tonumber(u)), 1 - assert(tonumber(v)) }
        elseif op == "vn" then
            local x, y, z = rest:match("^(%S+)%s+(%S+)%s+(%S+)")
            if not x then error((label or "OBJ") .. ":" .. lineNumber .. " malformed normal", 0) end
            x, y, z = objToWorld(assert(tonumber(x)), assert(tonumber(y)), assert(tonumber(z)))
            normals[#normals + 1] = { x, y, z }
        elseif op == "mtllib" then
            mtllib = rest
        elseif op == "usemtl" then
            builder:setMaterial(rest)
        elseif op == "f" then
            local refs = {}
            for token in rest:gmatch("%S+") do
                local p, t, n = token:match("^([^/]+)/?([^/]*)/?([^/]*)$")
                refs[#refs + 1] = {
                    p = resolveIndex(p, #positions, "position"),
                    t = t ~= "" and resolveIndex(t, #uvs, "UV") or nil,
                    n = n ~= "" and resolveIndex(n, #normals, "normal") or nil,
                }
            end
            if #refs < 3 then error((label or "OBJ") .. ":" .. lineNumber .. " face needs 3+ vertices", 0) end
            for i = 2, #refs - 1 do
                local tri, corners = { refs[1], refs[i], refs[i + 1] }, {}
                for index, ref in ipairs(tri) do
                    local p, uv, normal = positions[ref.p], uvs[ref.t] or { 0, 0 }, normals[ref.n]
                    local color = colors[ref.p] or { 1, 1, 1, 1 }
                    corners[index] = {
                        p[1], p[2], p[3], uv[1], uv[2],
                        normal and normal[1], normal and normal[2], normal and normal[3],
                        color[1], color[2], color[3], color[4],
                    }
                end
                builder:triangle(corners[1], corners[2], corners[3])
            end
        elseif op and op ~= "o" and op ~= "g" and op ~= "s" then
            error((label or "OBJ") .. ":" .. lineNumber .. " unsupported directive '" .. op .. "'", 0)
        end
    end
    local parsed = builder:build()
    parsed.mtllib = mtllib
    return parsed
end


return source
