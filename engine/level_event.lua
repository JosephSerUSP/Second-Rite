-- LEVEL_REACHED domain publication (#550).
--
-- A level transition is authoritative in Battler:gainExp: EXP is consumed and
-- the numeric level is committed there exactly once. This module publishes the
-- resulting fact to the shared Event Program substrate immediately after that
-- commit. It does not decide growth, healing, skills or transformation.
--
-- Domain-wide authored policy participates through progression.level_reached
-- Flow. Source-local Unit reactions join this same fact later under #554/#308;
-- keeping publication here means neither host becomes the semantic owner.
local flow = require("engine.flow")
local formula = require("engine.formula")
local resolved_event = require("engine.resolved_event")
local unit_reactions = require("engine.unit_reactions")

local level_event = {}

local function safeView(unit, session, previousLevel, level)
    return {
        type = "level_reached",
        unit = formula.battlerView(unit, session),
        previousLevel = previousLevel,
        level = level,
    }
end

-- Builds the exact host context used by production publication. Exposed for
-- headless conformance tests so they can prove authored Formula programs see
-- `event.*` without inventing a parallel test-only context.
function level_event.context(session, unit, previousLevel, level)
    assert(session, "LEVEL_REACHED requires session")
    assert(unit, "LEVEL_REACHED requires unit")
    assert(level == unit.level, "LEVEL_REACHED is post-commit: unit.level must equal event.level")
    assert(previousLevel == level - 1,
        "LEVEL_REACHED must describe one atomic level crossing")

    local fact = {
        type = "level_reached",
        unit = unit,
        target = unit,
        previousLevel = previousLevel,
        level = level,
    }
    -- Resolved snapshots are attached before authored consequences run. The
    -- fact therefore describes the committed transition, never a reconstruction
    -- after a reaction changed the Unit again.
    resolved_event.attach(fact, session)

    local view = safeView(unit, session, previousLevel, level)
    local ctx = {
        session = session,
        loader = session.loader,
        a = unit,
        target = unit,
        event = fact,
        -- Formula's generic Event noun is bridged through v.event so existing
        -- interpreter callers need no progression-specific evaluator. `v` is
        -- flow-local and discarded unless the host explicitly keeps it.
        v = { event = view },
    }
    return fact, ctx
end

-- Publish one reached level. Called inside gainExp's threshold loop, so authored
-- policy for level N completes before the engine considers crossing N+1.
function level_event.publish(session, unit, previousLevel, level)
    local fact, ctx = level_event.context(session, unit, previousLevel, level)
    local events = flow.run("progression.level_reached", ctx)
    unit_reactions.run(unit, "LEVEL_REACHED", ctx)
    return fact, events, ctx
end

local function safeGainResolvedView(unit, session, previousLevel, level)
    return {
        type = "level_gain_resolved",
        unit = formula.battlerView(unit, session),
        previousLevel = previousLevel,
        level = level,
        levelsGained = level - previousLevel,
    }
end

-- One EXP grant may cross several thresholds. This fact is published only
-- after every atomic LEVEL_REACHED program has completed, but before any
-- transaction-complete Project policy such as recovery or transformation.
-- `previousLevel` therefore means the level before this gainExp transaction,
-- not merely the immediately preceding atomic crossing.
function level_event.gainResolvedContext(session, unit, previousLevel, level)
    assert(session, "LEVEL_GAIN_RESOLVED requires session")
    assert(unit, "LEVEL_GAIN_RESOLVED requires unit")
    assert(level == unit.level,
        "LEVEL_GAIN_RESOLVED is post-commit: unit.level must equal event.level")
    assert(previousLevel < level,
        "LEVEL_GAIN_RESOLVED requires at least one committed level crossing")

    local fact = {
        type = "level_gain_resolved",
        unit = unit,
        target = unit,
        previousLevel = previousLevel,
        level = level,
        levelsGained = level - previousLevel,
    }
    resolved_event.attach(fact, session)

    local view = safeGainResolvedView(unit, session, previousLevel, level)
    local ctx = {
        session = session,
        loader = session.loader,
        a = unit,
        target = unit,
        event = fact,
        v = { event = view },
    }
    return fact, ctx
end

function level_event.publishGainResolved(session, unit, previousLevel, level)
    local fact, ctx = level_event.gainResolvedContext(session, unit, previousLevel, level)
    local events = flow.run("progression.level_gain_resolved", ctx)
    return fact, events, ctx
end

return level_event
