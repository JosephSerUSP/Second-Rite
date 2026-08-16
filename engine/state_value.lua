-- Deterministic authored value semantics shared by persistent state owners (#407).
--
-- This is deliberately smaller than Lua's value model. Authored state is a
-- serializable value tree, not an object graph: booleans, finite numbers,
-- strings, dense lists, records, and nil/unset. Every write crosses a
-- copy-by-value boundary. Metatables, cycles, shared table aliases and sparse
-- or mixed-key collections are rejected so save/load can never change the
-- meaning of an authored value behind the author's back.
local state_value = {}

local function fail(path, message, level)
    error(("invalid authored state value at %s: %s"):format(path or "$", message), level or 3)
end

local function finite(value)
    return type(value) == "number"
        and value == value and value ~= math.huge and value ~= -math.huge
end

function state_value.isFiniteNumber(value)
    return finite(value)
end

local function copyValue(value, path, seen)
    local kind = type(value)
    if kind == "nil" or kind == "boolean" or kind == "string" then
        return value
    end
    if kind == "number" then
        if not finite(value) then fail(path, "number must be finite", 4) end
        return value
    end
    if kind ~= "table" then
        fail(path, "unsupported Lua type '" .. kind .. "'", 4)
    end
    if getmetatable(value) ~= nil then
        fail(path, "metatables are not authored state", 4)
    end
    if seen[value] then
        fail(path, "table is cyclic or shares identity with " .. seen[value], 4)
    end
    seen[value] = path

    local numericCount, stringCount, maxIndex = 0, 0, 0
    local stringKeys = {}
    for key in pairs(value) do
        local keyKind = type(key)
        if keyKind == "number" then
            if not finite(key) or key < 1 or key ~= math.floor(key) then
                fail(path, "list keys must be positive integers", 4)
            end
            numericCount = numericCount + 1
            if key > maxIndex then maxIndex = key end
        elseif keyKind == "string" then
            stringCount = stringCount + 1
            stringKeys[#stringKeys + 1] = key
        else
            fail(path, "record/list keys must be strings or positive integers", 4)
        end
    end

    if numericCount > 0 and stringCount > 0 then
        fail(path, "mixed record/list keys are not allowed", 4)
    end

    local out = {}
    if numericCount > 0 or stringCount == 0 then
        -- Empty tables follow the repository JSON convention and therefore
        -- mean an empty dense list. An empty record has no observable fields;
        -- authors can leave/unset that value instead.
        if maxIndex ~= numericCount then
            fail(path, "lists must be dense (no holes)", 4)
        end
        for index = 1, maxIndex do
            out[index] = copyValue(value[index], path .. "[" .. index .. "]", seen)
        end
    else
        table.sort(stringKeys)
        for _, key in ipairs(stringKeys) do
            out[key] = copyValue(value[key], path .. "." .. key, seen)
        end
    end
    return out
end

function state_value.copy(value, path)
    return copyValue(value, path or "$", {})
end

function state_value.validate(value, path)
    state_value.copy(value, path)
    return true
end

local function equalValues(a, b)
    if type(a) ~= type(b) then return false end
    if type(a) ~= "table" then return a == b end
    for key, value in pairs(a) do
        if not equalValues(value, b[key]) then return false end
    end
    for key in pairs(b) do
        if a[key] == nil then return false end
    end
    return true
end

-- Deterministic value equality over the same serializable tree contract.
-- Copying first rejects cycles, aliases, metatables and non-finite numbers.
function state_value.equals(a, b)
    local left = state_value.copy(a, "left value")
    local right = state_value.copy(b, "right value")
    return equalValues(left, right)
end

function state_value.tryCopy(value, path)
    local ok, result = pcall(state_value.copy, value, path)
    if ok then return result, nil end
    return nil, result
end

return state_value
