-- Symmetric threshold transition for wall-bound door events. Scene changes
-- happen only at full black, with a short dark hold on either side.
local subtractive_fade = require("presentation.subtractive_fade")
local util = require("presentation.util")
local world_view = require("engine.generated.world-view")

local door_transition = {}
local state = nil

local DURATIONS = {
    entry_approach = 0.24,
    entry_cover = 0.58,
    entry_hold = 0.16,
    entry_reveal = 0.68,
    exit_cover = 0.68,
    exit_hold = 0.16,
    exit_reveal = 0.58,
}

function door_transition.begin(onCovered, options)
    if state then return false end
    local approach = not (options and options.approach == false)
    local actorDirection = options and options.actorDirection
    if actorDirection then world_view.transitionArrowAxis(actorDirection) end
    state = { phase = (approach or actorDirection) and "entry_approach" or "entry_cover", elapsed = 0,
        onCovered = onCovered, approach = approach, actorDirection = actorDirection }
    return true
end

function door_transition.setArrivalDirection(direction)
    if not state then return end
    world_view.transitionArrowAxis(direction)
    state.arrivalDirection = direction
end

-- Visual offsets never change the lane root, collision or arrival anchor.
-- Both plate and mesh renderers consume this one resolved walking pose.
function door_transition.actorPose()
    if not state then return nil end
    local direction, distance, elapsed
    if state.actorDirection and (state.phase == "entry_approach" or state.phase == "entry_cover") then
        direction = state.actorDirection
        elapsed = state.elapsed + (state.phase == "entry_cover" and DURATIONS.entry_approach or 0)
        distance = math.min(1, elapsed / 0.48) * 1.2
    elseif state.arrivalDirection and state.phase == "entry_reveal" then
        direction = state.arrivalDirection
        elapsed = state.elapsed
        distance = (1 - util.easeOut(math.min(1, elapsed / DURATIONS.entry_reveal))) * 1.2
    else return nil end
    local axis = world_view.transitionArrowAxis(direction)
    return {x = axis.x * distance, y = axis.y * distance,
        frame = math.floor(elapsed * 12) % 6, direction = direction}
end

function door_transition.beginExit(onCovered)
    if state then return false end
    state = { phase = "exit_cover", elapsed = 0, onCovered = onCovered }
    return true
end

local function enterHold(phase)
    local callback = state.onCovered
    state.onCovered = nil
    state.phase, state.elapsed = phase, 0
    if callback then callback() end
end

function door_transition.update(dt)
    if not state then return end
    state.elapsed = state.elapsed + dt
    local duration = DURATIONS[state.phase]
    if state.elapsed < duration then return end

    if state.phase == "entry_approach" then
        state.phase, state.elapsed = "entry_cover", 0
    elseif state.phase == "entry_cover" then
        enterHold("entry_hold")
    elseif state.phase == "entry_hold" then
        state.phase, state.elapsed = "entry_reveal", 0
    elseif state.phase == "exit_cover" then
        enterHold("exit_hold")
    elseif state.phase == "exit_hold" then
        state.phase, state.elapsed = "exit_reveal", 0
    else
        state = nil
    end
end

function door_transition.isActive()
    return state ~= nil
end

function door_transition.approachProgress()
    if not state then return 0 end
    if state.approach == false then return 0 end
    if state.phase == "entry_approach" then
        local p = math.min(1, state.elapsed / DURATIONS.entry_approach)
        return util.easeOut(p)
    elseif state.phase == "entry_cover"
        or state.phase == "exit_hold" then
        return 1
    elseif state.phase == "exit_reveal" then
        local p = math.min(1, state.elapsed / DURATIONS.exit_reveal)
        return 1 - util.easeOut(p)
    end
    return 0
end

function door_transition.overlayAlpha()
    if not state then return 0 end
    if state.phase == "entry_cover" then
        local p = math.min(1, state.elapsed / DURATIONS.entry_cover)
        return util.easeInCubic(p)
    elseif state.phase == "entry_hold" or state.phase == "exit_hold" then
        return 1
    elseif state.phase == "entry_reveal" then
        local p = math.min(1, state.elapsed / DURATIONS.entry_reveal)
        return 1 - util.smoothstep(p)
    elseif state.phase == "exit_cover" then
        local p = math.min(1, state.elapsed / DURATIONS.exit_cover)
        return util.easeInCubic(p)
    elseif state.phase == "exit_reveal" then
        local p = math.min(1, state.elapsed / DURATIONS.exit_reveal)
        return 1 - util.smoothstep(p)
    end
    return 0
end

function door_transition.draw()
    -- This darkens the world during a transition; it does not own a modal
    -- panel, so it must not arm the solid modal-windowskin rule.
    subtractive_fade.draw(door_transition.overlayAlpha(), false)
end

return door_transition
