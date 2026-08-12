-- Typed HP-damage transition seam (#331 / #308A).
--
-- This module deliberately knows one phenomenon only. It does not discover
-- traits, freeze the eventual source precedence, or offer a universal event
-- callback surface. A caller supplies an explicitly ordered, local participant
-- collection for the transition it is proving.
local transition = {}

local nextLineageId = 0

local function readOnly(data, label)
    return setmetatable({}, {
        __index = data,
        __newindex = function()
            error((label or "value") .. " is immutable", 0)
        end,
        __metatable = false,
    })
end

local function identity(battler)
    if not battler then return nil end
    return readOnly({
        id = battler.id,
        instanceId = battler.instanceId,
        name = battler.name,
    }, "damage participant identity")
end

local function finiteNumber(value, label)
    if type(value) ~= "number" or value ~= value
            or value == math.huge or value == -math.huge then
        error((label or "number") .. " must be a finite number", 0)
    end
    return value
end

local function participantList(participants, key)
    if not participants then return {} end
    local list = participants[key]
    if list == nil then return {} end
    if type(list) ~= "table" then
        error("hp damage " .. key .. " must be an ordered list", 0)
    end
    return list
end

local function makePending(source, target, attemptedDamage, effectData)
    local state = { currentDamage = attemptedDamage }
    local fields = {
        type = "hp_damage",
        source = identity(source),
        target = identity(target),
        attemptedDamage = attemptedDamage,
        effect = effectData and effectData.type or "hp_damage",
    }

    -- The pending contract is a read-only view. Its current value is exposed
    -- dynamically so an interceptor can observe earlier ordered transforms,
    -- while the only writes available to it are the operations below.
    local pending = setmetatable({}, {
        __index = function(_, key)
            if key == "currentDamage" then return state.currentDamage end
            return fields[key]
        end,
        __newindex = function()
            error("pending hp damage is immutable; use a declared operation", 0)
        end,
        __metatable = false,
    })

    local operations = {
        -- A bounded multiplier is enough for this proof's reduction fixture and
        -- keeps an interceptor from writing arbitrary domain state.
        scale = function(factor)
            factor = finiteNumber(factor, "damage scale")
            if factor < 0 or factor > 1 then
                error("damage scale must be between 0 and 1", 0)
            end
            state.currentDamage = math.max(0, math.floor(state.currentDamage * factor))
        end,
        reduce = function(amount)
            amount = finiteNumber(amount, "damage reduction")
            if amount < 0 then error("damage reduction cannot be negative", 0) end
            state.currentDamage = math.max(0, state.currentDamage - math.floor(amount))
        end,
        currentDamage = function()
            return state.currentDamage
        end,
    }

    return pending, readOnly(operations, "damage operations"), state
end

local function makeLineage(context)
    nextLineageId = nextLineageId + 1
    local parent = context and context.damageLineage
    local rootId = parent and (parent.rootId or parent.id) or nextLineageId
    return {
        id = nextLineageId,
        rootId = rootId,
        origin = (parent and parent.origin) or rootId,
        parent = parent and parent.id or nil,
    }
end

local function nestedContext(context, lineage)
    local out = {
        element = context and context.element,
        user = context and context.user,
        isItem = context and context.isItem,
        battle = context and context.battle,
        hpDamageParticipants = context and context.hpDamageParticipants,
        damageLineage = {
            id = lineage.id,
            rootId = lineage.rootId,
            origin = lineage.origin,
            parent = lineage.parent,
        },
    }
    return out
end

-- `spec.calculate` and `spec.commit` are the mature effects-core helpers. The
-- transition owns only the typed boundary between them; it never calculates or
-- mutates HP itself.
function transition.apply(spec)
    assert(type(spec) == "table", "hp damage transition requires a spec")
    assert(type(spec.calculate) == "function", "hp damage transition requires calculation authority")
    assert(type(spec.commit) == "function", "hp damage transition requires commit authority")
    assert(type(spec.publish) == "function", "hp damage transition requires fact publication")
    assert(type(spec.applyEffect) == "function", "hp damage transition requires effect capability")

    local context = spec.context or {}
    local events = {}
    local attemptedDamage, critical = spec.calculate(
        spec.effectData, spec.source, spec.target, spec.session, context, events)
    attemptedDamage = finiteNumber(attemptedDamage, "calculated hp damage")
    attemptedDamage = math.max(0, math.floor(attemptedDamage))

    local pending, operations, pendingState = makePending(
        spec.source, spec.target, attemptedDamage, spec.effectData)
    local participants = context.hpDamageParticipants
    local interceptors = participantList(participants, "interceptors")
    for i, participant in ipairs(interceptors) do
        if type(participant) ~= "table" or type(participant.intercept) ~= "function" then
            error("hp damage interceptor " .. tostring(i) .. " must expose intercept", 0)
        end
        -- No event stream, interpreter, or presentation hook is passed here:
        -- interceptors are synchronous and non-suspending by construction.
        participant.intercept(pending, operations)
    end

    local commit = spec.commit(
        spec.effectData, spec.source, spec.target, spec.session, context, events,
        pendingState.currentDamage, critical)
    if type(commit) ~= "table" or type(commit.damageEvent) ~= "table" then
        error("hp damage commit did not publish its damage event", 0)
    end

    local lineage = makeLineage(context)
    local fact = readOnly({
        type = "hp_damage",
        source = identity(spec.source),
        target = identity(spec.target),
        attemptedDamage = attemptedDamage,
        finalDamage = pendingState.currentDamage,
        committedDamage = commit.committedDamage,
        hpBefore = commit.hpBefore,
        hpAfterDamage = commit.hpAfterDamage,
        critical = critical == true,
        damageKilled = commit.damageKilled,
        commitCount = 1,
        lineage = readOnly(lineage, "damage lineage"),
    }, "resolved damage fact")

    -- Publish the fact on the event before any reaction can observe it. The
    -- existing resolved_event publisher then adds its normal after-snapshot.
    commit.damageEvent.resolvedDamage = fact
    spec.publish(events)

    -- The mature commit helper is the only authority that knows whether this
    -- operation crossed the alive -> dead boundary or whether Execution later
    -- finished a survivor. Publish one typed fact on the existing death event;
    -- this adds no new gameplay event and keeps the current event ordering.
    -- `cause` is intentionally provisional until #308 settles the full death
    -- vocabulary and lineage contract.
    if commit.kill then
        local deathEvent = commit.kill.deathEvent
        if type(deathEvent) ~= "table" then
            error("hp damage kill did not identify its death event", 0)
        end
        if deathEvent.resolvedKill ~= nil then
            error("hp damage operation published duplicate resolved kill facts", 0)
        end
        deathEvent.resolvedKill = readOnly({
            type = "kill",
            killer = identity(spec.source),
            target = identity(spec.target),
            cause = commit.kill.cause,
            lineage = readOnly({
                id = lineage.id,
                rootId = lineage.rootId,
                origin = lineage.origin,
                parent = lineage.parent,
            }, "kill lineage"),
        }, "resolved kill fact")
    end

    local reactions = participantList(participants, "reactions")
    local api = readOnly({
        lineage = readOnly({
            rootId = lineage.rootId,
            origin = lineage.origin,
            parent = lineage.id,
        }, "reaction lineage"),
        applyEffect = function(effectData, targetRole)
            if targetRole ~= "source" and targetRole ~= "target" then
                error("damage reaction targetRole must be source or target", 0)
            end
            local target = targetRole == "source" and spec.source or spec.target
            local nestedEvents = spec.applyEffect(effectData, spec.source, target,
                nestedContext(context, lineage))
            for _, event in ipairs(nestedEvents or {}) do
                table.insert(events, event)
            end
            return nestedEvents
        end,
    }, "resolved damage reaction capability")

    for i, participant in ipairs(reactions) do
        if type(participant) ~= "table" or type(participant.react) ~= "function" then
            error("hp damage reaction " .. tostring(i) .. " must expose react", 0)
        end
        participant.react(fact, api)
    end

    return events
end

return transition
