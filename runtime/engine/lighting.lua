-- Shared, deterministic light baking and static-light composition for authored
-- light objects, generated dungeon fixtures, and signed art-direction
-- corrections.  Values are vertex colours because that is the format the
-- raycaster samples; a source is blocked by walls rather than bleeding through
-- them as a simple painted circle would.
--
-- Bounded composition contract (#474):
--   sourceBase  = bake(topology, sources, ambient)   -- derived, never authored
--   finalStatic = clamp(sourceBase + paintCorrection, 0, 1)
--
-- `paintCorrection` is a SIGNED (-1..1) art-direction delta.  It can only push
-- an already-derived value; it can never define lighting on its own, which is
-- what the legacy absolute `light` grid did.
local lighting = {}

local function isWall(grid, x, y)
    return not grid[y] or not grid[y][x] or grid[y][x] == "#"
end

local function visible(grid, x0, y0, x1, y1)
    local dx, dy = math.abs(x1 - x0), math.abs(y1 - y0)
    local sx, sy = x0 < x1 and 1 or -1, y0 < y1 and 1 or -1
    local err, x, y = dx - dy, x0, y0
    while x ~= x1 or y ~= y1 do
        if (x ~= x0 or y ~= y0) and isWall(grid, x, y) then return false end
        local e2 = err * 2
        if e2 > -dy then err = err - dy; x = x + sx end
        if e2 < dx then err = err + dx; y = y + sy end
    end
    return true
end

-- `sources` use zero-based cell coordinates, colour 0..1, and a tile radius.
function lighting.bake(grid, sources, ambient)
    local h, w = #grid, #grid[1]
    ambient = ambient or { 0.12, 0.12, 0.12 }
    local out = {}
    for vy = 0, h do
        out[vy + 1] = {}
        for vx = 0, w do out[vy + 1][vx + 1] = { ambient[1], ambient[2], ambient[3] } end
    end
    for _, source in ipairs(sources or {}) do
        local radius = math.max(0.1, source.radius or 4)
        local col = source.color or { 1, 0.65, 0.3 }
        for vy = math.max(0, math.floor(source.y - radius)), math.min(h, math.ceil(source.y + radius)) do
            for vx = math.max(0, math.floor(source.x - radius)), math.min(w, math.ceil(source.x + radius)) do
                local dx, dy = vx - (source.x + 0.5), vy - (source.y + 0.5)
                local dist = math.sqrt(dx * dx + dy * dy)
                if dist <= radius and visible(grid, source.x + 1, source.y + 1, math.max(1, math.min(w, vx)), math.max(1, math.min(h, vy))) then
                    local strength = (1 - dist / radius) ^ (source.falloff or 2)
                    local dst = out[vy + 1][vx + 1]
                    for c = 1, 3 do dst[c] = math.min(1, dst[c] + col[c] * strength) end
                end
            end
        end
    end
    return out
end

-- Full-white neutral field, for maps that author a correction but derive no
-- illumination of their own.  Sized like a bake result: (h+1) x (w+1) vertices.
function lighting.neutralBase(w, h)
    local out = {}
    for vy = 0, h do
        out[vy + 1] = {}
        for vx = 0, w do
            out[vy + 1][vx + 1] = { 1, 1, 1 }
        end
    end
    return out
end

-- finalStatic = clamp(sourceBase + paintCorrection, 0, 1)
function lighting.compose(sourceBase, paintCorrection)
    if not sourceBase then return nil end
    if not paintCorrection then return sourceBase end
    local h = #sourceBase
    local w = #sourceBase[1]
    local out = {}
    for vy = 1, h do
        out[vy] = {}
        local baseRow = sourceBase[vy]
        local corrRow = paintCorrection[vy]
        for vx = 1, w do
            local baseCell = baseRow[vx]
            local corrCell = corrRow and corrRow[vx]
            if corrCell then
                out[vy][vx] = {
                    math.max(0, math.min(1, baseCell[1] + (corrCell[1] or 0))),
                    math.max(0, math.min(1, baseCell[2] + (corrCell[2] or 0))),
                    math.max(0, math.min(1, baseCell[3] + (corrCell[3] or 0))),
                }
            else
                out[vy][vx] = { baseCell[1], baseCell[2], baseCell[3] }
            end
        end
    end
    return out
end

-- The one entry point for static map lighting.  Callers gather their own
-- sources (see `lighting.gatherSources`) so this module never learns the shape
-- of map data.  `bake` supplies the 0.12 ambient floor when `ambient` is nil.
function lighting.resolve(grid, sources, ambient, paintCorrection)
    if not grid or not grid[1] then return nil end
    local hasSources = sources ~= nil and #sources > 0
    local hasAmbient = ambient ~= nil
    if not hasSources and not hasAmbient and paintCorrection == nil then
        return nil
    end
    local h, w = #grid, #grid[1]
    local sourceBase
    if hasSources or hasAmbient then
        sourceBase = lighting.bake(grid, sources, ambient)
    else
        sourceBase = lighting.neutralBase(w, h)
    end
    return lighting.compose(sourceBase, paintCorrection)
end

-- Authored light objects and generated fixtures light a map identically; this
-- is the one place that order is decided.
function lighting.gatherSources(mapData, generatedLights)
    local sources = {}
    for _, source in ipairs(mapData and mapData.lightObjects or {}) do
        sources[#sources + 1] = source
    end
    for _, source in ipairs(generatedLights or {}) do
        sources[#sources + 1] = source
    end
    return sources
end

return lighting
