-- Characterization coverage for the current trait/reaction families selected
-- for #308. These tests pin observable gameplay contracts, not Lua call
-- structure; future migrations must preserve the results while changing the
-- discovery/authoring mechanism.
package.path = package.path .. ";./?.lua;./engine/?.lua"

local loader = require("engine.data.loader")
local sessionModule = require("engine.session")
local effects = require("engine.effects")
local flow = require("engine.flow")
local traits = require("engine.traits")
local semantic_calculation = require("engine.semantic_calculation")

print("[TEST] Starting trait characterization tests...")

local passed, failed = 0, 0
local function check(ok, message)
    if ok then
        passed = passed + 1
        print("  [PASS] " .. message)
    else
        failed = failed + 1
        print("  [FAIL] " .. message)
    end
end

loader.init()

local function eventOf(events, kind)
    for _, event in ipairs(events or {}) do
        if event.type == kind then return event end
    end
end

local function eventTypes(events)
    local out = {}
    for _, event in ipairs(events or {}) do table.insert(out, event.type) end
    return table.concat(out, ",")
end

-- KILL_MP_RESTORE is authored by the Reaper passive on Diablos. A lethal
-- damage effect restores Summoner MP once, after the kill is established, and
-- the authoritative value is the capped amount that was actually restored.
do
    local session = sessionModule.GameSession.new(loader)
    local killer = session:recruitActor("diablos", 1)
    local target = sessionModule.Battler.new(loader.getUnit("skeleton"), 1)
    session.mp, session.maxMp = 40, 50
    target.hp = 1

    local events = effects.apply({ type = "hp_damage", formula = "1" },
        killer, target, session, {})
    local restore = eventOf(events, "kill_mp_restore")
    check(target:isDead() and session.mp == 50,
        "a Reaper kill restores Summoner MP, capped at max MP")
    check(restore and restore.value == 10,
        "KILL_MP_RESTORE reports exactly the committed MP delta")
    check(eventTypes(events) == "damage,death,kill_mp_restore,text"
            and restore.resolved and restore.resolved.mp == 50,
        "the restore preserves the damage/death/event/text contract")
    check(events[4].text == "- Diablos's finishing blow restores 10 MP.",
        "the kill restore keeps its authored presentation text")
    local death = eventOf(events, "death")
    local killFact = death and death.resolvedKill
    local immutable = killFact and not pcall(function()
        killFact.cause = "not_a_kill"
        killFact.killer.id = 999
    end)
    check(immutable and killFact.cause == "hp_damage",
        "the production reaction consumes an immutable resolved kill fact")

    target.hp = 2
    session.mp = 50
    local second = effects.apply({ type = "hp_damage", formula = "1" },
        killer, target, session, {})
    check(session.mp == 50 and not eventOf(second, "kill_mp_restore"),
        "a non-lethal hit does not restore MP")

    target.hp = 0
    session.mp = 0
    local alreadyDead = effects.apply({ type = "hp_damage", formula = "1" },
        killer, target, session, {})
    check(session.mp == 0 and not eventOf(alreadyDead, "kill_mp_restore"),
        "an already-dead target cannot duplicate the restore")
end

-- The typed production reaction also handles the existing Execution kill
-- result. The fixture keeps the authored Reaper passive and only tunes this
-- instance's combat numbers so the hit leaves the target below the threshold.
do
    local session = sessionModule.GameSession.new(loader)
    local killer = session:recruitActor("diablos", 1)
    local tuned = {}
    for key, value in pairs(killer.actorData) do tuned[key] = value end
    tuned.baseParams = { maxHp = 100, atk = 20, def = 10, mat = 20, mdf = 10 }
    tuned.traits = { { code = "EXECUTION_THRESHOLD", value = 0.25 } }
    killer.actorData = tuned

    local target = sessionModule.Battler.new(loader.getUnit("skeleton"), 1)
    local targetData = {}
    for key, value in pairs(target.actorData) do targetData[key] = value end
    targetData.baseParams = { maxHp = 100, atk = 20, def = 10, mat = 20, mdf = 10 }
    target.actorData = targetData
    target.hp = 30
    session.mp, session.maxMp = 0, 50

    local events = effects.apply({ type = "hp_damage", power = "atk", potency = 1 },
        killer, target, session, {})
    local restore = eventOf(events, "kill_mp_restore")
    check(eventOf(events, "execution") ~= nil and target:isDead()
            and restore and restore.value == 12 and session.mp == 12,
        "an Execution kill runs one Reaper typed kill reaction")
end

-- A source without the trait still travels through the same lethal path, but
-- has no production participant effect.
do
    local session = sessionModule.GameSession.new(loader)
    local killer = session:recruitActor("skeleton", 1)
    local target = sessionModule.Battler.new(loader.getUnit("skeleton"), 1)
    target.hp = 1
    local events = effects.apply({ type = "hp_damage", formula = "1" },
        killer, target, session, {})
    check(target:isDead() and not eventOf(events, "kill_mp_restore"),
        "a lethal kill with no eligible trait does not restore MP")
end

-- The resource authority remains symmetric when the killer is an enemy
-- battler rather than a party member.
do
    local session = sessionModule.GameSession.new(loader)
    local killer = sessionModule.Battler.new(loader.getUnit("diablos"), 2)
    local target = sessionModule.Battler.new(loader.getUnit("skeleton"), 1)
    target.hp = 1
    session.mp, session.maxMp = 0, 50
    local events = effects.apply({ type = "hp_damage", formula = "1" },
        killer, target, session, {})
    local restore = eventOf(events, "kill_mp_restore")
    check(restore and restore.actor == killer and restore.target == target
            and restore.value == 12 and session.mp == 12,
        "enemy Reaper authority remains compatible with the production reaction")
end

-- The mature drain calculation remains authoritative, while its lethal result
-- now uses the same typed kill participant instead of the removed special case.
do
    local session = sessionModule.GameSession.new(loader)
    local killer = session:recruitActor("diablos", 1)
    local target = sessionModule.Battler.new(loader.getUnit("skeleton"), 1)
    target.hp = 1
    session.mp, session.maxMp = 0, 50
    local events = effects.apply({ type = "hp_drain", formula = "1" },
        killer, target, session, {})
    local restore = eventOf(events, "kill_mp_restore")
    check(target:isDead() and restore and restore.value == 12 and session.mp == 12,
        "a lethal drain keeps Reaper compatibility through resolvedKill")
end

-- Multiple active contributions retain the mature aggregate query. Savor is
-- instance-local state here, so this does not mutate shared loader data or
-- prescribe the eventual #308 source precedence.
do
    local session = sessionModule.GameSession.new(loader)
    local killer = session:recruitActor("diablos", 1)
    killer.savor = {
        itemId = 174,
        battlesRemaining = 2,
        traits = { { code = "KILL_MP_RESTORE", value = 5 } },
    }
    local target = sessionModule.Battler.new(loader.getUnit("skeleton"), 1)
    target.hp = 1
    session.mp, session.maxMp = 0, 50
    local events = effects.apply({ type = "hp_damage", formula = "1" },
        killer, target, session, {})
    local restore = eventOf(events, "kill_mp_restore")
    check(restore and restore.value == 17 and session.mp == 17,
        "multiple current KILL_MP_RESTORE contributions keep the aggregate result")
end

-- The mature special-case must not return as a second production path.
do
    local file
    if os.getenv("THESTRA_REPOSITORY_ROOT") then
        file = assert(io.open(os.getenv("THESTRA_REPOSITORY_ROOT") .. "/runtime/engine/effects.lua", "rb"))
    else
        file = assert(io.open("engine/effects.lua", "rb"))
    end
    local source = file:read("*a")
    file:close()
    check(not source:find("awardKill", 1, true),
        "the old awardKill restoration path is removed")
end

-- BATTLE_START_DAMAGE is authored on Shadow Stalker as a party passive, but
-- the battle-start flow discovers it through the party aggregate and applies
-- it to the first living enemy after SPAWN_ENEMIES publishes the roster.
do
    local session = sessionModule.GameSession.new(loader)
    session:recruitActor("shadow_stalker", 1)
    local events = flow.run("battle.battle_start", {
        session = session,
        loader = loader,
        troopId = "recruit_skeleton",
    })
    local spawned = eventOf(events, "spawn_enemies")
    local enemy = spawned and spawned.enemies and spawned.enemies[1]
    local damage = eventOf(events, "damage")
    check(enemy ~= nil and damage ~= nil and damage.target == enemy,
        "BATTLE_START_DAMAGE hits the first living enemy after spawn")
    check(enemy and enemy.hp < enemy:getMaxHp(session),
        "the authored ambush changes enemy HP during battle_start")
    local damageCount = 0
    for _, event in ipairs(events) do
        if event.type == "damage" then damageCount = damageCount + 1 end
    end
    check(damageCount == 1,
        "the battle-start ambush damages exactly one enemy")
end

-- POST_BATTLE_HEAL and GOLD_DIGGER are both consumed by the victory flow,
-- but through different surrounding operations: one targets each living
-- carrier, while the other contributes once to the party reward formula.
do
    local session = sessionModule.GameSession.new(loader)
    local healer = session:recruitActor("high_pixie", 1)
    local greedy = session:recruitActor("ghoul", 1)
    healer.hp = 1
    greedy.hp = math.max(1, greedy:getMaxHp(session) - 1)
    session.gold = 0

    local enemy = sessionModule.Battler.new(loader.getUnit("skeleton"), 1)
    local beforeGold = session.gold
    local events = flow.run("battle.victory", {
        session = session,
        loader = loader,
        party = session.party,
        enemies = { enemy },
    })
    check(healer.hp == 2,
        "POST_BATTLE_HEAL restores exactly the authored amount on victory")
    check(greedy.hp == math.max(1, greedy:getMaxHp(session) - 1),
        "victory healing is carrier-local and does not heal other party members")
    check(session.gold - beforeGold == 16,
        "GOLD_DIGGER contributes +5 to the authored victory gold formula")
end

-- MOVE_HEAL is one aggregate calculation today, not one independently
-- committed reaction per source. All current active-object kinds may
-- contribute the same registered code. The step host asks for the signed net
-- once, applies it silently when positive, keeps fractional values, and clamps
-- once at Max HP. This characterization is the key reason this slice does not
-- force a source-local reaction migration before #308 has a calculation layer.
do
    local session = sessionModule.GameSession.new(loader)
    local carrier = session:recruitActor("wisp", 3)

    -- Keep shared loader data immutable. Actor/equipment/Savor are local to this
    -- battler; a loader proxy supplies one fixture state while delegating all
    -- real authored resources back to the canonical loader.
    local actorData = {}
    for key, value in pairs(carrier.actorData) do actorData[key] = value end
    actorData.traits = { { code = "MOVE_HEAL", value = 0.25 } }
    carrier.actorData = actorData
    carrier.equipment[1] = {
        traits = { { code = "MOVE_HEAL", value = 0.5 } },
    }
    carrier.savor = {
        itemId = "fixture_move_heal_savor",
        battlesRemaining = 2,
        traits = { { code = "MOVE_HEAL", value = -0.125 } },
    }

    local baseLoader = session.loader
    local fixtureState = {
        id = "fixture_move_heal_state",
        traits = { { code = "MOVE_HEAL", value = -0.25 } },
    }
    session.loader = setmetatable({
        getState = function(id)
            if id == fixtureState.id then return fixtureState end
            return baseLoader.getState(id)
        end,
    }, { __index = baseLoader })
    carrier.states = { { id = fixtureState.id } }

    local found = traits.findAllSources(carrier, "MOVE_HEAL", session)
    local sourceKinds = {}
    for _, entry in ipairs(found) do sourceKinds[entry.source.source] = true end
    check(sourceKinds.actor and sourceKinds.passive and sourceKinds.equipment
            and sourceKinds.state and sourceKinds.savor,
        "MOVE_HEAL can currently aggregate actor, passive, equipment, state, and Savor sources")

    carrier.hp = 10
    local hpBeforePreview = carrier.hp
    local previewA = traits.getRateCalculation(carrier, "MOVE_HEAL", session)
    local previewB = traits.getRateCalculation(carrier, "MOVE_HEAL", session)
    check(math.abs(previewA.value - 1.375) < 0.000001
            and previewA.value == previewB.value
            and carrier.hp == hpBeforePreview,
        "MOVE_HEAL's production calculation is repeatable and side-effect-free before commit")
    check(previewA.authored == previewA.value and #previewA.steps == 5,
        "MOVE_HEAL preserves one signed additive aggregate across all five contributing sources")

    local events = flow.run("exploration.step", { session = session })
    check(math.abs(carrier.hp - (hpBeforePreview + previewA.value)) < 0.000001,
        "exploration.step consumes the same MOVE_HEAL calculation that preview returned")
    check(eventOf(events, "heal") == nil,
        "MOVE_HEAL remains a silent HP mutation with no heal/log event")

    -- A sufficiently negative active source cancels the positive sources as one
    -- net aggregate. Independent per-source reactions would not preserve this.
    carrier.savor.traits[1].value = -2
    local cancelled = traits.getRateCalculation(carrier, "MOVE_HEAL", session)
    local beforeCancelledStep = carrier.hp
    flow.run("exploration.step", { session = session })
    check(cancelled.value < 0 and carrier.hp == beforeCancelledStep,
        "non-positive signed MOVE_HEAL aggregate is a no-op rather than separate source commits")
end

-- Generic calculation proof for the new substrate. This is deliberately
-- fixture-only: explicit ordered records prove reusable add/multiply/clamp/
-- replace semantics without inventing source discovery, channel registration,
-- package order, or an authored reaction schema.
do
    local contributions = {
        { operation = "add", value = 0.25 },
        { operation = "multiply", value = 2 },
        { operation = "clamp", min = 0, max = 1 },
        { operation = "replace", value = 0.6 },
    }
    local first = semantic_calculation.evaluate({
        channel = "fixture.chance",
        base = 0.5,
        contributions = contributions,
    })
    local second = semantic_calculation.evaluate({
        channel = "fixture.chance",
        base = 0.5,
        contributions = contributions,
    })
    check(math.abs(first.value - 0.6) < 0.000001
            and second.value == first.value and #first.steps == 4,
        "semantic calculations compose ordered generic operations deterministically")
    check(contributions[1].value == 0.25 and contributions[2].value == 2
            and contributions[3].min == 0 and contributions[3].max == 1,
        "semantic calculation evaluation does not mutate its authored contribution records")
    check(first.steps[1].before == 0.5 and first.steps[1].after == 0.75
            and first.steps[2].after == 1.5 and first.steps[3].after == 1
            and math.abs(first.steps[4].after - 0.6) < 0.000001,
        "semantic calculation returns an inspectable ordered trace")

    local sparseRejected = not pcall(semantic_calculation.evaluate, {
        base = 0,
        contributions = { [1] = { operation = "add", value = 1 }, [3] = { operation = "add", value = 1 } },
    })
    local unknownRejected = not pcall(semantic_calculation.evaluate, {
        base = 0,
        contributions = { { operation = "mystery", value = 1 } },
    })
    check(sparseRejected and unknownRejected,
        "semantic calculations reject unordered/sparse input and unknown operations loudly")
end

print(("=== Trait Characterization Tests: %d passed, %d failed ==="):format(passed, failed))
if failed > 0 then require("tests.fail_fast")("trait characterization tests failed", failed) end
