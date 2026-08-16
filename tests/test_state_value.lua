-- #407 deterministic authored-state value semantics.
local state_value = require("engine.state_value")

local passed, failed = 0, 0
local function check(ok, message)
    if ok then
        passed = passed + 1
    else
        failed = failed + 1
        print("  FAIL: " .. message)
    end
end
local function rejects(value, needle)
    local ok, err = pcall(state_value.copy, value)
    return not ok and tostring(err):find(needle, 1, true) ~= nil
end

local source = {
    opened = true,
    count = 3,
    label = "west",
    nested = { tags = { "old", "wet" }, stats = { visits = 2 } },
}
local copied = state_value.copy(source)
check(copied.opened == true and copied.count == 3 and copied.label == "west",
    "scalar authored values copy")
check(copied ~= source and copied.nested ~= source.nested and copied.nested.tags ~= source.nested.tags,
    "records/lists deep-copy by value")
source.nested.tags[1] = "mutated"
check(copied.nested.tags[1] == "old", "copy is isolated from source mutation")

check(rejects(0 / 0, "finite"), "NaN is rejected")
check(rejects(math.huge, "finite"), "infinity is rejected")
check(rejects({ [1] = "a", [3] = "c" }, "dense"), "sparse lists are rejected")
check(rejects({ [1] = "a", name = "mixed" }, "mixed"), "mixed list/record keys are rejected")

local metatableValue = setmetatable({ answer = 42 }, {})
check(rejects(metatableValue, "metatables"), "metatables are rejected")
local cyclic = {}
cyclic.self = cyclic
check(rejects(cyclic, "cyclic or shares identity"), "cycles are rejected")
local shared = { n = 1 }
check(rejects({ a = shared, b = shared }, "cyclic or shares identity"),
    "shared-reference aliases are rejected")
check(rejects(function() end, "unsupported Lua type"), "functions are rejected")
check(state_value.isFiniteNumber(3.5) and not state_value.isFiniteNumber(math.huge)
        and not state_value.isFiniteNumber("3.5"),
    "finite-number helper shares the authored-state numeric contract")
check(state_value.equals({ a = 1, nested = { true, "x" } }, { nested = { true, "x" }, a = 1 }),
    "value equality ignores record insertion order")
check(not state_value.equals({ a = 1 }, { a = 2 }),
    "value equality distinguishes unequal authored trees")

print(("=== Authored State Value Tests: %d passed, %d failed ==="):format(passed, failed))
if failed > 0 then require("tests.fail_fast")("authored state value tests failed", failed) end
