-- Presentation materialization for the static geometry model.
--
-- Engine-neutral triangle accumulation, normal generation, material grouping
-- and bounds live in engine/geometry/model.lua. This module owns only the
-- presentation side of the seam: vertex format, texture acquisition/cache,
-- love.graphics mesh creation, and material/texture binding.
--
-- `finalize` attaches presentation fields to a neutral model in place so the
-- renderer sees the same representation it always has:
--   { groups = { { material, vertices, mesh, color, texture }, ... },
--     vertexCount = n,
--     bounds = { minX, minY, minZ, maxX, maxY, maxZ } }
local mesh = {}
local model = require("engine.geometry.model")
local buildProfiler = require("engine.map_build_profiler")

mesh.FORMAT = {
    { "VertexPosition", "float", 3 },
    { "VertexTexCoord", "float", 2 },
    { "VertexNormal", "float", 3 },
    { "VertexColor", "float", 4 },
}

local textureCache = {}

function mesh.dirname(path)
    return path:match("^(.*)/[^/]+$") or ""
end

-- Asset references inside a model may be written relative to the model file or
-- as an ordinary project path; a leading `assets/` marks the latter.
function mesh.joined(base, path)
    if path:match("^assets/") then return path end
    return base == "" and path or (base .. "/" .. path)
end

-- Nearest-filtered and shared, so an atlas used by several models -- which is
-- the normal case for image-authored geometry -- is uploaded once.
function mesh.texture(path)
    if textureCache[path] then
        buildProfiler.cache("source.texture", true)
        return textureCache[path]
    end
    buildProfiler.cache("source.texture", false)
    if not love.filesystem.getInfo(path) then
        error("mesh texture missing: " .. path, 0)
    end
    local textureSpan = buildProfiler.span("source.textureAcquire", "graphics")
    local image = love.graphics.newImage(path)
    image:setFilter("nearest", "nearest")
    textureSpan()
    textureCache[path] = image
    return image
end

-- Bind materials and upload. `materials` maps a material name to one of:
--   { color = {r,g,b,a}, texture = path }
--   { color, image = <Drawable> }
--   { color, imageData = <ImageData> }
-- `base` resolves relative texture paths. A live `image` is used as-is, which
-- is how an atlas surface passes an already-uploaded texture. CPU-composed
-- `imageData` crosses the seam here and is uploaded exactly once, keeping
-- love.graphics out of engine geometry.
function mesh.finalize(modelToFinalize, materials, base)
    for _, group in ipairs(modelToFinalize.groups) do
        local material = (materials or {})[group.material] or { color = { 1, 1, 1, 1 } }
        local gpuSpan = buildProfiler.span("geometry.sourceGpuMeshCreate", "graphics")
        group.mesh = love.graphics.newMesh(mesh.FORMAT, group.vertices, "triangles", "static")
        gpuSpan()
        group.color = material.color
        if material.image then
            group.texture = material.image
            group.mesh:setTexture(group.texture)
        elseif material.imageData then
            -- Composed albedo used to be uploaded by engine.geometry immediately
            -- before finalize(), without source.textureAcquire profiling. Keep
            -- that observable profiler behavior while moving the graphics call
            -- to its rightful presentation owner.
            group.texture = love.graphics.newImage(material.imageData)
            group.texture:setFilter("nearest", "nearest")
            group.mesh:setTexture(group.texture)
        elseif material.texture then
            group.texture = mesh.texture(mesh.joined(base or "", material.texture))
            group.mesh:setTexture(group.texture)
        end
    end
    return modelToFinalize
end

-- Presentation-side callers that intentionally construct a CPU model (notably
-- the OBJ integration tests) may use the neutral constructor through this
-- facade. The implementation and authority remain engine-neutral; runtime
-- engine geometry never depends on this export.
mesh.newBuilder = model.newBuilder

-- The ownership direction is presentation -> engine. Geometry orchestration
-- receives one explicit materialization callback; it never requires us back.
require("engine.geometry").bindMaterializer(mesh.finalize)

return mesh
