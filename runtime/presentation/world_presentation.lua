-- Scene-owned world presentation semantics.
--
-- `pixelsPerTile` describes authored/design raster density: how many source-art
-- pixels correspond to one world tile at native authored scale. It is NOT a
-- physical monitor-pixel guarantee and does not move the camera by itself.
local world_presentation = {}

local function finite(value, label)
    value = tonumber(value)
    if not value or value ~= value or value == math.huge or value == -math.huge then
        error(label .. " must be finite", 0)
    end
    return value
end

function world_presentation.resolvePixelsPerTile(value)
    if value == nil then return nil end
    value = finite(value, "pixelsPerTile")
    if value <= 0 then error("pixelsPerTile must be positive", 0) end
    return value
end

function world_presentation.designPixelsToTiles(pixels, pixelsPerTile)
    pixels = finite(pixels, "design pixels")
    pixelsPerTile = world_presentation.resolvePixelsPerTile(pixelsPerTile)
    return pixels / pixelsPerTile
end

function world_presentation.tilesToDesignPixels(tiles, pixelsPerTile)
    tiles = finite(tiles, "world tiles")
    pixelsPerTile = world_presentation.resolvePixelsPerTile(pixelsPerTile)
    return tiles * pixelsPerTile
end

function world_presentation.imageSizeInTiles(width, height, pixelsPerTile)
    return world_presentation.designPixelsToTiles(width, pixelsPerTile),
        world_presentation.designPixelsToTiles(height, pixelsPerTile)
end

-- Return a presentation-only copy so callers can freely resolve/inspect it
-- without mutating the authored Scene table held by the loader/editor.
function world_presentation.resolve(spec)
    if spec == nil then return nil end
    if type(spec) ~= "table" then error("worldPresentation must be an object", 0) end
    local result = {}
    result.pixelsPerTile = world_presentation.resolvePixelsPerTile(spec.pixelsPerTile)
    if spec.camera ~= nil then
        if type(spec.camera) ~= "table" then
            error("worldPresentation.camera must be an object", 0)
        end
        local camera = {}
        for key, value in pairs(spec.camera) do camera[key] = value end
        result.camera = camera
    end
    return result
end

return world_presentation
