-- Renderer- and owner-neutral semantic animation state for a world character.
--
-- This module knows nothing about Maps, Events, the player, cameras, sprite
-- sheets, Blender Actions, frame rates or collision. Owners provide a plain
-- state table and publish semantic facts; presentation resolves the returned
-- clip/facing into an actual visual.
local character_state = {}

local VALID_LOCOMOTION = {
    idle = true,
    moving = true,
}

local FACING_ALIASES = {
    N = "N", E = "E", S = "S", W = "W",
    north = "N", east = "E", south = "S", west = "W",
    up = "N", right = "E", down = "S", left = "W",
}

function character_state.normalizeFacing(value)
    if value == nil then return nil end
    local text = tostring(value)
    return FACING_ALIASES[text]
        or FACING_ALIASES[text:lower()]
        or FACING_ALIASES[text:upper()]
end

function character_state.new(facing)
    return {
        facing = character_state.normalizeFacing(facing) or "S",
        locomotion = "idle",
        override = nil,
    }
end

local function requireState(state, operation)
    if type(state) ~= "table" then
        error("character_state." .. operation .. ": state table required", 3)
    end
end

local function requireClip(clip, operation)
    if type(clip) ~= "string" or clip == "" then
        error("character_state." .. operation .. ": non-empty semantic clip required", 3)
    end
end

function character_state.resolvedClip(state)
    requireState(state, "resolvedClip")
    if state.override then return state.override.clip end
    if state.locomotion == "moving" then return "walk" end
    return "idle"
end

function character_state.snapshot(state)
    requireState(state, "snapshot")
    local override = state.override
    return {
        facing = state.facing,
        locomotion = state.locomotion,
        clip = character_state.resolvedClip(state),
        overrideKind = override and override.kind or nil,
        overrideRemaining = override and override.remaining or nil,
    }
end

function character_state.setFacing(state, facing)
    requireState(state, "setFacing")
    local normalized = character_state.normalizeFacing(facing)
    if not normalized then
        error("character_state.setFacing: expected N/E/S/W (or cardinal alias), got "
            .. tostring(facing), 2)
    end
    state.facing = normalized
    return character_state.snapshot(state)
end

function character_state.setLocomotion(state, locomotion)
    requireState(state, "setLocomotion")
    local value = type(locomotion) == "string" and locomotion:lower() or locomotion
    if not VALID_LOCOMOTION[value] then
        error("character_state.setLocomotion: expected 'idle' or 'moving', got "
            .. tostring(locomotion), 2)
    end
    state.locomotion = value
    return character_state.snapshot(state)
end

-- Cardinal motion updates facing; stopping preserves the last facing. Owners
-- may move a root separately at whatever interpolation/pathfinding cadence they
-- own. This semantic state never moves anything by itself.
function character_state.setMotion(state, dx, dy)
    requireState(state, "setMotion")
    if type(dx) ~= "number" or type(dy) ~= "number" then
        error("character_state.setMotion: dx and dy must be numbers", 2)
    end
    if dx ~= 0 and dy ~= 0 then
        error("character_state.setMotion: diagonal motion is not a single cardinal facing", 2)
    end
    if dx == 0 and dy == 0 then
        state.locomotion = "idle"
    else
        state.locomotion = "moving"
        if dx > 0 then state.facing = "E"
        elseif dx < 0 then state.facing = "W"
        elseif dy > 0 then state.facing = "S"
        else state.facing = "N" end
    end
    return character_state.snapshot(state)
end

function character_state.playOneShot(state, clip, duration)
    requireState(state, "playOneShot")
    requireClip(clip, "playOneShot")
    if duration ~= nil and (type(duration) ~= "number" or duration <= 0) then
        error("character_state.playOneShot: duration must be a positive number when supplied", 2)
    end
    state.override = {
        kind = "one_shot",
        clip = clip,
        remaining = duration,
    }
    return character_state.snapshot(state)
end

function character_state.holdPose(state, clip)
    requireState(state, "holdPose")
    requireClip(clip, "holdPose")
    state.override = {
        kind = "pose",
        clip = clip,
    }
    return character_state.snapshot(state)
end

function character_state.completeOverride(state)
    requireState(state, "completeOverride")
    local hadOverride = state.override ~= nil
    state.override = nil
    return hadOverride, character_state.snapshot(state)
end

character_state.clearOverride = character_state.completeOverride

function character_state.isOverrideActive(state)
    requireState(state, "isOverrideActive")
    return state.override ~= nil
end

-- Only duration-driven one-shots own a clock here. Completion-driven one-shots
-- and held poses are explicitly completed by their owner/presentation adapter.
function character_state.update(state, dt)
    requireState(state, "update")
    if type(dt) ~= "number" or dt < 0 then
        error("character_state.update: dt must be a non-negative number", 2)
    end
    local override = state.override
    if override and override.kind == "one_shot" and override.remaining ~= nil then
        override.remaining = override.remaining - dt
        if override.remaining <= 0 then state.override = nil end
    end
    return character_state.snapshot(state)
end

return character_state
