-- Engine-neutral static geometry model construction.
--
-- This module owns the deterministic CPU representation shared by image-authored
-- geometry and presentation-side OBJ parsing. It deliberately knows nothing
-- about textures, love.graphics, GPU meshes, or presentation modules.
--
-- A built model is:
--   { groups = { { material, vertices }, ... },
--     vertexCount = n,
--     bounds = { minX, minY, minZ, maxX, maxY, maxZ } }
--
-- Vertices are flat 12-float records in world axes (Z up, one unit = one map
-- cell): x, y, z, u, v, nx, ny, nz, r, g, b, a.
local model = {}

function model.faceNormal(a, b, c)
    local ux, uy, uz = b[1] - a[1], b[2] - a[2], b[3] - a[3]
    local vx, vy, vz = c[1] - a[1], c[2] - a[2], c[3] - a[3]
    local nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    local length = math.sqrt(nx * nx + ny * ny + nz * nz)
    if length == 0 then error("mesh contains a degenerate face", 0) end
    return { nx / length, ny / length, nz / length }
end

local Builder = {}
Builder.__index = Builder

-- Accumulates triangles into per-material groups. Producers supply geometry in
-- world axes; the builder owns grouping, normal generation and bounds.
function model.newBuilder(label)
    return setmetatable({
        label = label or "mesh",
        groups = {}, order = {}, material = "",
        min = { math.huge, math.huge, math.huge },
        max = { -math.huge, -math.huge, -math.huge },
    }, Builder)
end

function Builder:setMaterial(name)
    self.material = name or ""
end

function Builder:group()
    local existing = self.groups[self.material]
    if existing then return existing end
    local created = { material = self.material, vertices = {} }
    self.groups[self.material] = created
    self.order[#self.order + 1] = created
    return created
end

-- Each vertex is { x, y, z, u, v [, nx, ny, nz] }. A vertex without a normal
-- takes the triangle's generated face normal, which is what flat-shaded
-- authored geometry wants.
function Builder:triangle(a, b, c)
    -- Computed even when every vertex carries an authored normal: it is also
    -- the degeneracy check, and a zero-area triangle must fail loudly rather
    -- than reach the renderer as an invisible face.
    local generated = model.faceNormal(a, b, c)
    local vertices = self:group().vertices
    for _, vertex in ipairs({ a, b, c }) do
        local nx, ny, nz = vertex[6], vertex[7], vertex[8]
        if not nx then
            nx, ny, nz = generated[1], generated[2], generated[3]
        end
        for axis = 1, 3 do
            if vertex[axis] < self.min[axis] then self.min[axis] = vertex[axis] end
            if vertex[axis] > self.max[axis] then self.max[axis] = vertex[axis] end
        end
        vertices[#vertices + 1] = {
            vertex[1], vertex[2], vertex[3], vertex[4], vertex[5], nx, ny, nz,
            vertex[9] or 1, vertex[10] or 1, vertex[11] or 1, vertex[12] or 1,
        }
    end
end

function Builder:build()
    if #self.order == 0 then error(self.label .. " contains no faces", 0) end
    local count = 0
    for _, group in ipairs(self.order) do count = count + #group.vertices end
    return {
        groups = self.order, vertexCount = count,
        bounds = {
            minX = self.min[1], minY = self.min[2], minZ = self.min[3],
            maxX = self.max[1], maxY = self.max[2], maxZ = self.max[3],
        },
    }
end

return model
