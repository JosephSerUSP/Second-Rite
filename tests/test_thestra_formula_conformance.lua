-- Backend-neutral conformance fixture for the authored Thestra Formula Contract
-- (SPEC 1.1.1).  It deliberately tests the live Lua evaluator, not Lua syntax
-- generally: every fixture construct is present in current authored resources.
local formula = require("engine.formula")
local json = require("engine.data.json")

local fixtureText = assert(love.filesystem.read("tests/fixtures/thestra_formula_conformance.json"))
local fixture = json.decode(fixtureText)

local function fail(message)
    error("Thestra formula conformance: " .. message, 0)
end

for _, case in ipairs(fixture.cases) do
    local value, err = formula.eval(case.expr, fixture.context)
    if err ~= nil then fail(case.name .. " unexpectedly failed: " .. tostring(err)) end
    if value ~= case.expect then
        fail(case.name .. " expected " .. tostring(case.expect) .. ", got " .. tostring(value))
    end
end

for _, case in ipairs(fixture.errors) do
    local value, err = formula.eval(case.expr, fixture.context)
    if err == nil or value ~= 0 then
        fail(case.name .. " must return fallback 0 plus an error")
    end
end

-- random is deliberately range-tested, not sequence-pinned: seeded callers
-- receive repeatable values from the host PRNG, while exact sequences belong
-- to that host's deterministic golden fixtures.
math.randomseed(416)
local firstFloat = formula.eval("random()", fixture.context)
local firstInt = formula.eval("random(4, 9)", fixture.context)
math.randomseed(416)
local secondFloat = formula.eval("random()", fixture.context)
local secondInt = formula.eval("random(4, 9)", fixture.context)
if type(firstFloat) ~= "number" or firstFloat < 0 or firstFloat >= 1 then
    fail("random() must return a float in [0, 1)")
end
if type(firstInt) ~= "number" or firstInt % 1 ~= 0 or firstInt < 4 or firstInt > 9 then
    fail("random(m, n) must return an inclusive integer in [m, n]")
end
if firstFloat ~= secondFloat or firstInt ~= secondInt then
    fail("random must repeat under the same caller-provided seed")
end

-- Keep backend-neutral numeric corpora under one already-registered conformance
-- entrypoint. Lighting owns its own fixture/module; Formula semantics above do
-- not import or duplicate any lighting rule.
require("tests.backend_neutral_lighting_conformance")
