-- Level-up reporting (engine/progress.lua), authored progression (#549), and
-- LEVEL_REACHED lifecycle publication (#550).
--
-- None of this is visible to the golden gates: they prove the battle log did
-- not change, not that a diff taken around an EXP grant names the right
-- creature, the right numbers, survives a transform, or publishes every
-- semantic level crossing in deterministic order.
package.path = package.path .. ";./?.lua;./engine/?.lua"

local loader = require("data.loader")
local sessionModule = require("engine.session")
local progress = require("engine.progress")
local progression = require("engine.progression")
local level_event = require("engine.level_event")
local formula = require("engine.formula")
local flow = require("engine.flow")
local traits = require("engine.traits")
local interpreter = require("engine.interpreter")
local windowRenderer = require("presentation.window_renderer")

print("[TEST] Starting progress tests...")

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

local function rowFor(entry, param)
    for _, r in ipairs(entry.rows) do
        if r.param == param then return r end
    end
end

do
    -- The current Project explicitly owns the same curve as RTP 1.0. The
    -- runtime must read data/progression.json rather than reconstructing that
    -- sentence from system.growth.expPerLevel.
    check(progression.nextLevelExp(1) == 15, "authored progression resolves the level-1 threshold")
    check(progression.nextLevelExp(5) == 75, "authored progression evaluates against the current level")
    check(progression.curveCost(1, 4) == 90, "curveCost sums the same authored thresholds gainExp crosses")
end

do
    -- A nonlinear candidate proves the semantic helper is a real Formula
    -- boundary, not a renamed multiplier. Tooling can evaluate a candidate spec
    -- without mutating the active Project resource.
    local nonlinear = { nextLevelExp = "level * level + 7" }
    check(progression.nextLevelExp(4, nonlinear) == 23, "nonlinear authored curves are supported")
    check(progression.curveCost(1, 4, nonlinear) == 35, "nonlinear curveCost uses the exact same helper")

    local okZero = pcall(progression.nextLevelExp, 3, { nextLevelExp = "0" })
    check(not okZero, "nonpositive thresholds fail visibly instead of hanging level resolution")
    local okInfinite = pcall(progression.nextLevelExp, 3, { nextLevelExp = "1 / 0" })
    check(not okInfinite, "nonfinite thresholds fail visibly")
    local okFraction = pcall(progression.nextLevelExp, 3, { nextLevelExp = "2.5" })
    check(not okFraction, "fractional EXP thresholds require an explicit authored rounding choice")
    local okBroken = pcall(progression.nextLevelExp, 3, { nextLevelExp = "level *" })
    check(not okBroken, "broken threshold formulas fail visibly")
end

do
    -- Presentation must consume the same semantic helper, not merely happen to
    -- agree with today's linear house curve. Swap in a nonlinear threshold at
    -- the helper seam and resolve an ordinary party-list row headlessly: stale
    -- `level * expPerLevel` presentation would report 60 here instead of 23.
    local realNextLevelExp = progression.nextLevelExp
    progression.nextLevelExp = function(level)
        return level * level + 7
    end

    local sess = sessionModule.GameSession.new(loader)
    local b = sess:recruitActor("pixie", 4)
    b.level = 4
    local probeScene = {
        windows = {
            {
                id = "progression_probe",
                content = {
                    { type = "list", listId = "party", format = "{expNeeded}" },
                },
            },
        },
    }
    local resolved = windowRenderer.resolveDataState(
        probeScene,
        { session = sess, loader = loader, party = sess.party },
        { v = {}, winState = {}, windowOrder = {} })

    progression.nextLevelExp = realNextLevelExp
    local row = resolved.windows and resolved.windows[1]
        and resolved.windows[1].rows and resolved.windows[1].rows[1]
    check(row and row.text == "23",
        "headless party/status rows use the shared nonlinear progression threshold")
end

do
    -- The lifecycle host itself is an ordinary authored Event Program. This
    -- Project extends the behaviorless RTP phase with its seeded growth policy;
    -- the same event noun remains directly readable without a persistent
    -- Variable or progression-specific interpreter.
    local sess = sessionModule.GameSession.new(loader)
    local b = sess:recruitActor("pixie", 1)
    b.level = 2 -- model the already-committed atomic crossing for the host proof
    local growthBefore = b.growth.maxHp or 0
    local expectedGrowth = require("engine.growth").packetFor(b.actorData, b.growthSeed, 2)
    local fact, ctx = level_event.context(sess, b, 1, 2)
    local events = flow.run("progression.level_reached", ctx)
    check(#events == 0, "Project LEVEL_REACHED policy adds no presentation event")
    check(ctx.v.reachedLevel == 2, "ordinary SET_VAR reads event.level from lifecycle context")
    check((b.growth.maxHp or 0) == growthBefore + (expectedGrowth.maxHp or 0),
        "Project LEVEL_REACHED policy applies the exact seeded growth packet")
    check(ctx.v.event.unit.id == "pixie" and ctx.v.event.unit.level == 2,
        "event.unit is a sanitized battler view with stable Unit identity")
    check(fact.level == 2 and fact.previousLevel == 1 and fact.unit == b,
        "resolved LEVEL_REACHED fact retains authoritative Unit identity and crossing values")

    local fctx = formula.makeContext({ v = ctx.v }, sess)
    local visible = formula.eval(
        "event.level == 2 and event.previousLevel == 1 and event.unit.level == event.level",
        fctx)
    check(visible == true, "Formula exposes LEVEL_REACHED as the top-level event.* noun")

    local okJump = pcall(level_event.context, sess, b, 0, 2)
    check(not okJump, "LEVEL_REACHED rejects non-atomic previousLevel/level pairs")
end

do
    -- RESTORE_HP is intentionally not HEAL: it reproduces the old direct
    -- level-up assignment exactly, including silence and leaving states
    -- untouched.
    local sess = sessionModule.GameSession.new(loader)
    local b = sessionModule.Battler.new(loader.getUnit("pixie"), 2, 4242)
    b.hp = 1
    b.states = { "dead" }
    local events = interpreter.runImmediate({
        { cmd = "RESTORE_HP", target = "target" },
    }, { session = sess, loader = loader, target = b, a = b, events = {}, v = {} })
    check(b.hp == b:getMaxHp(sess), "RESTORE_HP sets current HP directly to effective Max HP")
    check(b.states[1] == "dead", "RESTORE_HP does not clear or reinterpret target states")
    check(#events == 0, "RESTORE_HP emits no heal/presentation event")
end

do
    -- The Project transaction Flow owns level-gain recovery. Use a form that
    -- does not transform so this test characterizes recovery policy itself;
    -- transform ordering and replacement recovery are proven separately by
    -- the authored transform tests.
    local sess = sessionModule.GameSession.new(loader)
    local b = sessionModule.Battler.new(loader.getUnit("pixie"), 1, 4242)
    sess.party[1] = b
    b.hp = 1
    local ok, err = pcall(function()
        b:gainExp(progression.nextLevelExp(1), sess)
    end)
    check(ok, "level gain remains executable after authored HP restoration migration: " .. tostring(err))
    check(b.hp == b:getMaxHp(sess),
        "Project LEVEL_GAIN_RESOLVED owns level-gain HP restoration")
end

do
    -- A complete gain transaction is a different semantic fact from an
    -- atomic threshold crossing. The required Flow is behaviorless here,
    -- proving ordinary Formula/Event code can inspect the final span.
    local sess = sessionModule.GameSession.new(loader)
    local b = sess:recruitActor("pixie", 1)
    b.level = 4
    local fact, ctx = level_event.gainResolvedContext(sess, b, 1, 4)
    local events = flow.run("progression.level_gain_resolved", ctx)
    check(#events == 0, "LEVEL_GAIN_RESOLVED default adds no presentation event")
    check(ctx.v.levelsGained == 3,
        "ordinary SET_VAR reads event.levelsGained from transaction context")
    check(fact.previousLevel == 1 and fact.level == 4 and fact.levelsGained == 3,
        "LEVEL_GAIN_RESOLVED retains the whole committed level span")
    local fctx = formula.makeContext({ v = ctx.v }, sess)
    check(formula.eval(
            "event.previousLevel == 1 and event.level == 4 and event.levelsGained == 3",
            fctx) == true,
        "Formula exposes the transaction-complete event.* noun directly")
    check(not pcall(level_event.gainResolvedContext, sess, b, 4, 4),
        "LEVEL_GAIN_RESOLVED rejects a transaction with no level crossing")
end

do
    -- The native transition must not imply seeded growth. Model the pinned
    -- house baseline with a loader whose required progression Flow retains
    -- only the behaviorless context proof: the Unit still reaches level 2,
    -- but its permanent growth record stays untouched.
    local bareLoader = {}
    for k, v in pairs(loader) do bareLoader[k] = v end
    bareLoader.flows = {}
    for k, v in pairs(loader.flows or {}) do bareLoader.flows[k] = v end
    bareLoader.flows.progression = {
        level_reached = {
            { cmd = "SET_VAR", name = "reachedLevel", value = "event.level" },
        },
        level_gain_resolved = {
            { cmd = "SET_VAR", name = "levelsGained", value = "event.levelsGained" },
        },
    }

    local sess = sessionModule.GameSession.new(bareLoader)
    local b = sessionModule.Battler.new(loader.getUnit("pixie"), 1, 4242)
    local before = {}
    for _, p in ipairs(require("engine.growth").PARAMS) do
        before[p] = b.growth[p] or 0
    end

    b:gainExp(progression.nextLevelExp(1), sess)
    local unchanged = true
    for _, p in ipairs(require("engine.growth").PARAMS) do
        if (b.growth[p] or 0) ~= before[p] then unchanged = false end
    end
    check(b.level == 2, "a Project with no seeded growth policy still crosses the authored level threshold")
    check(unchanged, "native gainExp does not apply seeded growth when the resolved level policy omits it")
end

do
    -- Native bookkeeping still owns the transaction. One grant can cross
    -- several authored thresholds and keeps the exact residual EXP. Publication
    -- happens immediately after EACH numeric commit, before the next threshold
    -- is considered.
    local sess = sessionModule.GameSession.new(loader)
    local b = sess:recruitActor("pixie", 1)
    local seen = {}
    local sequence = {}
    local resolvedSeen
    local publish = level_event.publish
    local publishResolved = level_event.publishGainResolved
    level_event.publish = function(s, unit, previousLevel, level)
        table.insert(seen, {
            previousLevel = previousLevel,
            level = level,
            unitLevelAtPublish = unit.level,
        })
        table.insert(sequence, "reached:" .. tostring(level))
        return publish(s, unit, previousLevel, level)
    end
    level_event.publishGainResolved = function(s, unit, previousLevel, level)
        local accumulated = require("engine.growth").accumulate(unit.actorData, unit.growthSeed, level)
        local growthReady = true
        for _, p in ipairs(require("engine.growth").PARAMS) do
            if (unit.growth[p] or 0) ~= (accumulated[p] or 0) then growthReady = false end
        end
        resolvedSeen = {
            previousLevel = previousLevel,
            level = level,
            unitLevelAtPublish = unit.level,
            levelsGained = level - previousLevel,
            growthReady = growthReady,
        }
        table.insert(sequence, "resolved:" .. tostring(previousLevel) .. "-" .. tostring(level))
        return publishResolved(s, unit, previousLevel, level)
    end

    local ok, leveled = pcall(function()
        return b:gainExp(100, sess) -- 15 + 30 + 45 = level 4, 10 residual
    end)
    level_event.publish = publish
    level_event.publishGainResolved = publishResolved

    check(ok and leveled == true, "multi-level gain completes with LEVEL_REACHED publication active")
    check(sess.party[1].level == 4, "gainExp crosses every authored threshold in order")
    check(sess.party[1].exp == 10, "gainExp preserves residual EXP after a multi-level grant")
    check(#seen == 3
        and seen[1].previousLevel == 1 and seen[1].level == 2
        and seen[2].previousLevel == 2 and seen[2].level == 3
        and seen[3].previousLevel == 3 and seen[3].level == 4,
        "LEVEL_REACHED publishes every intermediate level in deterministic order")
    local postCommit = true
    for _, entry in ipairs(seen) do
        if entry.unitLevelAtPublish ~= entry.level then postCommit = false end
    end
    check(postCommit, "each LEVEL_REACHED publication is post-commit")
    check(resolvedSeen
            and resolvedSeen.previousLevel == 1 and resolvedSeen.level == 4
            and resolvedSeen.levelsGained == 3 and resolvedSeen.unitLevelAtPublish == 4,
        "LEVEL_GAIN_RESOLVED publishes exactly the final committed transaction span")
    check(resolvedSeen and resolvedSeen.growthReady,
        "transaction-complete publication occurs after every per-level growth packet")
    check(#sequence == 4
            and sequence[1] == "reached:2"
            and sequence[2] == "reached:3"
            and sequence[3] == "reached:4"
            and sequence[4] == "resolved:1-4",
        "transaction-complete publication follows all atomic LEVEL_REACHED programs")
    check(sessionModule.expCurveCost(1, 4) == 90,
        "economy training value and native level crossing share one curve authority")
end

do
    -- The base case: one creature crosses a threshold and the report is a
    -- before/after of what the player can see on the status screen.
    local sess = sessionModule.GameSession.new(loader)
    local b = sess:recruitActor("pixie", 1)
    local before = progress.snapshot(sess)
    local hpBefore = traits.getParam(b, "maxHp", sess)
    b:gainExp(1000, sess)
    local entries = progress.levelUps(sess, before)

    check(#entries == 1, "a creature that levelled produces exactly one entry")
    local e = entries[1]
    check(e and e.fromLevel == 1 and e.toLevel == sess.party[1].level,
        "the entry spans the whole grant, not one level of it")
    check(e and e.portraitKey ~= "", "the entry carries a portrait key")
    check(e and e.expNeeded == progression.nextLevelExp(e.toLevel),
        "the published next threshold comes from the authored progression authority")
    local hp = e and rowFor(e, "maxHp")
    check(hp and hp.from == hpBefore and hp.to == traits.getParam(sess.party[1], "maxHp", sess),
        "HP is reported from the same accessor the status screen reads")
    check(hp and hp.delta == hp.to - hp.from and hp.deltaText == "+" .. hp.delta,
        "the delta is derived, and pre-signed for the window's format string")
end

do
    -- No level, no event. Keep gainExp's existing return contract unchanged and
    -- observe the lifecycle publisher directly instead of adding a new return.
    local sess = sessionModule.GameSession.new(loader)
    local b = sess:recruitActor("pixie", 1)
    local before = progress.snapshot(sess)
    local publishCount, resolvedCount = 0, 0
    local publish = level_event.publish
    local publishResolved = level_event.publishGainResolved
    level_event.publish = function(...)
        publishCount = publishCount + 1
        return publish(...)
    end
    level_event.publishGainResolved = function(...)
        resolvedCount = resolvedCount + 1
        return publishResolved(...)
    end
    b:gainExp(1, sess)
    level_event.publish = publish
    level_event.publishGainResolved = publishResolved
    check(publishCount == 0, "sub-threshold EXP publishes no LEVEL_REACHED fact")
    check(resolvedCount == 0, "sub-threshold EXP publishes no LEVEL_GAIN_RESOLVED fact")
    check(#progress.levelUps(sess, before) == 0, "a sub-threshold grant reports nothing")
end

do
    -- A stat that sat this level out prints nothing rather than "+0" -- every
    -- growing parameter still gets a row, so the table doesn't reflow.
    local sess = sessionModule.GameSession.new(loader)
    local b = sess:recruitActor("pixie", 1)
    local before = progress.snapshot(sess)
    b:gainExp(1000, sess)
    local e = progress.levelUps(sess, before)[1]
    check(e and #e.rows == 5, "every growing parameter gets a row")
    local ok = true
    for _, r in ipairs(e.rows) do
        if r.delta == 0 and r.deltaText ~= "" then ok = false end
    end
    check(ok, "an unchanged stat shows no delta text")
end

do
    -- Slot-keyed, not identity-keyed: an Egg levelling to 10 hatches, which
    -- REPLACES the object in the party slot. An identity-keyed diff would lose
    -- exactly the creature whose report matters most.
    local sess = sessionModule.GameSession.new(loader)
    local egg = sess:recruitActor("egg", 9)
    local wasId = egg.actorData.id
    local before = progress.snapshot(sess)
    egg:gainExp(1000, sess)
    local entries = progress.levelUps(sess, before)
    check(sess.party[1].actorData.id ~= wasId, "the Egg hatched into another actor")
    check(#entries == 1, "a level-up that transforms the creature still reports once")
    check(entries[1] and entries[1].noteText ~= "", "and says what it became")
end

do
    -- publish() is the seam the data-authored window reads. Index 0 (nobody
    -- levelled) must leave the vars empty rather than nil-erroring a format.
    local v = {}
    progress.publish(v, {}, 0)
    check(v.levelUpName == "" and #v.levelUpRows == 0, "publishing nothing clears the vars")

    local entries = {
        { name = "A", portraitKey = "a", fromLevel = 1, toLevel = 2, exp = 3,
          expNeeded = 30, rows = {}, noteText = "" },
        { name = "B", portraitKey = "b", fromLevel = 4, toLevel = 5, exp = 6,
          expNeeded = 75, rows = {}, noteText = "" },
    }
    progress.publish(v, entries, 2)
    check(v.levelUpName == "B" and v.levelUpToLevel == 5, "publishing selects by index")
    check(v.levelUpCounter == "2/2", "and shows a position while there is more than one")
    progress.publish(v, { entries[1] }, 1)
    check(v.levelUpCounter == "", "a lone level-up needs no position indicator")
end

print(("=== Progress Tests: %d passed, %d failed ==="):format(passed, failed))
if failed > 0 then require("tests.fail_fast")("progress tests failed", failed) end