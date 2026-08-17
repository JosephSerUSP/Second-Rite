-- Shared static-light numeric corpus for #475. The same JSON is consumed by
-- Studio's Node test so ambient/falloff/occlusion/clamp behavior cannot drift
-- independently across the two implementations.
local lighting = require("engine.lighting")
local json = require("data.json")

local fixtureText = assert(love.filesystem.read("tests/fixtures/lighting_parity.json"))
local fixture = json.decode(fixtureText)
local tolerance = fixture.tolerance or 1e-8

local function fail(message)
    error("lighting parity: " .. message, 0)
end

local function gridFromRows(rows)
    local grid = {}
    for y, row in ipairs(rows) do
        grid[y] = {}
        for x = 1, #row do grid[y][x] = row:sub(x, x) end
    end
    return grid
end

local function closeEnough(actual, expected)
    return math.abs(actual - expected) <= tolerance
end

local function assertRgb(caseName, label, actual, expected)
    for channel = 1, 3 do
        if not closeEnough(actual[channel], expected[channel]) then
            fail(("%s %s channel %d expected %.12f, got %.12f")
                :format(caseName, label, channel, expected[channel], actual[channel]))
        end
    end
end

for _, case in ipairs(fixture.cases) do
    local field = lighting.bake(gridFromRows(case.rows), case.sources, case.ambient)
    for _, sample in ipairs(case.samples or {}) do
        local actual = field[sample.y + 1][sample.x + 1]
        assertRgb(case.name, ("vertex (%d,%d)"):format(sample.x, sample.y), actual, sample.expect)
    end

    for _, sample in ipairs(case.surfaceSamples or {}) do
        local base = field[sample.y + 1][sample.x + 1]
        local factor = assert(fixture.orientationFactors[sample.faceRole],
            "missing orientation factor for " .. tostring(sample.faceRole))
        local actual = { base[1] * factor, base[2] * factor, base[3] * factor }
        assertRgb(case.name, sample.faceRole, actual, sample.expect)
    end
end

-- Bind the shared corpus' side-wall sample to the real runtime presentation
-- rule rather than merely hard-coding 0.76 inside this module. viewport_3d keeps
-- colorAt private, so source-level ownership is the narrow non-production seam.
local viewportSource = assert(love.filesystem.read("presentation/viewport_3d.lua"))
if not viewportSource:find("r %* 0%.76", 1) or not viewportSource:find("g %* 0%.76", 1)
        or not viewportSource:find("b %* 0%.76", 1) then
    fail("runtime side-wall orientation modulation is no longer the fixture's 0.76 rule")
end

print("LIGHTING PARITY TEST OK")
return true
