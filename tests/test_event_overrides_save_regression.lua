-- Regression test for issue #429:
-- session.eventOverrides silently reverts after save/load because numeric keys
-- become strings through JSON object encoding/decoding.
local loader = require("engine.data.loader")
local session = require("engine.session")
local interpreter = require("engine.interpreter")
local exploration = require("engine.exploration")
local savegame = require("engine.savegame")
local gameVariables = require("engine.game_variables")
local json = require("engine.data.json")

local function assertEq(actual, expected, message)
    if actual ~= expected then
        error((message or "values differ") .. ": expected " .. tostring(expected)
            .. ", got " .. tostring(actual))
    end
end

local function assertTrue(val, message)
    if not val then
        error((message or "assertion failed") .. ": expected truthy value, got " .. tostring(val))
    end
end

print("[TEST] Starting eventOverrides save/load regression tests...")

-- 1. Check fresh session initialization
local s = session.GameSession.new(loader)
assertTrue(type(s.eventOverrides) == "table", "fresh session initializes eventOverrides table")
assertEq(next(s.eventOverrides), nil, "fresh session eventOverrides is empty")

-- 2. Authored Map 1 check (Alicia, event 7)
s:initializeStartingParty()
exploration.loadMap(s, 1)
local aliciaEv = nil
for _, ev in ipairs(s.currentMapData.events) do
    if ev.id == 7 then aliciaEv = ev break end
end
assertTrue(aliciaEv ~= nil, "found Alicia event (id 7) on Map 1")
assertEq(aliciaEv.label, "Pink-haired girl", "Alicia's authored label is 'Pink-haired girl'")
assertEq(aliciaEv.name, "Alicia", "Alicia's authored name is 'Alicia'")

local effectiveBefore = exploration.resolvePage(aliciaEv, s)
assertEq(effectiveBefore.label, "Pink-haired girl", "effective label before override is authored value")

-- 3. Execute CHANGE_EVENT_PROPERTIES on Alicia (persistent = true) on Map 1
local ctx = { session = s, loader = loader, party = s.party, events = {}, v = {} }
interpreter.runImmediate({
    {
        cmd = "CHANGE_EVENT_PROPERTIES",
        eventId = 7,
        label = "Alicia",
        name = "Alicia (Shopkeeper)",
        persistent = true,
    }
}, ctx)

assertEq(s.eventOverrides[1][7].label, "Alicia", "in-memory eventOverrides label set")
assertEq(s.eventOverrides[1][7].name, "Alicia (Shopkeeper)", "in-memory eventOverrides name set")

local effectiveAfter = exploration.resolvePage(aliciaEv, s)
assertEq(effectiveAfter.label, "Alicia", "effective label reflects override before saving")
assertEq(effectiveAfter.name, "Alicia (Shopkeeper)", "effective name reflects override before saving")

-- 4. Set an override on another map (Map 2, event 3) to test sparse outer map index
s.eventOverrides[2] = s.eventOverrides[2] or {}
s.eventOverrides[2][3] = { label = "Guarded Passage", name = "Old Sentry" }

-- 5. Also set an override on a string-keyed event (e.g. Map 13 'shrine')
s.eventOverrides[13] = s.eventOverrides[13] or {}
s.eventOverrides[13]["shrine"] = { label = "Ancient Altar" }

-- 6. Unlock a lore entry to verify lore round-trip & string-keyed construction
interpreter.runImmediate({ { cmd = "UNLOCK_LORE", loreId = "old_gate" } }, ctx)
assertEq(s.unlockedLore["old_gate"], true, "lore unlocked")

-- #407: Game Variables are independent persistent playthrough state. Include
-- booleans, scalars and a structured value so the real JSON save boundary
-- proves typed copy/value semantics rather than only the in-memory owner API.
gameVariables.setSwitch(s, "labyrinth.permission", true)
gameVariables.set(s, "visits", 4)
gameVariables.set(s, "journal", { chapter = "gate", marks = { "north", "red" } })

-- 7. Serialize to JSON and parse back
local serialized = savegame.serialize(s, loader, "town")
local jsonText = json.encode(serialized)
local decoded = json.decode(jsonText)

-- Verify that raw JSON decoding produced string keys for sparse tables
-- For map 1 event 7: event 7 is sparse in map 1's event map
local ev1 = decoded.eventOverrides[1] or decoded.eventOverrides["1"]
assertTrue(ev1 ~= nil, "map 1 overrides exist in decoded JSON")
assertTrue(ev1["7"] ~= nil and ev1[7] == nil, "event 7 key decoded as string '7' in JSON")

-- For map 2: map 2 is sparse when maps 3..12 are absent
local ev2 = decoded.eventOverrides["2"] or decoded.eventOverrides[2]
assertTrue(ev2 ~= nil, "map 2 overrides exist in decoded JSON")
assertTrue((ev2["3"] ~= nil and ev2[3] == nil) or (ev2[3] ~= nil), "event 3 present in map 2 overrides")
assertTrue(decoded.gameVariables ~= nil, "#407 save payload owns gameVariables explicitly")

-- 8. Deserialize back into GameSession
local restored = savegame.deserialize(decoded, loader)

-- Verify restored numeric keys in eventOverrides for Map 1 (Alicia)
assertTrue(restored.eventOverrides[1] ~= nil, "savegame.deserialize restored numeric outer key 1")
assertTrue(restored.eventOverrides[1][7] ~= nil, "savegame.deserialize restored numeric inner key 7")
assertEq(restored.eventOverrides[1][7].label, "Alicia", "restored eventOverrides label matches")
assertEq(restored.eventOverrides[1][7].name, "Alicia (Shopkeeper)", "restored eventOverrides name matches")

-- Verify restored numeric keys in eventOverrides for Map 2
assertTrue(restored.eventOverrides[2] ~= nil, "savegame.deserialize restored numeric outer key 2")
assertTrue(restored.eventOverrides[2][3] ~= nil, "savegame.deserialize restored numeric inner key 3")
assertEq(restored.eventOverrides[2][3].label, "Guarded Passage", "restored map 2 override label matches")
assertEq(restored.eventOverrides[2][3].name, "Old Sentry", "restored map 2 override name matches")

-- Verify string-keyed event override was preserved
assertTrue(restored.eventOverrides[13] ~= nil, "savegame.deserialize restored numeric outer key 13")
assertTrue(restored.eventOverrides[13]["shrine"] ~= nil, "savegame.deserialize preserved string event key 'shrine'")
assertEq(restored.eventOverrides[13]["shrine"].label, "Ancient Altar", "restored shrine override label matches")

-- 9. Verify resolvePage on restored session
local effectiveRestored = exploration.resolvePage(aliciaEv, restored)
assertEq(effectiveRestored.label, "Alicia", "restored effective label matches override")
assertEq(effectiveRestored.name, "Alicia (Shopkeeper)", "restored effective name matches override")

-- 10. Verify unlockedLore round-trip with string keys
assertEq(restored.unlockedLore["old_gate"], true, "restored unlockedLore preserves string key 'old_gate'")

-- 11. #407 Game Variables survive the same save/load path and remain typed.
assertEq(gameVariables.getSwitch(restored, "labyrinth.permission"), true,
    "restored boolean Variable survives as Switch")
assertEq(gameVariables.get(restored, "visits"), 4, "restored number Variable survives")
local journal = gameVariables.get(restored, "journal")
assertEq(journal.chapter, "gate", "restored record Variable survives")
assertEq(journal.marks[2], "red", "restored dense-list child survives")
journal.marks[1] = "mutated after load"
assertEq(gameVariables.get(restored, "journal").marks[1], "north",
    "restored Variable reads still copy by value")

print("  [PASS] eventOverrides numeric and string keys survive save/load round-trip")
print("  [PASS] resolvePage reflects restored eventOverrides")
print("  [PASS] unlockedLore string keys preserved")
print("  [PASS] #407 Game Variables survive save/load with typed value semantics")

-- Event actor runtime is the transient counterpart to these persistent Event
-- overrides, so its focused suite is chained here rather than from an unrelated
-- UI/battle suite. The suite-registration guard follows registered requires.
require("tests.test_event_actor")
-- #407 value/store suites are chained through this already-registered save
-- regression suite so `lovec . unittest` proves them without growing the
-- main.lua suite list/upvalue-sensitive CLI surface.
require("tests.test_state_value")
require("tests.test_game_variables")
-- #631 replaces JSON grammar mechanics beneath this same persistence boundary.
-- Keep its conformance suite chained here so the standard unit path proves the
-- parser/encoder swap cannot silently change save projection semantics.
require("tests.test_json_codec")

print("=== eventOverrides save regression: all checks passed ===")
