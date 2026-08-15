-- Developer mode is a property of the launch, not of a session, so it must
-- survive every path that builds a new session. The one that used to lose it
-- was LOAD_GAME: RESET_SESSION carried the flag by hand and loading did not,
-- so a developer who loaded a save was silently returned to ordinary mode.
package.path = package.path .. ";./?.lua;./engine/?.lua"

local loader = require("data.loader")
local sessionModule = require("engine.session")
local savegame = require("engine.savegame")
local formula = require("engine.formula")
local interpreter = require("engine.interpreter")

print("[TEST] Starting developer mode tests...")

local passed, failed = 0, 0
local function check(cond, msg)
    if cond then passed = passed + 1 print("  [PASS] " .. msg)
    else failed = failed + 1 print("  [FAIL] " .. msg) end
end

loader.init()

local launchFlag = sessionModule.developerMode

-- Ordinary launch: constructing the runtime container is not New Game. Title
-- and Options need a session for command/formula plumbing, but no player party
-- and no protagonist Battler should exist before RESET_SESSION or LOAD_GAME.
sessionModule.developerMode = false
local plain = sessionModule.GameSession.new(loader)
check(plain.developerMode == false, "an ordinary launch builds ordinary sessions")
check(formula.sessionView(plain).developerMode == false,
    "and data reads it as false, not nil")
check(next(plain.party) == nil, "a freshly constructed pre-run session has no party")
check(plain.summoner == nil, "the protagonist is not represented as a Summoner Battler")
check(loader.getUnit("summoner") == nil, "the legacy Summoner Unit is absent from the live registry")
check(plain.shopProgression == 1, "Shop Progression starts at the Project-authored initial value")

-- Developer launch: the flag reaches sessions built afterwards, including the
-- one a save round-trip reconstructs.
sessionModule.developerMode = true
local dev = sessionModule.GameSession.new(loader)
dev:initializeStartingParty()
check(dev.developerMode == true, "a developer launch builds developer sessions")
check(formula.sessionView(dev).developerMode == true, "and data can read it")
check(dev.party[1] ~= nil, "explicit New Game population still creates the starting party")
dev.shopProgression = 5

local data = savegame.serialize(dev, loader, "map")
local restored = savegame.deserialize(data, loader)
check(restored.developerMode == true, "a loaded save is still a developer session")
check(restored.shopProgression == 5, "Shop Progression survives save/load")
check(restored.summoner == nil, "save/load does not recreate a Summoner Battler")

-- The flag describes the launch, so it must not be written into the save --
-- an ordinary launch loading a developer's save is an ordinary session.
sessionModule.developerMode = false
local afterPlainLaunch = savegame.deserialize(data, loader)
check(afterPlainLaunch.developerMode == false,
    "and an ordinary launch loading that same save is not")

-- The title's Developer Room command is intentionally available in an
-- ordinary launch. Its RESET_SESSION override makes that one fresh session a
-- real developer session, without changing the launch-wide default. It is also
-- the explicit New Game boundary, so the starting party appears here rather
-- than when the title screen boots.
local resetCtx = { session = afterPlainLaunch, loader = loader, events = {} }
interpreter.runImmediate({ { cmd = "RESET_SESSION", developerMode = "true" } }, resetCtx)
check(resetCtx.session.developerMode == true,
    "RESET_SESSION can explicitly create a developer-room session")
check(resetCtx.session.party[1] ~= nil,
    "RESET_SESSION populates the starting party at the New Game boundary")
check(resetCtx.session.summoner == nil,
    "RESET_SESSION still creates no Summoner Battler")
check(sessionModule.developerMode == false,
    "the developer-room override does not change the launch default")

-- Developer Menu "ADD EVERY ITEM" works for ordinary player sessions
local ordinaryCtx = { session = plain, loader = loader, events = {} }
interpreter.runImmediate({ { cmd = "SCRIPT", code = "api.giveAllItems()" } }, ordinaryCtx)
local allGiven = true
local count = 0
for _, item in ipairs(loader.items) do
    count = count + 1
    if (plain.inventory[item.id] or 0) < 99 then
        allGiven = false
    end
end
check(count > 0 and allGiven == true, "giveAllItems populates full stacks of all authored items in ordinary sessions")

-- Also test end-to-end developer_menu scene on_select hook with idx = 10
local sceneDef = loader.getScene("developer_menu")
local sceneCtx = {
    session = afterPlainLaunch,
    loader = loader,
    v = { idx = 10, _guard = 0 },
    events = {},
    scene = sceneDef,
}
interpreter.runImmediate(sceneDef.hooks.on_select, sceneCtx)
local sceneGaveAll = true
for _, item in ipairs(loader.items) do
    if (afterPlainLaunch.inventory[item.id] or 0) < 99 then
        sceneGaveAll = false
    end
end
check(sceneGaveAll == true, "developer_menu on_select hook with idx 10 grants full item stacks")

sessionModule.developerMode = launchFlag

print(string.format("=== Developer Mode Tests: %d passed, %d failed ===", passed, failed))
if failed > 0 then require("tests.fail_fast")(failed .. " developer mode test(s) failed", failed) end
