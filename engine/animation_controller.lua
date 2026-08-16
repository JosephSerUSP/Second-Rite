-- Pure deterministic presentation-only animation controller.
--
-- A controller observes public facts (for now Event movement plus generic
-- signals/completion) and selects a semantic visual state. It never mutates
-- gameplay truth, Event Pages, collision, coordinates, Variables, or inventory.
local controller = {}

local SUPPORTED_FACTS = {
    ["event.moving"] = true,
    ["event.interacting"] = true,
    ["event.enabled"] = true,
    ["animation.finished"] = true,
}

local function fail(message, level)
    error("animation_controller: " .. message, level or 3)
end

local function stateDef(definition, stateId)
    return definition and definition.states and definition.states[stateId]
end

local function validateCondition(value, controllerId, index)
    if type(value) ~= "string" or value == "" then
        fail("controller '" .. tostring(controllerId) .. "' transition " .. index
            .. " requires a non-empty when condition", 4)
    end
    local condition = value
    if condition:sub(1, 4) == "not " then condition = condition:sub(5) end
    if SUPPORTED_FACTS[condition] then return end
    if condition:match("^signal%.[A-Za-z0-9_.%-]+$") then return end
    fail("controller '" .. tostring(controllerId) .. "' transition " .. index
        .. " uses unsupported condition '" .. tostring(value) .. "'", 4)
end

function controller.validate(definition, controllerId)
    if type(definition) ~= "table" then
        fail("controller '" .. tostring(controllerId) .. "' must be an object", 3)
    end
    controllerId = controllerId or definition.id or "<anonymous>"
    if type(definition.initial) ~= "string" or definition.initial == "" then
        fail("controller '" .. tostring(controllerId) .. "' requires initial state", 3)
    end
    if type(definition.states) ~= "table" or not stateDef(definition, definition.initial) then
        fail("controller '" .. tostring(controllerId) .. "' initial state is not declared", 3)
    end
    for stateId, state in pairs(definition.states) do
        if type(stateId) ~= "string" or stateId == "" or type(state) ~= "table" then
            fail("controller '" .. tostring(controllerId) .. "' has an invalid state", 3)
        end
        if type(state.animation) ~= "string" or state.animation == "" then
            fail("controller '" .. tostring(controllerId) .. "' state '" .. stateId
                .. "' requires semantic animation", 3)
        end
        if state.loop ~= nil and type(state.loop) ~= "boolean" then
            fail("controller '" .. tostring(controllerId) .. "' state '" .. stateId
                .. "' loop must be boolean", 3)
        end
    end
    for index, transition in ipairs(definition.transitions or {}) do
        if type(transition) ~= "table" then
            fail("controller '" .. tostring(controllerId) .. "' transition " .. index
                .. " must be an object", 3)
        end
        local from = transition.from or "*"
        if from ~= "*" and not stateDef(definition, from) then
            fail("controller '" .. tostring(controllerId) .. "' transition " .. index
                .. " has unknown from state '" .. tostring(from) .. "'", 3)
        end
        if type(transition.to) ~= "string" or not stateDef(definition, transition.to) then
            fail("controller '" .. tostring(controllerId) .. "' transition " .. index
                .. " has unknown to state '" .. tostring(transition.to) .. "'", 3)
        end
        validateCondition(transition.when, controllerId, index)
    end
    return definition
end

function controller.validateRegistry(registry)
    if registry == nil then return {} end
    if type(registry) ~= "table" then fail("registry must be an object", 3) end
    for id, definition in pairs(registry) do
        if type(id) ~= "string" or id == "" then fail("registry ids must be non-empty strings", 3) end
        if type(definition) ~= "table" then
            fail("controller '" .. id .. "' must be an object", 3)
        end
        if definition.id ~= nil and tostring(definition.id) ~= id then
            fail("registry key '" .. id .. "' disagrees with controller.id '"
                .. tostring(definition.id) .. "'", 3)
        end
        controller.validate(definition, id)
    end
    return registry
end

function controller.new(definition, controllerId)
    controller.validate(definition, controllerId)
    return {
        state = definition.initial,
        elapsed = 0,
        signals = {},
        animationFinished = false,
    }
end

local function factValue(instance, condition, facts)
    local negate = false
    if condition:sub(1, 4) == "not " then
        negate = true
        condition = condition:sub(5)
    end

    local value = false
    if condition == "event.moving" then
        value = facts.event and facts.event.moving == true
    elseif condition == "event.interacting" then
        value = facts.event and facts.event.interacting == true
    elseif condition == "event.enabled" then
        value = not facts.event or facts.event.enabled ~= false
    elseif condition == "animation.finished" then
        value = instance.animationFinished == true
            or (facts.animation and facts.animation.finished == true)
    else
        local signal = condition:match("^signal%.(.+)$")
        if signal then value = instance.signals[signal] == true end
    end
    return negate and not value or value
end

local function consumedSignal(condition)
    if condition:sub(1, 4) == "not " then return nil end
    return condition:match("^signal%.(.+)$")
end

local function isPositiveSignal(condition)
    return condition:sub(1, 4) ~= "not " and condition:match("^signal%.") ~= nil
end

local function tryTransitions(instance, definition, facts, signalsOnly)
    for _, transition in ipairs(definition.transitions or {}) do
        if isPositiveSignal(transition.when) == signalsOnly then
            local from = transition.from or "*"
            if (from == "*" or from == instance.state)
                    and factValue(instance, transition.when, facts) then
                local signal = consumedSignal(transition.when)
                if signal then instance.signals[signal] = nil end
                instance.state = transition.to
                instance.elapsed = 0
                instance.animationFinished = false
                return true
            end
        end
    end
    return false
end

-- Advance using explicit logical dt. At most one transition fires per call.
-- Deliberate positive signals are checked before observed ambient facts, while
-- authored order remains the priority within each class. This lets a generic
-- `signal.interact` interrupt idle/walk even when `event.moving` is currently
-- true, matching the controller's choreography role without inventing bespoke
-- hooks. A malformed cycle still cannot spin within one frame.
function controller.update(instance, definition, dt, facts)
    if type(instance) ~= "table" then fail("instance required", 2) end
    controller.validate(definition)
    if type(dt) ~= "number" or dt < 0 then fail("dt must be a non-negative number", 2) end
    facts = facts or {}
    instance.elapsed = (instance.elapsed or 0) + dt

    if tryTransitions(instance, definition, facts, true)
            or tryTransitions(instance, definition, facts, false) then
        return true, controller.snapshot(instance, definition)
    end

    -- A completion fact is edge-like. If it did not cause a transition this
    -- frame, consume it rather than leaving an immortal true flag behind.
    instance.animationFinished = false
    return false, controller.snapshot(instance, definition)
end

function controller.signal(instance, name)
    if type(instance) ~= "table" then fail("instance required", 2) end
    if type(name) ~= "string" or not name:match("^[A-Za-z0-9_.%-]+$") then
        fail("signal name must be a non-empty semantic identifier", 2)
    end
    instance.signals[name] = true
end

function controller.completeAnimation(instance)
    if type(instance) ~= "table" then fail("instance required", 2) end
    instance.animationFinished = true
end

function controller.snapshot(instance, definition)
    if type(instance) ~= "table" then fail("instance required", 2) end
    local state = stateDef(definition, instance.state)
    if not state then fail("instance references unknown state '" .. tostring(instance.state) .. "'", 2) end
    return {
        state = instance.state,
        animation = state.animation,
        loop = state.loop ~= false,
        elapsed = instance.elapsed or 0,
    }
end

return controller