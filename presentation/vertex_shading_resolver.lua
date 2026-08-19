-- Presentation-side composition of environment vertex shading with the static
-- illumination field consumed by viewport_3d.
--
-- Authored truth stays separate (`vertexShadingLayers` vs light sources/grid).
-- This module derives one transient RGB vertex modulation only at the renderer
-- boundary so the established viewport interpolation/mesh path stays singular.
local resolver = {}
local viewport_3d = require("presentation.viewport_3d")
local vertex_shading = require("engine.vertex_shading")

local cache = setmetatable({}, { __mode = "k" })
local WHITE = { 1, 1, 1 }

local function lightAt(light, x, y)
    local row = light and light[y]
    return (row and row[x]) or WHITE
end

function resolver.composite(session)
    local mapData = session and session.currentMapData
    local grid = session and session.mapGrid
    local layers = mapData and mapData.vertexShadingLayers
    if not (mapData and grid and grid[1] and layers and #layers > 0) then return nil end

    local light = mapData.runtimeLight
    local width, height = #grid[1], #grid
    local previous = cache[mapData]
    if previous and previous.gridIdentity == grid and previous.layersIdentity == layers
            and previous.lightIdentity == light and previous.width == width and previous.height == height then
        return previous.composite
    end

    local shading = vertex_shading.grid(layers, width, height)
    local combined = {}
    for y = 1, height + 1 do
        combined[y] = {}
        for x = 1, width + 1 do
            local base = lightAt(light, x, y)
            local tint = shading[y][x]
            combined[y][x] = {
                base[1] * tint[1],
                base[2] * tint[2],
                base[3] * tint[3],
            }
        end
    end

    cache[mapData] = {
        gridIdentity = grid,
        layersIdentity = layers,
        lightIdentity = light,
        width = width,
        height = height,
        composite = combined,
    }
    return combined
end

-- Run an existing presentation path under the derived vertex modulation while
-- preserving all of that path's other responsibilities (HUD, composition
-- origin, etc.). Restoration happens even if the draw raises.
function resolver.withComposite(session, fn)
    local mapData = session and session.currentMapData
    local combined = resolver.composite(session)
    if not combined then return fn() end

    local previous = mapData.runtimeLight
    mapData.runtimeLight = combined
    local ok, a, b, c = pcall(fn)
    mapData.runtimeLight = previous
    if not ok then error(a, 0) end
    return a, b, c
end

function resolver.draw(session)
    return resolver.withComposite(session, function()
        return viewport_3d.draw(session)
    end)
end

function resolver.forget(mapData)
    if mapData then cache[mapData] = nil end
end

return resolver
