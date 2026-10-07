-- Installs the PE Day 1 Project's combat data and scenes into the shared
-- loader for one test suite, and returns a restore function. The loader is
-- pinned to one Project per process, so suites that exercise pe-day1 swap its
-- tables in rather than staging a second process.
local json = require("engine.data.json")

local SWAPPED = { "skills", "units", "unitsById", "items", "itemsById", "troops", "system", "scenes" }

return function(loader, opts)
    opts = opts or {}
    local root = assert(os.getenv("THESTRA_REPOSITORY_ROOT"), "pe-day1 fixture requires repository root")
    local DATA = root .. "/projects/pe-day1/data/"
    local function read(rel)
        local f = assert(io.open(DATA .. rel, "r"), "missing " .. rel)
        local value = json.decode(f:read("*a"))
        f:close()
        return value
    end

    local saved = {}
    for _, k in ipairs(SWAPPED) do saved[k] = loader[k] end
    local savedBattleFlows = loader.flows.battle

    loader.skills = read("skills.json")
    loader.items = read("items.json")
    loader.itemsById = {}
    for _, item in ipairs(loader.items) do loader.itemsById[item.id] = item end
    loader.units, loader.unitsById = {}, {}
    for _, file in ipairs(read("units/index.json").files) do
        local unit = read("units/" .. file)
        loader.units[#loader.units + 1] = unit
        loader.unitsById[unit.id] = unit
    end
    loader.troops = read("troops.json")
    local system = {}
    for k, v in pairs(saved.system) do system[k] = v end
    for k, v in pairs(read("system.json")) do system[k] = v end
    loader.system = system
    loader.flows.battle = read("flows/battle.json")
    -- The EXP curve is a file the progression module reads from the pinned
    -- Project; route its queries to pe-day1's curve for this suite.
    local progression = require("engine.progression")
    local savedNextLevelExp = progression.nextLevelExp
    local peCurve = read("progression.json")
    progression.nextLevelExp = function(level, spec) return savedNextLevelExp(level, spec or peCurve) end
    if opts.scenes then
        loader.scenes = {}
        for _, id in ipairs(opts.scenes) do loader.scenes[#loader.scenes + 1] = read("scenes/" .. id .. ".json") end
    end

    return function()
        for _, k in ipairs(SWAPPED) do loader[k] = saved[k] end
        loader.flows.battle = savedBattleFlows
        progression.nextLevelExp = savedNextLevelExp
    end
end
