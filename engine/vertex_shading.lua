-- Deterministic, renderer-neutral vertex shading for map/environment colour variation.
--
-- This is deliberately NOT illumination. Authored shading layers describe local
-- material/environment tint in map space; presentation composes that tint with
-- static lighting afterwards. The same layer therefore works on a fixed layout
-- and on any procedural topology resolved under it.
local vertex_shading = {}

local MODULUS = 65521
local HASH_MULTIPLIER = 25173
local HASH_ADDEND = 13849
local MAX_SEED = 2147483646
local FRACTAL_PERSISTENCE = 0.55
local FRACTAL_OCTAVES = {
    { 0.8, -0.6, 0.6, 0.8, 3.17, -5.29 },
    { 0.6, 0.8, -0.8, 0.6, 17.17, -9.31 },
    { -0.8, 0.6, -0.6, -0.8, -13.73, 21.47 },
    { -0.6, -0.8, 0.8, -0.6, 29.11, 14.53 },
}

local function positiveModulo(value, modulus)
    local result = value % modulus
    if result < 0 then result = result + modulus end
    return result
end

local function lerp(a, b, t)
    return a + (b - a) * t
end

local function smoothstep(t)
    return t * t * (3 - 2 * t)
end

-- All intermediate products stay far below 2^53. That matters because LuaJIT
-- numbers and browser JavaScript numbers are both IEEE doubles: the paired JS
-- implementation can therefore reproduce these samples exactly enough to be a
-- useful authoring/runtime contract instead of a lookalike noise function.
function vertex_shading.hash01(x, y, seed)
    local ix = positiveModulo(math.floor(x), MODULUS)
    local iy = positiveModulo(math.floor(y), MODULUS)
    local iseed = positiveModulo(math.floor(seed or 0), MODULUS)
    local value = (ix * 3749 + iy * 9151 + iseed * 1013) % MODULUS
    value = (value * HASH_MULTIPLIER + HASH_ADDEND) % MODULUS
    value = (value * HASH_MULTIPLIER + HASH_ADDEND) % MODULUS
    return value / (MODULUS - 1)
end

function vertex_shading.valueNoise(x, y, seed)
    local x0, y0 = math.floor(x), math.floor(y)
    local fx, fy = x - x0, y - y0
    local sx, sy = smoothstep(fx), smoothstep(fy)
    local top = lerp(
        vertex_shading.hash01(x0, y0, seed),
        vertex_shading.hash01(x0 + 1, y0, seed), sx)
    local bottom = lerp(
        vertex_shading.hash01(x0, y0 + 1, seed),
        vertex_shading.hash01(x0 + 1, y0 + 1, seed), sx)
    return lerp(top, bottom, sy)
end

-- Same four literal rotated/offset octaves as Studio. The first octave already
-- breaks the lattice's authored X/Y alignment; later octaves add progressively
-- smaller structure. Weighted normalization keeps the result in 0..1.
function vertex_shading.fractalNoise(x, y, seed)
    local total, amplitude, normalizer, frequency = 0, 1, 0, 1
    for octaveIndex, octave in ipairs(FRACTAL_OCTAVES) do
        local xx, xy, yx, yy = octave[1], octave[2], octave[3], octave[4]
        local rotatedX = (x * xx + y * xy + octave[5]) * frequency
        local rotatedY = (x * yx + y * yy + octave[6]) * frequency
        total = total + vertex_shading.valueNoise(
            rotatedX, rotatedY, seed + (octaveIndex - 1) * 7919) * amplitude
        normalizer = normalizer + amplitude
        amplitude = amplitude * FRACTAL_PERSISTENCE
        frequency = frequency * 2
    end
    return total / normalizer
end

local function validateRgb(problems, value, where)
    if type(value) ~= "table" or #value ~= 3 then
        problems[#problems + 1] = where .. " must be an RGB triple"
        return
    end
    for channel = 1, 3 do
        if type(value[channel]) ~= "number" or value[channel] < 0 or value[channel] > 1 then
            problems[#problems + 1] = where .. " channel " .. channel .. " must be a number in 0..1"
        end
    end
end

local function isDenseList(value)
    if type(value) ~= "table" then return false end
    local count = 0
    for key in pairs(value) do
        if type(key) ~= "number" or key < 1 or key ~= math.floor(key) then return false end
        count = count + 1
    end
    return count == #value
end

function vertex_shading.validate(layers, where)
    where = where or "vertexShadingLayers"
    local problems = {}
    if layers == nil then return problems end
    if not isDenseList(layers) then
        problems[#problems + 1] = where .. " must be a dense list"
        return problems
    end
    for index, layer in ipairs(layers) do
        local desc = where .. "[" .. index .. "]"
        if type(layer) ~= "table" then
            problems[#problems + 1] = desc .. " must be an object"
        elseif layer.type ~= "colorNoise" then
            problems[#problems + 1] = desc .. ".type '" .. tostring(layer.type)
                .. "' is unsupported (expected colorNoise)"
        else
            validateRgb(problems, layer.colorA, desc .. ".colorA")
            validateRgb(problems, layer.colorB, desc .. ".colorB")
            if type(layer.strength) ~= "number" or layer.strength < 0 or layer.strength > 1 then
                problems[#problems + 1] = desc .. ".strength must be a number in 0..1"
            end
            if type(layer.scale) ~= "number" or layer.scale <= 0 then
                problems[#problems + 1] = desc .. ".scale must be a number > 0"
            end
            if type(layer.seed) ~= "number" or layer.seed ~= math.floor(layer.seed)
                    or math.abs(layer.seed) > MAX_SEED then
                problems[#problems + 1] = desc .. ".seed must be an integer between -"
                    .. MAX_SEED .. " and " .. MAX_SEED
            end
        end
    end
    return problems
end

function vertex_shading.assertValid(layers, where)
    local problems = vertex_shading.validate(layers, where)
    if #problems > 0 then error(table.concat(problems, "\n"), 0) end
    return true
end

function vertex_shading.compile(layers, where)
    vertex_shading.assertValid(layers, where)
    local compiled = {}
    for _, layer in ipairs(layers or {}) do
        compiled[#compiled + 1] = {
            type = layer.type,
            colorA = { layer.colorA[1], layer.colorA[2], layer.colorA[3] },
            colorB = { layer.colorB[1], layer.colorB[2], layer.colorB[3] },
            strength = layer.strength,
            scale = layer.scale,
            seed = layer.seed,
        }
    end
    return compiled
end

function vertex_shading.sampleCompiled(compiled, x, y)
    local r, g, b = 1, 1, 1
    for _, layer in ipairs(compiled or {}) do
        local noise = vertex_shading.fractalNoise(x / layer.scale, y / layer.scale, layer.seed)
        local nr = lerp(layer.colorA[1], layer.colorB[1], noise)
        local ng = lerp(layer.colorA[2], layer.colorB[2], noise)
        local nb = lerp(layer.colorA[3], layer.colorB[3], noise)
        local strength = layer.strength
        r = r * lerp(1, nr, strength)
        g = g * lerp(1, ng, strength)
        b = b * lerp(1, nb, strength)
    end
    return r, g, b
end

function vertex_shading.sample(layers, x, y)
    return vertex_shading.sampleCompiled(vertex_shading.compile(layers), x, y)
end

-- Returns an (height + 1) x (width + 1) vertex field. Authored map-space
-- coordinates are zero-based, matching engine.lighting's baked grid contract.
function vertex_shading.grid(layers, width, height)
    local compiled = vertex_shading.compile(layers)
    local out = {}
    for vy = 0, height do
        local row = {}
        out[vy + 1] = row
        for vx = 0, width do
            local r, g, b = vertex_shading.sampleCompiled(compiled, vx, vy)
            row[vx + 1] = { r, g, b }
        end
    end
    return out
end

local function assertPinned(actual, expected, label)
    if math.abs(actual - expected) > 1e-12 then
        error("vertex shading numerical contract drifted at " .. label
            .. ": expected " .. tostring(expected) .. ", got " .. tostring(actual), 0)
    end
end

function vertex_shading.validateAuthored(loader)
    -- Paired with tools/editor/tests/test-map-vertex-shading.js. Pin both the
    -- value-noise primitive and the composed fractal field so renderer/editor
    -- parity cannot drift while the richer visual character evolves.
    assertPinned(vertex_shading.hash01(0, 0, 0), 0.9616300366300367, "hash 0,0,0")
    assertPinned(vertex_shading.hash01(1, 2, 1729), 0.18543956043956045, "hash 1,2,1729")
    assertPinned(vertex_shading.hash01(-1, 0, 23), 0.6313644688644688, "hash -1,0,23")
    assertPinned(vertex_shading.valueNoise(0.5, 0.5, 1729), 0.42679334554334547, "value noise .5,.5")
    assertPinned(vertex_shading.fractalNoise(0.5, 0.5, 1729), 0.4540415838459217, "fractal .5,.5")
    assertPinned(vertex_shading.fractalNoise(1.25, 2.75, 1729), 0.45447714242048237, "fractal 1.25,2.75")
    assertPinned(vertex_shading.fractalNoise(-0.25, 0.5, 23), 0.3765472024340493, "fractal -.25,.5")

    local problems = {}
    for index, map in ipairs((loader and loader.maps) or {}) do
        local label = map.name or map.title or map.id or index
        local found = vertex_shading.validate(map.vertexShadingLayers,
            "map '" .. tostring(label) .. "' vertexShadingLayers")
        for _, problem in ipairs(found) do problems[#problems + 1] = problem end
    end
    if #problems > 0 then
        error("vertex shading validation failed:\n" .. table.concat(problems, "\n"), 0)
    end
    return true
end

return vertex_shading
