local loader = require("data.loader")
local sessionModule = require("engine.session")
local exploration = require("engine.exploration")
local event_self_state = require("engine.event_self_state")
local state_value = require("engine.state_value")
local interpreter = require("engine.interpreter")
local savegame = require("engine.savegame")
local json = require("data.json")
local failFast = require("tests.fail_fast")

local passed, failed = 0, 0
local function check(condition, message)
    if condition then
        passed = passed + 1
        print("  [PASS] " .. message)
    else
        failed = failed + 1
        print("  [FAIL] " .. message)
    end
end

local function errors(fn)
    local ok = pcall(fn)
    return not ok
end

local function newMapSession(mapIndex)
    local s = sessionModule.GameSession.new(loader)
    s:initializeStartingParty()
    exploration.loadMap(s, mapIndex or 1)
    return s
end

local function eventByNumericId(s, id)
    for _, event in ipairs((s.currentMapData and s.currentMapData.events) or {}) do
        if event.id == id then return event end
    end
    return nil
end

local parityFixture = json.decode(assert(love.filesystem.read("tests/fixtures/event_self_state_authoring.json")))

print("[TEST] Starting persistent Map Event SELF state tests...")

-- A/B isolation uses two real authored placements on one Map. Numeric ids are
-- deliberately irrelevant to storage after owner resolution.
do
    local s = newMapSession(1)
    local a, b = eventByNumericId(s, 1), eventByNumericId(s, 2)
    check(a and a.instanceId and b and b.instanceId and a.instanceId ~= b.instanceId,
        "authored placed Events carry distinct stable instanceId values")
    event_self_state.writeSwitch(s, a, "A", true)
    event_self_state.writeVariable(s, a, "phase", 3)
    check(event_self_state.readSwitch(s, a, "A") == true
            and event_self_state.readSwitch(s, b, "A") == false,
        "Event A Self Switch does not affect Event B")
    check(event_self_state.readVariable(s, a, "phase") == 3
            and event_self_state.readVariable(s, b, "phase") == nil,
        "Event A Self Variable does not affect Event B")
end

-- Reusable Common Event/template behavior runs against the placed owner, not
-- against the shared behavior definition.
do
    local s = newMapSession(1)
    local a, b = eventByNumericId(s, 1), eventByNumericId(s, 2)
    a.scriptId, b.scriptId = 999, 999
    local sharedBehavior = {
        { cmd = "SET_SELF_SWITCH", name = "shared_behavior_ran", value = true },
        { cmd = "SET_SELF_VARIABLE", name = "counter", operation = "set", value = 7 },
    }
    interpreter.runImmediate(sharedBehavior, { session = s, loader = loader, event = a })
    check(event_self_state.readSwitch(s, a, "shared_behavior_ran") == true
            and event_self_state.readSwitch(s, b, "shared_behavior_ran") == false,
        "two placements sharing one reusable behavior keep independent Self Switch state")
    check(event_self_state.readVariable(s, a, "counter") == 7
            and event_self_state.readVariable(s, b, "counter") == nil,
        "two placements sharing one reusable behavior keep independent Self Variable state")
end

-- Interpreter operations read the same SELF view Formula exposes and numeric
-- change operations remain strict/deterministic.
do
    local s = newMapSession(1)
    local event = eventByNumericId(s, 1)
    interpreter.runImmediate({
        { cmd = "SET_SELF_VARIABLE", name = "phase", operation = "set", value = 2 },
        { cmd = "SET_SELF_VARIABLE", name = "phase", operation = "add", value = 3 },
        { cmd = "SET_SELF_VARIABLE", name = "mirror", operation = "set", value = "self.variables.phase + 1" },
        { cmd = "SET_SELF_VARIABLE", name = "structured", operation = "set",
          value = "{ count = self.variables.phase, tags = { 'a', 'b' } }" },
        { cmd = "SET_SELF_SWITCH", name = "done", value = true },
    }, { session = s, loader = loader, event = event })
    check(event_self_state.readVariable(s, event, "phase") == 5,
        "Control SELF Variable set/change uses deterministic numeric operations")
    check(event_self_state.readVariable(s, event, "mirror") == 6,
        "SELF Variable is readable from the formula context")
    local structured = event_self_state.readVariable(s, event, "structured")
    check(structured and structured.count == 5 and structured.tags[2] == "b",
        "Control SELF Variable authors structured values through the shared stateValue evaluator")
    check(event_self_state.readSwitch(s, event, "done") == true,
        "Control SELF Switch mutates persistent SELF gameplay state")
end

-- One shared fixture is consumed by both Studio's serializer test and runtime,
-- so editor/runtime parity is contractual rather than inferred from duplicate literals.
do
    local s = newMapSession(1)
    local event = eventByNumericId(s, 1)
    interpreter.runImmediate(parityFixture.commands, { session = s, loader = loader, event = event })
    check(event_self_state.readSwitch(s, event, "open") == true
            and event_self_state.readVariable(s, event, "phase") == 2,
        "shared authoring fixture executes with the same SELF command semantics at runtime")
end

-- Structured Page conditions re-evaluate against current persistent state on
-- every resolvePage call; no page cache or presentation state participates.
do
    local s = newMapSession(1)
    local event = {
        id = 777,
        instanceId = "event:test-page-reevaluation",
        name = "Page Test",
        sprite = "base.png",
        trigger = "interact",
        pages = {
            {
                selfConditions = parityFixture.pageSelfConditions,
                sprite = "active.png",
                trigger = "bump",
            },
        },
    }
    local before = exploration.resolvePage(event, s)
    event_self_state.writeSwitch(s, event, "open", true)
    local switchOnly = exploration.resolvePage(event, s)
    event_self_state.writeVariable(s, event, "phase", 2)
    local active = exploration.resolvePage(event, s)
    event_self_state.writeVariable(s, event, "phase", 1)
    local inactiveAgain = exploration.resolvePage(event, s)
    check(before.sprite == "base.png" and switchOnly.sprite == "base.png"
            and active.sprite == "active.png" and active.trigger == "bump"
            and inactiveAgain.sprite == "base.png",
        "Page SELF conditions deterministically change the active Page after each mutation")
end

-- Save/load round trip includes both boolean and non-boolean SELF values and
-- retains string authored identity keys rather than numeric-key restoration.
do
    local s = newMapSession(1)
    local event = eventByNumericId(s, 1)
    event_self_state.writeSwitch(s, event, "saved", true)
    event_self_state.writeVariable(s, event, "greeting", "persistent string")
    event_self_state.writeVariable(s, event, "record", { count = 2, tags = { "a", "b" } })

    local encoded = json.encode(savegame.serialize(s, loader, "map"))
    local decoded = json.decode(encoded)
    local restored = savegame.deserialize(decoded, loader)
    local restoredEvent = nil
    for _, candidate in ipairs(restored.currentMapData.events or {}) do
        if candidate.instanceId == event.instanceId then restoredEvent = candidate break end
    end
    local record = restoredEvent and event_self_state.readVariable(restored, restoredEvent, "record")
    check(restoredEvent ~= nil and event_self_state.readSwitch(restored, restoredEvent, "saved") == true,
        "save/load preserves Self Switch state")
    check(restoredEvent ~= nil
            and event_self_state.readVariable(restored, restoredEvent, "greeting") == "persistent string"
            and record and record.count == 2 and record.tags[2] == "b",
        "save/load preserves non-boolean typed Self Variable state")
end

-- Identity migration/fail-safe rule: reusing a numeric editor slot cannot claim
-- state from the deleted placement. No content/coordinate heuristic is used.
do
    local s = newMapSession(1)
    local oldEvent = { id = 55, instanceId = "event:deleted-placement", x = 4, y = 4 }
    local recreated = { id = 55, instanceId = "event:new-placement", x = 4, y = 4 }
    event_self_state.writeSwitch(s, oldEvent, "opened", true)
    event_self_state.writeVariable(s, oldEvent, "loot", "claimed")
    check(event_self_state.readSwitch(s, recreated, "opened") == false
            and event_self_state.readVariable(s, recreated, "loot") == nil,
        "deleted/recreated Event reusing numeric id and coordinates cannot inherit old SELF state")
    check(errors(function()
        event_self_state.writeSwitch(s, { id = 55, x = 4, y = 4 }, "opened", true)
    end), "Event without stable authored instanceId fails SELF access instead of falling back to numeric id")
end

-- Explicit cross-Event access is possible, but only through the complete stable
-- Map/Event identity pair. Ordinary SELF remains current-owner-only.
do
    local s = newMapSession(1)
    local a, b = eventByNumericId(s, 1), eventByNumericId(s, 2)
    event_self_state.writeSwitch(s, a, "remote", true, {
        mapId = s.currentMapData.id,
        eventInstanceId = b.instanceId,
        loader = loader,
    })
    check(event_self_state.readSwitch(s, b, "remote") == true
            and event_self_state.readSwitch(s, a, "remote") == false,
        "deliberate cross-Event access requires and honors stable Map/Event identity")
    check(errors(function()
        event_self_state.writeSwitch(s, a, "bad", true, { mapId = s.currentMapData.id, loader = loader })
    end), "partial cross-Event target is rejected")
    check(errors(function()
        event_self_state.writeSwitch(s, a, "bad", true, {
            mapId = s.currentMapData.id, eventInstanceId = "event:does-not-exist", loader = loader,
        })
    end), "unknown cross-Event stable identity is rejected")
end

-- #407 value contract: scalars, records and dense lists are by-value; live or
-- non-deterministic Lua object graphs never enter persistent state.
do
    local s = newMapSession(1)
    local event = eventByNumericId(s, 1)
    local original = { nested = { 1, 2, 3 } }
    event_self_state.writeVariable(s, event, "copy", original)
    original.nested[1] = 99
    local stored = event_self_state.readVariable(s, event, "copy")
    stored.nested[2] = 88
    local reread = event_self_state.readVariable(s, event, "copy")
    check(reread.nested[1] == 1 and reread.nested[2] == 2,
        "Self Variables use by-value copy semantics on write and read")

    local cyclic = {}; cyclic.self = cyclic
    local shared = {}; local aliased = { a = shared, b = shared }
    local cases = {
        function() event_self_state.writeVariable(s, event, "bad", function() end) end,
        function() event_self_state.writeVariable(s, event, "bad", 0 / 0) end,
        function() event_self_state.writeVariable(s, event, "bad", math.huge) end,
        function() event_self_state.writeVariable(s, event, "bad", setmetatable({}, {})) end,
        function() event_self_state.writeVariable(s, event, "bad", cyclic) end,
        function() event_self_state.writeVariable(s, event, "bad", aliased) end,
        function() state_value.copy({ [1] = "a", [3] = "hole" }, "sparse") end,
    }
    local rejected = true
    for _, case in ipairs(cases) do rejected = rejected and errors(case) end
    check(rejected, "malformed/unserializable values fail under shared typed authored-state semantics")

    check(errors(function()
        interpreter.runImmediate({
            { cmd = "SET_SELF_SWITCH", name = "bad_switch", value = "true" },
        }, { session = s, loader = loader, event = event })
    end), "malformed Self Switch values fail instead of coercing to boolean")
    check(errors(function()
        event_self_state.validatePageConditions({
            variable = { name = "phase", operator = ">=", value = "2" },
        })
    end), "relational Self Variable Page conditions require finite numeric authored values")
    check(errors(function()
        event_self_state.validatePageConditions({
            variable = { name = "phase", operator = "==", op = "!=", value = 2 },
        })
    end), "SELF Page conditions reject undeclared compatibility aliases")
    check(errors(function()
        event_self_state.validatePageConditions({
            variable = { name = "phase", operator = "==" },
        })
    end), "SELF Page equality requires an explicit value instead of overloading absence")
    local validStore = s.eventSelfState
    s.eventSelfState = {
        [tostring(s.currentMapData.id)] = {
            [event.instanceId] = { switches = { bad = "true" }, variables = {} },
        },
    }
    check(errors(function()
        savegame.serialize(s, loader, "map")
    end), "malformed saved Self Switch values fail the save serialization boundary")
    s.eventSelfState = validStore
end

-- Compatibility: no SELF condition means no stable identity is consulted. Old
-- Projects/Events remain behavior-identical until they actually author SELF.
do
    local s = newMapSession(1)
    local legacy = {
        id = 12,
        name = "Legacy Event",
        sprite = "base.png",
        pages = { { condition = "1 == 1", sprite = "legacy-page.png" } },
    }
    local effective = exploration.resolvePage(legacy, s)
    check(effective.sprite == "legacy-page.png",
        "existing Event with no SELF state behaves identically without instanceId")
end

failFast("event_self_state", failed, passed)
