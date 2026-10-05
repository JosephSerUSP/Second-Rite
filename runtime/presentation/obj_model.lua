-- Strict, deliberately small OBJ/MTL loader for static dungeon kit pieces.
-- Supports standard Y-up OBJ positions, UVs, normals, polygon triangulation,
-- negative indices, mtllib/usemtl, Kd, map_Kd and sphere-mapped refl. Parsed positions are
-- normalized to the engine's Z-up world coordinates. Unsupported geometry
-- fails at load time.
--
-- This is one producer of engine/geometry/model.lua's neutral representation;
-- the image-authored geometry compiler is the other. presentation/mesh.lua then
-- owns material binding, texture caching, the graphics vertex format and GPU
-- upload for both producers.
local mesh = require("presentation.mesh")

local obj_model = {}

local cache = {}

obj_model.parseMtl = require("presentation.mtl").parse

obj_model.parse = require("engine.geometry.obj_source").parse

function obj_model.load(path)
    if cache[path] then return cache[path] end
    local text = love.filesystem.read(path)
    if not text then error("OBJ model missing: " .. tostring(path), 0) end
    local parsed = obj_model.parse(text, path)
    local materials, base = {}, mesh.dirname(path)
    if parsed.mtllib then
        local mtlPath = mesh.joined(base, parsed.mtllib)
        local mtlText = love.filesystem.read(mtlPath)
        if not mtlText then error("OBJ material library missing: " .. mtlPath, 0) end
        materials = obj_model.parseMtl(mtlText)
    end
    mesh.finalize(parsed, materials, base)
    parsed.path = path
    cache[path] = parsed
    return parsed
end

return obj_model