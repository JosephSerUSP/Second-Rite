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

local function __TS__StringIncludes(self, searchString, position)
    if not position then
        position = 1
    else
        position = position + 1
    end
    local index = string.find(self, searchString, position, true)
    return index ~= nil
end

local __TS__Match = string.match

local function __TS__SourceMapTraceBack(fileName, sourceMap)
    _G.__TS__sourcemap = _G.__TS__sourcemap or ({})
    _G.__TS__sourcemap[fileName] = sourceMap
    if _G.__TS__originalTraceback == nil then
        local originalTraceback = debug.traceback
        _G.__TS__originalTraceback = originalTraceback
        debug.traceback = function(thread, message, level)
            local trace
            if thread == nil and message == nil and level == nil then
                trace = originalTraceback()
            elseif __TS__StringIncludes(_VERSION, "Lua 5.0") then
                trace = originalTraceback((("[Level " .. tostring(level)) .. "] ") .. tostring(message))
            else
                trace = originalTraceback(thread, message, level)
            end
            if type(trace) ~= "string" then
                return trace
            end
            local function replacer(____, file, srcFile, line)
                local fileSourceMap = _G.__TS__sourcemap[file]
                if fileSourceMap ~= nil and fileSourceMap[line] ~= nil then
                    local data = fileSourceMap[line]
                    if type(data) == "number" then
                        return (srcFile .. ":") .. tostring(data)
                    end
                    return (data.file .. ":") .. tostring(data.line)
                end
                return (file .. ":") .. line
            end
            local result = string.gsub(
                trace,
                "([^%s<]+)%.lua:(%d+)",
                function(file, line) return replacer(nil, file .. ".lua", file .. ".ts", line) end
            )
            local function stringReplacer(____, file, line)
                local fileSourceMap = _G.__TS__sourcemap[file]
                if fileSourceMap ~= nil and fileSourceMap[line] ~= nil then
                    local chunkName = (__TS__Match(file, "%[string \"([^\"]+)\"%]"))
                    local sourceName = string.gsub(chunkName, ".lua$", ".ts")
                    local data = fileSourceMap[line]
                    if type(data) == "number" then
                        return (sourceName .. ":") .. tostring(data)
                    end
                    return (data.file .. ":") .. tostring(data.line)
                end
                return (file .. ":") .. line
            end
            result = string.gsub(
                result,
                "(%[string \"[^\"]+\"%]):(%d+)",
                function(file, line) return stringReplacer(nil, file, line) end
            )
            return result
        end
    end
end
-- End of Lua Library inline imports
__TS__SourceMapTraceBack(debug.getinfo(1).short_src, {["132"] = 8,["134"] = 24,["135"] = 25,["136"] = 24,["137"] = 28,["138"] = 29,["139"] = 30,["140"] = 31,["141"] = 31,["143"] = 32,["144"] = 32,["146"] = 33,["147"] = 28,["148"] = 40,["149"] = 41,["150"] = 42,["151"] = 42,["153"] = 43,["154"] = 44,["155"] = 40,["156"] = 47,["157"] = 48,["158"] = 48,["160"] = 49,["161"] = 50,["162"] = 50,["164"] = 51,["165"] = 52,["166"] = 47,["167"] = 8,["168"] = 56,["169"] = 57,["170"] = 57,["172"] = 58,["173"] = 58,["175"] = 59,["176"] = 55,["177"] = 8,["178"] = 66,["179"] = 67,["180"] = 68,["181"] = 70,["182"] = 71,["183"] = 71,["184"] = 71,["185"] = 71,["186"] = 71,["187"] = 71,["188"] = 72,["189"] = 73,["192"] = 76,["193"] = 77,["194"] = 77,["195"] = 77,["196"] = 77,["197"] = 77,["198"] = 77,["199"] = 78,["200"] = 78,["201"] = 78,["202"] = 78,["203"] = 78,["204"] = 78,["205"] = 79,["206"] = 80,["207"] = 81,["208"] = 82,["209"] = 83,["211"] = 85,["212"] = 86,["215"] = 90,["216"] = 90,["217"] = 90,["218"] = 90,["219"] = 65,["220"] = 8,["221"] = 8,["222"] = 97,["223"] = 98,["224"] = 98,["227"] = 100,["228"] = 94,["229"] = 8,["230"] = 105,["231"] = 106,["232"] = 8,["233"] = 109,["234"] = 110,["235"] = 111,["236"] = 111,["237"] = 111,["238"] = 111,["239"] = 111,["240"] = 111,["242"] = 119,["243"] = 120,["244"] = 121,["245"] = 123,["246"] = 123,["247"] = 123,["249"] = 123,["251"] = 122,["253"] = 130,["254"] = 103,["255"] = 8,["256"] = 134,["257"] = 135,["258"] = 135,["260"] = 136,["261"] = 137,["262"] = 138,["263"] = 138,["264"] = 138,["266"] = 138,["268"] = 138,["270"] = 140,["271"] = 133});
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
    local function tokenValue(raw)
        local trimmed = trimAscii(raw)
        if #trimmed == 0 then
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
        if #trimmed == 0 then
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
