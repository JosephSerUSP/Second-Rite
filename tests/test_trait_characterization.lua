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
    check(#events >= 3 and events[1].type == "damage"
            and events[2].type == "death" and events[3].type == "kill_mp_restore",
        "the restore follows the lethal damage and death events")

    target.hp = 2
    session.mp = 50
    local second = effects.apply({ type = "hp_damage", formula = "1" },
        killer, target, session, {})
    check(session.mp == 50 and not eventOf(second, "kill_mp_restore"),
        "a non-lethal hit does not restore MP")
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
