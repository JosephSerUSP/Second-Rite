-- #760 exact constant-field fixture.
--
-- This deliberately goes through geometry.loadAtlasSurface(), the same plane
-- compiler/QEM/sealing authority as atlas-authored relief. The height image is
-- exactly neutral (128/255), offset is exactly zero, and no epsilon or
-- near-flat classification exists. The surrounding #760 probe wraps this call
-- and records its normal compiler counters/timing.
local flat = {}

local SURFACES = { "wall", "floor", "ceiling" }
local NEUTRAL = 128 / 255

function flat.compile()
    local geometry = require("engine.geometry")

    local heightData = love.image.newImageData(1, 1)
    heightData:setPixel(0, 0, NEUTRAL, NEUTRAL, NEUTRAL, 1)
    local texture = love.graphics.newImage(heightData)
    texture:setFilter("nearest", "nearest")

    local models = {}
    for _, surface in ipairs(SURFACES) do
        local spec = {
            id = "issue760_flat_" .. surface,
            label = "#760 exact flat " .. surface,
            topology = "plane",
            role = "surfaceFixture",
            surface = surface,
            heightOperation = "add",
            heightScale = 0.08,
            meshColumns = 24,
            meshRows = 24,
            sampleColumns = 48,
            sampleRows = 48,
            triangleBudget = 384,
            offset = 0,
            sealPerimeter = true,
        }
        models[surface] = geometry.loadAtlasSurface(
            "issue760-flat:" .. surface,
            spec,
            heightData,
            texture,
            function(u, v) return u, v end)
    end
    return models
end

return flat
