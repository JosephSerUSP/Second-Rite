local oldLove = love
local loadedImages = 0
local drawn = {}
local colors = {}

local files = {
    ["assets/smallBattlers/Pixie[fps=15].png"] = { w = 72, h = 24 },
    ["assets/system/Cursor.png"] = { w = 16, h = 8 },
}
local dirs = {
    ["assets/smallBattlers"] = { "Pixie[fps=15].png" },
    ["assets/sprites"] = {},
    ["assets/system"] = { "Cursor.png" },
}

love = {
    filesystem = {
        getDirectoryItems = function(dir)
            return dirs[dir] or {}
        end,
        getInfo = function(path)
            return files[path] and { type = "file" } or nil
        end,
    },
    graphics = {
        newImage = function(path)
            loadedImages = loadedImages + 1
            local spec = assert(files[path], "unexpected image path " .. tostring(path))
            local image = { filter = nil }
            function image:setFilter(min, mag) self.filter = { min, mag } end
            function image:getWidth() return spec.w end
            function image:getHeight() return spec.h end
            return image
        end,
        newQuad = function(x, y, w, h, iw, ih)
            return { x = x, y = y, w = w, h = h, iw = iw, ih = ih }
        end,
        setColor = function(r, g, b, a)
            colors[#colors + 1] = { r, g, b, a }
        end,
        draw = function(image, quad, x, y, rotation, sx, sy)
            drawn[#drawn + 1] = { image = image, quad = quad, x = x, y = y, sx = sx, sy = sy }
        end,
    },
}

package.loaded["presentation.sprite_sheet"] = nil
local sprites = require("presentation.sprite_sheet")

local function eq(actual, expected, message)
    if actual ~= expected then
        error((message or "values differ") .. ": expected " .. tostring(expected)
            .. ", got " .. tostring(actual), 0)
    end
end

local function truthy(value, message)
    if not value then error(message or "expected truthy value", 0) end
end

-- A stripped key finds a token-bearing filename and inherits its timing.
local resolved = assert(sprites.resolveFile("pixie"), "pixie should resolve")
eq(resolved.path, "assets/smallBattlers/Pixie[fps=15].png", "indexed token filename")
eq(resolved.tokens.fps, 15, "filename fps token")

-- Key-authored tokens override filename defaults without changing the file lookup.
local overridden = assert(sprites.resolveFile("pixie[fps=9]"), "overridden pixie should resolve")
eq(overridden.path, resolved.path, "override uses same file")
eq(overridden.tokens.fps, 9, "key fps overrides filename token")
eq(overridden.keyTokens.fps, 9, "key token provenance is retained")
eq(overridden.filenameTokens.fps, 15, "filename token provenance is retained")

local fileDefault = sprites.describe("pixie")
eq(fileDefault.timing.fps, 15, "description reports effective filename fps")
eq(fileDefault.timing.source, "filename", "description attributes inherited fps to filename")
eq(fileDefault.timing.token, "fps", "description names winning token")
truthy(fileDefault.summary:find("Filename tokens: fps=15", 1, true), "summary exposes filename provenance")

local keyOverride = sprites.describe("pixie[fps=9]")
eq(keyOverride.timing.fps, 9, "description reports key override fps")
eq(keyOverride.timing.source, "key", "description attributes override to authored key")

-- fps has priority over speed even when the speed token is the key-authored one.
local crossPriority = sprites.describe("pixie[speed=2]")
eq(crossPriority.keyTokens.speed, 2, "key speed provenance")
eq(crossPriority.filenameTokens.fps, 15, "filename fps provenance")
eq(crossPriority.timing.fps, 15, "fps outranks speed globally")
eq(crossPriority.timing.source, "filename", "winning filename fps is reported truthfully")

local pathDefault = sprites.describePath("assets/smallBattlers/Pixie[fps=15].png")
eq(pathDefault.timing.fps, 15, "file inspection uses runtime timing grammar")
eq(pathDefault.timing.source, "filename", "file inspection attributes token to filename")

-- Loading, horizontal square-cell slicing and cache reuse have one implementation.
local sheet = assert(sprites.get("pixie"), "sheet should load")
eq(sheet.cellW, 24, "cell width follows image height")
eq(sheet.cellH, 24, "cell height")
eq(sheet.numFrames, 3, "horizontal frame count")
eq(sheet.img.filter[1], "nearest", "nearest min filter")
eq(sheet.img.filter[2], "nearest", "nearest mag filter")
truthy(sprites.get("pixie") == sheet, "same key reuses cached sheet")
eq(loadedImages, 1, "cache prevents duplicate image load")

-- Explicit preview time and the shared idle clock use the same rate math.
eq(sprites.frameAt(sheet, 0), 0, "frameAt begins on frame zero")
eq(sprites.frameAt(sheet, 0.08), 1, "filename fps drives explicit-time frame")
sprites.update(0.08)
eq(sprites.frame(sheet), 1, "shared clock uses the same frame rate")
sprites.reset()
eq(sprites.frame(sheet), 0, "reset rewinds only the shared clock")

-- Quad slicing is cached per frame, and generic UI sprites can draw without any
-- dependency on presentation.small_battlers. The draw also preserves the old
-- path's white graphics-state hygiene so caller tint cannot leak into cursors.
local q1 = sprites.quad(sheet, 1)
local q1again = sprites.quad(sheet, 1)
truthy(q1 == q1again, "quad cache reuses the same frame quad")
eq(q1.x, 24, "frame-one quad x")
truthy(sprites.draw("Cursor", 3, 4, 16, 1), "generic sprite draw succeeds")
eq(#drawn, 1, "one generic draw call")
eq(drawn[1].quad.x, 8, "cursor frame one is sliced from its own cell width")
eq(drawn[1].sx, 2, "requested size scales from cell width")
eq(#colors, 2, "generic draw sets and restores white")
for i, color in ipairs(colors) do
    eq(color[1], 1, "white red at call " .. i)
    eq(color[2], 1, "white green at call " .. i)
    eq(color[3], 1, "white blue at call " .. i)
    eq(color[4], 1, "white alpha at call " .. i)
end

package.loaded["presentation.sprite_sheet"] = nil
love = oldLove

print("SPRITE SHEET TEST OK")
