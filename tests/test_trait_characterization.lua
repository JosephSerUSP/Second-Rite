-- Characterization coverage for the current trait/reaction families selected
-- for #308. These tests pin observable gameplay contracts, not Lua call
-- structure; future migrations must preserve the results while changing the
-- discovery/authoring mechanism.
package.path = package.path .. ";./?.lua;./engine/?.lua"

local loader = require("data.loader")
local sessionModule = require("engine.session")
local effects = require("engine.effects")
local flow = require("engine.flow")

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
    local file = assert(io.open("engine/effects_core.lua", "rb"))
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

print(("=== Trait Characterization Tests: %d passed, %d failed ==="):format(passed, failed))
if failed > 0 then require("tests.fail_fast")("trait characterization tests failed", failed) end
