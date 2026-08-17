-- #331 / #308A / #308B / #308C: typed damage, kill fact, and kill reaction proofs.
--
-- These participants are deliberately fixture-only. They are supplied as an
-- ordered local list by the test context; no production trait is migrated and
-- no final global source precedence is implied.
package.path = package.path .. ";./?.lua;./engine/?.lua"

local loader = require("engine.data.loader")
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

local function killFacts(events)
    local facts = {}
    for _, event in ipairs(events or {}) do
        if event.resolvedKill then table.insert(facts, event.resolvedKill) end
    end
    return facts
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
            and damage.resolvedDamage.hpAfterDamage == 88
            and not damage.resolvedDamage.damageKilled,
        "the baseline publishes the committed damage fact without recomputation")
    check(damage.resolvedDamage.commitCount == 1 and damage.resolved.hp == 88,
        "the baseline records one authoritative commit and its after-snapshot")
    check(#killFacts(events) == 0,
        "non-lethal ordinary damage publishes no resolved kill fact")
end

----------------------------------------------------- ordinary lethal hit --

do
    local session, source, target = rig()
    target.hp = 30
    local events = effects.apply({ type = "hp_damage", formula = "40" },
        source, target, session, {})
    local damage = damageEvent(events)
    local kills = killFacts(events)
    check(damage.resolvedDamage.finalDamage == 40
            and damage.resolvedDamage.committedDamage == 30
            and damage.resolvedDamage.hpAfterDamage == 0
            and damage.resolvedDamage.damageKilled
            and target:isDead(),
        "ordinary lethal damage reports its capped commit and damage-caused kill")
    check(#kills == 1 and kills[1].cause == "hp_damage"
            and kills[1].killer.id == source.id
            and kills[1].target.id == target.id
            and kills[1].lineage.id == damage.resolvedDamage.lineage.id,
        "ordinary lethal damage publishes exactly one kill with its damage provenance")
    local mutationRejected = not pcall(function() kills[1].cause = "execution" end)
    check(mutationRejected and not pcall(function() kills[1].killer.id = 999 end),
        "the resolved kill fact and its identities are immutable")

    local repeated = effects.apply({ type = "hp_damage", formula = "1" },
        source, target, session, {})
    check(#killFacts(repeated) == 0,
        "damage against an already-dead target does not publish a duplicate kill fact")
end

----------------------------------------------- resolved kill reaction --

do
    local session, source, target = rig()
    session.mp, session.maxMp = 45, 50
    target.hp = 5
    local order, killFact, restoreResult = {}, nil, nil
    local reactionCalls = 0
    local mutationRejected = false
    local participants = {
        killReactions = {
            {
                id = "fixture_kill_mp_first",
                react = function(fact, api)
                    table.insert(order, "first")
                    killFact = fact
                    reactionCalls = reactionCalls + 1
                    local ok = pcall(function()
                        fact.cause = "not_a_kill"
                        fact.killer.id = 999
                    end)
                    mutationRejected = not ok and fact.cause == "hp_damage"
                    check(api.session == nil,
                        "a kill reaction receives no arbitrary session handle")
                    restoreResult = api.restoreSummonerMp(12)
                end,
            },
            {
                id = "fixture_kill_mp_second",
                react = function()
                    table.insert(order, "second")
                end,
            },
        },
    }
    local events = effects.apply({ type = "hp_damage", formula = "10" },
        source, target, session, { hpDamageParticipants = participants })
    check(#killFacts(events) == 1 and killFact ~= nil
            and killFact.killer.id == source.id
            and killFact.target.id == target.id
            and killFact.cause == "hp_damage",
        "a kill reaction receives the immutable killer, target, and cause")
    check(mutationRejected and restoreResult and restoreResult.requested == 12,
        "a resolved kill fact cannot be mutated and the reaction requests a typed follow-up")
    check(reactionCalls == 1 and session.mp == 50 and restoreResult.restored == 5,
        "the semantic Summoner MP follow-up runs once and respects the resource cap")
    check(table.concat(order, ",") == "first,second"
            and restoreResult.lineage.parent == killFact.lineage.id
            and restoreResult.lineage.rootId == killFact.lineage.rootId,
        "local kill reactions run in supplied order and preserve follow-up lineage")

    target.hp = 0
    local repeated = effects.apply({ type = "hp_damage", formula = "10" },
        source, target, session, { hpDamageParticipants = participants })
    check(#killFacts(repeated) == 0 and reactionCalls == 1 and session.mp == 50,
        "an already-dead target cannot duplicate the resolved-kill reaction")

    local nonLethalSession, nonLethalSource, nonLethalTarget = rig()
    nonLethalSession.mp, nonLethalSession.maxMp = 0, 50
    nonLethalTarget.hp = 100
    local nonLethalCalls = 0
    local nonLethalParticipants = {
        killReactions = {
            { react = function() nonLethalCalls = nonLethalCalls + 1 end },
        },
    }
    local nonLethal = effects.apply({ type = "hp_damage", formula = "10" },
        nonLethalSource, nonLethalTarget, nonLethalSession,
        { hpDamageParticipants = nonLethalParticipants })
    check(#killFacts(nonLethal) == 0 and nonLethalCalls == 0,
        "a non-lethal damage transition does not run a kill reaction")
end

------------------------------------------------------ execution reaction --

do
    local session, source, target = rig()
    source.actorData.traits = {
        { code = "EXECUTION_THRESHOLD", value = 0.25 },
    }
    -- This proof is about ordinary damage before Execution. Give the fixture
    -- absolute critical evasion so the authored 5% base CRI cannot change its
    -- exact damage magnitudes, regardless of the shared RNG stream.
    target.actorData.traits = {
        { code = "CEV", value = 1.0 },
    }
    session.mp, session.maxMp = 0, 50
    target.hp = 30
    local calls, cause, restored = 0, nil, nil
    local events = effects.apply({
        type = "hp_damage",
        power = "atk",
        potency = 1.0,
    }, source, target, session, {
        hpDamageParticipants = {
            killReactions = {
                {
                    react = function(fact, api)
                        calls = calls + 1
                        cause = fact.cause
                        restored = api.restoreSummonerMp(12)
                    end,
                },
            },
        },
    })
    check(#killFacts(events) == 1 and cause == "execution"
            and calls == 1 and restored and restored.restored == 12
            and session.mp == 12,
        "Execution produces one typed kill reaction with execution cause")
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
            and damage.resolvedDamage.hpAfterDamage == 95
            and not damage.resolvedDamage.damageKilled,
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
            and parentFact.hpAfterDamage == 88,
        "a reaction reads the final committed fact, not a recalculated formula")
    check(factMutationRejected and target.hp == 76,
        "a reaction cannot repair or mutate its already-resolved parent fact")
    check(nestedEvents and #nestedEvents == 1 and nestedEvents[1].type == "damage"
            and nestedFact and nestedFact.finalDamage == 12,
        "a reaction follow-up enters the ordinary typed effect path")
    check(nestedFact.lineage.parent == parentFact.lineage.id
            and nestedFact.lineage.rootId == parentFact.lineage.rootId
            and nestedFact.lineage.origin == parentFact.lineage.origin,
        "the nested semantic operation preserves minimal parent/origin lineage")
    check(damage.resolvedDamage.hpAfterDamage == 88,
        "the parent resolved fact remains immutable after its nested operation")
end

-------------------------------------------------------- lineage roots --

do
    local session, source, target = rig()
    local first = damageEvent(effects.apply({ type = "hp_damage", formula = "3" },
        source, target, session, {})).resolvedDamage
    local second = damageEvent(effects.apply({ type = "hp_damage", formula = "4" },
        source, target, session, {})).resolvedDamage
    local nestedFact
    local reactionStarted = false
    local reaction = {
        react = function(_, api)
            if not reactionStarted then
                reactionStarted = true
                local nested = api.applyEffect({
                    type = "hp_damage",
                    formula = "1",
                }, "target")
                nestedFact = damageEvent(nested).resolvedDamage
            end
        end,
    }
    local rootEvent = damageEvent(effects.apply({ type = "hp_damage", formula = "2" },
        source, target, session, { hpDamageParticipants = { reactions = { reaction } } }))
    local root = rootEvent.resolvedDamage
    check(first.lineage.rootId ~= second.lineage.rootId
            and first.lineage.origin ~= second.lineage.origin,
        "unrelated root damage transitions have distinct provisional chain identities")
    check(nestedFact and nestedFact.lineage.id ~= root.lineage.id
            and nestedFact.lineage.parent == root.lineage.id
            and nestedFact.lineage.rootId == root.lineage.rootId,
        "nested damage has its own id, links to its parent, and preserves the root identity")
end

---------------------------------------------- damage before execution --

do
    local session, source, target = rig()
    source.actorData.traits = {
        { code = "EXECUTION_THRESHOLD", value = 0.25 },
    }
    -- This proof is about ordinary damage before Execution. Give the fixture
    -- absolute critical evasion so the authored 5% base CRI cannot change its
    -- exact damage magnitudes, regardless of the shared RNG stream.
    --
    -- #422 named this block's two magnitude assertions specifically, and its
    -- first fix guarded the other EXECUTION_THRESHOLD fixture above instead --
    -- which left the reported flake live. A 5% crit survives any number of
    -- green repeat runs, so "it passed N times" cannot close a bug like this.
    -- The control that can: force CRI to 1.0 and confirm this block still
    -- reports 43/43, because CEV drives the effective rate to zero.
    target.actorData.traits = {
        { code = "CEV", value = 1.0 },
    }
    source.hp = 50
    target.hp = 30
    local reactionAmount
    local events = effects.apply({
        type = "hp_damage",
        power = "atk",
        potency = 1.0,
    }, source, target, session, {
        hpDamageParticipants = {
            reactions = {
                {
                    react = function(fact, api)
                        reactionAmount = fact.committedDamage
                        api.applyEffect({
                            type = "hp_heal",
                            formula = tostring(fact.committedDamage),
                        }, "source")
                    end,
                },
            },
        },
    })
    local damage = damageEvent(events)
    local execution = nil
    for _, event in ipairs(events) do
        if event.type == "execution" then execution = event end
    end
    check(damage and damage.resolvedDamage.committedDamage == 13
            and damage.resolvedDamage.finalDamage == 13
            and damage.resolvedDamage.hpBefore == 30
            and damage.resolvedDamage.hpAfterDamage == 17
            and not damage.resolvedDamage.damageKilled,
        "the typed fact reports only the ordinary HP damage before Execution")
    check(execution ~= nil and target.hp == 0 and target:isDead(),
        "the existing Execution event and final death behavior remain intact")
    local kills = killFacts(events)
    check(#kills == 1 and kills[1].cause == "execution"
            and kills[1].killer.id == source.id
            and kills[1].target.id == target.id
            and kills[1].lineage.id == damage.resolvedDamage.lineage.id,
        "Execution publishes exactly one kill with Execution provenance")
    check(kills[1].cause ~= "hp_damage",
        "an Execution kill is not falsely attributed to ordinary damage")
    check(damage.resolved.hp == 0,
        "the legacy event snapshot may still observe post-Execution HP")
    check(reactionAmount == 13 and source.hp == 63,
        "a resolved reaction consumes ordinary committed damage, not Execution loss")
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
    local function lethal(source, target)
        target.hp = 5
        return killFacts(effects.apply({ type = "hp_damage", formula = "10" },
            source, target, session, { hpDamageParticipants = participants }))
    end
    local allyKills = lethal(ally, enemy)
    local enemyKills = lethal(enemy, ally)
    check(hit(ally, enemy) == 95 and hit(enemy, ally) == 95,
        "the typed damage mechanism is symmetric for ally and enemy battlers")
    check(#allyKills == 1 and allyKills[1].killer.id == ally.id
            and #enemyKills == 1 and enemyKills[1].killer.id == enemy.id,
        "resolved kill provenance is symmetric for ally and enemy authorities")
end

print(("=== Typed Damage Transition Tests: %d passed, %d failed ==="):format(passed, failed))
if failed > 0 then require("tests.fail_fast")("typed damage transition tests failed", failed) end
