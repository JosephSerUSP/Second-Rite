-- Executable capability probe for #841. This deliberately exercises LÖVE 11.5
-- attachments instead of inferring depth ownership from an API signature.
-- It is not a renderer implementation or a retained render-target abstraction.
local function fail(message)
    error("test_world_presentation_audit: " .. message, 0)
end

local function check(condition, message)
    if not condition then fail(message) end
    print("  [PASS] " .. message)
end

print("=== TEST WORLD PRESENTATION AUDIT ===")

local color = love.graphics.newCanvas(16, 16)
local depthStencil = love.graphics.newCanvas(16, 16, { format = "depth24stencil8" })

-- First pass writes red and depth 0. Rebinding the exact same depth/stencil
-- Canvas for a second pass makes another default-z (0) primitive fail the
-- strict "less" test. The retained attachment, rather than a sampled depth
-- texture or an inferred mask, remains the cross-pass spatial authority.
love.graphics.push("all")
love.graphics.setCanvas({ color, depthstencil = depthStencil })
love.graphics.clear(0, 0, 0, 1, true, true)
love.graphics.setDepthMode("less", true)
love.graphics.setColor(1, 0, 0, 1)
love.graphics.rectangle("fill", 0, 0, 16, 16)
love.graphics.setCanvas()

love.graphics.setCanvas({ color, depthstencil = depthStencil })
love.graphics.setDepthMode("less", true)
love.graphics.setColor(0, 0, 1, 1)
love.graphics.rectangle("fill", 0, 0, 16, 16)
love.graphics.setDepthMode()
love.graphics.setCanvas()
love.graphics.pop()

local data = color:newImageData()
local r, g, b = data:getPixel(8, 8)
check(r > 0.99 and g < 0.01 and b < 0.01,
    "retained depth24stencil8 attachment rejects a later equal-depth draw")

-- MSAA applies to the attachment set as a whole: color and supplied
-- depth/stencil use matching sample counts. We only assert successful binding
-- here; the semantic outcome is the documented multisample resolve owned by
-- LÖVE, not an assumption that depth becomes sampleable by this game.
local limits = love.graphics.getSystemLimits()
local maxMsaa = limits and limits.canvasmsaa or 0
if maxMsaa >= 2 then
    local msaaColor = love.graphics.newCanvas(16, 16, { msaa = 2 })
    local msaaDepth = love.graphics.newCanvas(16, 16, {
        format = "depth24stencil8", msaa = 2,
    })
    local ok, err = pcall(function()
        love.graphics.setCanvas({ msaaColor, depthstencil = msaaDepth })
        love.graphics.clear(0, 0, 0, 1, true, true)
        love.graphics.setCanvas()
    end)
    check(ok, "matching MSAA color and depth/stencil attachments bind cleanly: " .. tostring(err))
    msaaColor:release()
    msaaDepth:release()
else
    print("  [SKIP] canvas MSAA unavailable on this renderer")
end

color:release()
depthStencil:release()
print("test_world_presentation_audit: OK")
