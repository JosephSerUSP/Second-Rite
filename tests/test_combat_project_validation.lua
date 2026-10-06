-- Reusable combat-data validation for every Project (PE Day 1 M1, #1424).
-- Sparse Projects never run the Second Gate fixture rules, so a Project that
-- authors troops and skills must still be told about missing battle phases,
-- dangling troop members and malformed item-stock costs.
local project_validator = require("engine.project_validator_rules")

local PHASES = { "battle_start", "round_start", "after_action", "round_end",
    "victory", "defeat", "escaped", "flee_attempt" }

local function loaderFor(opts)
    local battle = {}
    if opts.phases then
        for _, phase in ipairs(PHASES) do battle[phase] = {{ cmd = "COMMENT", text = phase }} end
    end
    local items = { ammo = { id = "ammo", name = "Ammo" } }
    local units = { rat = { id = "rat", name = "Rat" } }
    local value = {
        system = { rtp = { revision = "test" } },
        engine = { commands = {{ id = "COMMENT" }} },
        scenes = {
            { id = "map", kind = "map", draw = "windows", hooks = {} },
            { id = "title", kind = "title", draw = "windows", hooks = {} },
            { id = "dialogue", kind = "dialogue", draw = "windows", hooks = {} },
        },
        flows = { exploration = { step = {{ cmd = "COMMENT", text = "step" }} }, battle = battle },
        maps = {},
        units = {},
        skills = opts.skills or {},
        troops = opts.troops or {},
    }
    value.system.battlerResources = opts.resources
    value.getScene = function(id)
        for _, scene in ipairs(value.scenes) do
            if scene.id == id then return scene end
        end
        return nil
    end
    value.getItem = function(id) return items[id] end
    value.getUnit = function(id) return units[id] end
    value.getSkill = function(id) return value.skills[id] end
    return value
end

local passed = 0
local function expectFail(opts, pattern, label)
    local ok, err = pcall(project_validator.run, loaderFor(opts))
    assert(not ok and tostring(err):match(pattern), label .. ": " .. tostring(err))
    passed = passed + 1
end
local function expectPass(opts, label)
    local ok, err = pcall(project_validator.run, loaderFor(opts))
    assert(ok, label .. ": " .. tostring(err))
    passed = passed + 1
end

local troop = { fight = { id = "fight", members = {{ actor = "rat", level = 1 }} } }

expectPass({}, "a Project with no combat need not author battle phases")
expectPass({ troops = { base = { id = "base", abstract = true, members = {} } } },
    "an abstract troop alone does not make a Project combat-capable")
expectFail({ troops = troop }, "require non%-empty flow phase 'battle%.battle_start'",
    "a concrete troop without battle phases fails")
expectPass({ troops = troop, phases = true }, "a concrete troop with every phase passes")
expectFail({ phases = true, troops = { fight = { id = "fight", members = {{ actor = "ghost" }} } } },
    "references missing unit 'ghost'", "a troop member must name a real unit")
expectFail({ skills = { shot = { id = "shot", itemCost = { item = "nope" } } } },
    "itemCost references missing item 'nope'", "an item cost must name a real item")
expectFail({ skills = { shot = { id = "shot", itemCost = { item = "ammo", count = 0 } } } },
    "itemCost%.count must be a whole number", "an item cost count must be at least 1")
expectFail({ skills = { shot = { id = "shot", itemCost = "ammo" } } },
    "itemCost must be", "an item cost must be a table")
expectPass({ skills = { shot = { id = "shot", itemCost = { item = "ammo", count = 2 } } } },
    "a well-formed item cost passes")

local pe = { pe = { name = "PE", max = 100 } }
expectPass({ resources = pe, skills = { heal = { id = "heal", resourceCost = { resource = "pe", amount = 30 } } } },
    "a resource cost naming a declared resource passes")
expectFail({ skills = { heal = { id = "heal", resourceCost = { resource = "pe", amount = 30 } } } },
    "undeclared battler resource 'pe'", "a resource cost must name a declared resource")
expectFail({ resources = pe, skills = { heal = { id = "heal", resourceCost = { resource = "pe", amount = -1 } } } },
    "resourceCost%.amount must be a number", "a resource cost amount cannot be negative")
expectFail({ resources = { pe = { name = "PE" } } }, "needs a max", "a declared resource needs a maximum")

print(("=== Combat Project Validation Tests: %d passed, 0 failed ==="):format(passed))
