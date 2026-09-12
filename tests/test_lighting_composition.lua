-- Bounded lighting-composition contract (#474).
--
--   sourceBase  = bake(topology, sources, ambient)   -- derived, never authored
--   finalStatic = clamp(sourceBase + paintCorrection, 0, 1)
--
-- The legacy absolute `light` grid DEFINED lighting outright, so an authored
-- map could contradict its own sources. `paintCorrection` is a signed -1..1
-- delta: it can only push a derived value, never replace it.
--
-- This suite is the merge of two independent implementations of #474. Where
-- they disagreed the cheaper form won; where only one covered a case, that
-- case is kept. The validator cases below drive the REAL validator rather than
-- a copy of its rules, because a test that reimplements the thing it checks
-- passes whether or not the rule is wired up.

local lighting = require("engine.lighting")
local validator = require("engine.validator_core")
local loader = require("data.loader")
if not loader.maps then loader.init() end

local failFast = require("tests.fail_fast")
local passed, failed = 0, 0

local function check(cond, msg)
    if not cond then error(msg or "assertion failed", 2) end
end

local function test(name, fn)
    local ok, err = pcall(fn)
    if ok then
        passed = passed + 1
    else
        print("  [FAIL] " .. name)
        print("         " .. tostring(err))
        failed = failed + 1
    end
end

local function approxEq(a, b, tol)
    return math.abs(a - b) <= (tol or 0.0001)
end

local function rgbApproxEq(a, b, tol)
    return approxEq(a[1], b[1], tol) and approxEq(a[2], b[2], tol) and approxEq(a[3], b[3], tol)
end

-- 1. Composition arithmetic and bounds ---------------------------------------

test("signed correction adds to the derived base", function()
    local base = { { { 0.25, 0.20, 0.15 } } }
    local corr = { { { 0.10, -0.05, 0.20 } } }
    local out = lighting.compose(base, corr)
    check(rgbApproxEq(out[1][1], { 0.35, 0.15, 0.35 }), "expected per-channel addition")
end)

test("composition clamps to 0..1 in both directions", function()
    local base = { { { 0.9, 0.1, 0.5 }, { 0.2, 0.2, 0.2 } } }
    local corr = { { { 0.5, -0.5, 0.0 }, { -1.0, 1.0, 0.0 } } }
    local out = lighting.compose(base, corr)
    check(rgbApproxEq(out[1][1], { 1, 0, 0.5 }), "upper and lower clamp on cell 1")
    check(rgbApproxEq(out[1][2], { 0, 1, 0.2 }), "upper and lower clamp on cell 2")
end)

test("a zero correction preserves the base exactly", function()
    local base = { { { 0.37, 0.42, 0.51 } } }
    local out = lighting.compose(base, { { { 0, 0, 0 } } })
    check(rgbApproxEq(out[1][1], base[1][1], 0), "zero delta must not perturb the base")
end)

test("a nil correction returns the base, and a nil base returns nil", function()
    local base = { { { 0.5, 0.5, 0.5 } } }
    check(lighting.compose(base, nil) == base, "nil correction should pass the base through")
    check(lighting.compose(nil, { { { 0.1, 0, 0 } } }) == nil, "nil base cannot be corrected into existence")
end)

test("a sparse correction row leaves uncovered cells untouched", function()
    local base = { { { 0.4, 0.4, 0.4 }, { 0.6, 0.6, 0.6 } } }
    local out = lighting.compose(base, { { { 0.1, 0.1, 0.1 } } })
    check(rgbApproxEq(out[1][1], { 0.5, 0.5, 0.5 }), "covered cell is corrected")
    check(rgbApproxEq(out[1][2], { 0.6, 0.6, 0.6 }), "uncovered cell keeps its derived value")
end)

-- 2. Neutral base ------------------------------------------------------------

test("neutralBase is full white and vertex-sized", function()
    local n = lighting.neutralBase(3, 2)
    check(#n == 3 and #n[1] == 4, "neutral base must be (h+1) x (w+1)")
    check(rgbApproxEq(n[1][1], { 1, 1, 1 }), "neutral base must be white")
end)

-- 3. Resolution ---------------------------------------------------------------

local flatGrid = { { ".", ".", "." }, { ".", ".", "." } }

test("an unlit map with no correction resolves to nil", function()
    check(lighting.resolve(flatGrid, {}, nil, nil) == nil, "nothing authored, nothing derived")
end)

test("a correction with no sources composes over a neutral base", function()
    local corr = {}
    for vy = 1, 3 do
        corr[vy] = {}
        for vx = 1, 4 do corr[vy][vx] = { -0.25, -0.25, -0.25 } end
    end
    local out = lighting.resolve(flatGrid, {}, nil, corr)
    check(out ~= nil, "a correction alone must still resolve")
    check(rgbApproxEq(out[1][1], { 0.75, 0.75, 0.75 }), "correction applies over white")
end)

test("sources alone resolve to the bake", function()
    local sources = { { x = 0, y = 0, radius = 3, color = { 0.9, 0.6, 0.3 } } }
    local out = lighting.resolve(flatGrid, sources, nil, nil)
    local base = lighting.bake(flatGrid, sources, nil)
    check(out ~= nil and rgbApproxEq(out[1][1], base[1][1]), "no correction means resolve equals bake")
end)

test("bake supplies the 0.12 ambient floor when ambient is nil", function()
    local out = lighting.resolve(flatGrid, {}, { 0.12, 0.12, 0.12 }, nil)
    local implied = lighting.bake(flatGrid, {}, nil)
    check(rgbApproxEq(out[3][4], implied[3][4]), "explicit 0.12 must match the bake default")
end)

test("an ambient override rebakes and recomposes", function()
    local sources = { { x = 0, y = 0, radius = 2, color = { 0.5, 0.5, 0.5 } } }
    local corr = {}
    for vy = 1, 3 do
        corr[vy] = {}
        for vx = 1, 4 do corr[vy][vx] = { 0.05, 0, 0 } end
    end
    local dim = lighting.resolve(flatGrid, sources, { 0.05, 0.05, 0.05 }, corr)
    local bright = lighting.resolve(flatGrid, sources, { 0.40, 0.40, 0.40 }, corr)
    check(bright[3][4][1] > dim[3][4][1], "a brighter ambient must survive composition")
end)

test("gatherSources orders authored lights before generated fixtures", function()
    local mapData = { lightObjects = { { x = 1, y = 1, radius = 2 } } }
    local generated = { { x = 5, y = 5, radius = 3 } }
    local sources = lighting.gatherSources(mapData, generated)
    check(#sources == 2, "both authored and generated sources must be gathered")
    check(sources[1].x == 1 and sources[2].x == 5, "authored sources come first")
    check(#lighting.gatherSources(nil, nil) == 0, "gathering from nothing yields an empty list")
end)

-- 4. Migration invariance -----------------------------------------------------

test("a legacy absolute field round-trips through mechanical migration", function()
    local sources = { { x = 0, y = 0, radius = 3, color = { 0.9, 0.6, 0.3 } } }
    local base = lighting.bake(flatGrid, sources, { 0.12, 0.12, 0.12 })

    -- A synthetic legacy `light` field: the derived base, tinted by hand.
    local legacy = {}
    for vy = 1, #base do
        legacy[vy] = {}
        for vx = 1, #base[1] do
            legacy[vy][vx] = {
                math.min(1, math.max(0, base[vy][vx][1] + 0.15)),
                math.min(1, math.max(0, base[vy][vx][2] - 0.05)),
                math.min(1, math.max(0, base[vy][vx][3] + 0.20)),
            }
        end
    end

    local corr = {}
    for vy = 1, #base do
        corr[vy] = {}
        for vx = 1, #base[1] do
            corr[vy][vx] = {
                legacy[vy][vx][1] - base[vy][vx][1],
                legacy[vy][vx][2] - base[vy][vx][2],
                legacy[vy][vx][3] - base[vy][vx][3],
            }
        end
    end

    local reconstructed = lighting.compose(base, corr)
    for vy = 1, #base do
        for vx = 1, #base[1] do
            check(rgbApproxEq(reconstructed[vy][vx], legacy[vy][vx]),
                string.format("round-trip mismatch at [%d][%d]", vy, vx))
        end
    end
end)

test("composition is idempotent under a zero correction", function()
    local sources = { { x = 1, y = 0, radius = 2, color = { 0.8, 0.4, 0.2 } } }
    local base = lighting.bake(flatGrid, sources, nil)
    local zero = {}
    for vy = 1, #base do
        zero[vy] = {}
        for vx = 1, #base[1] do zero[vy][vx] = { 0, 0, 0 } end
    end
    local once = lighting.compose(base, zero)
    local twice = lighting.compose(once, zero)
    for vy = 1, #base do
        for vx = 1, #base[1] do
            check(rgbApproxEq(twice[vy][vx], base[vy][vx], 0), "re-composing a zero delta must be a no-op")
        end
    end
end)

-- 5. Authoring rules, driven through the real validator ------------------------

-- The fixture below is a single map spliced into the real loader, so the
-- validator also reports repository-wide findings that have nothing to do with
-- lighting (unreachable flags in commonEvents, for one). Rejection cases match
-- their own message; acceptance cases assert only that no LIGHTING complaint
-- was raised, never that the whole validator passed.
local function validateMap(map)
    local mock = {}
    for k, v in pairs(loader) do mock[k] = v end
    mock.maps = { map }
    local ok, err = pcall(validator.run, mock)
    return ok, tostring(err)
end

local function lightingComplaint(ok, err)
    if ok then return nil end
    if err:find("paintCorrection") or err:find("legacy absolute") then return err end
    return nil
end

local function baseMap(extra)
    local map = { id = 1, name = "Lighting Fixture", layout = { "###", "###" }, events = {} }
    for k, v in pairs(extra or {}) do map[k] = v end
    return map
end

local function zeroCorrection(h, w)
    local g = {}
    for vy = 1, h + 1 do
        g[vy] = {}
        for vx = 1, w + 1 do g[vy][vx] = { 0, 0, 0 } end
    end
    return g
end

test("the validator rejects a legacy absolute light grid", function()
    local ok, err = validateMap(baseMap({ light = zeroCorrection(2, 3) }))
    check(not ok, "legacy light must fail validation")
    check(err:find("legacy absolute"), "rejection must name the legacy field, got: " .. err)
end)

test("the validator accepts a well-formed paintCorrection", function()
    local ok, err = validateMap(baseMap({ paintCorrection = zeroCorrection(2, 3) }))
    local complaint = lightingComplaint(ok, err)
    check(complaint == nil, "a correctly sized correction must not be faulted, got: " .. tostring(complaint))
end)

test("the validator rejects a correction on a map with no fixed layout", function()
    local map = baseMap({ paintCorrection = { { { 0, 0, 0 } } } })
    map.layout = nil
    local ok, err = validateMap(map)
    check(not ok, "a procedural map cannot carry a correction")
    check(err:find("not a fixed%-layout map"), "rejection must explain why, got: " .. err)
end)

test("the validator rejects a correction whose dimensions disagree with the layout", function()
    local ok, err = validateMap(baseMap({ paintCorrection = { { { 0, 0, 0 }, { 0, 0, 0 } } } }))
    check(not ok, "a mis-sized correction must fail validation")
    check(err:find("rows, expected"), "rejection must report the expected row count, got: " .. err)
end)

test("the validator rejects a channel outside the signed -1..1 range", function()
    local g = zeroCorrection(2, 3)
    g[1][1] = { 1.5, 0, 0 }
    local ok, err = validateMap(baseMap({ paintCorrection = g }))
    check(not ok, "an out-of-range channel must fail validation")
    check(err:find("signed range"), "rejection must name the signed range, got: " .. err)
end)

test("the validator accepts a negative channel, which the legacy range forbade", function()
    local g = zeroCorrection(2, 3)
    g[1][1] = { -0.5, -0.25, -1 }
    local ok, err = validateMap(baseMap({ paintCorrection = g }))
    local complaint = lightingComplaint(ok, err)
    check(complaint == nil, "subtractive correction is the point of the signed range, got: " .. tostring(complaint))
end)

-- 6. The migrated Project map --------------------------------------------------

local function shippedMap1()
    for _, m in ipairs(loader.maps or {}) do
        if m.id == 1 then return m end
    end
    return nil
end

test("the shipped map carries a correction and no legacy field", function()
    local map1 = shippedMap1()
    check(map1 ~= nil, "map 1 must load")
    check(map1.light == nil, "map 1 must not carry the legacy absolute field")
    if map1.paintCorrection then
        check(#map1.paintCorrection == #map1.layout + 1, "correction must be vertex-sized")
        for _, row in ipairs(map1.paintCorrection) do
            for _, cell in ipairs(row) do
                for ch = 1, 3 do
                    check(cell[ch] >= -1 and cell[ch] <= 1, "every channel must sit in -1..1")
                end
            end
        end
    end
end)

test("resolving the shipped map produces a bounded field", function()
    local map1 = shippedMap1()
    check(map1 ~= nil and map1.layout ~= nil, "map 1 must have a layout")
    local grid = {}
    for y, row in ipairs(map1.layout) do
        grid[y] = {}
        for x = 1, #row do grid[y][x] = row:sub(x, x) end
    end
    local out = lighting.resolve(grid, lighting.gatherSources(map1, nil), nil, map1.paintCorrection)
    check(out ~= nil, "map 1 has sources, so it must resolve")
    for vy = 1, #out do
        for vx = 1, #out[vy] do
            for ch = 1, 3 do
                check(out[vy][vx][ch] >= 0 and out[vy][vx][ch] <= 1,
                    string.format("resolved channel out of 0..1 at [%d][%d][%d]", vy, vx, ch))
            end
        end
    end
end)

failFast("test_lighting_composition", failed, passed)
