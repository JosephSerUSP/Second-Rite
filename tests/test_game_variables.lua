-- #407 persistent Game Variable / Switch owner semantics.
local loader = require("data.loader")
local session = require("engine.session")
local variables = require("engine.game_variables")

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

print(("=== Game Variable Tests: %d passed, %d failed ==="):format(passed, failed))
if failed > 0 then require("tests.fail_fast")("game variable tests failed", failed) end
