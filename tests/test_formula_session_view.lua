-- Regression coverage for #453: formula.sessionView must receive inventory
-- tab context explicitly through formula.makeContext, never via a leaked global.

package.path = package.path .. ";./?.lua;./engine/?.lua"

local formula = require("engine.formula")

print("[TEST] Starting formula session-view tests...")

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

local items = {
    potion = { id = "potion", type = "consumable" },
    sword = { id = "sword", type = "equipment" },
    writ = { id = "writ", type = "quest" },
    scrap = { id = "scrap", type = "junk" },
}

local session = {
    inventory = {
        potion = 3,
        sword = 1,
        writ = 1,
        scrap = 2,
        empty = 0,
    },
    loader = {
        getItem = function(id) return items[id] end,
    },
}

local expected = {
    [1] = 4, -- all non-empty stacks
    [2] = 1, -- consumables
    [3] = 1, -- equipment
    [4] = 2, -- quest + junk
}

for tab = 1, 4 do
    local ctx = formula.makeContext({ session = session, v = { tab = tab } })
    check(ctx.session.itemCount == expected[tab],
        ("inventory tab %d reports %d matching stacks"):format(tab, expected[tab]))
end

-- No scene-local tab still has the historical default meaning: tab 1/all.
local defaultCtx = formula.makeContext({ session = session })
check(defaultCtx.session.itemCount == expected[1],
    "missing tab context deliberately defaults to inventory tab 1")

print(("=== Formula Session-View Tests Completed: %d passed, %d failed ==="):format(passed, failed))
if failed > 0 then require("tests.fail_fast")("formula session-view tests failed", failed) end
