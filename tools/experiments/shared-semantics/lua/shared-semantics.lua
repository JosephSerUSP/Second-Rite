-- Experimental same-source-Lua control. This is deliberately isolated from
-- production. The exact same file is executed by LÖVE/LuaJIT and Wasmoon/Lua 5.4.
local shared = {}

local ASSET_DIRS = {
    "assets/smallBattlers",
    "assets/sprites",
    "assets/system",
}

local function copyTokens(tokens)
    local out = {}
    for k, v in pairs(tokens or {}) do out[k] = v end
    return out
end

function shared.parseSpriteKey(spriteKey)
    local tokens = {}
    local fileKey = tostring(spriteKey):gsub("%[([^=]+)=([^%]]+)%]", function(k, v)
        tokens[k] = tonumber(v) or v
        return ""
    end)
    fileKey = fileKey:gsub("^%s*(.-)%s*$", "%1")
    return { fileKey = fileKey, tokens = tokens }
end

local function mergedTokens(keyTokens, filenameTokens)
    local merged = copyTokens(filenameTokens)
    for k, v in pairs(keyTokens or {}) do merged[k] = v end
    return merged
end

function shared.resolveTiming(keyTokens, filenameTokens)
    keyTokens = keyTokens or {}
    filenameTokens = filenameTokens or {}
    local merged = mergedTokens(keyTokens, filenameTokens)
    if merged.fps ~= nil then
        local numeric = tonumber(merged.fps)
        return {
            fps = numeric,
            source = keyTokens.fps ~= nil and "key"
                or (filenameTokens.fps ~= nil and "filename" or "resolved"),
            token = "fps",
            value = merged.fps,
        }
    elseif merged.speed ~= nil then
        local numeric = tonumber(merged.speed)
        return {
            fps = numeric and 4 * numeric or nil,
            source = keyTokens.speed ~= nil and "key"
                or (filenameTokens.speed ~= nil and "filename" or "resolved"),
            token = "speed",
            value = merged.speed,
        }
    end
    return { fps = 4, source = "default", token = nil, value = nil }
end

local function containsPath(files, path)
    for _, candidate in ipairs(files or {}) do
        if candidate == path then return true end
    end
    return false
end

local function basename(path)
    return tostring(path):match("([^/\\]+)$") or tostring(path)
end

local function titleCaseFirst(value)
    if #value == 0 then return value end
    return value:sub(1, 1):upper() .. value:sub(2):lower()
end

local function stripPng(filename)
    return filename:gsub("%.png$", "")
end

local function indexedFilename(files, fileKey)
    local wanted = fileKey:lower()
    for _, dir in ipairs(ASSET_DIRS) do
        local prefix = dir .. "/"
        for _, path in ipairs(files or {}) do
            if path:sub(1, #prefix) == prefix then
                local localName = path:sub(#prefix + 1)
                if not localName:find("/", 1, true) and localName:match("%.png$") then
                    local parsed = shared.parseSpriteKey(stripPng(localName))
                    if parsed.fileKey:lower() == wanted then
                        return { path = path, tokens = parsed.tokens }
                    end
                end
            end
        end
    end
    return nil
end

function shared.resolveSpriteKey(spriteKey, files)
    local parsed = shared.parseSpriteKey(spriteKey)
    local fileKey = parsed.fileKey
    local indexed = indexedFilename(files, fileKey)
    local filenameTokens = indexed and copyTokens(indexed.tokens) or {}
    local candidates = {
        "assets/smallBattlers/" .. titleCaseFirst(fileKey) .. ".png",
        "assets/smallBattlers/" .. fileKey .. ".png",
        "assets/smallBattlers/" .. fileKey:lower() .. ".png",
        "assets/sprites/" .. fileKey .. ".png",
        "assets/system/" .. fileKey .. ".png",
        "assets/system/" .. titleCaseFirst(fileKey) .. ".png",
    }
    local path
    for _, candidate in ipairs(candidates) do
        if containsPath(files, candidate) then
            path = candidate
            break
        end
    end
    if not path and indexed then path = indexed.path end
    return {
        resolved = path ~= nil,
        key = spriteKey,
        path = path,
        tokenSourcePath = indexed and indexed.path or nil,
        keyTokens = copyTokens(parsed.tokens),
        filenameTokens = filenameTokens,
        tokens = mergedTokens(parsed.tokens, filenameTokens),
        timing = shared.resolveTiming(parsed.tokens, filenameTokens),
    }
end

function shared.describeSpritePath(path)
    local parsed = shared.parseSpriteKey(stripPng(basename(path)))
    local filenameTokens = parsed.tokens
    return {
        resolved = true,
        key = "",
        path = path,
        tokenSourcePath = path,
        keyTokens = {},
        filenameTokens = copyTokens(filenameTokens),
        tokens = copyTokens(filenameTokens),
        timing = shared.resolveTiming({}, filenameTokens),
    }
end

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

function shared.hash01(x, y, seed)
    local ix = positiveModulo(math.floor(x), MODULUS)
    local iy = positiveModulo(math.floor(y), MODULUS)
    local iseed = positiveModulo(math.floor(seed or 0), MODULUS)
    local value = (ix * 3749 + iy * 9151 + iseed * 1013) % MODULUS
    value = (value * HASH_MULTIPLIER + HASH_ADDEND) % MODULUS
    value = (value * HASH_MULTIPLIER + HASH_ADDEND) % MODULUS
    return value / (MODULUS - 1)
end

function shared.valueNoise(x, y, seed)
    local x0, y0 = math.floor(x), math.floor(y)
    local fx, fy = x - x0, y - y0
    local sx, sy = smoothstep(fx), smoothstep(fy)
    local top = lerp(shared.hash01(x0, y0, seed), shared.hash01(x0 + 1, y0, seed), sx)
    local bottom = lerp(shared.hash01(x0, y0 + 1, seed), shared.hash01(x0 + 1, y0 + 1, seed), sx)
    return lerp(top, bottom, sy)
end

function shared.fractalNoise(x, y, seed)
    local total, amplitude, normalizer, frequency = 0, 1, 0, 1
    for octaveIndex, octave in ipairs(FRACTAL_OCTAVES) do
        local rotatedX = (x * octave[1] + y * octave[2] + octave[5]) * frequency
        local rotatedY = (x * octave[3] + y * octave[4] + octave[6]) * frequency
        total = total + shared.valueNoise(rotatedX, rotatedY, seed + (octaveIndex - 1) * 7919) * amplitude
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

function shared.validate(layers, where)
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

function shared.compile(layers, where)
    local problems = shared.validate(layers, where)
    if #problems > 0 then error(table.concat(problems, "\n"), 0) end
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

function shared.sampleCompiled(compiled, x, y)
    local r, g, b = 1, 1, 1
    for _, layer in ipairs(compiled or {}) do
        local noise = shared.fractalNoise(x / layer.scale, y / layer.scale, layer.seed)
        local nr = lerp(layer.colorA[1], layer.colorB[1], noise)
        local ng = lerp(layer.colorA[2], layer.colorB[2], noise)
        local nb = lerp(layer.colorA[3], layer.colorB[3], noise)
        r = r * lerp(1, nr, layer.strength)
        g = g * lerp(1, ng, layer.strength)
        b = b * lerp(1, nb, layer.strength)
    end
    return r, g, b
end

function shared.sample(layers, x, y)
    return shared.sampleCompiled(shared.compile(layers), x, y)
end

function shared.grid(layers, width, height)
    local compiled = shared.compile(layers)
    local out = {}
    for y = 0, height do
        local row = {}
        out[y + 1] = row
        for x = 0, width do
            local r, g, b = shared.sampleCompiled(compiled, x, y)
            row[x + 1] = { r, g, b }
        end
    end
    return out
end

return shared
