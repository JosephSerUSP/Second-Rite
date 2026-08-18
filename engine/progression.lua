-- Authored level-threshold policy (#549).
--
-- The runtime owns the invariant operation "how much EXP is required to cross
-- the current level?" but not the concrete curve.  The curve is ordinary
-- authored data resolved/materialized into data/progression.json before the
-- player runtime starts (Project override -> pinned RTP baseline).
--
-- Keep this module deliberately small.  Progression consequences such as
-- growth, recovery, transformation and skill learning do NOT belong here;
-- those move behind LEVEL_REACHED / authored policy in later slices.
local json = require("engine.data.json")
local formula = require("engine.formula")

local progression = {}
local DATA_PATH = require("engine.data.loader").root .. "/progression.json"
local cached

local function authored()
    if cached then return cached end
    if not love or not love.filesystem then
        error("progression requires the Project game filesystem")
    end
    local contents = love.filesystem.read(DATA_PATH)
    if not contents then
        error("Required authored progression resource is missing: " .. DATA_PATH)
    end
    local ok, value = pcall(json.decode, contents)
    if not ok then
        error("Authored progression resource is not readable JSON: " .. tostring(value))
    end
    if type(value) ~= "table" then
        error("Authored progression resource must be a JSON object: " .. DATA_PATH)
    end
    cached = value
    return cached
end

-- Explicit reload seam for Project/runtime reloads and focused tests.  There is
-- no built-in gameplay fallback: if the resolved resource is absent or broken,
-- the next query fails visibly.
function progression.reload()
    cached = nil
    return authored()
end

local function positiveIntegerLevel(level, label)
    local n = tonumber(level)
    if not n or n < 1 or n ~= math.floor(n) then
        error((label or "level") .. " must be a positive integer, got " .. tostring(level))
    end
    return n
end

local function finite(n)
    return n == n and n ~= math.huge and n ~= -math.huge
end

-- EXP required to advance FROM `level` to `level + 1`.
--
-- `spec` is optional so unit tests and tooling can evaluate a candidate authored
-- definition without rewriting Project files. Runtime callers omit it and use
-- the materialized effective data/progression.json.
function progression.nextLevelExp(level, spec)
    level = positiveIntegerLevel(level, "progression level")
    spec = spec or authored()
    if type(spec) ~= "table" then
        error("progression spec must be an object")
    end

    local expr = spec.nextLevelExp
    if type(expr) ~= "string" and type(expr) ~= "number" then
        error("progression.nextLevelExp must be a Formula string or number")
    end

    local value, evalErr = formula.eval(expr, { level = level })
    if evalErr then
        error("progression.nextLevelExp formula failed: " .. tostring(evalErr))
    end
    value = tonumber(value)
    if not value or not finite(value) or value <= 0 then
        error("progression.nextLevelExp must resolve to a positive finite number, got " .. tostring(value))
    end
    if value ~= math.floor(value) then
        error("progression.nextLevelExp must resolve to an integer EXP threshold; use floor()/ceil()/round() explicitly")
    end
    return value
end

-- Total EXP represented by complete level crossings from fromLevel up to (but
-- excluding) toLevel. Economy code uses this same function as gainExp so summon
-- pricing/sacrifice value cannot silently reconstruct a different curve.
function progression.curveCost(fromLevel, toLevel, spec)
    fromLevel = positiveIntegerLevel(fromLevel, "fromLevel")
    toLevel = positiveIntegerLevel(toLevel, "toLevel")
    if toLevel < fromLevel then
        error("toLevel must be >= fromLevel")
    end
    local total = 0
    for level = fromLevel, toLevel - 1 do
        total = total + progression.nextLevelExp(level, spec)
    end
    return total
end

return progression
