-- Canonical G1 composition root.
--
-- validator_rules contains the existing authored-data/schema/gameplay checks.
-- resource_reference owns the typed filesystem-resolution vocabulary added by
-- #353. Keeping both behind this module preserves `lovec . validate` as one
-- deterministic gate while letting resource lookup reuse runtime authorities
-- instead of growing more one-off getInfo checks inside the rule monolith.
local validator = {}
local rules = require("engine.validator_rules")
local resource_reference = require("engine.resource_reference")

function validator.run(loader)
    rules.run(loader)
    resource_reference.validateAuthored(loader)
end

return validator
