-- Authored Scene update cadence contract (#386).
--
-- This module is intentionally small and pure. It does not own a scheduler,
-- Map Event lifetimes, rendering cadence, or Battle time. It only validates
-- and resolves the optional clock a Scene may request for its own `on_frame`
-- hook.
--
-- Legacy Scene (field absent):
--   host update -> one on_frame invocation, exactly as before #386.
--
-- Fixed Scene:
--   "update": {
--     "mode": "fixed",
--     "step": 0.0166666666666667,
--     "maxCatchUp": 8
--   }
--
-- The host accumulates wall-clock dt and emits zero or more logical ticks of
-- exactly `step` seconds. maxCatchUp bounds work in one host update but does
-- not discard remaining backlog, preserving deterministic simulation state.
local contract = {}

local DEFAULT_MAX_CATCH_UP = 8
local MAX_CATCH_UP_LIMIT = 120

local function finitePositive(value)
    return type(value) == "number"
        and value == value
        and value > 0
        and value < math.huge
end

function contract.resolve(scene)
    if type(scene) ~= "table" or scene.update == nil then return nil end
    local update = scene.update
    if type(update) ~= "table" then
        error("Scene '" .. tostring(scene.id or "?") .. "' update must be an object", 0)
    end
    if update.mode ~= "fixed" then
        error("Scene '" .. tostring(scene.id or "?")
            .. "' update.mode must be 'fixed' when update is authored", 0)
    end
    if not finitePositive(update.step) then
        error("Scene '" .. tostring(scene.id or "?")
            .. "' fixed update.step must be a finite positive number", 0)
    end
    local maxCatchUp = update.maxCatchUp
    if maxCatchUp == nil then maxCatchUp = DEFAULT_MAX_CATCH_UP end
    if type(maxCatchUp) ~= "number" or maxCatchUp ~= math.floor(maxCatchUp)
            or maxCatchUp < 1 or maxCatchUp > MAX_CATCH_UP_LIMIT then
        error("Scene '" .. tostring(scene.id or "?")
            .. "' fixed update.maxCatchUp must be an integer from 1 to "
            .. tostring(MAX_CATCH_UP_LIMIT), 0)
    end
    return {
        mode = "fixed",
        step = update.step,
        maxCatchUp = maxCatchUp,
    }
end

function contract.validateScenes(scenes)
    local problems = {}
    for index, scene in ipairs(scenes or {}) do
        local ok, err = pcall(contract.resolve, scene)
        if not ok then
            problems[#problems + 1] = "scene[" .. tostring(index) .. "]: " .. tostring(err)
        end
    end
    if #problems > 0 then error(table.concat(problems, "\n"), 0) end
end

contract.DEFAULT_MAX_CATCH_UP = DEFAULT_MAX_CATCH_UP
contract.MAX_CATCH_UP_LIMIT = MAX_CATCH_UP_LIMIT

return contract
