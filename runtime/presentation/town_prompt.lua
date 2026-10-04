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

local VALID_DIRECTIONS = {
    UP = true,
    DOWN = true,
    LEFT = true,
    RIGHT = true,
}

function town_prompt.compactLabel(event)
    if not event then return "Door" end
    local authored = event.label
    if type(authored) == "string" and authored ~= "" then return authored end

    local name = tostring(event.name or "")
    -- Event names are useful as durable/debug descriptions, but navigation
    -- words duplicate the direction icon in this particular HUD projection.
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

function town_prompt.directionIcon(button)
    if button == nil then return nil end
    if not VALID_DIRECTIONS[button] then
        error("unknown town prompt direction '" .. tostring(button) .. "'", 2)
    end
    return { direction = button }
end

return town_prompt
