-- Canonical G1 composition root.
--
-- validator_rules contains the historical installation/game regression suite;
-- project_validator_rules owns the Project-generic gate exposed by #485.
-- resource_reference owns the typed filesystem-resolution vocabulary added by
-- #353. vertex_shading owns the portable vertex-lighting seam from #487.
-- Keeping them behind this module preserves `lovec . validate` as one
-- deterministic command while preventing a neutral Project from inheriting
-- Second Gate's concrete validation fixtures merely to pass G1.
local validator = {}
local full_rules = require("engine.validator_rules")
local project_rules = require("engine.project_validator_rules")
local resource_reference = require("engine.resource_reference")
local vertex_shading = require("engine.vertex_shading")

local function usesFullRegressionFixture(loader)
    -- `_test` is deliberately validator-only authored data. The root Second
    -- Gate development Project still carries it, so existing G1 behavior and
    -- its deep gameplay simulations remain unchanged there. Sparse/external
    -- Projects do not carry `_test` and therefore receive only reusable Thestra
    -- Project validation. This is an explicit fixture boundary, not inference
    -- from game title, paths, Unit ids, or other Project content.
    return type(loader.flows) == "table" and type(loader.flows._test) == "table"
end

function validator.run(loader)
    if usesFullRegressionFixture(loader) then
        full_rules.run(loader)
    else
        project_rules.run(loader)
    end
    resource_reference.validateAuthored(loader)
    vertex_shading.validateAuthored(loader)
end

validator.usesFullRegressionFixture = usesFullRegressionFixture

return validator
