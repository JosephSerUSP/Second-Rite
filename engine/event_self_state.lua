-- Persistent gameplay state owned by one authored placed Map Event instance.
--
-- Storage identity is deliberately NOT the editor/runtime numeric event id:
--   stable authored Map id + stable placed Event instanceId
--
-- Presentation state (event_actor, animation controllers, etc.) does not pass
-- through this module and is never serialized here.
local state_value = require("engine.state_value")

local event_self_state = {}

local VALID_VARIABLE_OPERATIONS = {
    set = true,
    add = true,
    subtract = true,
    multiply = true,
    divide = true,
}

local VALID_PAGE_OPERATORS = {
    ["=="] = true,
    ["!="] = true,
    [">"] = true,
    [">="] = true,
    ["<"] = true,
    ["<="] = true,
    is_set = true,
    is_unset = true,
}

local function fail(message, level)
    error("event_self_state: " .. message, level or 3)
end

local function cleanName(name, noun)
    if type(name) ~= "string" or name:match("^%s*$") then
        fail((noun or "state name") .. " must be a non-empty string", 4)
    end
    return name
end

local function stableMapId(map)
    if type(map) ~= "table" or map.id == nil then
        fail("SELF state requires a stable authored Map id", 4)
    end
    local kind = type(map.id)
    if kind ~= "string" and kind ~= "number" then
        fail("authored Map id must be a string or number", 4)
    end
    return tostring(map.id)
end

local function stableEventId(event)
    if type(event) ~= "table" or type(event.instanceId) ~= "string"
        or event.instanceId:match("^%s*$") then
        fail("SELF state requires a stable authored placed Event instanceId; numeric event id is not a persistence identity", 4)
    end
    return event.instanceId
end

local function loaderFor(session, explicitLoader)
    return explicitLoader or (session and session.loader)
end

local function findAuthoredMap(loader, mapId)
    if not loader then return nil end
    if loader.getMapIndex then
        local index = loader.getMapIndex(mapId)
        if index then return loader.maps and loader.maps[index] end
        local numeric = tonumber(mapId)
        if numeric then
            index = loader.getMapIndex(numeric)
            if index then return loader.maps and loader.maps[index] end
        end
    end
    for _, map in ipairs(loader.maps or {}) do
        if tostring(map.id) == tostring(mapId) then return map end
    end
    return nil
end

local function findAuthoredEvent(map, instanceId)
    if not map then return nil end
    for _, event in ipairs(map.events or {}) do
        if event.instanceId == instanceId then return event end
    end
    return nil
end

-- Resolve an owner. Ordinary SELF access accepts only the currently executing
-- placed Event supplied in ctx.event. It never falls back to session.activeEvent
-- or a numeric event slot. Cross-event access must provide BOTH stable ids.
function event_self_state.resolveOwner(session, event, options)
    if not session then fail("SELF state requires a GameSession", 3) end
    options = options or {}
    local hasMap = options.mapId ~= nil
    local hasEvent = options.eventInstanceId ~= nil
    if hasMap ~= hasEvent then
        fail("cross-Event SELF access requires both mapId and eventInstanceId", 3)
    end

    if hasMap then
        local mapId = tostring(options.mapId)
        local instanceId = cleanName(options.eventInstanceId, "eventInstanceId")
        local authoredMap = findAuthoredMap(loaderFor(session, options.loader), options.mapId)
        if not authoredMap then
            fail("cross-Event SELF target references unknown authored Map '" .. mapId .. "'", 3)
        end
        local authoredEvent = findAuthoredEvent(authoredMap, instanceId)
        if not authoredEvent then
            fail("cross-Event SELF target Map '" .. mapId .. "' has no placed Event instance '" .. instanceId .. "'", 3)
        end
        return tostring(authoredMap.id), instanceId, authoredEvent
    end

    local map = session.currentMapData
    return stableMapId(map), stableEventId(event), event
end

local function stateRoot(session)
    session.eventSelfState = session.eventSelfState or {}
    return session.eventSelfState
end

local function readBucket(session, mapId, instanceId)
    local mapBucket = session.eventSelfState and session.eventSelfState[mapId]
    return mapBucket and mapBucket[instanceId] or nil
end

local function writeBucket(session, mapId, instanceId)
    local root = stateRoot(session)
    root[mapId] = root[mapId] or {}
    root[mapId][instanceId] = root[mapId][instanceId] or { switches = {}, variables = {} }
    local bucket = root[mapId][instanceId]
    bucket.switches = bucket.switches or {}
    bucket.variables = bucket.variables or {}
    return bucket
end

local function owner(session, event, options)
    local mapId, instanceId = event_self_state.resolveOwner(session, event, options)
    return mapId, instanceId
end

function event_self_state.readSwitch(session, event, name, options)
    name = cleanName(name, "Self Switch name")
    local mapId, instanceId = owner(session, event, options)
    local bucket = readBucket(session, mapId, instanceId)
    return bucket ~= nil and bucket.switches ~= nil and bucket.switches[name] == true
end

function event_self_state.writeSwitch(session, event, name, value, options)
    name = cleanName(name, "Self Switch name")
    if type(value) ~= "boolean" then
        fail("Self Switch value must be boolean", 3)
    end
    local mapId, instanceId = owner(session, event, options)
    local bucket = writeBucket(session, mapId, instanceId)
    -- False is the authored/default value. Elide it rather than manufacturing
    -- persistent false records, exactly like the existing flag affordance.
    bucket.switches[name] = value and true or nil
    return value
end

function event_self_state.readVariable(session, event, name, options)
    name = cleanName(name, "Self Variable name")
    local mapId, instanceId = owner(session, event, options)
    local bucket = readBucket(session, mapId, instanceId)
    local value = bucket and bucket.variables and bucket.variables[name] or nil
    return state_value.copy(value, "Self Variable '" .. name .. "'")
end

function event_self_state.writeVariable(session, event, name, value, options)
    name = cleanName(name, "Self Variable name")
    local mapId, instanceId = owner(session, event, options)
    local copy = state_value.copy(value, "Self Variable '" .. name .. "'")
    local bucket = writeBucket(session, mapId, instanceId)
    bucket.variables[name] = copy -- nil means unset
    return state_value.copy(copy, "Self Variable '" .. name .. "'")
end

function event_self_state.changeVariable(session, event, name, operation, operand, options)
    operation = operation or "set"
    if not VALID_VARIABLE_OPERATIONS[operation] then
        fail("unsupported Self Variable operation '" .. tostring(operation) .. "'", 3)
    end
    if operation == "set" then
        return event_self_state.writeVariable(session, event, name, operand, options)
    end
    if not state_value.isFiniteNumber(operand) then
        fail("Self Variable " .. operation .. " operand must be a finite number", 3)
    end
    local current = event_self_state.readVariable(session, event, name, options)
    if not state_value.isFiniteNumber(current) then
        fail("Self Variable '" .. tostring(name) .. "' must already be a finite number for " .. operation, 3)
    end
    local result
    if operation == "add" then result = current + operand
    elseif operation == "subtract" then result = current - operand
    elseif operation == "multiply" then result = current * operand
    elseif operation == "divide" then
        if operand == 0 then fail("Self Variable division by zero", 3) end
        result = current / operand
    end
    if not state_value.isFiniteNumber(result) then
        fail("Self Variable " .. operation .. " produced a non-finite number", 3)
    end
    return event_self_state.writeVariable(session, event, name, result, options)
end

local function compareVariable(actual, condition)
    local op = condition.operator or "=="
    if not VALID_PAGE_OPERATORS[op] then
        fail("unsupported Self Variable page operator '" .. tostring(op) .. "'", 4)
    end
    if op == "is_set" then return actual ~= nil end
    if op == "is_unset" then return actual == nil end
    if op == "==" then return state_value.equals(actual, condition.value) end
    if op == "!=" then return not state_value.equals(actual, condition.value) end
    if not state_value.isFiniteNumber(actual) or not state_value.isFiniteNumber(condition.value) then
        return false
    end
    if op == ">" then return actual > condition.value end
    if op == ">=" then return actual >= condition.value end
    if op == "<" then return actual < condition.value end
    return actual <= condition.value
end

function event_self_state.validatePageConditions(spec)
    if spec == nil then return true end
    if type(spec) ~= "table" then fail("page selfConditions must be an object", 4) end
    for key in pairs(spec) do
        if key ~= "switch" and key ~= "variable" then
            fail("page selfConditions has unknown field '" .. tostring(key) .. "'", 4)
        end
    end
    if spec.switch ~= nil then
        local condition = spec.switch
        if type(condition) ~= "table" then fail("Self Switch page condition must be an object", 4) end
        for key in pairs(condition) do
            if key ~= "name" and key ~= "value" then
                fail("Self Switch page condition has unknown field '" .. tostring(key) .. "'", 4)
            end
        end
        cleanName(condition.name, "Self Switch page condition name")
        local expected = condition.value
        if expected == nil then expected = true end
        if type(expected) ~= "boolean" then fail("Self Switch page condition value must be boolean", 4) end
    end
    if spec.variable ~= nil then
        local condition = spec.variable
        if type(condition) ~= "table" then fail("Self Variable page condition must be an object", 4) end
        for key in pairs(condition) do
            if key ~= "name" and key ~= "operator" and key ~= "value" then
                fail("Self Variable page condition has unknown field '" .. tostring(key) .. "'", 4)
            end
        end
        cleanName(condition.name, "Self Variable page condition name")
        local op = condition.operator or "=="
        if not VALID_PAGE_OPERATORS[op] then fail("unsupported Self Variable page operator '" .. tostring(op) .. "'", 4) end
        if op == "is_set" or op == "is_unset" then
            if condition.value ~= nil then
                fail("Self Variable page operator '" .. op .. "' does not accept a value", 4)
            end
        else
            if condition.value == nil then
                fail("Self Variable page operator '" .. op .. "' requires a value; use is_unset for absence", 4)
            end
            state_value.validate(condition.value, "Self Variable page condition value")
            if (op == ">" or op == ">=" or op == "<" or op == "<=")
                and not state_value.isFiniteNumber(condition.value) then
                fail("Self Variable page operator '" .. op .. "' requires a finite numeric value", 4)
            end
        end
    end
    return true
end

-- Structured Page SELF conditions are always relative to the placed Event whose
-- page is being resolved. They are ANDed with the legacy condition string.
function event_self_state.pageConditionsPass(session, event, spec)
    if spec == nil then return true end
    event_self_state.validatePageConditions(spec)
    stableMapId(session and session.currentMapData)
    stableEventId(event)

    if spec.switch ~= nil then
        local condition = spec.switch
        local expected = condition.value
        if expected == nil then expected = true end
        if event_self_state.readSwitch(session, event, condition.name) ~= expected then return false end
    end
    if spec.variable ~= nil then
        local condition = spec.variable
        local actual = event_self_state.readVariable(session, event, condition.name)
        if not compareVariable(actual, condition) then return false end
    end
    return true
end

-- Formula receives a snapshot-like view. Unknown Self Switches default false;
-- Self Variables default nil. Nested authored values are copied by value before
-- exposure, so formulas never receive the persistent storage tables themselves.
function event_self_state.formulaView(session, event)
    if not session or not event then return nil end
    local ok, mapId, instanceId = pcall(function()
        local m, e = event_self_state.resolveOwner(session, event)
        return m, e
    end)
    if not ok then return nil end
    local bucket = readBucket(session, mapId, instanceId)
    local variableCopy = state_value.copy((bucket and bucket.variables) or {}, "Self Variables formula view")
    local switchCopy = state_value.copy((bucket and bucket.switches) or {}, "Self Switches formula view")
    return {
        switches = setmetatable(switchCopy, { __index = function() return false end }),
        variables = variableCopy,
    }
end

function event_self_state.validateStore(store)
    store = store or {}
    state_value.validate(store, "eventSelfState save payload")
    for mapId, mapBucket in pairs(store) do
        if type(mapId) ~= "string" or mapId:match("^%s*$") then
            fail("eventSelfState Map identity keys must be non-empty strings", 3)
        end
        if type(mapBucket) ~= "table" then
            fail("eventSelfState Map '" .. mapId .. "' bucket must be an object", 3)
        end
        for instanceId, bucket in pairs(mapBucket) do
            cleanName(instanceId, "eventSelfState Event identity")
            if type(bucket) ~= "table" then
                fail("eventSelfState Event '" .. instanceId .. "' bucket must be an object", 3)
            end
            for key in pairs(bucket) do
                if key ~= "switches" and key ~= "variables" then
                    fail("eventSelfState Event '" .. instanceId .. "' has unknown field '" .. tostring(key) .. "'", 3)
                end
            end
            local switches = bucket.switches or {}
            local variables = bucket.variables or {}
            if type(switches) ~= "table" or type(variables) ~= "table" then
                fail("eventSelfState Event '" .. instanceId .. "' switches/variables must be objects", 3)
            end
            for name, value in pairs(switches) do
                cleanName(name, "Self Switch save key")
                if type(value) ~= "boolean" then
                    fail("Self Switch '" .. name .. "' save value must be boolean", 3)
                end
            end
            for name, value in pairs(variables) do
                cleanName(name, "Self Variable save key")
                state_value.validate(value, "Self Variable '" .. name .. "' save value")
            end
        end
    end
    return true
end

event_self_state.VALID_VARIABLE_OPERATIONS = VALID_VARIABLE_OPERATIONS
event_self_state.VALID_PAGE_OPERATORS = VALID_PAGE_OPERATORS

return event_self_state
