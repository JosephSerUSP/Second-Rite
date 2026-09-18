-- #407 persistent Game Variable / Switch owner semantics.
local loader = require("engine.data.loader")
local session = require("engine.session")
local variables = require("engine.game_variables")
local formula = require("engine.formula")
local interpreter = require("engine.interpreter")

local passed, failed = 0, 0
local function check(ok, message)
    if ok then
        passed = passed + 1
    else
        failed = failed + 1
        print("  FAIL: " .. message)
    end
end

local s = session.GameSession.new(loader)
check(type(s.gameVariables) == "table" and next(s.gameVariables) == nil,
    "fresh GameSession initializes one empty persistent Variable owner")
check(not variables.has(s, "labyrinth.permission"), "fresh Variable is unset")
check(variables.get(s, "labyrinth.permission") == nil, "unset Variable reads nil")

variables.set(s, "labyrinth.permission", true)
check(variables.getSwitch(s, "labyrinth.permission"), "boolean Variable reads through Switch affordance")
variables.setSwitch(s, "gate.open", false)
check(variables.has(s, "gate.open") and variables.get(s, "gate.open") == false,
    "OFF is a stored boolean value, distinct from unset")

variables.set(s, "visits", 3)
variables.set(s, "title", "Thestra")
check(variables.get(s, "visits") == 3 and variables.get(s, "title") == "Thestra",
    "number/string Variables round-trip through owner")

local authored = { flags = { "a", "b" }, nested = { count = 2 } }
variables.set(s, "record", authored)
authored.flags[1] = "mutated"
local read1 = variables.get(s, "record")
check(read1.flags[1] == "a", "write boundary copies structured values")
read1.nested.count = 999
check(variables.get(s, "record").nested.count == 2, "read boundary returns a copy")

local fctx = formula.makeContext({}, s)
local formulaCount, formulaErr = formula.eval("variables.record.nested.count", fctx)
check(formulaErr == nil and formulaCount == 2, "Formula reads structured persistent Variables")
local formulaSwitch, switchErr = formula.eval('variables["labyrinth.permission"]', fctx)
check(switchErr == nil and formulaSwitch == true,
    "Formula can read named Switch/Variable keys that contain punctuation")
fctx.variables.record.nested.count = 777
check(variables.get(s, "record").nested.count == 2,
    "Formula context owns a read-only-by-copy Variable snapshot")

local snapshot = variables.snapshot(s)
snapshot.record.nested.count = 1000
check(variables.get(s, "record").nested.count == 2, "snapshot cannot mutate live store")

variables.unset(s, "visits")
check(not variables.has(s, "visits") and variables.get(s, "visits") == nil,
    "unset removes Variable")

local okSwitch = pcall(variables.setSwitch, s, "bad", 1)
check(not okSwitch, "Switch authoring rejects non-boolean values")
local cyclic = {}; cyclic.self = cyclic
local okCycle = pcall(variables.set, s, "badCycle", cyclic)
check(not okCycle and not variables.has(s, "badCycle"), "invalid value never enters persistent store")

local restored = session.GameSession.new(loader)
variables.restore(restored, variables.snapshot(s))
check(variables.get(restored, "record").nested.count == 2 and variables.getSwitch(restored, "labyrinth.permission"),
    "snapshot restore reproduces values by copy")

-- Event Programs own the write seam. These are deliberately separate from
-- SET_VAR (flow-local v) and SET_FLAG (legacy flag semantics).
local eventCtx = { session = restored, loader = loader, party = restored.party, events = {}, v = {} }
interpreter.runImmediate({
    { cmd = "SET_GAME_VARIABLE", name = "visits", value = "variables.record.nested.count + 3" },
    { cmd = "SET_GAME_VARIABLE", name = "journal", value = '{ chapter = "second", marks = { "east", "blue" } }' },
    { cmd = "SET_GAME_SWITCH", name = "gate.open", value = true },
}, eventCtx)
check(variables.get(restored, "visits") == 5,
    "SET_GAME_VARIABLE evaluates against persistent Formula context")
local journal = variables.get(restored, "journal")
check(journal.chapter == "second" and journal.marks[2] == "blue",
    "stateValue command expressions can author deterministic records/lists")
check(variables.getSwitch(restored, "gate.open"),
    "SET_GAME_SWITCH authors the boolean affordance through the same store")
interpreter.runImmediate({ { cmd = "UNSET_GAME_VARIABLE", name = "visits" } }, eventCtx)
check(not variables.has(restored, "visits"),
    "UNSET_GAME_VARIABLE removes persistent state explicitly")



-- #410 owner-explicit transient state substrate. Local scratch and Scene state
-- are distinct Formula nouns; SET_SCENE_STATE must never silently fall back to
-- whichever table an arbitrary immediate host happened to provide.
local transientCtx = { session = restored, loader = loader, party = restored.party, events = {} }
interpreter.runImmediate({
    { cmd = "SET_LOCAL", assignments = {
        { name = "roll", value = 2 },
        { name = "scaled", value = "locals.roll + 3" },
    } },
}, transientCtx)
check(transientCtx.locals.roll == 2 and transientCtx.locals.scaled == 5,
    "SET_LOCAL owns in-order invocation scratch under locals")
check(transientCtx.v == transientCtx.locals,
    "legacy v aliases locals for non-Scene immediate callers during migration")

local sceneState = {}
local sceneCtx = {
    session = restored, loader = loader, party = restored.party, events = {},
    sceneState = sceneState, locals = {}, v = sceneState,
}
interpreter.runImmediate({
    { cmd = "SET_SCENE_STATE", assignments = {
        { name = "cursor", value = 1 },
        { name = "nextCursor", value = "sceneState.cursor + 1" },
    } },
    { cmd = "SET_LOCAL", name = "guard", value = 1 },
}, sceneCtx)
check(sceneState.cursor == 1 and sceneState.nextCursor == 2,
    "SET_SCENE_STATE mutates the Scene owner and supports in-order reads")
check(sceneCtx.locals.guard == 1 and sceneState.guard == nil,
    "Scene invocation locals do not leak into Scene state")
local noSceneOk = pcall(interpreter.runImmediate,
    { { cmd = "SET_SCENE_STATE", name = "bad", value = 1 } },
    { session = restored, loader = loader, events = {} })
check(not noSceneOk, "SET_SCENE_STATE fails loud without a Scene owner")

local ownerCtx = formula.makeContext({
    locals = { scratch = 4 },
    sceneState = { cursor = 2 },
}, restored)
local ownerValue, ownerErr = formula.eval("locals.scratch + sceneState.cursor", ownerCtx)
check(ownerErr == nil and ownerValue == 6,
    "Formula exposes locals and sceneState as distinct owner nouns")

print(("=== Game Variable Tests: %d passed, %d failed ==="):format(passed, failed))
if failed > 0 then require("tests.fail_fast")("game variable tests failed", failed) end
