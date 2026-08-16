-- Shared animated sprite-sheet service.
--
-- This is the presentation-level authority for resolving sprite keys, loading
-- and caching images, slicing horizontal square-cell strips, caching quads, and
-- selecting idle-animation frames from one shared deterministic clock. It is
-- intentionally not a battler module: cursors, waiting indicators, editor /
-- server markers, battlers, and validation/preview tooling all speak the same
-- sprite vocabulary without depending on combat presentation semantics.
--
-- Sheet format: animated horizontal strip, square cell size = image height.
-- Filenames may carry [key=value] tokens overriding animation parameters:
--   [speed=N]  multiplier on the base frame rate (default 4)
--   [fps=N]    explicit frames per second (overrides speed)

local sprite_sheet = {}

local cache = {}
local fileIndex = nil
local animTimer = 0

local ASSET_DIRS = {
    "assets/smallBattlers",
    "assets/sprites",
    "assets/system",
}

local function parseKey(spriteKey)
    local overrides = {}
    local fileKey = tostring(spriteKey):gsub("%[([^=]+)=([^%]]+)%]", function(k, v)
        overrides[k] = tonumber(v) or v
        return ""
    end)
    fileKey = fileKey:gsub("^%s*(.-)%s*$", "%1")
    return fileKey, overrides
end

local function ensureFileIndex()
    if fileIndex then return fileIndex end
    local index = {}
    for _, dir in ipairs(ASSET_DIRS) do
        for _, filename in ipairs(love.filesystem.getDirectoryItems(dir) or {}) do
            if filename:match("%.png$") then
                local tokens = {}
                local base = filename:gsub("%.png$", ""):gsub(
                    "%[([^=]+)=([^%]]+)%]", function(k, v)
                        tokens[k] = tonumber(v) or v
                        return ""
                    end)
                base = base:gsub("^%s*(.-)%s*$", "%1"):lower()
                -- Directory order is part of the historical lookup contract:
                -- the first matching stripped basename wins.
                if index[base] == nil then
                    index[base] = { path = dir .. "/" .. filename, tokens = tokens }
                end
            end
        end
    end
    fileIndex = index
    return index
end

-- Resolve a sprite key to { path, tokens } without loading the image. Key-level
-- [k=v] tokens override filename tokens; filename tokens remain useful defaults.
function sprite_sheet.resolveFile(spriteKey)
    if not spriteKey or spriteKey == "" then return nil end

    local fileKey, overrides = parseKey(spriteKey)
    local paths = {
        "assets/smallBattlers/" .. fileKey:sub(1, 1):upper() .. fileKey:sub(2):lower() .. ".png",
        "assets/smallBattlers/" .. fileKey .. ".png",
        "assets/smallBattlers/" .. fileKey:lower() .. ".png",
        "assets/sprites/" .. fileKey .. ".png",
        "assets/system/" .. fileKey .. ".png",
        "assets/system/" .. fileKey:sub(1, 1):upper() .. fileKey:sub(2):lower() .. ".png",
    }

    local indexed = ensureFileIndex()[fileKey:lower()]
    if indexed then
        table.insert(paths, indexed.path)
        for k, v in pairs(indexed.tokens) do
            if overrides[k] == nil then overrides[k] = v end
        end
    end

    for _, path in ipairs(paths) do
        if love.filesystem.getInfo(path) then
            return { path = path, tokens = overrides }
        end
    end
    return nil
end

-- Load/cache one sprite sheet. A false cache entry preserves the historical
-- behavior that a missing key is not repeatedly re-scanned every draw frame.
function sprite_sheet.get(spriteKey)
    if not spriteKey or spriteKey == "" then return nil end
    local key = tostring(spriteKey)
    if cache[key] ~= nil then return cache[key] or nil end

    local resolved = sprite_sheet.resolveFile(key)
    if not resolved then
        cache[key] = false
        return nil
    end

    local image = love.graphics.newImage(resolved.path)
    image:setFilter("nearest", "nearest")
    local width = image:getWidth()
    local height = image:getHeight()
    local cellH = height
    local cellW = math.min(width, cellH)
    local numFrames = math.max(1, math.floor(width / cellW))
    local result = {
        img = image,
        cellW = cellW,
        cellH = cellH,
        numFrames = numFrames,
        speed = resolved.tokens.speed,
        fps = resolved.tokens.fps,
        quads = {},
        path = resolved.path,
    }
    cache[key] = result
    return result
end

local function frameRate(sheet)
    return sheet.fps or (sheet.speed and 4 * sheet.speed or 4)
end

-- Deterministic frame selection for callers that own an explicit elapsed time
-- (animation preview) as well as the process-wide idle clock below.
function sprite_sheet.frameAt(sheet, elapsed)
    if not sheet then return 0 end
    return math.floor((elapsed or 0) * frameRate(sheet)) % sheet.numFrames
end

function sprite_sheet.frame(sheet)
    return sprite_sheet.frameAt(sheet, animTimer)
end

function sprite_sheet.quad(sheet, frame)
    if not sheet then return nil end
    frame = frame or 0
    if not sheet.quads[frame] then
        sheet.quads[frame] = love.graphics.newQuad(
            frame * sheet.cellW, 0, sheet.cellW, sheet.cellH,
            sheet.img:getWidth(), sheet.img:getHeight())
    end
    return sheet.quads[frame]
end

-- Generic animated sprite draw. Battler-specific tint/shake/particles live in
-- presentation/small_battlers.lua and deliberately do not leak into this API.
-- The historical generic path through small_battlers also forced draw colour
-- to white before/after the sprite; preserve that graphics-state hygiene so
-- extracting the service cannot tint a cursor/indicator based on its caller.
function sprite_sheet.draw(spriteKey, x, y, size, frame)
    local sheet = sprite_sheet.get(spriteKey)
    if not (sheet and sheet.img) then return false end
    local current = frame
    if current == nil then current = sprite_sheet.frame(sheet) end
    local scale = (size or sheet.cellW) / sheet.cellW
    love.graphics.setColor(1, 1, 1, 1)
    love.graphics.draw(sheet.img, sprite_sheet.quad(sheet, current), x, y, 0, scale, scale)
    love.graphics.setColor(1, 1, 1, 1)
    return true
end

function sprite_sheet.update(dt)
    animTimer = animTimer + dt
end

-- Harness reset: rewind only the shared clock. Loaded image/file caches remain
-- process-scoped exactly as before, so this changes determinism, not I/O policy.
function sprite_sheet.reset()
    animTimer = 0
end

return sprite_sheet
