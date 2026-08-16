local json = require("data.json")

local function mustFail(label, fn)
    local ok = pcall(fn)
    assert(not ok, label .. " should fail")
end

local function bytes(...)
    return string.char(...)
end

-- Standards-compliant decode: Unicode escapes, including surrogate pairs, and
-- ordinary UTF-8 source bytes pass through unchanged.
assert(json.decode('"\\u00E9"') == bytes(0xC3, 0xA9), "BMP unicode escape should decode as UTF-8")
assert(json.decode('"\\uD83D\\uDE00"') == bytes(0xF0, 0x9F, 0x98, 0x80),
    "surrogate pair should decode as UTF-8")
local utf8Source = bytes(0xE6, 0xB0, 0xB4) -- U+6C34
assert(json.decode('"' .. utf8Source .. '"') == utf8Source, "UTF-8 source string should survive")
mustFail("lonely high surrogate", function() json.decode('"\\uD83D"') end)
mustFail("lonely low surrogate", function() json.decode('"\\uDE00"') end)

-- Full JSON escape surface used by authored strings.
local escaped = json.decode('"quote: \\" slash: \\/ backslash: \\\\ b: \\b f: \\f n: \\n r: \\r t: \\t"')
assert(escaped == 'quote: " slash: / backslash: \\ b: ' .. string.char(8)
    .. ' f: ' .. string.char(12) .. ' n: \n r: \r t: \t', "JSON escapes should decode exactly")
local controls = '"\\' .. string.char(8) .. string.char(12) .. '\n\r\t' .. string.char(1)
local controlsEncoded = json.encode(controls)
assert(json.decode(controlsEncoded) == controls, "encoder control escaping should round-trip")
assert(not controlsEncoded:find(string.char(1), 1, true), "raw control byte must not leak into JSON output")

-- Valid JSON number forms decode; JS-like and malformed spellings fail.
assert(json.decode("0") == 0 and json.decode("-12") == -12, "integers should decode")
assert(math.abs(json.decode("1.25") - 1.25) < 1e-12, "fraction should decode")
assert(json.decode("2e3") == 2000 and math.abs(json.decode("-4.5E-2") + 0.045) < 1e-12,
    "exponent notation should decode")
for _, source in ipairs({
    '01', '1.', '+1', '.5', '1e', 'NaN', 'Infinity',
    '"\\q"',
    '// comment\n1',
    '/* comment */ 1',
    'true false',
    '[1,]',
    '{"a":1,}',
}) do
    mustFail("strict decode " .. source, function() json.decode(source) end)
end
mustFail("raw control in string", function()
    json.decode('"' .. string.char(1) .. '"')
end)

-- Null has two explicit contracts. The long-standing decode() surface preserves
-- current gameplay semantics: authored null behaves as absent/nil. Boundaries
-- that need lossless JSON values opt into decodeExact() and compare json.null.
assert(json.decode("null") == nil, "compatibility decode should keep historical null-as-nil semantics")
local legacyNull = json.decode('{"value":null,"array":[null,2]}')
assert(legacyNull.value == nil, "compatibility object null should be absent")
assert(legacyNull.array[1] == nil and legacyNull.array[2] == 2,
    "compatibility array null should remain a nil slot")
assert(json.encode(legacyNull.array) == '[null,2]',
    "array length metadata should preserve a decoded null slot on re-encode")

assert(json.decodeExact("null") == json.null, "lossless top-level null identity should survive")
local withNull = json.decodeExact('[null,{"value":null}]')
assert(withNull[1] == json.null, "lossless array null should survive")
assert(withNull[2].value == json.null, "lossless object null should survive")
assert(json.encode(withNull) == '[null,{"value":null}]', "lossless null should round-trip")

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
assert(decodedSave.explicitNull == nil, "ordinary save decode keeps legacy null-as-absence semantics")
local decodedSaveExact = json.decodeExact(saveBody)
assert(decodedSaveExact.explicitNull == json.null, "lossless save decode can preserve explicit null")

print("JSON codec membrane: OK")
