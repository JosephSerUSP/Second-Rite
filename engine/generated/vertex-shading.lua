--[[ Generated with https://github.com/TypeScriptToLua/TypeScriptToLua ]]
-- Lua Library inline imports
local function __TS__ArrayIsArray(value)
    return type(value) == "table" and (value[1] ~= nil or next(value) == nil)
end

local function __TS__NumberIsFinite(value)
    return type(value) == "number" and value == value and value ~= math.huge and value ~= -math.huge
end

local function __TS__StringIncludes(self, searchString, position)
    if not position then
        position = 1
    else
        position = position + 1
    end
    local index = string.find(self, searchString, position, true)
    return index ~= nil
end

local function __TS__New(target, ...)
    local instance = setmetatable({}, target.prototype)
    instance:____constructor(...)
    return instance
end

local function __TS__Class(self)
    local c = {prototype = {}}
    c.prototype.__index = c.prototype
    c.prototype.constructor = c
    return c
end

local function __TS__ClassExtends(target, base)
    target.____super = base
    local staticMetatable = setmetatable({__index = base}, base)
    setmetatable(target, staticMetatable)
    local baseMetatable = getmetatable(base)
    if baseMetatable then
        if type(baseMetatable.__index) == "function" then
            staticMetatable.__index = baseMetatable.__index
        end
        if type(baseMetatable.__newindex) == "function" then
            staticMetatable.__newindex = baseMetatable.__newindex
        end
    end
    setmetatable(target.prototype, base.prototype)
    if type(base.prototype.__index) == "function" then
        target.prototype.__index = base.prototype.__index
    end
    if type(base.prototype.__newindex) == "function" then
        target.prototype.__newindex = base.prototype.__newindex
    end
    if type(base.prototype.__tostring) == "function" then
        target.prototype.__tostring = base.prototype.__tostring
    end
end

local Error, RangeError, ReferenceError, SyntaxError, TypeError, URIError
do
    local function getErrorStack(self, constructor)
        if debug == nil then
            return nil
        end
        local level = 1
        while true do
            local info = debug.getinfo(level, "f")
            level = level + 1
            if not info then
                level = 1
                break
            elseif info.func == constructor then
                break
            end
        end
        if __TS__StringIncludes(_VERSION, "Lua 5.0") then
            return debug.traceback(("[Level " .. tostring(level)) .. "]")
        elseif _VERSION == "Lua 5.1" then
            return string.sub(
                debug.traceback("", level),
                2
            )
        else
            return debug.traceback(nil, level)
        end
    end
    local function wrapErrorToString(self, getDescription)
        return function(self)
            local description = getDescription(self)
            local caller = debug.getinfo(3, "f")
            local isClassicLua = __TS__StringIncludes(_VERSION, "Lua 5.0")
            if isClassicLua or caller and caller.func ~= error then
                return description
            else
                return (description .. "\n") .. tostring(self.stack)
            end
        end
    end
    local function initErrorClass(self, Type, name)
        Type.name = name
        return setmetatable(
            Type,
            {__call = function(____, _self, message) return __TS__New(Type, message) end}
        )
    end
    local ____initErrorClass_1 = initErrorClass
    local ____class_0 = __TS__Class()
    ____class_0.name = ""
    function ____class_0.prototype.____constructor(self, message)
        if message == nil then
            message = ""
        end
        self.message = message
        self.name = "Error"
        self.stack = getErrorStack(nil, __TS__New)
        local metatable = getmetatable(self)
        if metatable and not metatable.__errorToStringPatched then
            metatable.__errorToStringPatched = true
            metatable.__tostring = wrapErrorToString(nil, metatable.__tostring)
        end
    end
    function ____class_0.prototype.__tostring(self)
        return self.message ~= "" and (self.name .. ": ") .. self.message or self.name
    end
    Error = ____initErrorClass_1(nil, ____class_0, "Error")
    local function createErrorClass(self, name)
        local ____initErrorClass_3 = initErrorClass
        local ____class_2 = __TS__Class()
        ____class_2.name = ____class_2.name
        __TS__ClassExtends(____class_2, Error)
        function ____class_2.prototype.____constructor(self, ...)
            ____class_2.____super.prototype.____constructor(self, ...)
            self.name = name
        end
        return ____initErrorClass_3(nil, ____class_2, name)
    end
    RangeError = createErrorClass(nil, "RangeError")
    ReferenceError = createErrorClass(nil, "ReferenceError")
    SyntaxError = createErrorClass(nil, "SyntaxError")
    TypeError = createErrorClass(nil, "TypeError")
    URIError = createErrorClass(nil, "URIError")
end
-- End of Lua Library inline imports
ThestraVertexShadingSemantics = ThestraVertexShadingSemantics or ({})
do
    local MODULUS = 65521
    local HASH_MULTIPLIER = 25173
    local HASH_ADDEND = 13849
    local MAX_SEED = 2147483646
    local FRACTAL_PERSISTENCE = 0.55
    local FRACTAL_OCTAVES = {{
        0.8,
        -0.6,
        0.6,
        0.8,
        3.17,
        -5.29
    }, {
        0.6,
        0.8,
        -0.8,
        0.6,
        17.17,
        -9.31
    }, {
        -0.8,
        0.6,
        -0.6,
        -0.8,
        -13.73,
        21.47
    }, {
        -0.6,
        -0.8,
        0.8,
        -0.6,
        29.11,
        14.53
    }}
    local function positiveModulo(value, modulus)
        local result = value % modulus
        return result < 0 and result + modulus or result
    end
    local function lerp(a, b, t)
        return a + (b - a) * t
    end
    local function smoothstep(t)
        return t * t * (3 - 2 * t)
    end
    function ThestraVertexShadingSemantics.hash01(x, y, seed)
        local ix = positiveModulo(
            math.floor(x),
            MODULUS
        )
        local iy = positiveModulo(
            math.floor(y),
            MODULUS
        )
        local iseed = positiveModulo(
            math.floor(seed or 0),
            MODULUS
        )
        local value = (ix * 3749 + iy * 9151 + iseed * 1013) % MODULUS
        value = (value * HASH_MULTIPLIER + HASH_ADDEND) % MODULUS
        value = (value * HASH_MULTIPLIER + HASH_ADDEND) % MODULUS
        return value / (MODULUS - 1)
    end
    function ThestraVertexShadingSemantics.valueNoise(x, y, seed)
        local x0 = math.floor(x)
        local y0 = math.floor(y)
        local fx = x - x0
        local fy = y - y0
        local sx = smoothstep(fx)
        local sy = smoothstep(fy)
        local top = lerp(
            ThestraVertexShadingSemantics.hash01(x0, y0, seed),
            ThestraVertexShadingSemantics.hash01(x0 + 1, y0, seed),
            sx
        )
        local bottom = lerp(
            ThestraVertexShadingSemantics.hash01(x0, y0 + 1, seed),
            ThestraVertexShadingSemantics.hash01(x0 + 1, y0 + 1, seed),
            sx
        )
        return lerp(top, bottom, sy)
    end
    function ThestraVertexShadingSemantics.fractalNoise(x, y, seed)
        local total = 0
        local amplitude = 1
        local normalizer = 0
        local frequency = 1
        do
            local octaveIndex = 0
            while octaveIndex < #FRACTAL_OCTAVES do
                local octave = FRACTAL_OCTAVES[octaveIndex + 1]
                local rotatedX = (x * octave[1] + y * octave[2] + octave[5]) * frequency
                local rotatedY = (x * octave[3] + y * octave[4] + octave[6]) * frequency
                total = total + ThestraVertexShadingSemantics.valueNoise(rotatedX, rotatedY, seed + octaveIndex * 7919) * amplitude
                normalizer = normalizer + amplitude
                amplitude = amplitude * FRACTAL_PERSISTENCE
                frequency = frequency * 2
                octaveIndex = octaveIndex + 1
            end
        end
        return total / normalizer
    end
    local function validateRgb(problems, value, where)
        if not __TS__ArrayIsArray(value) or #value ~= 3 then
            problems[#problems + 1] = where .. " must be an RGB triple"
            return
        end
        do
            local channel = 0
            while channel < 3 do
                local sample = value[channel + 1]
                if type(sample) ~= "number" or not __TS__NumberIsFinite(sample) or sample < 0 or sample > 1 then
                    problems[#problems + 1] = ((where .. " channel ") .. tostring(channel + 1)) .. " must be a number in 0..1"
                end
                channel = channel + 1
            end
        end
    end
    function ThestraVertexShadingSemantics.validate(layers, where)
        if where == nil then
            where = "vertexShadingLayers"
        end
        local problems = {}
        if layers == nil then
            return problems
        end
        if not __TS__ArrayIsArray(layers) then
            problems[#problems + 1] = where .. " must be a dense list"
            return problems
        end
        do
            local index = 0
            while index < #layers do
                local layer = layers[index + 1]
                local desc = ((where .. "[") .. tostring(index + 1)) .. "]"
                if layer == nil or type(layer) ~= "table" or __TS__ArrayIsArray(layer) then
                    problems[#problems + 1] = desc .. " must be an object"
                elseif layer.type ~= "colorNoise" then
                    problems[#problems + 1] = ((desc .. ".type '") .. tostring(layer.type)) .. "' is unsupported (expected colorNoise)"
                else
                    validateRgb(problems, layer.colorA, desc .. ".colorA")
                    validateRgb(problems, layer.colorB, desc .. ".colorB")
                    if type(layer.strength) ~= "number" or not __TS__NumberIsFinite(layer.strength) or layer.strength < 0 or layer.strength > 1 then
                        problems[#problems + 1] = desc .. ".strength must be a number in 0..1"
                    end
                    if type(layer.scale) ~= "number" or not __TS__NumberIsFinite(layer.scale) or layer.scale <= 0 then
                        problems[#problems + 1] = desc .. ".scale must be a number > 0"
                    end
                    if type(layer.seed) ~= "number" or not __TS__NumberIsFinite(layer.seed) or math.floor(layer.seed) ~= layer.seed or math.abs(layer.seed) > MAX_SEED then
                        problems[#problems + 1] = (((desc .. ".seed must be an integer between -") .. tostring(MAX_SEED)) .. " and ") .. tostring(MAX_SEED)
                    end
                end
                index = index + 1
            end
        end
        return problems
    end
    function ThestraVertexShadingSemantics.compile(layers, where)
        if where == nil then
            where = "vertexShadingLayers"
        end
        local problems = ThestraVertexShadingSemantics.validate(layers, where)
        if #problems > 0 then
            error(
                __TS__New(
                    Error,
                    table.concat(problems, "\n")
                ),
                0
            )
        end
        local source = layers or ({})
        local compiled = {}
        do
            local index = 0
            while index < #source do
                local layer = source[index + 1]
                compiled[#compiled + 1] = {
                    type = layer.type,
                    colorA = {layer.colorA[1], layer.colorA[2], layer.colorA[3]},
                    colorB = {layer.colorB[1], layer.colorB[2], layer.colorB[3]},
                    strength = layer.strength,
                    scale = layer.scale,
                    seed = layer.seed
                }
                index = index + 1
            end
        end
        return compiled
    end
    function ThestraVertexShadingSemantics.sampleCompiled(compiled, x, y, target)
        local out = target or ({1, 1, 1})
        local r = 1
        local g = 1
        local b = 1
        if compiled ~= nil then
            do
                local index = 0
                while index < #compiled do
                    local layer = compiled[index + 1]
                    local noise = ThestraVertexShadingSemantics.fractalNoise(x / layer.scale, y / layer.scale, layer.seed)
                    local nr = lerp(layer.colorA[1], layer.colorB[1], noise)
                    local ng = lerp(layer.colorA[2], layer.colorB[2], noise)
                    local nb = lerp(layer.colorA[3], layer.colorB[3], noise)
                    r = r * lerp(1, nr, layer.strength)
                    g = g * lerp(1, ng, layer.strength)
                    b = b * lerp(1, nb, layer.strength)
                    index = index + 1
                end
            end
        end
        out[1] = r
        out[2] = g
        out[3] = b
        return out
    end
    function ThestraVertexShadingSemantics.sample(layers, x, y, target)
        return ThestraVertexShadingSemantics.sampleCompiled(
            ThestraVertexShadingSemantics.compile(layers),
            x,
            y,
            target
        )
    end
    function ThestraVertexShadingSemantics.grid(layers, width, height)
        local compiled = ThestraVertexShadingSemantics.compile(layers)
        local result = {}
        do
            local y = 0
            while y <= height do
                local row = {}
                do
                    local x = 0
                    while x <= width do
                        row[#row + 1] = ThestraVertexShadingSemantics.sampleCompiled(compiled, x, y)
                        x = x + 1
                    end
                end
                result[#result + 1] = row
                y = y + 1
            end
        end
        return result
    end
end
-- THES_SHARED_LUA_VERTEX_SHADING: generated module adapter; do not edit.
return ThestraVertexShadingSemantics
