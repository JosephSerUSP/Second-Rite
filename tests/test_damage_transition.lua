-- #331 / #308A: the first typed HP-damage transition proof.
--
-- These participants are deliberately fixture-only. They are supplied as an
-- ordered local list by the test context; no production trait is migrated and
-- no final global source precedence is implied.
package.path = package.path .. ";./?.lua;./engine/?.lua"

local loader = require("data.loader")
local sessionModule = require("engine.session")
local effects = require("engine.effects")
local interpreter = require("engine.interpreter")

print("[TEST] Starting typed damage transition tests...")

local passed, failed = 0, 0
local function check(cond, msg)
    if cond then
        passed = passed + 1
        print("  [PASS] " .. msg)
    else
        failed = failed + 1
        print("  [FAIL] " .. msg)
    end
end

loader.init()

local function tune(battler, hp)
    local private = {}
    for k, v in pairs(battler.actorData) do private[k] = v end
    private.traits = {}
    private.elements = {}
    private.baseParams = {
        maxHp = 100, atk = 20, def = 10, mat = 20, mdf = 10,
    }
    private.growthMultiplier = 0
    battler.actorData = private
    battler.hp = hp or 100
    return battler
end

local function rig()
    local session = sessionModule.GameSession.new(loader)
    local source = session:recruitActor("skeleton", 1)
    local target = session:recruitActor("skeleton", 1)
    return session, tune(source), tune(target)
end

local function damageEvent(events)
    for _, event in ipairs(events or {}) do
        if event.type == "damage" then return event end
    end
    return nil
end

local function eventTypes(events)
    local out = {}
    for _, event in ipairs(events or {}) do table.insert(out, event.type) end
    return out
end

--------------------------------------------------------------- baseline --

do
    local session, source, target = rig()
    local events = effects.apply({ type = "hp_damage", formula = "12" },
        source, target, session, {})
    local damage = damageEvent(events)
    check(#events == 1 and damage ~= nil,
        "zero participants preserve the existing one-damage-event behavior")
    check(target.hp == 88 and damage.value == 12,
        "zero participants preserve the mature HP result")
    check(damage.resolvedDamage ~= nil
            and damage.resolvedDamage.attemptedDamage == 12
            and damage.resolvedDamage.finalDamage == 12
            and damage.resolvedDamage.committedDamage == 12
            and damage.resolvedDamage.hpAfter == 88,
        "the baseline publishes the committed damage fact without recomputation")
    check(damage.resolvedDamage.commitCount == 1 and damage.resolved.hp == 88,
        "the baseline records one authoritative commit and its after-snapshot")
end

------------------------------------------------------ typed interceptor --

do
    local session, source, target = rig()
    local order, reactionOrder = {}, {}
    local mutationRejected, identityReadOnly = false, false
    local participants = {
        interceptors = {
            {
                id = "fixture_scale",
                intercept = function(pending, operations)
                    table.insert(order, "scale")
                    identityReadOnly = pending.source.id == source.id
                    local ok = pcall(function() pending.currentDamage = 999 end)
                    mutationRejected = not ok
                    operations.scale(0.5)
                    check(pending.currentDamage == 6,
                        "the second read sees the first ordered transform")
                end,
            },
            {
                id = "fixture_reduce",
                intercept = function(pending, operations)
                    table.insert(order, "reduce")
                    operations.reduce(1)
                    check(pending.currentDamage == 5,
                        "a later interceptor receives the typed pending value")
                end,
            },
        },
        reactions = {
            { id = "first", react = function() table.insert(reactionOrder, "first") end },
            { id = "second", react = function() table.insert(reactionOrder, "second") end },
        },
    }
    local events = effects.apply({ type = "hp_damage", formula = "12" },
        source, target, session, { hpDamageParticipants = participants })
    local damage = damageEvent(events)
    check(table.concat(order, ",") == "scale,reduce",
        "immediate interceptors run in the supplied deterministic order")
    check(identityReadOnly and mutationRejected,
        "an interceptor sees typed identities and cannot mutate the pending record")
    check(target.hp == 95 and damage.value == 5,
        "the interceptor transforms the candidate before the single HP commit")
    check(damage.resolvedDamage.finalDamage == 5
            and damage.resolvedDamage.committedDamage == 5
            and damage.resolvedDamage.hpAfter == 95,
        "the resolved fact contains the transformed committed result")
    check(table.concat(reactionOrder, ",") == "first,second",
        "resolved reactions run in the supplied deterministic order")
end

--------------------------------------------------------- reaction fact --

do
    local session, source, target = rig()
    local parentFact, nestedFact
    local factMutationRejected, nestedEvents
    local reaction = {
        id = "fixture_nested_damage",
        react = function(fact, api)
            if not parentFact then
                parentFact = fact
                local ok = pcall(function()
                    fact.finalDamage = 999
                    fact.target.hp = 1
                end)
                factMutationRejected = not ok
                -- This is the ordinary effect capability, deliberately using
                -- the resolved amount instead of evaluating the parent formula.
                nestedEvents = api.applyEffect({
                    type = "hp_damage",
                    formula = tostring(fact.committedDamage),
                }, "target")
            else
                nestedFact = fact
            end
        end,
    }
    local events = effects.apply({ type = "hp_damage", formula = "12" },
        source, target, session, { hpDamageParticipants = { reactions = { reaction } } })
    local damage = damageEvent(events)
    check(parentFact and parentFact.finalDamage == 12
            and parentFact.committedDamage == 12
            and parentFact.hpAfter == 88,
        "a reaction reads the final committed fact, not a recalculated formula")
    check(factMutationRejected and target.hp == 76,
        "a reaction cannot repair or mutate its already-resolved parent fact")
    check(nestedEvents and #nestedEvents == 1 and nestedEvents[1].type == "damage"
            and nestedFact and nestedFact.finalDamage == 12,
        "a reaction follow-up enters the ordinary typed effect path")
    check(nestedFact.lineage.parent == parentFact.lineage.id
            and nestedFact.lineage.origin == parentFact.lineage.origin,
        "the nested semantic operation preserves minimal parent/origin lineage")
    check(damage.resolvedDamage.hpAfter == 88,
        "the parent resolved fact remains immutable after its nested operation")
end

---------------------------------------------------------- multi-hit --

do
    local session, source, target = rig()
    source.hp = 50
    local order = {}
    local participants = {
        interceptors = {
            {
                id = "fixture_half_damage",
                intercept = function(_, operations)
                    table.insert(order, "pending")
                    operations.scale(0.5)
                end,
            },
        },
        reactions = {
            {
                id = "fixture_recover_source",
                react = function(fact, api)
                    table.insert(order, "reaction")
                    api.applyEffect({
                        type = "hp_heal",
                        formula = tostring(fact.committedDamage),
                    }, "source")
                end,
            },
        },
    }
    local ctx = {
        session = session,
        loader = loader,
        a = source,
        targets = { target },
        skill = { effects = { { type = "hp_damage", formula = "10" } } },
        events = {},
        hpDamageParticipants = participants,
        damageLineage = { id = "action-sequence", origin = "fixture-action" },
    }
    interpreter.runImmediate({
        { cmd = "APPLY_EFFECT" },
        { cmd = "WAIT", duration = 1 },
        { cmd = "APPLY_EFFECT" },
    }, ctx)

    local types = eventTypes(ctx.events)
    check(table.concat(order, ",") == "pending,reaction,pending,reaction",
        "each hit completes its pending and resolved stages before the next")
    check(table.concat(types, ",") == "damage,heal,wait,damage,heal",
        "an immediate WAIT remains presentation pacing between semantic hits")
    check(target.hp == 90 and source.hp == 60,
        "the two-hit Action Sequence commits both hits and both follow-ups")
    check(damageEvent(ctx.events).resolvedDamage.finalDamage == 5,
        "each multi-hit commit publishes its own resolved final amount")
end

----------------------------------------------------- ally/enemy symmetry --

do
    local session, ally = rig()
    local enemy = tune(sessionModule.Battler.new(loader.getUnit("skeleton"), 1))
    local participants = {
        interceptors = {
            { intercept = function(_, operations) operations.scale(0.5) end },
        },
    }
    local function hit(source, target)
        target.hp = 100
        effects.apply({ type = "hp_damage", formula = "10" }, source, target,
            session, { hpDamageParticipants = participants })
        return target.hp
    end
    check(hit(ally, enemy) == 95 and hit(enemy, ally) == 95,
        "the typed damage mechanism is symmetric for ally and enemy battlers")
end

print(("=== Typed Damage Transition Tests: %d passed, %d failed ==="):format(passed, failed))
if failed > 0 then require("tests.fail_fast")("typed damage transition tests failed", failed) end
