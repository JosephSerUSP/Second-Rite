local json = require("data.json")

local function mustFail(label, fn)
    local ok = pcall(fn)
    assert(not ok, label .. " should fail")
end

local function bytes(...)
    return string.char(...)
end

-- Standards-compliant decode: Unicode escapes, including surrogate pairs.
assert(json.decode('"\\u00E9"') == bytes(0xC3, 0xA9), "BMP unicode escape should decode as UTF-8")
assert(json.decode('"\\uD83D\\uDE00"') == bytes(0xF0, 0x9F, 0x98, 0x80),
    "surrogate pair should decode as UTF-8")
mustFail("lonely high surrogate", function() json.decode('"\\uD83D"') end)
mustFail("lonely low surrogate", function() json.decode('"\\uDE00"') end)

-- Strict JSON grammar: no JS extensions, malformed numbers, bad escapes, raw
-- controls, or trailing material.
for _, source in ipairs({
    '01', '1.', '+1', 'NaN', 'Infinity',
    '"\\q"',
    '// comment\n1',
    '/* comment */ 1',
    'true false',
}) do
    mustFail("strict decode " .. source, function() json.decode(source) end)
end
mustFail("raw control in string", function()
    json.decode('"' .. string.char(1) .. '"')
end)

-- Explicit JSON null survives as a value instead of collapsing to Lua nil.
assert(json.decode("null") == json.null, "top-level null identity should survive")
local withNull = json.decode('[null,{"value":null}]')
assert(withNull[1] == json.null, "array null should survive")
assert(withNull[2].value == json.null, "object null should survive")
assert(json.encode(withNull) == '[null,{"value":null}]', "null should round-trip")

-- Empty container identity survives decode and can be authored explicitly.
assert(json.encode(json.decode("[]")) == "[]", "decoded empty array should stay an array")
assert(json.encode(json.decode("{}")) == "{}", "decoded empty object should stay an object")
assert(json.encode(json.array({})) == "[]", "explicit empty array helper")
assert(json.encode(json.object({})) == "{}", "explicit empty object helper")
-- Historical data.json behavior: an unmarked empty Lua table means array.
assert(json.encode({}) == "[]", "unmarked empty table compatibility")

-- Preserve the existing Thestra projection used by save/authored data.
assert(json.encode({ "a", "b" }) == '["a","b"]', "contiguous numeric keys should be an array")
assert(json.encode({ [1] = "a", [3] = "c" }) == '{"1":"a","3":"c"}',
    "sparse numeric keys should remain an object")
assert(json.encode(json.object({ [1] = "a", [2] = "b" })) == '{"1":"a","2":"b"}',
    "explicit object identity should beat array inference")
assert(json.encode(json.array({ [2] = "b" })) == '[null,"b"]',
    "explicit array holes should become JSON null")
mustFail("stringified object-key collision", function()
    json.encode({ [1] = "numeric", ["1"] = "string" })
end)

-- Deterministic output remains a Thestra boundary guarantee even though JSON
-- object ordering is semantically irrelevant.
assert(json.encode({ z = 1, a = 2, middle = 3 }) == '{"a":2,"middle":3,"z":1}',
    "object bytes should remain deterministic")

-- Encoder rejects values outside the JSON data model.
mustFail("NaN encode", function() json.encode(0/0) end)
mustFail("positive infinity encode", function() json.encode(1/0) end)
mustFail("negative infinity encode", function() json.encode(-1/0) end)
mustFail("function encode", function() json.encode(function() end) end)
local cycle = {}; cycle.self = cycle
mustFail("cyclic table encode", function() json.encode(cycle) end)

-- Representative Project JSON: the runtime input map is ordinary authored JSON
-- and must survive a decode/encode/decode cycle semantically.
local inputBody = assert(love.filesystem.read("data/input.json"), "representative Project JSON missing")
local inputA = json.decode(inputBody)
local inputB = json.decode(json.encode(inputA))
assert(type(inputA) == "table" and type(inputB) == "table", "Project JSON should decode")
assert(json.encode(inputA) == json.encode(inputB), "Project JSON semantic round-trip should stabilize")

-- Representative save shape: sparse numeric maps intentionally serialize as
-- objects, then the save boundary restores their domain keys. This guards the
-- policy that a dependency swap must not accidentally turn into a save migration.
local saveLike = {
    version = 5,
    inventory = { [1] = 2, [198] = 7 },
    eventOverrides = { [1] = { [7] = { page = 2 } } },
    party = { false, { id = "unit:test", hp = 12 } },
    explicitNull = json.null,
}
local saveBody = json.encode(saveLike)
local decodedSave = json.decode(saveBody)
assert(decodedSave.inventory["1"] == 2 and decodedSave.inventory["198"] == 7,
    "save sparse numeric map should remain string-keyed JSON object")
assert(decodedSave.eventOverrides["1"]["7"].page == 2,
    "nested save sparse numeric maps should preserve shape")
assert(decodedSave.party[1] == false and decodedSave.party[2].id == "unit:test",
    "save arrays should preserve slots")
assert(decodedSave.explicitNull == json.null, "save explicit null should survive")

print("JSON codec membrane: OK")
