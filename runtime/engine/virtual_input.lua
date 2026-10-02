-- Logical touch ownership used by the mobile presentation adapter.
--
-- This module tracks which canonical SNES-style buttons are physically held by
-- touches so the renderer can show state and the adapter can release the right
-- player_controller button. Dispatch/repeat belongs exclusively to
-- engine.player_controller.
local virtual_input = {}

local touches = {}      -- touch id -> { button }
local downCounts = {}   -- logical button -> active touch count

local function inc(button)
    downCounts[button] = (downCounts[button] or 0) + 1
end

local function dec(button)
    local n = (downCounts[button] or 0) - 1
    if n > 0 then downCounts[button] = n else downCounts[button] = nil end
end

function virtual_input.press(id, button)
    if id == nil or not button then return false end
    local previous = touches[id]
    if previous and previous.button == button then return false end
    if previous then dec(previous.button) end
    touches[id] = { button = button }
    inc(button)
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
        touches[id] = { button = button }
        inc(button)
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

-- Device adapters may need to release the canonical controller button that a
-- touch owned before mutating the touch table. This exposes only logical input,
-- never presentation coordinates.
function virtual_input.touchButton(id)
    local touch = touches[id]
    return touch and touch.button or nil
end

function virtual_input.downButtons()
    local result = {}
    for button in pairs(downCounts) do result[#result + 1] = button end
    table.sort(result)
    return result
end

function virtual_input.clear()
    touches = {}
    downCounts = {}
end

function virtual_input.isDown(button)
    return (downCounts[button] or 0) > 0
end

function virtual_input.activeTouchCount()
    local n = 0
    for _ in pairs(touches) do n = n + 1 end
    return n
end

return virtual_input
