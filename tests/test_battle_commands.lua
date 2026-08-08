-- The battle console used to draw a fixed five rows and dispatch on the row
-- number, so every creature could attack, flee and rummage in the bag -- an Egg
-- included, despite its only skill being Wait. The command set is data now.
package.path = package.path .. ";./?.lua;./engine/?.lua"

local loader = require("data.loader")
local sessionModule = require("engine.session")
local battle = require("engine.battle")

print("[TEST] Starting battle command tests...")

local passed, failed = 0, 0
local function check(cond, msg)
    if cond then passed = passed + 1 print("  [PASS] " .. msg)
    else failed = failed + 1 print("  [FAIL] " .. msg) end
end

loader.init()

local function ids(battler)
    local out = {}
    for _, c in ipairs(battle.commandsFor(battler, loader)) do table.insert(out, c.id) end
    return out
end
local function join(t) return table.concat(t, ",") end

-- An ordinary creature authors nothing and gets the default set, in the order
-- the registry declares -- which is the order the menu has always had.
local ordinary = sessionModule.Battler.new(loader.getActor(3), 1)
check(join(ids(ordinary)) == "attack,skill,defend,item,flee",
    "a creature that authors no list gets the default set, in menu order")

-- The Egg: the whole of "an Egg can do nothing else" is one authored list.
local egg = sessionModule.Battler.new(loader.getActor(15), 1)
check(join(ids(egg)) == "wait", "an Egg can only wait")

-- Registry order wins over the order an actor happens to list them in, so the
-- menu never reshuffles between creatures.
local scrambled = { actorData = { battleCommands = { "flee", "attack", "defend" } } }
check(join(ids(scrambled)) == "attack,defend,flee",
    "an actor's list is drawn in registry order, not authoring order")

-- An unknown id is ignored rather than drawn as a blank row; G1 is what
-- actually rejects it, this only pins that it cannot reach the menu.
local bogus = { actorData = { battleCommands = { "attack", "nonexistent" } } }
check(join(ids(bogus)) == "attack", "an unknown command id never reaches the menu")

-- Every command the registry offers must be dispatchable by the console: it
-- either opens target selection, opens a submenu, or commits outright.
local seen = {}
for _, cmd in ipairs(loader.engine.battleCommands or {}) do
    seen[cmd.id] = true
    check(cmd.resolve == "target" or cmd.resolve == "submenu" or cmd.resolve == "commit",
        "command '" .. tostring(cmd.id) .. "' declares how it resolves")
end
check(seen.wait and seen.flee, "Wait and Flee are registry commands like the rest")

-- Flee is a skill now, so it is authorable the way attack, defend and wait are.
check(loader.getSkill("flee") ~= nil, "Flee is backed by a real skill")
local waitSkill = loader.getSkill("wait")
check(waitSkill and #(waitSkill.effects or {}) == 0,
    "Wait is a genuine no-op -- it spends the turn and does nothing")

-- Escaping is an effect, not a keyword. It used to be `act.type == "flee"`
-- scanned before the round was built, so it preempted the whole round and no
-- item could ever carry it. It resolves in speed order now, which is why the
-- default golden fixture's fleeing Pixie dies to a faster Skeleton first --
-- that fixture no longer covers a SUCCESSFUL escape, so this does.
local effects = require("engine.effects")

local fleeSkill = loader.getSkill("flee")
local escapeEffect
for _, eff in ipairs(fleeSkill.effects or {}) do
    if eff.type == "escape" then escapeEffect = eff end
end
check(escapeEffect ~= nil, "the Flee skill escapes by declaring an effect, not by its id")

local sess = sessionModule.GameSession.new(loader)
sess:initializeStartingParty()
local enemy = sessionModule.Battler.new(loader.getActor(3), 1)
local arena = battle.Battle.new(sess, { enemy })
local actor = sess.party[1]

-- The flow decides, so run it enough times to see both branches rather than
-- reaching past it and asserting the roll.
local sawSuccess, sawFailure = false, false
for _ = 1, 200 do
    local evs = effects.apply(escapeEffect, actor, actor, sess, { battle = arena })
    for _, ev in ipairs(evs) do
        if ev.type == "flee_success" then sawSuccess = true end
        if ev.type == "text" then sawFailure = true end
    end
end
check(sawSuccess, "an escape effect can succeed, emitting flee_success")
check(sawFailure, "and can fail, which is what makes it a gamble")

-- Outside a battle there is nothing to escape from; a menu must not blow up.
local outside = effects.apply(escapeEffect, actor, actor, sess, {})
check(type(outside) == "table" and #outside == 0,
    "an escape effect outside battle does nothing rather than erroring")

---------------------------------------------------------------- #179 authority --

-- Regression specimen found while investigating #179: Overcast is paid by
-- Battle:resolveRound(), but the old live-scene wrapper restored the previous
-- MP and had no `overcast` replay branch, so the cast was free in live play and
-- only in live play. Headless fixtures never saw it.
--
-- This is deliberately driven through scene_host + the real battle scene rather
-- than by poking BattleView directly. tests/test_battle_presentation_authority
-- proves the seam's invariants against synthetic events; this proves the live
-- path actually reaches that seam, which no golden gate currently does.
do
    local sceneHost = require("engine.scene_host")
    local battleScene = require("engine.scenes.battle")
    local battle_view = require("presentation.battle_view")
    local oldGetSkill = loader.getSkill
    local testSkill = {
        id = "testOvercast179", name = "Test Overcast", target = "enemy",
        speed = 999, effects = {}, charges = 0, overcast = { mp = 37 },
    }
    loader.getSkill = function(id)
        if id == testSkill.id then return testSkill end
        return oldGetSkill(id)
    end

    local s = sessionModule.GameSession.new(loader)
    s:initializeStartingParty()
    s.mp, s.maxMp = 100, 100
    local member = s.party[1]
    member.skills = { testSkill.id }
    local foe = sessionModule.Battler.new(loader.getActor(3), 1)
    foe.hp = foe:getMaxHp(s)
    local b = battle.Battle.new(s, { foe })

    local oldGlobal = _G.activeSession
    _G.activeSession = s
    sceneHost.init()
    sceneHost.push("battle", { session = s, loader = loader, party = s.party })
    local v = battleScene.getState()
    v.battle = b
    v.collectedActions = { [1] = { type = "skill", id = testSkill.id, target = foe } }
    battleScene.resolveRound()

    check(s.mp == 63,
        "live scene resolution preserves the authoritative Overcast MP spend")
    check(battle_view.isActive(),
        "live scene resolution starts a presentation projection instead of rolling state back")

    battle_view.clear()
    sceneHost.init()
    _G.activeSession = oldGlobal
    loader.getSkill = oldGetSkill
end

-- Both MP directions. The old rollback erased Reaper/KILL_MP_RESTORE rewards
-- because presentation restored MP and then only replayed the drain branch.
-- Here the engine has already resolved each transition; the view only catches
-- the drawn pool up to a fact it is handed.
do
    local battle_view = require("presentation.battle_view")
    local s = sessionModule.GameSession.new(loader)
    s:initializeStartingParty()
    s.mp, s.maxMp = 100, 100
    local foe = sessionModule.Battler.new(loader.getActor(3), 1)
    local b = battle.Battle.new(s, { foe })

    battle_view.beginRound(b, s)
    local member = s.party[1]

    -- The engine has already spent the Overcast MP; the view is still showing
    -- the pre-cast pool until the event's beat lands.
    s.mp = 63
    check(battle_view.inspect(member).mp == 100,
        "the projection holds the pre-resolution MP frame after the engine has spent it")
    battle_view.apply({ type = "overcast", resolved = { mp = 63 } }, { mp = true })
    check(battle_view.inspect(member).mp == 63,
        "the resolved Overcast fact advances the projected MP pool")

    s.mp = 75
    battle_view.apply({ type = "kill_mp_restore", resolved = { mp = 75 } }, { mp = true })
    check(battle_view.inspect(member).mp == 75,
        "KILL_MP_RESTORE advances the projected MP to the engine's resolved value")
    check(s.mp == 75,
        "projecting a Reaper MP reward does not perform the authoritative restore again")

    -- The seam refuses to guess: a producer that stops publishing resolved
    -- facts must fail loudly rather than leave the projection silently stale.
    local ok = pcall(battle_view.apply, { type = "damage", target = s.party[1], value = 7 },
        { hp = true })
    check(not ok,
        "a requested channel with no resolved fact behind it is refused, not guessed")

    battle_view.clear()
end

print(string.format("=== Battle Command Tests: %d passed, %d failed ===", passed, failed))
if failed > 0 then require("tests.fail_fast")(failed .. " battle command test(s) failed", failed) end
