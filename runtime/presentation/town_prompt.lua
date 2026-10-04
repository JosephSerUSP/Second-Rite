-- Presentation-only formatting for bounded-lane interaction prompts.
-- Gameplay keeps using engine.bounded_lane's UP/DOWN/LEFT/RIGHT semantics;
-- this module only turns that resolved input fact into compact HUD language.
local town_prompt = {}

local NAVIGATION_PREFIXES = {
    "^Out to the%s+",
    "^Out to%s+",
    "^Up to the%s+",
    "^Up to%s+",
    "^Down to the%s+",
    "^Down to%s+",
    "^Into the%s+",
    "^Into%s+",
}

local DIRECTION_ROTATION = {
    UP = 0,
    RIGHT = math.pi / 2,
    DOWN = math.pi,
    LEFT = -math.pi / 2,
}

function town_prompt.compactLabel(event)
    if not event then return "Door" end
    local authored = event.label
    if type(authored) == "string" and authored ~= "" then return authored end

    local name = tostring(event.name or "")
    -- Event names are useful as durable/debug descriptions, but navigation
    -- words duplicate the direction glyph in this particular HUD projection.
    -- Strip only generic route grammar; never substitute destination content.
    name = name:gsub("%s*%([23][Dd]%)%s*$", "")
    for _, prefix in ipairs(NAVIGATION_PREFIXES) do
        local compact, count = name:gsub(prefix, "", 1)
        if count > 0 then
            name = compact
            break
        end
    end
    name = name:gsub("^The%s+", "")
    name = name:match("^%s*(.-)%s*$") or ""
    if name == "" then return "Door" end
    -- Prefix removal can expose an authored lowercase article/noun.
    name = name:gsub("^%l", string.upper, 1)
    return name
end

local function parseRenderedDoorLabel(text)
    if type(text) ~= "string" then return nil end
    -- Lua patterns do not have regex alternation; capture the uppercase input
    -- token, then validate it against the same four rotations the glyph owns.
    local name, direction = text:match("^(.-)%s+%-%s+([A-Z]+)$")
    if not direction or DIRECTION_ROTATION[direction] == nil then return nil end
    return name, direction
end

town_prompt.parseRenderedDoorLabel = parseRenderedDoorLabel

local function resolvedCompactLabel(session, renderedName, direction)
    local lane = require("engine.bounded_lane")
    local doorway = lane.promptDoorway(session)
    local event = lane.eventFor(session, doorway)
    if event and lane.doorwayButton(session, doorway) == direction then
        return town_prompt.compactLabel(event)
    end
    return town_prompt.compactLabel({ name = renderedName })
end

-- Small D-pad-style control glyph used only by the town prompt projection.
-- This is not an iconset asset: it intentionally carries no authored item/
-- state semantics and never computes or samples iconset atlas coordinates.
local function drawDirectionGlyph(direction, x, y, color, size)
    local rotation = DIRECTION_ROTATION[direction]
    if rotation == nil then
        error("unknown town prompt direction '" .. tostring(direction) .. "'", 2)
    end
    size = math.max(6, math.floor(size or 8))
    local half = math.floor(size / 2)
    local stem = math.max(1, math.floor(size / 5))
    local head = math.max(2, half - 1)

    local function drawAt(dx, dy, c)
        love.graphics.push("all")
        love.graphics.translate(math.floor(x + half + dx), math.floor(y + half + dy))
        love.graphics.rotate(rotation)
        love.graphics.setColor(c)
        love.graphics.polygon("fill",
            0, -half,
            head, -stem,
            stem, -stem,
            stem, half - 1,
            -stem, half - 1,
            -stem, -stem,
            -head, -stem)
        love.graphics.pop()
    end

    drawAt(1, 1, { 0, 0, 0, 0.8 })
    drawAt(0, 0, color or { 1, 1, 0.5, 1 })
end

town_prompt.drawDirectionGlyph = drawDirectionGlyph

-- renderer.drawMap still owns the generic event-label animation. Keep that
-- single animation/layout path and project bounded-lane door labels through a
-- scoped UI adapter: measurement and drawing both see the same compact content,
-- so the panel itself shrinks rather than merely replacing the visible words.
-- The adapter exists only for the duration of one bounded-lane world draw and
-- restores the shared UI functions even if rendering raises.
function town_prompt.withCompactDoorUi(session, drawFn)
    local lane = require("engine.bounded_lane")
    if not session or not lane.isActive(session) then
        return drawFn()
    end

    local ui = require("presentation.ui")
    local originalMeasure = ui.measureText
    local originalDrawString = ui.drawString
    local iconSize = ui.iconSize or 8
    local gap = math.max(2, math.floor((ui.tileSize or 8) / 2))

    local function projection(text)
        local renderedName, direction = parseRenderedDoorLabel(text)
        if not direction then return nil end
        local label = resolvedCompactLabel(session, renderedName, direction)
        return label, direction
    end

    ui.measureText = function(text)
        local label, direction = projection(text)
        if label and direction then
            return iconSize + gap + originalMeasure(label)
        end
        return originalMeasure(text)
    end

    ui.drawString = function(text, x, y, color, alignment, limit, eventName, font)
        local label, direction = projection(text)
        if not label or not direction then
            return originalDrawString(text, x, y, color, alignment, limit, eventName, font)
        end

        color = color or { 1, 1, 1, 1 }
        local labelW = originalMeasure(label)
        local totalW = iconSize + gap + labelW
        local startX = x
        if alignment == "center" and limit then
            startX = x + math.floor((limit - totalW) / 2)
        elseif alignment == "right" and limit then
            startX = x + math.max(0, limit - totalW)
        end
        local iconY = y + math.floor(((ui.lineHeight or iconSize) - iconSize) / 2)
        drawDirectionGlyph(direction, startX, iconY, color, iconSize)
        return originalDrawString(label, startX + iconSize + gap, y, color,
            "left", math.max(labelW + 2, 2), eventName, font)
    end

    local results = { xpcall(drawFn, debug.traceback) }
    ui.measureText = originalMeasure
    ui.drawString = originalDrawString
    if not results[1] then error(results[2], 0) end
    table.remove(results, 1)
    return unpack(results)
end

return town_prompt
