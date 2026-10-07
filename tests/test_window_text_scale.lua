local rules = require("engine.window_layout_rules")
local passed = 0
local function problemsFor(value)
    local problems = {}
    rules.validate(value, function(ok, message)
        if not ok then problems[#problems + 1] = message end
    end)
    return problems
end
local function fixture(scale)
    return { engine = { windowLayout = { readout = { textScale = scale } } },
        scenes = { { id = "probe", windows = {{ textScale = scale }} } } }
end
assert(#problemsFor(fixture(nil)) == 0, "default text remains valid")
assert(#problemsFor(fixture(2)) == 0, "large readouts remain valid")
passed = passed + 2
for _, scale in ipairs({0, -1, "2", false, math.huge, 0/0}) do
    local problems = problemsFor(fixture(scale))
    assert(#problems == 2 and problems[1]:match("textScale") and problems[2]:match("textScale"),
        "both shared and inline window scales reject invalid authored values")
    passed = passed + 1
end
local paged = { engine = { windowLayout = { readout = { pages = {{textScale = 0}} } } } }
assert(#problemsFor(paged) == 1, "paged layouts reject invalid scales")
passed = passed + 1
print(("=== Window Text Scale Tests: %d passed, 0 failed ==="):format(passed))
