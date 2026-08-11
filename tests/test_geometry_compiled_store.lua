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

local function assertSameModel(expected, actual, prefix)
    prefix = prefix or "model"
    assert(actual, prefix .. ": actual model missing")
    assert(actual.vertexCount == expected.vertexCount, prefix .. ": vertexCount")
    assert(#actual.groups == #expected.groups, prefix .. ": group count")
    for groupIndex, group in ipairs(expected.groups) do
        local out = actual.groups[groupIndex]
        assert(out.material == group.material, prefix .. ": material " .. groupIndex)
        assert(#out.vertices == #group.vertices, prefix .. ": vertex count in group " .. groupIndex)
        for vertexIndex, vertex in ipairs(group.vertices) do
            for field = 1, 12 do
                local a, b = vertex[field], out.vertices[vertexIndex][field]
                assert(a == b, string.format(
                    "%s group %d vertex %d field %d: %.17g ~= %.17g",
                    prefix, groupIndex, vertexIndex, field, a, b))
            end
        end
    end
    for _, key in ipairs({ "minX", "minY", "minZ", "maxX", "maxY", "maxZ" }) do
        assert(actual.bounds[key] == expected.bounds[key],
            prefix .. " " .. key .. ": " .. tostring(actual.bounds[key])
                .. " ~= " .. tostring(expected.bounds[key]))
    end
end

local function withGeometryQuality(density, maxError, fn)
    local quality = require("engine.geometry.quality")
    quality.setDensity(density)
    quality.setMaxError(maxError)
    local ok, a, b = pcall(fn)
    quality.setDensity(nil)
    quality.setMaxError(nil)
    if not ok then error(a, 0) end
    return a, b
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
    assert(identity == IDENTITY, "embedded identity changed")
    assertSameModel(model, decoded, "round-trip")
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

check("a real prebaked plane exactly reproduces the neutral runtime compiler", function()
    withGeometryQuality(0.25, 0.0008, function()
        local prebake = require("engine.geometry.prebake")
        local plane = require("engine.geometry.plane")
        local heightPath = "tests/fixtures/geometry/valid_plane/height.png"
        local texturePath = "tests/fixtures/geometry/valid_plane/albedo.png"
        local def = {
            id = "fixture",
            texture = texturePath,
            heightMap = heightPath,
            tileWidth = 1,
            tileHeight = 1,
            heightMapScale = { wall = 0.1 },
            heightMapMeshColumns = 2,
            heightMapMeshRows = 2,
            heightMapSampleColumns = 2,
            heightMapSampleRows = 2,
            heightMapTriangleBudget = 2,
            heightMapOffset = 0.004,
            base = { walls = { { id = "fixture_wall", middle = { 0, 0 } } } },
        }
        local loader = {
            root = "tests/fixtures/geometry/valid_plane",
            maps = { { id = 1, tileset = "fixture" } },
            getTileset = function() return def end,
        }
        local manifest = prebake.build(loader)
        local expectedKey = prebake.runtimeKey(heightPath, "wall", 0, 0, false)
        local entry
        for _, candidate in ipairs(manifest.entries) do
            if candidate.key == expectedKey then entry = candidate break end
        end
        assert(entry and entry._blob, "prebaker did not emit the runtime wall identity")
        local baked = store.decode(entry._blob, expectedKey)

        -- Reconstruct the exact live atlas input without using the prebaker's
        -- private helpers, then ask plane.build() directly. A 1x1 tile keeps
        -- this unit fixture tiny while still exercising dense sampling, QEM,
        -- normals, sealing, UVs and final bounds.
        local source = love.image.newImageData(heightPath)
        local tile = love.image.newImageData(1, 1)
        tile:setPixel(0, 0, source:getPixel(0, 0))
        local texture = love.image.newImageData(texturePath)
        local spec = {
            id = "tileset_height_wall_0_0",
            label = "tileset height map '" .. heightPath .. "' wall",
            topology = "plane",
            role = "surfaceFixture",
            surface = "wall",
            heightOperation = "add",
            heightScale = 0.1,
            meshColumns = 2,
            meshRows = 2,
            sampleColumns = 2,
            sampleRows = 2,
            triangleBudget = 2,
            offset = 0.004,
            sealPerimeter = true,
        }
        local function uv()
            return 0.5 / texture:getWidth(), 0.5 / texture:getHeight()
        end
        local direct = plane.build(spec, { { data = tile, scale = 0.1, operation = "add" } }, uv)
        assertSameModel(direct, baked, "prebake vs direct plane.build")
    end)
end)

check("ambiguous legacy runtime identity is rejected instead of shipping stale geometry", function()
    withGeometryQuality(0.25, 0.0008, function()
        local prebake = require("engine.geometry.prebake")
        local def = {
            id = "fixture",
            texture = "tests/fixtures/geometry/valid_plane/albedo.png",
            heightMap = "tests/fixtures/geometry/valid_plane/height.png",
            tileWidth = 1,
            tileHeight = 1,
            heightMapScale = { wall = 0.1 },
            heightMapMeshColumns = 2,
            heightMapMeshRows = 2,
            heightMapSampleColumns = 2,
            heightMapSampleRows = 2,
            heightMapTriangleBudget = 2,
            heightMapOffset = 0.004,
            base = { walls = { { id = "fixture_wall", middle = { 0, 0 } } } },
        }
        local loader = {
            root = "tests/fixtures/geometry/valid_plane",
            maps = {
                { id = 1, tileset = "fixture" },
                { id = 2, tileset = "fixture", tilesetOverride = {
                    heightMapScale = { wall = 0.2 },
                    -- Offset moves every emitted surface even when this tiny
                    -- fixture's sampled height happens to be neutral. That
                    -- guarantees the two resolved compiler inputs produce
                    -- different neutral bytes while retaining the same legacy
                    -- runtime lookup key.
                    heightMapOffset = 0.02,
                } },
            },
            getTileset = function() return def end,
        }
        local ok, err = pcall(prebake.build, loader)
        assert(not ok and tostring(err):match("runtime identity is insufficient"),
            "different neutral geometry sharing one runtime key was not rejected")
    end)
end)

check("current campaign's eligible prebake set compiles without ambiguous identities", function()
    withGeometryQuality(1, 0.0001, function()
        -- main.lua initializes data.loader before running suites, so this is the
        -- actual materialized default campaign rather than another bespoke
        -- fixture. If a real tileset override collides under the current
        -- runtime key, the export-time compiler must fail here in CI too.
        local prebake = require("engine.geometry.prebake")
        local loader = require("data.loader")
        assert(type(loader.maps) == "table" and #loader.maps > 0, "production loader was not initialized")
        local manifest = prebake.build(loader)
        assert(manifest.quality == "d1.000:e0.00010", "unexpected production prebake quality")
        assert(#manifest.entries > 0, "current campaign produced no eligible prebakes")
        local seen = {}
        for _, entry in ipairs(manifest.entries) do
            assert(not seen[entry.key], "duplicate current-campaign prebake key: " .. tostring(entry.key))
            seen[entry.key] = true
            local decoded = store.decode(entry._blob, entry.key)
            assert(decoded and decoded.vertexCount > 0, "current-campaign prebake did not decode: " .. tostring(entry.key))
        end
    end)
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
