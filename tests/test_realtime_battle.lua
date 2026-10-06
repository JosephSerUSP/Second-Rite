-- Real-time battle scheduler (PE Day 1 M1, #1424), driven on the PE Day 1
-- Project's own combat data. Every hit, heal, cost, reward and outcome below
-- is resolved by production Battle; these assertions prove the scheduler
-- hands it the right actions at the right ticks.
local loader = require("engine.data.loader")
local sessionModule = require("engine.session")
local realtime = require("engine.realtime_battle")

local restore

local passed = 0
local function check(cond, msg)
    assert(cond, msg)
    passed = passed + 1
    print("  [PASS] " .. msg)
end

local function begin(seed)
    math.randomseed(seed or 1)
    local session = sessionModule.GameSession.new(loader)
    session:initializeStartingParty()
    local rt = realtime.start(session, "basement_rat", {
        positions = { party = { { -2, 1.2 } }, enemies = { { 2, 1.2 } } },
        bounds = { minX = -6, maxX = 6, minY = -1, maxY = 4 },
    })
    local aya, rat = session.party[1], rt.battle.enemies[1]
    return rt, session, aya, rat
end

local function idle(rat) rat.at = -1e9 end
local function ready(b) b.at = realtime.AT_FULL end
local function has(events, kind)
    for _, ev in ipairs(events) do if ev.type == kind then return ev end end
    return nil
end
local function force(rt, skillId, target)
    rt.battle.getAIAction = function(_, enemy)
        return { actor = enemy, skill = loader.getSkill(skillId), target = target }
    end
end

local ok, err = pcall(function()
    restore = require("tests.pe_day1_fixture")(loader)

    -- Start: the troop spawns through the production battle_start phase.
    local rt, session, aya, rat = begin()
    check(aya.id == "aya" and rat.actorData.id == "rat", "Aya and the troop's rat are real battlers")
    check(rat.hp == 20 and aya.hp == aya:getMaxHp(session), "rat HP 20 and Aya at full HP from unit data")
    local resources = require("engine.battler_resources")
    local function pe(b) return (resources.get(b, "pe", session)) end
    check(pe(aya) == 100, "PE is Aya's own declared resource, starting full at 100")
    check(session.inventory.handgun_ammo == 11 and session.inventory.medicine == 1,
        "new game grants 11 ammo and one Medicine")

    -- AT fills on the clock; a command needs a full gauge.
    idle(rat)
    local acted, why = rt:command("skill", "handgun_shot", rat)
    check(not acted and why == "not ready", "an empty AT gauge refuses commands")
    local ticks = 0
    while aya.at < realtime.AT_FULL do rt:step(); ticks = ticks + 1 end
    check(ticks > 1 and ticks == rt.tick, "the gauge fills over fixed ticks")

    -- Paused battles do not advance.
    rt.paused = true
    local frozen = rt.tick
    rt:step({ dx = 1, dy = 0 })
    check(rt.tick == frozen and aya.field.x == -2, "pause freezes the clock and movement")
    rt.paused = false

    -- Input is a direction; the Project's moveSpeed sets the distance, and a
    -- diagonal is never faster than a straight line.
    local speed = loader.system.realtimeBattle.moveSpeed
    local x0, y0 = aya.field.x, aya.field.y
    rt:step({ dx = 1, dy = 1 })
    check(math.abs(math.sqrt((aya.field.x - x0)^2 + (aya.field.y - y0)^2) - speed) < 1e-9,
        "diagonal movement covers exactly moveSpeed per tick")
    aya.field.x, aya.field.y = x0, y0

    -- The idle rat has been closing in (unit realtime.approach); pin it so
    -- the distance-sensitive shots below measure from a known spot.
    check(rat.field.x < 2, "an idle rat approaches Aya")
    rat.field.x, rat.field.y = 2, 1.2

    -- In range: damage comes from the skill's distance formula, the ammo
    -- from the item-stock cost, both resolved by production Battle.
    check(rt:command("skill", "handgun_shot", rat), "a ready, in-range shot is taken")
    check(rat.hp == 15, "distance 4 deals 7 - floor(4/2) = 5")
    check(session.inventory.handgun_ammo == 10 and aya.at == 0, "the shot spends one round and the AT turn")

    -- Out of range: a published miss; the round is still spent (O4 symmetry).
    rat.field.x = 3
    ready(aya)
    rt:drainEvents()
    rt:command("skill", "handgun_shot", rat)
    check(rat.hp == 15 and has(rt:drainEvents(), "miss"), "beyond range the shot misses")
    check(session.inventory.handgun_ammo == 9, "a missed shot still spends its round")

    -- Closer is stronger.
    rat.field.x = -1
    ready(aya)
    rt:command("skill", "handgun_shot", rat)
    check(rat.hp == 8, "distance 1 deals 7 - floor(1/2) = 7")

    -- No stock: production's blocked reason, nothing spent.
    session.inventory.handgun_ammo = nil
    ready(aya)
    acted, why = rt:command("skill", "handgun_shot", rat)
    check(not acted and why == "Out of ammunition" and aya.at == realtime.AT_FULL,
        "without ammunition the shot is refused and the turn kept")

    -- PE Heal 1 pays 30 from Aya's own PE (O3, revised): never the shared MP.
    local sharedMp = session.mp
    aya.hp = 10
    rt:command("skill", "heal1", aya)
    check(aya.hp == 40 and pe(aya) == 70 and aya.at == 0, "Heal 1 restores 30 HP for 30 PE")
    check(session.mp == sharedMp, "Heal 1 never touches the shared MP pool")
    resources.change(aya, "pe", -50, session)
    ready(aya)
    acted, why = rt:command("skill", "heal1", aya)
    check(not acted and why == "Not enough PE" and aya.hp == 40 and pe(aya) == 20,
        "Heal 1 is refused without 30 PE, with a readable reason")

    -- Medicine goes through Battle:applyItem: consumed, healing clamped.
    aya.hp = 20
    rt:command("item", "medicine", aya)
    check(aya.hp == aya:getMaxHp(session) and (session.inventory.medicine or 0) == 0,
        "Medicine heals to the cap and is consumed")
    ready(aya)
    acted = rt:command("item", "medicine", aya)
    check(not acted, "an item with no stock is refused")

    -- Lunge: the rat locks Aya's position after its telegraph.
    rt, session, aya, rat = begin()
    force(rt, "rat_bite", aya)
    ready(rat)
    rt:step()
    check(has(rt:drainEvents(), "telegraph"), "the bite is telegraphed before it lands")
    local hp = aya.hp
    for _ = 1, 40 do rt:step() end
    check(aya.hp == hp - 4, "standing still, the locked bite lands for 4")

    rt, session, aya, rat = begin()
    force(rt, "rat_bite", aya)
    idle(rat); ready(rat)
    rt:step()
    for _ = 1, 20 do rt:step({ dx = 0, dy = 1 }) end
    hp = aya.hp
    rat.at = -1e9
    for _ = 1, 20 do rt:step() end
    check(aya.hp == hp and has(rt:drainEvents(), "miss"), "moving off the locked spot evades the bite")

    -- Fire tail: three projectiles, each can hit at most once.
    rt, session, aya, rat = begin()
    force(rt, "rat_fire_tail", aya)
    ready(rat)
    hp = aya.hp
    for _ = 1, 140 do rt:step(); rat.at = math.min(rat.at, 0) end
    local lost = hp - aya.hp
    check(lost > 0 and lost <= 12 and lost % 4 == 0, "each fire-tail projectile hits at most once")

    -- Victory runs the Project's victory phase exactly once.
    rt, session, aya, rat = begin()
    idle(rat)
    rat.hp = 3
    ready(aya)
    rt:command("skill", "handgun_shot", rat)
    check(rt.outcome == "victory", "the last enemy falling is victory")
    check(session.inventory.handgun_ammo == 10 + 6, "victory grants Ammo +6 once")
    local tick = rt.tick
    rt:step()
    check(rt.tick == tick, "a finished battle no longer advances")

    -- Defeat.
    rt, session, aya, rat = begin()
    force(rt, "rat_bite", aya)
    aya.hp = 4
    ready(rat)
    for _ = 1, 40 do rt:step() end
    check(rt.outcome == "defeat" and aya.hp == 0, "a lethal bite is defeat")

    -- Escape is production's escape effect plus the Project's flee phase.
    rt, session, aya, rat = begin()
    idle(rat); ready(aya)
    rt:command("skill", "escape", aya)
    check(rt.outcome == "escaped", "Escape resolves through the production escape effect")

    -- A round is ticksPerRound ticks; its end runs the Project's round_end,
    -- whose PE regeneration proves the phase ran.
    rt, session, aya, rat = begin()
    idle(rat)
    local resources2 = require("engine.battler_resources")
    resources2.change(aya, "pe", -50, session)
    for _ = 1, loader.system.realtimeBattle.ticksPerRound - 1 do rt:step(); aya.at = 0 end
    check((resources2.get(aya, "pe", session)) == 50, "no round boundary before ticksPerRound ticks")
    rt:step()
    check((resources2.get(aya, "pe", session)) == 54 and rt.battle.round == 2,
        "the round boundary runs round_end once, regenerating PE")

    -- PE is creature state: it survives a save round trip.
    local savegame = require("engine.savegame")
    local data = savegame.serialize(session, loader, "map")
    local restored = savegame.deserialize(data, loader)
    check((resources2.get(restored.party[1], "pe", restored)) == 54, "PE round-trips through a save")

    -- Determinism: the same seed and inputs give the same event stream.
    local function transcript(seed)
        local r, _, a = begin(seed)
        local out = {}
        for i = 1, 400 do
            r:step({ dx = (i % 50 < 25) and 0.02 or -0.02, dy = 0 })
            if a.at >= realtime.AT_FULL then r:command("skill", "handgun_shot", r.battle.enemies[1]) end
            for _, ev in ipairs(r:drainEvents()) do out[#out + 1] = r.tick .. ":" .. tostring(ev.type) end
            if r.outcome then break end
        end
        return table.concat(out, ",")
    end
    check(transcript(7) == transcript(7), "identical seeds and inputs replay identically")
end)
if restore then restore() end
assert(ok, err)
print(("=== Real-time Battle Tests: %d passed, 0 failed ==="):format(passed))
