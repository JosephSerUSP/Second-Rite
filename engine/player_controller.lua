local controls = require("engine.player_controls")
local scene_host = require("engine.scene_host")

local controller = {}

-- Held state belongs to the logical player membrane, never to a keyboard
-- adapter. A physical key and an external player policy therefore accumulate
-- the exact same repeat timing after both have resolved to a canonical button.
local held = {}
local REPEAT_ORDER = { "UP", "DOWN", "LEFT", "RIGHT", "L", "R" }
local repeatable = {}
for _, button in ipairs(REPEAT_ORDER) do repeatable[button] = true end

local function assertButton(button)
    assert(controller.isButton(button), "unknown logical player button")
end

local function dispatch(button, ctx)
    return scene_host.buttonpressed(button, ctx)
end

function controller.isButton(button)
    return controls.contains(button)
end

function controller.press(button, ctx)
    assertButton(button)
    -- A press is an edge. Device key-repeat, replay duplication, or a policy
    -- calling press twice without release must not manufacture a second edge;
    -- repeatable held buttons are re-fired only by controller.update().
    if held[button] then return true end
    held[button] = { holdTime = 0, lastFire = 0 }
    return dispatch(button, ctx)
end

function controller.release(button)
    assertButton(button)
    held[button] = nil
    return true
end

function controller.isHeld(button)
    assertButton(button)
    return held[button] ~= nil
end

function controller.reset()
    held = {}
end

-- Host-driven logical repeat. `initial` and `interval` are supplied by the
-- ordinary Project UI configuration so physical and automated players share
-- the existing timing policy. This emits only canonical button presses; it has
-- no map-step, turn, dialogue-choice, Event, coordinate, or Scene-hook API.
function controller.update(dt, ctx, options)
    options = options or {}
    local initial = tonumber(options.initial) or 0.3
    local interval = tonumber(options.interval) or 0.06
    if initial < 0 then initial = 0 end
    if interval <= 0 then interval = 0.06 end
    dt = math.max(0, tonumber(dt) or 0)

    local fired = false
    for _, button in ipairs(REPEAT_ORDER) do
        local state = held[button]
        if state then
            state.holdTime = state.holdTime + dt
            if state.holdTime >= initial then
                local elapsed = state.holdTime - initial
                local fireCount = math.floor(elapsed / interval)
                if fireCount > state.lastFire then
                    state.lastFire = fireCount
                    if dispatch(button, ctx) then fired = true end
                end
            end
        end
    end
    return fired
end

-- Movement transitions historically re-fired the first still-held direction
-- immediately when their camera interpolation completed. Keep that feel at the
-- logical membrane instead of asking the keyboard which physical key is down.
function controller.refireFirstHeld(ctx)
    for _, button in ipairs(REPEAT_ORDER) do
        if repeatable[button] and held[button] then
            return dispatch(button, ctx), button
        end
    end
    return false, nil
end

return controller
