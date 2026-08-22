-- Thestra JSON membrane.
--
-- JSON grammar, Unicode handling, string escaping, and number validation are
-- delegated to the pinned Lunajson codec under data/vendor/lunajson. This file
-- deliberately keeps the engine-specific table projection policy that callers
-- already depend on: contiguous positive integer keys are arrays; sparse
-- numeric maps are JSON objects with string keys. That policy is part of our
-- save/authored-data schema, not part of JSON parsing itself.
local newdecoder = require("engine.data.vendor.lunajson.decoder")
local newencoder = require("engine.data.vendor.lunajson.encoder")

local decodeRaw = newdecoder()
local encodeRaw = newencoder()

local json = {}

-- Lua has no falsey value distinct from nil, so exposing a JSON-null sentinel
-- from the long-standing json.decode() API would silently change gameplay
-- semantics: existing authored `null` fields historically behaved as absent
-- values. Keep that compatibility on decode(), and make lossless JSON null an
-- explicit opt-in through decodeExact().
local NULL = {}
json.null = NULL

-- Keep decoded/explicit container identity out-of-band. Metatables or sentinel
-- keys would leak codec concerns into ordinary engine tables and could collide
-- with authored data. Weak keys ensure the metadata cannot retain dead values.
local kinds = setmetatable({}, { __mode = "k" })
local arrayLengths = setmetatable({}, { __mode = "k" })

local function markContainer(value, kind, length)
    kinds[value] = kind
    if kind == "array" then arrayLengths[value] = length or 0 end
    return value
end

function json.array(value)
    value = value or {}
    assert(type(value) == "table", "json.array expects a table")
    local maxIndex = 0
    for key in pairs(value) do
        assert(type(key) == "number" and key >= 1 and key % 1 == 0,
            "json.array tables may contain only positive integer keys")
        if key > maxIndex then maxIndex = key end
    end
    return markContainer(value, "array", maxIndex)
end

function json.object(value)
    value = value or {}
    assert(type(value) == "table", "json.object expects a table")
    return markContainer(value, "object")
end

local function tagDecoded(value)
    if type(value) ~= "table" or value == NULL then return value end

    local arrayLength = rawget(value, 0)
    if type(arrayLength) == "number" then
        value[0] = nil
        markContainer(value, "array", arrayLength)
        for i = 1, arrayLength do
            if value[i] ~= nil then tagDecoded(value[i]) end
        end
    else
        markContainer(value, "object")
        for _, child in pairs(value) do tagDecoded(child) end
    end
    return value
end

local function decode(text, preserveNull)
    assert(type(text) == "string", "json.decode expects a string")
    -- nil keeps Lunajson in full-document mode (including trailing-garbage
    -- rejection). arraylen=true exposes [] versus {} without adding sentinel
    -- fields to consumer tables. Lossless mode supplies the explicit NULL
    -- identity; compatibility mode supplies nil, matching the former codec.
    local nullValue = preserveNull and NULL or nil
    return tagDecoded(decodeRaw(text, nil, nullValue, true))
end

function json.decode(text)
    return decode(text, false)
end

-- Lossless JSON-value decode for boundaries that need to distinguish explicit
-- null from absence. Existing gameplay/authored-data callers intentionally keep
-- json.decode() until their domain schema chooses to own null as a real value.
function json.decodeExact(text)
    return decode(text, true)
end

local function inferredKind(value)
    local count, maxIndex = 0, 0
    for key in pairs(value) do
        count = count + 1
        if type(key) ~= "number" or key < 1 or key % 1 ~= 0 then
            return "object", nil
        end
        if key > maxIndex then maxIndex = key end
    end
    if count > 0 and maxIndex ~= count then return "object", nil end
    -- Compatibility with the former codec: an unmarked empty Lua table is an
    -- array. Call json.object({}) when empty-object identity matters.
    return "array", maxIndex
end

local function normalize(value, stack)
    if value == NULL then return NULL end

    local valueType = type(value)
    if valueType == "nil" then return NULL end
    if valueType == "string" or valueType == "number" or valueType == "boolean" then
        return value
    end
    if valueType ~= "table" then
        error("Unsupported JSON type: " .. valueType, 0)
    end

    if stack[value] then error("JSON table cycle detected", 0) end
    stack[value] = true

    local kind = kinds[value]
    local length
    if kind == "array" then
        length = arrayLengths[value] or 0
        for key in pairs(value) do
            if type(key) ~= "number" or key < 1 or key % 1 ~= 0 then
                stack[value] = nil
                error("JSON array contains a non-integer key: " .. tostring(key), 0)
            end
            if key > length then length = key end
        end
    elseif kind ~= "object" then
        kind, length = inferredKind(value)
    end

    local out = {}
    if kind == "array" then
        out[0] = length or 0 -- Lunajson's explicit array-length convention.
        for i = 1, length or 0 do
            out[i] = normalize(value[i], stack)
        end
    else
        local seen = {}
        for key, child in pairs(value) do
            local keyType = type(key)
            if keyType ~= "string" and keyType ~= "number" then
                stack[value] = nil
                error("Unsupported JSON object key type: " .. keyType, 0)
            end
            local encodedKey = tostring(key)
            if seen[encodedKey] then
                stack[value] = nil
                error("JSON object key collision after string conversion: " .. encodedKey, 0)
            end
            seen[encodedKey] = true
            out[encodedKey] = normalize(child, stack)
        end
    end

    stack[value] = nil
    return out
end

function json.encode(value)
    return encodeRaw(normalize(value, {}), NULL)
end

return json
