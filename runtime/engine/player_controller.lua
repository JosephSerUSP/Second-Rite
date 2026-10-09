local controls = require("engine.player_controls")
local scene_host = require("engine.scene_host")
local traversal_host = require("engine.traversal_host")

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
    -- A traversal provider consumes only canonical logical buttons. It never
    -- sees the physical key/device that produced them, and only gets first say
    -- while the Map Scene owns input. Providers that do not consume the edge
    -- fall through to the same authored Scene/main-host path as before.
    if scene_host.getCurrent() == "map" and ctx and ctx.session
            and traversal_host.buttonpressed(ctx.session, button) then
        return true
    end
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

-- A map transfer consumes a directional press until the device releases it.
-- Camera rotation can give the return threshold the same button as entry.
function controller.consumeUntilRelease(button)
    assertButton(button)
    if held[button] then held[button].consumed = true end
end

function controller.isHeld(button)
    assertButton(button)
    return held[button] ~= nil
end

function controller.snapshot()
    local result={}
    for button in pairs(require("engine.input_map").getBindings()) do result[button]=controller.isHeld(button) end
    return result
end

function controller.reset()
    held = {}
end

-- Host-driven logical repeat. `initial` and `interval` are supplied by the
-- ordinary Project UI configuration so physical and automated players share
-- the existing timing policy. Providers may additionally sample the canonical
-- held directions continuously; they still receive no physical key or device.
function controller.update(dt, ctx, options)
    options = options or {}
    local initial = tonumber(options.initial) or 0.3
    local interval = tonumber(options.interval) or 0.06
    if initial < 0 then initial = 0 end
    if interval <= 0 then interval = 0.06 end
    dt = math.max(0, tonumber(dt) or 0)

    if scene_host.getCurrent() == "map" and ctx and ctx.session then
        local function down(button)
            return held[button] ~= nil and held[button].consumed ~= true
        end
        local paused = require("engine.arena_host").update(ctx.session,dt)
        if paused then
            local root=ctx.session.continuousTraversal
            if root then root.moving=false end
        else
            traversal_host.update(ctx.session, dt, {
                up = down("UP"),
                down = down("DOWN"),
                left = down("LEFT"),
                right = down("RIGHT"),
            })
        end
    end

    local fired = false
    for _, button in ipairs(REPEAT_ORDER) do
        local state = held[button]
        if state and not state.consumed then
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
        if repeatable[button] and held[button] and not held[button].consumed then
            return dispatch(button, ctx), button
        end
    end
    return false, nil
end

return controller
