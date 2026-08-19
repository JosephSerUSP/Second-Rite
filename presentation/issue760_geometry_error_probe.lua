-- #760 geometric approximation error probe.
--
-- Installed only after issue760_height_budget_probe has wrapped the production
-- geometry entry points. It observes each cold plane compile, then compares the
-- QEM-exposed relief (before perimeter/backing triangles) against the exact
-- authored height field at every fixed dense sample intersection. This is not a
-- second geometry implementation: the candidate mesh is the real compiler
-- output and exact truth is plane.sampleField(), the compiler's own sampler.
local probe = {}

local installed = false
local rows = {}
local seen = {}

local function counter(snapshot, key)
    local counters = snapshot and snapshot.counters or {}
    return tonumber(counters[key]) or 0
end

local function delta(before, after, key)
    return counter(after, key) - counter(before, key)
end

local function round(value, digits)
    local scale = 10 ^ (digits or 9)
    return math.floor(value * scale + 0.5) / scale
end

local function layersFor(specs, heightOverride)
    local images = require("engine.geometry.images")
    local layers = {}
    if heightOverride then
        local spec = specs[1]
        layers[1] = {
            data = heightOverride,
            scale = spec.heightScale,
            operation = spec.heightOperation,
        }
    else
        for index, spec in ipairs(specs) do
            layers[index] = {
                data = images.data(spec.heightPath),
                scale = spec.heightScale,
                operation = spec.heightOperation,
            }
        end
    end
    return layers
end

local function tangentVertex(surface, vertex)
    if surface == "wall" then
        return vertex[2], vertex[3], vertex[1]
    elseif surface == "floor" then
        return vertex[1], vertex[2], vertex[3]
    elseif surface == "ceiling" then
        return vertex[1], vertex[2], 1 - vertex[3]
    end
    return nil
end

local function triangleData(surface, vertices, reliefTriangles)
    local triangles = {}
    local needed = reliefTriangles * 3
    if needed > #vertices then
        error("#760 geometry error: relief triangle count exceeds model vertex stream", 0)
    end
    for offset = 1, needed, 3 do
        local ax, ay, ah = tangentVertex(surface, vertices[offset])
        local bx, by, bh = tangentVertex(surface, vertices[offset + 1])
        local cx, cy, ch = tangentVertex(surface, vertices[offset + 2])
        if ax then
            triangles[#triangles + 1] = {
                ax, ay, ah, bx, by, bh, cx, cy, ch,
                minX = math.min(ax, bx, cx), maxX = math.max(ax, bx, cx),
                minY = math.min(ay, by, cy), maxY = math.max(ay, by, cy),
            }
        end
    end
    return triangles
end

local function interpolate(triangle, x, y)
    if x < triangle.minX - 1e-9 or x > triangle.maxX + 1e-9
            or y < triangle.minY - 1e-9 or y > triangle.maxY + 1e-9 then
        return nil
    end
    local ax, ay, ah = triangle[1], triangle[2], triangle[3]
    local bx, by, bh = triangle[4], triangle[5], triangle[6]
    local cx, cy, ch = triangle[7], triangle[8], triangle[9]
    local denominator = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    if math.abs(denominator) < 1e-12 then return nil end
    local a = ((by - cy) * (x - cx) + (cx - bx) * (y - cy)) / denominator
    local b = ((cy - ay) * (x - cx) + (ax - cx) * (y - cy)) / denominator
    local c = 1 - a - b
    if a < -1e-7 or b < -1e-7 or c < -1e-7 then return nil end
    return a * ah + b * bh + c * ch
end

local function samplePoint(spec, column, row)
    local u = column / spec.sampleColumns
    local v = row / spec.sampleRows
    if spec.surface == "wall" then
        return u - 0.5, 1 - v, u, v
    end
    return u - 0.5, v - 0.5, u, v
end

local function exactLift(spec, layers, u, v)
    local plane = require("engine.geometry.plane")
    local sampleU = plane.periodicSampleCoordinate(u)
    local sampleV = spec.surface == "wall" and v
        or plane.periodicSampleCoordinate(v)
    return plane.sampleField(layers, sampleU, sampleV) + (tonumber(spec.offset) or 0)
end

local function projectedError(surface, worldError)
    local out = {}
    -- Production first-person camera: base viewport 256x144, fovHalfX=.75,
    -- fovHalfY=.421875. Both axes therefore resolve to 170.666... px per
    -- world-cell at depth 1 before the 1px snap.
    local pixelPerCellAtDepth1 = 128 / 0.75
    for _, depth in ipairs({ 1, 3, 8 }) do
        local value
        if surface == "wall" then
            -- Wall relief error is camera-depth error. At the half-cell screen
            -- edge this bounds perspective scale motion from d to d-error.
            local safe = math.max(0.05, depth - worldError)
            value = 0.5 * pixelPerCellAtDepth1
                * math.abs((1 / safe) - (1 / depth))
        else
            -- Floor/ceiling relief is vertical, so this is the direct screen-Y
            -- displacement before the production integer pixel snap.
            value = pixelPerCellAtDepth1 * worldError / depth
        end
        out[tostring(depth)] = round(value, 6)
    end
    return out
end

local function record(identity, spec, specs, heightOverride, model, reliefTriangles)
    if not spec or spec.topology ~= "plane" then return end
    if spec.surface ~= "wall" and spec.surface ~= "floor" and spec.surface ~= "ceiling" then return end
    if reliefTriangles <= 0 then return end
    local key = tostring(identity) .. "|" .. tostring(spec.surface)
    if seen[key] then return end
    seen[key] = true

    local group = model and model.groups and model.groups[1]
    local vertices = group and group.vertices or nil
    if not vertices then return end
    local triangles = triangleData(spec.surface, vertices, reliefTriangles)
    local layers = layersFor(specs or { spec }, heightOverride)

    local count, missing = 0, 0
    local sumAbs, sumSq, maxAbs = 0, 0, 0
    for row = 0, spec.sampleRows do
        for column = 0, spec.sampleColumns do
            local x, y, u, v = samplePoint(spec, column, row)
            local actual = nil
            for _, triangle in ipairs(triangles) do
                actual = interpolate(triangle, x, y)
                if actual ~= nil then break end
            end
            if actual == nil then
                missing = missing + 1
            else
                local expected = exactLift(spec, layers, u, v)
                local err = math.abs(actual - expected)
                count = count + 1
                sumAbs = sumAbs + err
                sumSq = sumSq + err * err
                if err > maxAbs then maxAbs = err end
            end
        end
    end
    if missing > 0 then
        error("#760 geometry error: " .. missing
            .. " dense sample points were not covered by exposed relief triangles", 0)
    end

    rows[#rows + 1] = {
        identity = tostring(identity),
        id = spec.id,
        surface = spec.surface,
        sampleColumns = spec.sampleColumns,
        sampleRows = spec.sampleRows,
        denseSamplePoints = count,
        exposedReliefTriangles = reliefTriangles,
        maxWorldError = round(maxAbs, 9),
        meanAbsoluteWorldError = round(sumAbs / math.max(1, count), 9),
        rmsWorldError = round(math.sqrt(sumSq / math.max(1, count)), 9),
        projectedMaxPixelError = projectedError(spec.surface, maxAbs),
        projectionNote = spec.surface == "wall"
            and "perspective half-cell edge motion bound before 1px snap"
            or "direct vertical pixel displacement before 1px snap",
    }
end

function probe.install()
    if installed then return end
    installed = true
    rows, seen = {}, {}

    local geometry = require("engine.geometry")
    local profiler = require("engine.map_build_profiler")

    local originalLoad = geometry.load
    geometry.load = function(assetPaths)
        local before = profiler.snapshot()
        local model = originalLoad(assetPaths)
        local after = profiler.snapshot()
        local relief = delta(before, after, "geometry.reducedTriangles")
        if relief > 0 then
            local identity = type(assetPaths) == "table"
                and table.concat(assetPaths, "+") or assetPaths
            record(identity, model.spec, model.specs, nil, model, relief)
        end
        return model
    end

    local originalAtlas = geometry.loadAtlasSurface
    geometry.loadAtlasSurface = function(cacheKey, spec, heightData, texture, uv)
        local before = profiler.snapshot()
        local model = originalAtlas(cacheKey, spec, heightData, texture, uv)
        local after = profiler.snapshot()
        local relief = delta(before, after, "geometry.reducedTriangles")
        if relief > 0 then
            record(cacheKey, model.spec or spec, model.specs or { model.spec or spec },
                heightData, model, relief)
        end
        return model
    end
end

function probe.report()
    return rows
end

return probe
