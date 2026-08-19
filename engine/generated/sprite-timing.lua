--[[ Generated with https://github.com/TypeScriptToLua/TypeScriptToLua ]]
-- Lua Library inline imports
local function __TS__StringCharCodeAt(self, index)
    if index ~= index then
        index = 0
    end
    if index < 0 then
        return 0 / 0
    end
    return string.byte(self, index + 1) or 0 / 0
end

local function __TS__StringSubstring(self, start, ____end)
    if ____end ~= ____end then
        ____end = 0
    end
    if ____end ~= nil and start > ____end then
        start, ____end = ____end, start
    end
    if start >= 0 then
        start = start + 1
    else
        start = 1
    end
    if ____end ~= nil and ____end < 0 then
        ____end = 0
    end
    return string.sub(self, start, ____end)
end

local function __TS__Number(value)
    local valueType = type(value)
    if valueType == "number" then
        return value
    elseif valueType == "string" then
        local numberValue = tonumber(value)
        if numberValue then
            return numberValue
        end
        if value == "Infinity" then
            return math.huge
        end
        if value == "-Infinity" then
            return -math.huge
        end
        local stringWithoutSpaces = string.gsub(value, "%s", "")
        if stringWithoutSpaces == "" then
            return 0
        end
        return 0 / 0
    elseif valueType == "boolean" then
        return value and 1 or 0
    else
        return 0 / 0
    end
end

local function __TS__NumberIsFinite(value)
    return type(value) == "number" and value == value and value ~= math.huge and value ~= -math.huge
end
-- End of Lua Library inline imports
ThestraSpriteTimingSemantics = ThestraSpriteTimingSemantics or ({})
do
    local function isAsciiWhitespace(code)
        return code == 32 or code == 9 or code == 10 or code == 11 or code == 12 or code == 13
    end
    local function trimAscii(value)
        local first = 0
        local last = #value
        while first < last and isAsciiWhitespace(__TS__StringCharCodeAt(value, first)) do
            first = first + 1
        end
        while last > first and isAsciiWhitespace(__TS__StringCharCodeAt(value, last - 1)) do
            last = last - 1
        end
        return __TS__StringSubstring(value, first, last)
    end
    local function hasUnsupportedNumericPrefix(value)
        if #value < 2 then
            return false
        end
        local first = 0
        local leading = string.byte(value, 1) or 0 / 0
        if leading == 43 or leading == 45 then
            first = 1
        end
        if first + 1 >= #value or __TS__StringCharCodeAt(value, first) ~= 48 then
            return false
        end
        local prefix = __TS__StringCharCodeAt(value, first + 1)
        if prefix == 98 or prefix == 66 or prefix == 111 or prefix == 79 then
            return true
        end
        return first > 0 and (prefix == 120 or prefix == 88)
    end
    local function tokenValue(raw)
        local trimmed = trimAscii(raw)
        if #trimmed == 0 or hasUnsupportedNumericPrefix(trimmed) then
            return raw
        end
        local numeric = __TS__Number(trimmed)
        return __TS__NumberIsFinite(numeric) and numeric or raw
    end
    local function numericToken(value)
        if type(value) == "number" then
            return __TS__NumberIsFinite(value) and value or nil
        end
        local trimmed = trimAscii(value)
        if #trimmed == 0 or hasUnsupportedNumericPrefix(trimmed) then
            return nil
        end
        local numeric = __TS__Number(trimmed)
        return __TS__NumberIsFinite(numeric) and numeric or nil
    end
    function ThestraSpriteTimingSemantics.copyTokens(tokens)
        local result = {}
        if tokens == nil then
            return result
        end
        for key in pairs(tokens) do
            result[key] = tokens[key]
        end
        return result
    end
    function ThestraSpriteTimingSemantics.parseKey(spriteKey)
        local tokens = {}
        local fileKey = ""
        local cursor = 0
        while cursor < #spriteKey do
            local open = (string.find(
                spriteKey,
                "[",
                math.max(cursor + 1, 1),
                true
            ) or 0) - 1
            if open < 0 then
                fileKey = fileKey .. __TS__StringSubstring(spriteKey, cursor)
                break
            end
            fileKey = fileKey .. __TS__StringSubstring(spriteKey, cursor, open)
            local equals = (string.find(
                spriteKey,
                "=",
                math.max(open + 1 + 1, 1),
                true
            ) or 0) - 1
            local close = equals >= 0 and (string.find(
                spriteKey,
                "]",
                math.max(equals + 1 + 1, 1),
                true
            ) or 0) - 1 or -1
            if equals > open + 1 and close > equals + 1 then
                local key = __TS__StringSubstring(spriteKey, open + 1, equals)
                local value = __TS__StringSubstring(spriteKey, equals + 1, close)
                tokens[key] = tokenValue(value)
                cursor = close + 1
            else
                fileKey = fileKey .. "["
                cursor = open + 1
            end
        end
        return {
            fileKey = trimAscii(fileKey),
            tokens = tokens
        }
    end
    function ThestraSpriteTimingSemantics.mergeTokens(filenameTokens, keyTokens)
        local merged = ThestraSpriteTimingSemantics.copyTokens(filenameTokens)
        if keyTokens ~= nil then
            for key in pairs(keyTokens) do
                merged[key] = keyTokens[key]
            end
        end
        return merged
    end
    function ThestraSpriteTimingSemantics.resolveTiming(keyTokens, filenameTokens)
        local key = keyTokens or ({})
        local filename = filenameTokens or ({})
        local merged = ThestraSpriteTimingSemantics.mergeTokens(filename, key)
        if merged.fps ~= nil then
            local value = merged.fps
            return {
                fps = numericToken(value),
                source = key.fps ~= nil and "key" or (filename.fps ~= nil and "filename" or "resolved"),
                token = "fps",
                value = value
            }
        end
        if merged.speed ~= nil then
            local value = merged.speed
            local numeric = numericToken(value)
            local ____temp_0
            if numeric == nil then
                ____temp_0 = nil
            else
                ____temp_0 = 4 * numeric
            end
            return {fps = ____temp_0, source = key.speed ~= nil and "key" or (filename.speed ~= nil and "filename" or "resolved"), token = "speed", value = value}
        end
        return {fps = 4, source = "default", token = nil, value = nil}
    end
    function ThestraSpriteTimingSemantics.effectiveFps(tokens)
        local merged = tokens or ({})
        if merged.fps ~= nil then
            return numericToken(merged.fps)
        end
        if merged.speed ~= nil then
            local numeric = numericToken(merged.speed)
            local ____temp_1
            if numeric == nil then
                ____temp_1 = nil
            else
                ____temp_1 = 4 * numeric
            end
            return ____temp_1
        end
        return 4
    end
end
-- THES_SHARED_LUA_SPRITE_TIMING: generated module adapter; do not edit.
return ThestraSpriteTimingSemantics
