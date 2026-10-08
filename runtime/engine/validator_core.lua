-- Canonical G1 composition root.
--
-- validator_rules contains the historical installation/game regression suite;
-- project_validator_rules owns the Project-generic gate exposed by #485.
-- resource_reference owns the typed filesystem-resolution vocabulary added by
-- #353. vertex_shading owns the portable vertex-lighting seam from #487.
-- scene_update_contract owns the optional fixed logical clock for authored
-- Scene `on_frame` hooks (#386).
-- Keeping them behind this module preserves `lovec . validate` as one
-- deterministic command while preventing a neutral Project from inheriting
-- Second Gate's concrete validation fixtures merely to pass G1.
local validator = {}
local full_rules = require("engine.validator_rules")
local project_rules = require("engine.project_validator_rules")
local resource_reference = require("engine.resource_reference")
local vertex_shading = require("engine.vertex_shading")
local scene_update_contract = require("engine.scene_update_contract")

local function usesFullRegressionFixture(loader)
    -- `_test` is deliberately validator-only authored data. The root Second
    -- Gate development Project still carries it, so existing G1 behavior and
    -- its deep gameplay simulations remain unchanged there. Sparse/external
    -- Projects do not carry `_test` and therefore receive only reusable Thestra
    -- Project validation. This is an explicit fixture boundary, not inference
    -- from game title, paths, Unit ids, or other Project content.
    return type(loader.flows) == "table" and type(loader.flows._test) == "table"
end

-- Scene host lookup has historically treated numeric and string Scene ids as
-- the same identity (`tostring(scene.id) == tostring(requested)`). Second Gate
-- still contains one legacy numeric Scene id (1), while its SCENE_EVENT target
-- is authored as the string "1". Project validation should police the runtime
-- identity contract rather than invent a stricter one: normalize only the
-- validation view, leaving the actual resolved loader graph untouched for the
-- full game regression suite and runtime consumers.
local function projectValidationView(loader)
    local view = setmetatable({}, { __index = loader })
    view.scenes = {}
    for index, scene in ipairs(loader.scenes or {}) do
        local copy = {}
        for key, value in pairs(scene) do copy[key] = value end
        if scene.id ~= nil then copy.id = tostring(scene.id) end
        view.scenes[index] = copy
    end
    view.getScene = function(id)
        local wanted = tostring(id)
        for _, scene in ipairs(view.scenes) do
            if tostring(scene.id) == wanted then return scene end
        end
        return nil
    end
    return view
end

function validator.run(loader)
    -- Reusable Project invariants are the floor, not an alternative to the
    -- Second Gate regression fixture. Running only full_rules for the root
    -- Project let it validate while an authored Options hook referenced a Scene
    -- omitted from the ordered Scene index; the exported player then crashed
    -- when that transition was taken. Every Project, including the fixture,
    -- must first prove its startup graph and literal authored references.
    project_rules.run(projectValidationView(loader))
    if usesFullRegressionFixture(loader) then
        full_rules.run(loader)
    end
    scene_update_contract.validateScenes(loader.scenes)
    resource_reference.validateAuthored(loader)
    vertex_shading.validateAuthored(loader)
end

validator.usesFullRegressionFixture = usesFullRegressionFixture

return validator
