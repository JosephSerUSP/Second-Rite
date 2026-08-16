-- Developer-only input adapter for the overhead camera playtest.
--
-- Existing exploration input is relative to player facing (forward/back/strafe).
-- For an overhead camera, physical WASD should instead express world-cardinal
-- intent while still flowing through main.lua's existing movement, collision,
-- bump, Event, encounter and transition code. This adapter translates WASD to
-- the host's existing forward input after setting the desired cardinal facing.
--
-- It deliberately does not replace exploration movement or own repeat timing.
-- The host's existing held-key repeat continues to fire `w`; love.keyboard's
-- query is adapted while this developer profile is active so held A/S/D are
-- seen by that loop as the corresponding world-facing forward intent.
local scene_host = require("engine.scene_host")

local overhead_input = {}

local WORLD_FACING = {
    w = "N",
    d = "E",
    s = "S",
    a = "W",
}
local KEY_PRIORITY = { "w", "a", "s", "d" }

local boundSession = nil
local installed = false
local rawIsDown = nil
local rawKeypressed = nil

function overhead_input.worldFacingForKey(key)
    return WORLD_FACING[key]
end

local function active()
    if not (boundSession
        and boundSession.worldCameraProfile
        and boundSession.worldCameraProfile ~= "first_person"
        and scene_host.getCurrent() == "map") then
        return false
    end
    -- Map command/cursor overlays remain the Map scene. Do not reinterpret
    -- their navigation keys as world movement or rotate the actor behind them.
    local state = scene_host.getCurrentState()
    local mode = state and state.v and state.v.mode
    return mode == nil or mode == 0
end

local function transitionActive(session)
    return session.transitionTimer and session.transitionTimer > 0
end

local function adoptFacing(session, facing)
    if session.playerDir ~= facing then
        -- Turning in the existing first-person controls clears bump cooldowns;
        -- world-relative facing changes should keep that same usability rule.
        session.bumpCooldowns = {}
    end
    session.playerDir = facing
end

local function heldWorldFacing()
    if not rawIsDown then return nil end
    for _, key in ipairs(KEY_PRIORITY) do
        if rawIsDown(key) then return WORLD_FACING[key] end
    end
    return nil
end

local function installIfReady()
    if installed then return true end
    if not love or not love.keyboard or type(love.keyboard.isDown) ~= "function"
        or type(love.keypressed) ~= "function" then
        return false
    end

    installed = true
    rawIsDown = love.keyboard.isDown
    rawKeypressed = love.keypressed

    -- main.lua's repeat loop asks whether each direction key is held and then
    -- calls its local handleKeyPressed(key). Under overhead play, collapse the
    -- physical WASD quartet into the host's existing `w`/forward lane. This
    -- preserves its own repeat delay/rate and all post-step consequences.
    love.keyboard.isDown = function(key, ...)
        if active() then
            if key == "w" then
                local facing = heldWorldFacing()
                if facing then
                    -- Never change the facing basis underneath an in-flight
                    -- interpolation. The held key remains visible as `w`, so the
                    -- host retries naturally once the current step completes.
                    if not transitionActive(boundSession) then
                        adoptFacing(boundSession, facing)
                    end
                    return true
                end
            elseif WORLD_FACING[key] then
                return false
            end
        end
        return rawIsDown(key, ...)
    end

    love.keypressed = function(key, scancode, isrepeat)
        local facing = active() and WORLD_FACING[key] or nil
        if facing then
            if transitionActive(boundSession) then return end
            adoptFacing(boundSession, facing)
            -- The host still performs the actual move and therefore retains
            -- collision, bump/door Events, MP, per-step flows and encounters.
            return rawKeypressed("w", scancode, isrepeat)
        end
        return rawKeypressed(key, scancode, isrepeat)
    end

    return true
end

function overhead_input.bind(session)
    boundSession = session
    installIfReady()
end

function overhead_input.isInstalled()
    return installed
end

return overhead_input
