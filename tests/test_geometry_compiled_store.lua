-- The persistent compiled-geometry store (#161). The contract that matters is
-- EXACTNESS: a model restored from disk must be bit-identical to the compiled
-- one, or golden screenshots would depend on whether the store happened to be
-- warm -- a difference that is invisible locally and reddens G5 for someone
-- else. float32 storage would pass a "looks about right" test and fail this one.
local store = require("engine.geometry.compiled_store")

local passed, failed = 0, 0
local function check(label, fn)
    local ok, err = pcall(fn)
    if ok then
        passed = passed + 1
        print("  [PASS] " .. label)
    else
        failed = failed + 1
        print("  [FAIL] " .. label .. ": " .. tostring(err))
    end
end

local function sampleModel()
    return {
        groups = {
            {
                material = "surface",
                vertices = {
                    -- Deliberately awkward values: irrational-ish decimals, a
                    -- negative, a very small magnitude and a very large one.
                    { 0.1, -0.2, 1/3, 0.7071067811865476, 2.2250738585072014e-8,
                      0, 0, 1, 1, 1, 1, 1 },
                    { 1e7 + 0.5, -1e-7, 123456.789, 0.25, 0.75,
                      0.5773502691896258, -0.5773502691896258, 0.5773502691896258,
                      0.3, 0.4, 0.5, 0.6 },
                    { -3.5, 4.25, 0, 1, 0, 0, 1, 0, 1, 1, 1, 1 },
                },
            },
            {
                material = "second",
                vertices = { { 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12 } },
            },
        },
        vertexCount = 4,
        bounds = { minX = -3.5, minY = -0.2, minZ = 0,
                   maxX = 1e7 + 0.5, maxY = 4.25, maxZ = 123456.789 },
    }
end

print("[TEST] Starting compiled geometry store tests...")

check("round-trip preserves every vertex field EXACTLY", function()
    local model = sampleModel()
    local decoded = store.decode(store.encode(model))
    assert(decoded, "decode returned nil")
    assert(#decoded.groups == #model.groups, "group count")
    for g, group in ipairs(model.groups) do
        local out = decoded.groups[g]
        assert(out.material == group.material, "material " .. g)
        assert(#out.vertices == #group.vertices, "vertex count in group " .. g)
        for v, vertex in ipairs(group.vertices) do
            for f = 1, 12 do
                local a, b = vertex[f], out.vertices[v][f]
                -- Equality, not a tolerance. A tolerance here would accept the
                -- float32 truncation this test exists to forbid.
                assert(a == b, string.format(
                    "group %d vertex %d field %d: %.17g ~= %.17g", g, v, f, a, b))
            end
        end
    end
end)

check("round-trip preserves bounds and vertexCount", function()
    local model = sampleModel()
    local decoded = store.decode(store.encode(model))
    assert(decoded.vertexCount == model.vertexCount, "vertexCount")
    for _, k in ipairs({ "minX", "minY", "minZ", "maxX", "maxY", "maxZ" }) do
        assert(decoded.bounds[k] == model.bounds[k],
            k .. ": " .. tostring(decoded.bounds[k]) .. " ~= " .. tostring(model.bounds[k]))
    end
end)

check("a blob without the magic header is refused", function()
    assert(store.decode("not a geometry file at all") == nil, "accepted foreign data")
end)

check("a truncated blob is refused rather than half-decoded", function()
    local blob = store.encode(sampleModel())
    -- pcall because a truncated read may raise inside unpack; either a nil
    -- return or a caught error is acceptable, a partial model is not.
    local ok, result = pcall(store.decode, blob:sub(1, math.floor(#blob / 2)))
    assert(not ok or result == nil, "a truncated blob produced a model")
end)

check("a future format version is refused, not misread", function()
    local blob = store.encode(sampleModel())
    -- Byte 6..9 is the little-endian format version immediately after "SRGEO".
    local bumped = blob:sub(1, 5) .. love.data.pack("string", "<I4", 99) .. blob:sub(10)
    assert(store.decode(bumped) == nil, "accepted an unknown format version")
end)

check("an empty model is not written", function()
    assert(store.save("test-empty-key", { groups = {} }) == false, "wrote an empty model")
end)

print(string.format("=== Compiled Geometry Store Tests: %d passed, %d failed ===",
    passed, failed))
if failed > 0 then
    require("tests.fail_fast")("compiled geometry store tests failed", failed)
end
