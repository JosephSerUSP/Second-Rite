-- Developer-facing playable proof for overhead Map cameras.
--
-- The player is injected only for the duration of viewport rendering as a
-- synthetic sprite Event, so it reuses the exact world billboard/depth/fog/
-- lighting path without becoming authored Map data or participating in Event
-- lookup, collision, interaction, or save state.
--
-- Camera projection and structural visibility remain owned by world_camera.
-- This adapter selects camera profile identities only; it must not rewrite a
-- profile's visibility policy (in particular #606's play-overhead policy).
local viewport_3d = require("presentation.viewport_3d")
local player_actor = require("engine.player_actor")
local overhead_input = require("engine.overhead_playtest_input")
local player_visual = require("presentation.player_character_visual")

local playable = {}
local installed = false
local previousF7, previousF8 = false, false

local CAMERA_PROFILES = {
    "first_person",
    "ortho_oblique",
    "rpg_ortho",
    "perspective_oblique",
    "rpg_perspective",
}

local function cameraProfile(session)
    return session.worldCameraProfile or "first_person"
end

local function cycleCamera(session)
    local current = cameraProfile(session)
    local index = 1
    for i, id in ipairs(CAMERA_PROFILES) do
        if id == current then index = i break end
    end
    local nextId = CAMERA_PROFILES[index % #CAMERA_PROFILES + 1]
    session.worldCameraProfile = nextId
    print("[overhead playtest] camera: " .. nextId)
    return nextId
end

local function pollDeveloperControls(session)
    local keyboard = love and love.keyboard
    if not keyboard or not keyboard.isDown then return end

    local f7 = keyboard.isDown("f7")
    if f7 and not previousF7 then
        local profile = player_visual.cycle()
        print("[overhead playtest] character: " .. profile.label)
    end
    previousF7 = f7

    local f8 = keyboard.isDown("f8")
    if f8 and not previousF8 then cycleCamera(session) end
    previousF8 = f8
end

local function syntheticPlayerEvent(session)
    local actor = player_actor.snapshot(session)
    local clock = love and love.timer and love.timer.getTime and love.timer.getTime() or 0
    return {
        id = "__player_overhead_playtest",
        -- Event billboards historically receive tile-origin coordinates and
        -- add +1.5 internally. Offset the interpolated actor root so the final
        -- world center is exactly player_actor.root(session).
        x = actor.rootX - 1.5,
        y = actor.rootY - 1.5,
        sprite = player_visual.resolve(actor, clock),
        name = "Player (overhead playtest)",
        label = "Player (overhead playtest)",
        trigger = "none",
    }
end

function playable.cameraProfiles()
    local out = {}
    for i, id in ipairs(CAMERA_PROFILES) do out[i] = id end
    return out
end

function playable.install()
    if installed then return false end
    installed = true

    local originalDraw = viewport_3d.draw
    viewport_3d.draw = function(session)
        if session then
            -- Binding occurs on the first real frame, after main.lua has
            -- installed its LOVE callbacks. The adapter translates overhead
            -- WASD at the input seam while reusing the host's movement logic.
            overhead_input.bind(session)
            pollDeveloperControls(session)
        end
        if not session or cameraProfile(session) == "first_person"
                or not session.currentMapData then
            return originalDraw(session)
        end

        local mapData = session.currentMapData
        local originalEvents = mapData.events
        local events = originalEvents
        if type(events) ~= "table" then
            events = {}
            mapData.events = events
        end
        events[#events + 1] = syntheticPlayerEvent(session)

        local ok, err = pcall(originalDraw, session)
        events[#events] = nil
        if originalEvents == nil then mapData.events = nil end
        if not ok then error(err, 0) end
    end
    return true
end

function playable.isInstalled()
    return installed
end

return playable
