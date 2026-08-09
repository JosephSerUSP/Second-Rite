-- Semantic virtual-input state shared by touch presentation and scene input.
--
-- This module knows only the project's logical SNES-style button names. It
-- deliberately has no keyboard bindings and no presentation coordinates.
local virtual_input = {}

local REPEATABLE = {
    UP = true, DOWN = true, LEFT = true, RIGHT = true,
}

local touches = {}      -- touch id -> { button, held, nextRepeat }
local downCounts = {}   -- logical button -> active touch count
local pending = {}      -- edge/repeat queue of logical buttons

local function inc(button)
    downCounts[button] = (downCounts[button] or 0) + 1
end

local function dec(button)
    local n = (downCounts[button] or 0) - 1
    if n > 0 then downCounts[button] = n else downCounts[button] = nil end
end

local function queue(button)
    if button then pending[#pending + 1] = button end
end

function virtual_input.press(id, button)
    if id == nil or not button then return false end
    local previous = touches[id]
    if previous and previous.button == button then return false end
    if previous then dec(previous.button) end
    touches[id] = { button = button, held = 0, nextRepeat = nil }
    inc(button)
    queue(button)
    return true
end

function virtual_input.move(id, button)
    local previous = touches[id]
    if not previous then
        if button then return virtual_input.press(id, button) end
        return false
    end
    if previous.button == button then return false end
    dec(previous.button)
    touches[id] = nil
    if button then
        touches[id] = { button = button, held = 0, nextRepeat = nil }
        inc(button)
        queue(button)
    end
    return true
end

function virtual_input.release(id)
    local previous = touches[id]
    if not previous then return false end
    dec(previous.button)
    touches[id] = nil
    return true
end

function virtual_input.clear()
    touches = {}
    downCounts = {}
    pending = {}
end

function virtual_input.isDown(button)
    return (downCounts[button] or 0) > 0
end

function virtual_input.activeTouchCount()
    local n = 0
    for _ in pairs(touches) do n = n + 1 end
    return n
end

-- Dispatches queued press edges and deterministic repeats. Directional repeat
-- mirrors the keyboard layer's update-driven behaviour without pretending a
-- touch is a keyboard key. Face/action buttons are edge-triggered only.
function virtual_input.update(dt, dispatch, initialDelay, repeatInterval)
    initialDelay = tonumber(initialDelay) or 0.30
    repeatInterval = tonumber(repeatInterval) or 0.06
    if repeatInterval <= 0 then repeatInterval = 0.06 end

    local queued = pending
    pending = {}
    if dispatch then
        for _, button in ipairs(queued) do dispatch(button) end
    end

    for _, touch in pairs(touches) do
        if REPEATABLE[touch.button] then
            touch.held = touch.held + (dt or 0)
            if not touch.nextRepeat then touch.nextRepeat = initialDelay end
            while touch.held >= touch.nextRepeat do
                if dispatch then dispatch(touch.button) end
                touch.nextRepeat = touch.nextRepeat + repeatInterval
            end
        end
    end
end

return virtual_input
