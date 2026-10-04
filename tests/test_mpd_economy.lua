-- The Summoner MP economy: free traversal, battle activation, Battle Strain,
-- and the MPD floor.
--
-- Ordinary traversal is intentionally free. MPD becomes expedition pressure
-- when the Summoner channels the manifested party into combat: battle entry
-- costs a fixed base plus the living party's combined MPD, while only a
-- prolonged fight adds Strain. These tests pin that current contract rather
-- than the retired per-step drain model.
package.path = package.path .. ";./?.lua;./engine/?.lua"

local loader = require("engine.data.loader")
local sessionModule = require("engine.session")
local formula = require("engine.formula")
local flow = require("engine.flow")
local traits = require("engine.traits")

print("[TEST] Starting MPD economy tests...")

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

-- A party of creatures with exact MPD values, so a cost is arithmetic rather
-- than whatever the roster currently carries.
local function rig(mpdValues)
    local sess = sessionModule.GameSession.new(loader)
    sess.party = {}
    for i, mpd in ipairs(mpdValues) do
        local b = sessionModule.Battler.new(loader.getUnit("skeleton"), 1)
        local private = {}
        for k, val in pairs(b.actorData) do private[k] = val end
        private.traits = {}
        private.baseParams = { maxHp = 50, atk = 10, def = 10, mat = 10, mdf = 10, mpd = mpd }
        private.growthMultiplier = 0
        b.actorData = private
        b.level = 1
        b.hp = 50
        sess.party[i] = b
    end
    sess.maxMp = 3000
    sess.mp = 3000
    sess.currentMapData = { safe = false }
    return sess
end

------------------------------------------------------------- the party query --

do
    local sess = rig({ 1, 2, 4 })
    check(formula.groupView(sess.party, sess).mpd == 7,
        "party.mpd is the combined MPD of the party")

    -- A dead creature stops contributing to manifestation pressure.
    sess.party[3].hp = 0
    sess.party[3]:addState("dead")
    check(formula.groupView(sess.party, sess).mpd == 3,
        "a dead creature contributes no MPD")
end

-------------------------------------------------------------- free traversal --

local function step(sess)
    local before = sess.mp
    flow.run("exploration.step", { session = sess, party = sess.party, loader = loader })
    return before - sess.mp
end

do
    local sess = rig({ 1 })
    check(step(sess) == 0, "ordinary dangerous-map traversal spends no Summoner MP")
end

do
    local sess = rig({ 4, 6, 9 })
    check(step(sess) == 0, "a heavy manifested party still walks for free")
end

do
    local sess = rig({})
    check(step(sess) == 0, "the Summoner alone walks for free")
end

do
    local sess = rig({ 4, 6 })
    sess.currentMapData = { safe = true }
    check(step(sess) == 0, "safe-map traversal also spends no Summoner MP")
end

do
    local sess = rig({ 1, 4 })
    for _ = 1, 600 do step(sess) end
    check(sess.mp == 3000,
        "600 ordinary steps leave the expedition MP pool untouched")
end

---------------------------------------------------------- battle activation --

local function battleStart(sess)
    local before = sess.mp
    local events = flow.run("battle.battle_start", {
        session = sess,
        loader = loader,
        troopId = "recruit_skeleton",
    })
    return before - sess.mp, events
end

do
    local sess = rig({ 1 })
    check(battleStart(sess) == 65,
        "MPD-1 party pays the authored 50 + 15 * MPD battle activation cost")
end

do
    local sess = rig({ 4, 6, 9 })
    check(battleStart(sess) == 335,
        "battle activation scales with the living party's combined MPD")
end

do
    local sess = rig({ 4, 6 })
    sess.currentMapData = { safe = true }
    check(battleStart(sess) == 0,
        "safe-map battles skip expedition activation cost")
end

do
    local sess = rig({ 1 })
    sess.mp = 40
    local spent = battleStart(sess)
    check(spent == 40 and sess.mp == 0,
        "insufficient MP spends the remainder and still enters battle at zero")
end

------------------------------------------------------------------- Strain --

local function roundEnd(sess, round)
    local before = sess.mp
    flow.run("battle.round_end", {
        session = sess, party = sess.party, enemies = {},
        battle = { round = round, allies = sess.party, enemies = {} },
        loader = loader,
    })
    return before - sess.mp
end

do
    local sess = rig({ 2, 3 })  -- combined MPD 5

    -- Ordinary rounds are free. Taking a tactical turn is not priced; Strain
    -- is exceptional pressure against letting an expedition battle run long.
    for round = 1, 5 do
        check(roundEnd(sess, round) == 0, "round " .. round .. " costs nothing")
    end

    check(roundEnd(sess, 6) == 20, "round 6 strains at 4x combined MPD")
    check(roundEnd(sess, 9) == 20, "round 9 is still the first band")
    check(roundEnd(sess, 10) == 40, "round 10 escalates to 8x")
    check(roundEnd(sess, 14) == 40, "round 14 is still the second band")
    check(roundEnd(sess, 15) == 80, "round 15 escalates to 16x")
    check(roundEnd(sess, 40) == 80, "the top band does not escalate further")
end

do
    -- Strain scales with the party, so a cheap party can afford a long fight
    -- and a heavy one cannot. That is the tradeoff the roster is priced around.
    local cheap = rig({ 1 })
    local heavy = rig({ 9, 9 })
    check(roundEnd(cheap, 6) == 4 and roundEnd(heavy, 6) == 72,
        "Strain scales with the party's combined MPD")
end

do
    local sess = rig({ 2, 3 })
    sess.currentMapData = { safe = true }
    check(roundEnd(sess, 20) == 0, "no Strain on a safe map")
end

do
    -- A wiped party costs nothing to sustain, however long the fight runs.
    local sess = rig({ 4, 4 })
    for _, b in ipairs(sess.party) do b.hp = 0 b:addState("dead") end
    check(roundEnd(sess, 20) == 0, "a party with no living creatures strains nothing")
end

--------------------------------------------------------------- the MPD floor --

do
    -- "An accessory may reduce its wearer's MPD by 1, never below 1." The floor
    -- is traits.getParam's, not a special case -- asserted here because the
    -- design states it as a hard rule and nothing else pins it.
    local sess = rig({ 2 })
    local b = sess.party[1]
    check(traits.getParam(b, "mpd", sess) == 2, "a creature reports its form MPD")

    b.actorData.traits = { { code = "PARAM_PLUS", dataId = "mpd", value = -1 } }
    check(traits.getParam(b, "mpd", sess) == 1, "an MPD reduction applies")

    b.actorData.traits = { { code = "PARAM_PLUS", dataId = "mpd", value = -99 } }
    check(traits.getParam(b, "mpd", sess) == 1, "MPD never falls below 1")
    check(formula.groupView(sess.party, sess).mpd == 1,
        "the floored value is what the party query reports")
    check(battleStart(sess) == 65,
        "battle activation consumes the same floored MPD value")
end

print(("=== MPD Economy Tests Completed: %d passed, %d failed ==="):format(passed, failed))
if failed > 0 then require("tests.fail_fast")("MPD economy tests failed", failed) end
