-- Persistent + release-prebaked compiled geometry (#161).
--
-- The contract that matters is EXACTNESS: a model restored from bytes must be
-- bit-identical to the neutral compiler result. Positions, UVs, normals,
-- colour fields, triangle-stream order, materials and bounds all participate.
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

local IDENTITY = "atlas:v1:fixture:wall:0,0:false|d1.000:e0.00010"

print("[TEST] Starting compiled geometry store tests...")

check("identical neutral input + identity serializes deterministically", function()
    local model = sampleModel()
    assert(store.encode(model, IDENTITY) == store.encode(model, IDENTITY),
        "identical inputs produced different bytes")
end)

check("round-trip preserves every vertex field and triangle-stream position EXACTLY", function()
    local model = sampleModel()
    local decoded, identity = store.decode(store.encode(model, IDENTITY), IDENTITY)
    assert(decoded, "decode returned nil")
    assert(identity == IDENTITY, "embedded identity changed")
    assert(#decoded.groups == #model.groups, "group count")
    for groupIndex, group in ipairs(model.groups) do
        local out = decoded.groups[groupIndex]
        assert(out.material == group.material, "material " .. groupIndex)
        assert(#out.vertices == #group.vertices, "vertex count in group " .. groupIndex)
        for vertexIndex, vertex in ipairs(group.vertices) do
            for field = 1, 12 do
                local a, b = vertex[field], out.vertices[vertexIndex][field]
                -- Equality, not a tolerance. A tolerance here would accept the
                -- float32 truncation this test exists to forbid.
                assert(a == b, string.format(
                    "group %d vertex %d field %d: %.17g ~= %.17g",
                    groupIndex, vertexIndex, field, a, b))
            end
        end
    end
end)

check("round-trip preserves bounds and vertexCount", function()
    local model = sampleModel()
    local decoded = store.decode(store.encode(model, IDENTITY), IDENTITY)
    assert(decoded.vertexCount == model.vertexCount, "vertexCount")
    for _, key in ipairs({ "minX", "minY", "minZ", "maxX", "maxY", "maxZ" }) do
        assert(decoded.bounds[key] == model.bounds[key],
            key .. ": " .. tostring(decoded.bounds[key]) .. " ~= " .. tostring(model.bounds[key]))
    end
end)

check("renaming an artifact cannot bypass its embedded identity", function()
    local blob = store.encode(sampleModel(), IDENTITY)
    assert(store.decode(blob, IDENTITY .. ":other") == nil, "accepted a mismatched artifact identity")
end)

check("quality/compiler identity selects a different artifact path", function()
    local normal = "atlas:v1:fixture|d1.000:e0.00010"
    local coarse = "atlas:v1:fixture|d0.250:e0.00080"
    local newer = "atlas:v2:fixture|d1.000:e0.00010"
    assert(store.artifactName(normal) ~= store.artifactName(coarse), "quality did not select a new artifact")
    assert(store.artifactName(normal) ~= store.artifactName(newer), "compiler version did not select a new artifact")
end)

check("a blob without the magic header is refused", function()
    assert(store.decode("not a geometry file at all", IDENTITY) == nil, "accepted foreign data")
end)

check("a truncated blob is refused rather than half-decoded", function()
    local blob = store.encode(sampleModel(), IDENTITY)
    -- A truncated read may raise inside unpack; either nil or a caught error is
    -- acceptable, a partial model is not.
    local ok, result = pcall(store.decode, blob:sub(1, math.floor(#blob / 2)), IDENTITY)
    assert(not ok or result == nil, "a truncated blob produced a model")
end)

check("a future format version is refused, not misread", function()
    local blob = store.encode(sampleModel(), IDENTITY)
    -- Byte 6..9 is the little-endian format version immediately after SRGEO.
    local bumped = blob:sub(1, 5) .. love.data.pack("string", "<I4", 99) .. blob:sub(10)
    assert(store.decode(bumped, IDENTITY) == nil, "accepted an unknown format version")
end)

check("release provenance accepts identical source bytes and rejects changed identity", function()
    local sourcePath = "tests/fixtures/geometry/valid_plane/asset.json"
    local digest = assert(store.fileDigest(sourcePath), "fixture digest")
    local manifest = {
        version = store.MANIFEST_VERSION,
        formatVersion = store.FORMAT_VERSION,
        compilerVersion = 1,
        sourceFiles = { { path = sourcePath, digest = digest } },
        entries = {},
    }
    local valid, reason = store.validateManifest(manifest)
    assert(valid, tostring(reason))
    manifest.sourceFiles[1].digest = digest:gsub("^.", digest:sub(1, 1) == "0" and "1" or "0")
    local stillValid, changedReason = store.validateManifest(manifest)
    assert(not stillValid and tostring(changedReason):match("source changed"),
        "changed source identity was not rejected")
end)

check("manifest compiler mismatch rejects cleanly", function()
    local sourcePath = "tests/fixtures/geometry/valid_plane/asset.json"
    local manifest = {
        version = store.MANIFEST_VERSION,
        formatVersion = store.FORMAT_VERSION,
        compilerVersion = 1,
        sourceFiles = { { path = sourcePath, digest = store.fileDigest(sourcePath) } },
        entries = {},
    }
    local valid, reason = store.validateManifest(manifest, "atlas:v99:fixture|d1.000:e0.00010")
    assert(not valid and reason == "compiler version mismatch", "compiler mismatch was accepted")
end)

check("an absent release prebake remains a cache miss", function()
    store.resetPrebakeManifestCache()
    assert(store.loadPrebake("atlas:v999:missing|d1.000:e0.00010") == nil,
        "fabricated absent prebake loaded")
end)

check("an empty model is not written", function()
    assert(store.save("test-empty-key", { groups = {} }) == false, "wrote an empty model")
end)

print(string.format("=== Compiled Geometry Store Tests: %d passed, %d failed ===",
    passed, failed))
if failed > 0 then
    require("tests.fail_fast")("compiled geometry store tests failed", failed)
end
