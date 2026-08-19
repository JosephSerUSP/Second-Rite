-- Pure ordered numeric calculation seam for #308.
--
-- This module deliberately knows nothing about traits, battlers, source
-- discovery, packages, reactions, or commit authority. A caller supplies an
-- explicitly ordered dense list of typed numeric contributions. Evaluating the
-- same spec is side-effect-free and deterministic, so presentation and later
-- execution can consume the same calculation semantics without either layer
-- reconstructing the math.
--
-- Source precedence remains the caller's responsibility. That is intentional:
-- #308 has not settled the global order between innate/passive/equipment/state,
-- package, or future authored sources, and this reducer must not freeze it by
-- discovering participants itself.
local calculation = {}

local function finite(value, label)
    if type(value) ~= "number" or value ~= value
            or value == math.huge or value == -math.huge then
        error((label or "calculation value") .. " must be a finite number", 0)
    end
    return value
end

local function denseLength(list)
    if type(list) ~= "table" then
        error("semantic calculation contributions must be an ordered list", 0)
    end
    local count, highest = 0, 0
    for key in pairs(list) do
        if type(key) ~= "number" or key < 1 or key % 1 ~= 0 then
            error("semantic calculation contributions must use dense numeric indexes", 0)
        end
        count = count + 1
        if key > highest then highest = key end
    end
    if highest ~= count then
        error("semantic calculation contributions must be a dense ordered list", 0)
    end
    return count
end

local function contributionValue(step, index)
    return finite(step.value, "semantic calculation contribution " .. tostring(index) .. " value")
end

-- Evaluate one numeric semantic calculation without mutating the input spec or
-- any gameplay state. `channel` is descriptive only in this bounded slice; it
-- is not a global registry and carries no dispatch semantics.
--
-- Evidence-backed generic operations only:
--   add       current + value
--   multiply  current * value
--   replace   value
--   clamp     constrain current to [min, max]
--
-- The ordered trace is returned for inspection/debugging. It intentionally
-- carries no source handle yet: final source identity/precedence is unresolved
-- in #308 and belongs in the eventual participant-discovery layer.
function calculation.evaluate(spec)
    if type(spec) ~= "table" then
        error("semantic calculation requires a spec", 0)
    end
    if spec.channel ~= nil and type(spec.channel) ~= "string" then
        error("semantic calculation channel must be a string", 0)
    end

    local base = finite(spec.base == nil and 0 or spec.base,
        "semantic calculation base")
    local contributions = spec.contributions or {}
    local count = denseLength(contributions)
    local current = base
    local steps = {}

    for i = 1, count do
        local step = contributions[i]
        if type(step) ~= "table" then
            error("semantic calculation contribution " .. tostring(i) .. " must be a table", 0)
        end
        local operation = step.operation
        if type(operation) ~= "string" then
            error("semantic calculation contribution " .. tostring(i) .. " requires an operation", 0)
        end

        local before = current
        if operation == "add" then
            current = current + contributionValue(step, i)
        elseif operation == "multiply" then
            current = current * contributionValue(step, i)
        elseif operation == "replace" then
            current = contributionValue(step, i)
        elseif operation == "clamp" then
            local minimum = finite(step.min,
                "semantic calculation contribution " .. tostring(i) .. " min")
            local maximum = finite(step.max,
                "semantic calculation contribution " .. tostring(i) .. " max")
            if minimum > maximum then
                error("semantic calculation clamp min cannot exceed max", 0)
            end
            current = math.max(minimum, math.min(maximum, current))
        else
            error("unknown semantic calculation operation '" .. tostring(operation) .. "'", 0)
        end
        current = finite(current, "semantic calculation result")

        steps[#steps + 1] = {
            index = i,
            operation = operation,
            before = before,
            after = current,
        }
    end

    return {
        channel = spec.channel,
        base = base,
        value = current,
        steps = steps,
    }
end

return calculation
