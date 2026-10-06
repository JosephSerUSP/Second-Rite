-- Project-declared battler resources (PE Day 1 ledger O3, revised 06.10).
--
-- A per-battler pool that skills can cost: Parasite Eve's PE, a traditional
-- MP, focus, ki. It is deliberately NOT Second Gate's MP, which is the
-- Summoner's shared expedition pool (SPEC 1.11) that no skill may cost
-- (SPEC 1.20). A Project declares its resources in system.json:
--
--   "battlerResources": { "pe": { "name": "PE", "max": "100" } }
--
-- `max` is a number or a formula over the battler (`a`). Current values live
-- on the battler (`battler.resources[id]`) and are saved with it, exactly like
-- spell charges; a missing key means full, so a new or loaded battler starts
-- topped up. Undeclared ids are errors, never zero.

local formula = require("engine.formula")

local resources = {}

local function declarations(session)
    local loader = session and session.loader
    return (loader and loader.system and loader.system.battlerResources) or {}
end

function resources.declaration(session, id)
    local decl = declarations(session)[id]
    if not decl then
        error("undeclared battler resource '" .. tostring(id) .. "' (system.battlerResources)", 2)
    end
    return decl
end

function resources.ids(session)
    local out = {}
    for id in pairs(declarations(session)) do out[#out + 1] = id end
    table.sort(out)
    return out
end

function resources.max(battler, id, session)
    local decl = resources.declaration(session, id)
    if type(decl.max) == "number" then return math.max(0, math.floor(decl.max)) end
    -- The view omits resource values: a maximum may depend on level or stats,
    -- never on a resource, or reading it would recurse.
    local view = formula.battlerView(battler, session, { noResources = true })
    return math.max(0, math.floor(tonumber(formula.eval(decl.max, { a = view, b = view })) or 0))
end

function resources.get(battler, id, session)
    local max = resources.max(battler, id, session)
    local stored = battler and battler.resources and battler.resources[id]
    if stored == nil then return max, max end
    return math.max(0, math.min(stored, max)), max
end

--- Signed change, clamped to [0, max]. Returns the amount actually applied.
function resources.change(battler, id, delta, session)
    local current, max = resources.get(battler, id, session)
    local nextValue = math.max(0, math.min(max, current + math.floor(delta)))
    battler.resources = battler.resources or {}
    battler.resources[id] = nextValue
    return nextValue - current
end

function resources.label(session, id)
    return resources.declaration(session, id).name or id
end

return resources
