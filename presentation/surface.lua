-- Presentation-surface geometry.
--
-- Second Rite authors its composition in a canonical 256x240 coordinate frame,
-- but the logical render surface may be larger. World/render-surface layers use
-- render coordinates; authored UI/battle/dialogue layers use composition
-- coordinates translated by the active profile's explicit origin.
--
-- Keep canonical-size migration separate from this module's first job. #206 is
-- the follow-up that may make the 256x240 composition itself configurable.
local surface = {}

local COMPOSITION_WIDTH = 256
local COMPOSITION_HEIGHT = 240

local profiles = {}
local activeProfileId = "classic"
local compositionDepth = 0
local rawSetScissor, rawIntersectScissor
local savedScissor = nil

local function integer(name, value)
    if type(value) ~= "number" or value ~= math.floor(value) then
        error("presentation surface " .. name .. " must be an integer", 3)
    end
    return value
end

function surface.registerProfile(id, spec)
    if type(id) ~= "string" or id == "" then
        error("presentation surface profile id must be a non-empty string", 2)
    end
    if type(spec) ~= "table" then
        error("presentation surface profile '" .. id .. "' must be a table", 2)
    end

    local renderWidth = integer("renderWidth", spec.renderWidth)
    local renderHeight = integer("renderHeight", spec.renderHeight)
    local originX = integer("compositionOriginX", spec.compositionOriginX)
    local originY = integer("compositionOriginY", spec.compositionOriginY)

    if renderWidth < COMPOSITION_WIDTH or renderHeight < COMPOSITION_HEIGHT then
        error("presentation surface profile '" .. id
            .. "' cannot be smaller than the 256x240 composition", 2)
    end
    if originX < 0 or originY < 0
        or originX + COMPOSITION_WIDTH > renderWidth
        or originY + COMPOSITION_HEIGHT > renderHeight then
        error("presentation surface profile '" .. id
            .. "' places the composition outside the render surface", 2)
    end

    profiles[id] = {
        id = id,
        renderWidth = renderWidth,
        renderHeight = renderHeight,
        compositionOriginX = originX,
        compositionOriginY = originY,
    }
end

surface.registerProfile("classic", {
    renderWidth = 256, renderHeight = 240,
    compositionOriginX = 0, compositionOriginY = 0,
})
-- Exact 4:3 at the authored 240-line height. The 64 added columns split evenly
-- into 32 pixels on each side, so the canonical UI remains perfectly centred.
surface.registerProfile("four_three", {
    renderWidth = 320, renderHeight = 240,
    compositionOriginX = 32, compositionOriginY = 0,
})
-- 426x240 is the nearest useful integer-centred approximation to 16:9 while
-- preserving the authored 240-line height. The 170 added columns split evenly
-- into 85 pixels on each side of the canonical frame.
surface.registerProfile("wide", {
    renderWidth = 426, renderHeight = 240,
    compositionOriginX = 85, compositionOriginY = 0,
})

function surface.setProfile(id)
    if not profiles[id] then
        error("unknown presentation surface profile '" .. tostring(id) .. "'", 2)
    end
    activeProfileId = id
end

function surface.getProfileId()
    return activeProfileId
end

function surface.getProfile(id)
    local p = profiles[id or activeProfileId]
    if not p then return nil end
    -- Return a copy so callers cannot silently mutate the registry.
    return {
        id = p.id,
        renderWidth = p.renderWidth,
        renderHeight = p.renderHeight,
        compositionOriginX = p.compositionOriginX,
        compositionOriginY = p.compositionOriginY,
    }
end

function surface.profileIds()
    local ids = {}
    for id in pairs(profiles) do ids[#ids + 1] = id end
    table.sort(ids)
    return ids
end

-- True while drawing inside beginComposition/endComposition. Lets a full-cover
-- effect ask "what is 'everything' right now?" instead of guessing: inside the
-- frame that is the composition, outside it the render surface. Without this a
-- render-sized rectangle drawn while translated by the origin covers
-- ox..ox+renderWidth and misses the columns to its left.
function surface.isComposing()
    return compositionDepth > 0
end

function surface.compositionSize()
    return COMPOSITION_WIDTH, COMPOSITION_HEIGHT
end

function surface.compositionWidth()
    return COMPOSITION_WIDTH
end

function surface.compositionHeight()
    return COMPOSITION_HEIGHT
end

function surface.renderSize()
    local p = profiles[activeProfileId]
    return p.renderWidth, p.renderHeight
end

function surface.renderWidth()
    return profiles[activeProfileId].renderWidth
end

function surface.renderHeight()
    return profiles[activeProfileId].renderHeight
end

function surface.compositionOrigin()
    local p = profiles[activeProfileId]
    return p.compositionOriginX, p.compositionOriginY
end

function surface.compositionOriginX()
    return profiles[activeProfileId].compositionOriginX
end

function surface.compositionOriginY()
    return profiles[activeProfileId].compositionOriginY
end

function surface.compositionToRender(x, y)
    local ox, oy = surface.compositionOrigin()
    return x + ox, y + oy
end

function surface.renderToComposition(x, y)
    local ox, oy = surface.compositionOrigin()
    return x - ox, y - oy
end

function surface.isInsideComposition(renderX, renderY)
    local x, y = surface.renderToComposition(renderX, renderY)
    return x >= 0 and y >= 0 and x < COMPOSITION_WIDTH and y < COMPOSITION_HEIGHT
end

-- Host-window -> logical render coordinates. Kept here with outputTransform so
-- mouse/touch picking cannot grow a second copy of the scaling/offset math.
function surface.hostToRender(x, y, scale, offsetX, offsetY)
    if type(scale) ~= "number" or scale <= 0 then
        error("presentation surface host scale must be > 0", 2)
    end
    return (x - (offsetX or 0)) / scale, (y - (offsetY or 0)) / scale
end

function surface.hostToComposition(x, y, scale, offsetX, offsetY)
    local renderX, renderY = surface.hostToRender(x, y, scale, offsetX, offsetY)
    return surface.renderToComposition(renderX, renderY)
end

-- Integer-nearest logical-surface -> host-window placement. This remains
-- separate from the inner composition origin: changing one must never
-- accidentally reframe the other.
function surface.outputTransform(hostWidth, hostHeight)
    local renderWidth, renderHeight = surface.renderSize()
    local scale = math.floor(math.min(hostWidth / renderWidth, hostHeight / renderHeight))
    scale = math.max(1, scale)
    local offsetX = math.floor((hostWidth - renderWidth * scale) / 2)
    local offsetY = math.floor((hostHeight - renderHeight * scale) / 2)
    return scale, offsetX, offsetY
end

-- LÖVE transforms draw geometry but setScissor/intersectScissor remain in
-- canvas coordinates. Composition-space drawing therefore has to translate
-- both together or a centred UI is clipped by rectangles left at x=0.
-- Centralising that rule here keeps window_renderer/ui unaware of profiles.
function surface.beginComposition()
    local ox, oy = surface.compositionOrigin()
    if compositionDepth == 0 then
        rawSetScissor = love.graphics.setScissor
        rawIntersectScissor = love.graphics.intersectScissor
        local sx, sy, sw, sh = love.graphics.getScissor()
        savedScissor = sx and { sx, sy, sw, sh } or false

        love.graphics.setScissor = function(x, y, w, h)
            if x == nil then return rawSetScissor() end
            return rawSetScissor(x + ox, y + oy, w, h)
        end
        love.graphics.intersectScissor = function(x, y, w, h)
            return rawIntersectScissor(x + ox, y + oy, w, h)
        end

        love.graphics.push()
        love.graphics.translate(ox, oy)
    else
        -- Nested composition code is already translated; preserve only its
        -- local transform stack rather than applying the origin twice.
        love.graphics.push()
    end
    compositionDepth = compositionDepth + 1
end

function surface.endComposition()
    if compositionDepth <= 0 then
        error("presentation surface composition stack underflow", 2)
    end
    love.graphics.pop()
    compositionDepth = compositionDepth - 1
    if compositionDepth == 0 then
        love.graphics.setScissor = rawSetScissor
        love.graphics.intersectScissor = rawIntersectScissor
        if savedScissor then
            rawSetScissor(savedScissor[1], savedScissor[2], savedScissor[3], savedScissor[4])
        else
            rawSetScissor()
        end
        savedScissor = nil
        rawSetScissor, rawIntersectScissor = nil, nil
    end
end

return surface
