local vertex = require("engine.generated.vertex-shading")
local sprite_timing = require("engine.generated.sprite-timing")

local EPSILON = 1e-12
local function close(actual, expected, label, epsilon)
    epsilon = epsilon or EPSILON
    if math.abs(actual - expected) > epsilon then
        error(string.format("%s: expected %.17g, got %.17g", label, expected, actual), 0)
    end
end

local function equal(actual, expected, label)
    if actual ~= expected then
        error(string.format("%s: expected %s, got %s", label, tostring(expected), tostring(actual)), 0)
    end
end

close(vertex.hash01(0, 0, 0), 0.9616300366300367, "hash 0,0,0")
close(vertex.hash01(1, 2, 1729), 0.18543956043956045, "hash 1,2,1729")
close(vertex.hash01(-1, 0, 23), 0.6313644688644688, "hash -1,0,23")
close(vertex.valueNoise(0.5, 0.5, 1729), 0.42679334554334547, "value noise .5,.5")
close(vertex.fractalNoise(0.5, 0.5, 1729), 0.4540415838459217, "fractal .5,.5")
close(vertex.fractalNoise(1.25, 2.75, 1729), 0.45447714242048237, "fractal 1.25,2.75")
close(vertex.fractalNoise(-0.25, 0.5, 23), 0.3765472024340493, "fractal -.25,.5")

local layer = {
    type = "colorNoise",
    colorA = { 0.8, 0.85, 0.9 },
    colorB = { 1, 0.95, 0.85 },
    strength = 0.5,
    scale = 8,
    seed = 1729,
}
local rgb = vertex.sample({ layer }, 3, 4)
close(rgb[1], 0.950024025251864, "sample r")
close(rgb[2], 0.9500120126259319, "sample g")
close(rgb[3], 0.937493993687034, "sample b")

-- Same deterministic 2,048-point sweep as the Node target. The Park-Miller
-- products remain exact IEEE integers, so this is cross-host arithmetic
-- conformance evidence rather than a second shading implementation.
local state = 1729
local checksum = 0
local minimum = 1
local maximum = 0
for index = 0, 2047 do
    state = (state * 48271) % 2147483647
    local x = (state / 2147483647) * 2048 - 1024
    state = (state * 48271) % 2147483647
    local y = (state / 2147483647) * 2048 - 1024
    state = (state * 48271) % 2147483647
    local seed = math.floor((state / 2147483647) * 4294967292) - 2147483646
    local value = vertex.fractalNoise(x, y, seed)
    checksum = checksum + value * (index + 1)
    minimum = math.min(minimum, value)
    maximum = math.max(maximum, value)
end
close(checksum, 1048868.5265851377, "2048-point shading checksum", 1e-7)
close(minimum, 0.11815460869851695, "2048-point minimum")
close(maximum, 0.8671328344589253, "2048-point maximum")

local parsed = sprite_timing.parseKey(" Pixie[fps=15] ")
equal(parsed.fileKey, "Pixie", "trimmed file key")
equal(parsed.tokens.fps, 15, "parsed fps")
parsed = sprite_timing.parseKey("pixie[fps=9][fps=12]")
equal(parsed.tokens.fps, 12, "repeated token last-wins")
parsed = sprite_timing.parseKey("pixie[speed=2]")
equal(sprite_timing.effectiveFps(parsed.tokens), 8, "speed conversion")
parsed = sprite_timing.parseKey("Cursor")
equal(sprite_timing.effectiveFps(parsed.tokens), 4, "default rate")
parsed = sprite_timing.parseKey("x[fps=0]")
equal(sprite_timing.effectiveFps(parsed.tokens), 0, "zero fps")
parsed = sprite_timing.parseKey("x[speed=0]")
equal(sprite_timing.effectiveFps(parsed.tokens), 0, "zero speed")
parsed = sprite_timing.parseKey("x[fps=0x10]")
equal(sprite_timing.effectiveFps(parsed.tokens), 16, "hex numeric token")
parsed = sprite_timing.parseKey("x[fps=15oops]")
equal(sprite_timing.effectiveFps(parsed.tokens), nil, "malformed numeric token")
parsed = sprite_timing.parseKey("x[=2]")
equal(parsed.fileKey, "x[=2]", "empty token key is literal")
parsed = sprite_timing.parseKey("x[a=]")
equal(parsed.fileKey, "x[a=]", "empty token value is literal")

local timing = sprite_timing.resolveTiming({ fps = 9 }, { fps = 15 })
equal(timing.fps, 9, "same-token key override")
equal(timing.source, "key", "same-token key provenance")
timing = sprite_timing.resolveTiming({ speed = 2 }, { fps = 15 })
equal(timing.fps, 15, "fps globally outranks speed")
equal(timing.source, "filename", "cross-token filename provenance")
timing = sprite_timing.resolveTiming({ fps = 9 }, { speed = 2 })
equal(timing.fps, 9, "key fps outranks filename speed")
timing = sprite_timing.resolveTiming({ speed = 2 }, { speed = 3 })
equal(timing.fps, 8, "key speed replaces filename speed")
timing = sprite_timing.resolveTiming({}, {})
equal(timing.fps, 4, "resolved default")
equal(timing.source, "default", "default provenance")

local function bench(fn, iterations)
    for _ = 1, 2000 do fn() end
    local started = love.timer.getTime()
    for _ = 1, iterations do fn() end
    return (love.timer.getTime() - started) * 1000
end

local vertexMs = bench(function()
    return vertex.fractalNoise(1.25, 2.75, 1729)
end, 100000)
local spriteMs = bench(function()
    local value = sprite_timing.parseKey("Pixie[speed=2][fps=15]")
    return sprite_timing.effectiveFps(value.tokens)
end, 100000)

print("SHARED SEMANTICS LOVE CONFORMANCE OK")
print(string.format("MEASURE_SHARED_LOVE vertex_fractal_100k_ms=%.3f sprite_parse_and_rate_100k_ms=%.3f", vertexMs, spriteMs))
love.event.quit(0)
