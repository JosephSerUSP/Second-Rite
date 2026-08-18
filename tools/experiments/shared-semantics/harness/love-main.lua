local function close(actual, expected, label, epsilon)
    epsilon = epsilon or 1e-12
    if math.abs(actual - expected) > epsilon then
        error((label or "value") .. ": expected " .. tostring(expected) .. ", got " .. tostring(actual), 0)
    end
end

local function eq(actual, expected, label)
    if actual ~= expected then
        error((label or "value") .. ": expected " .. tostring(expected) .. ", got " .. tostring(actual), 0)
    end
end

local function elapsedMs(fn)
    collectgarbage("collect")
    local started = love.timer.getTime()
    local result = fn()
    return (love.timer.getTime() - started) * 1000, result
end

local current = require("engine.vertex_shading")
local sameLua = require("same_shared")
require("generated.shared_semantics")
local generated = assert(ThestraSharedSemantics, "generated TypeScriptToLua namespace missing")

local pins = {
    { "hash01", { 0, 0, 0 }, 0.9616300366300367 },
    { "hash01", { 1, 2, 1729 }, 0.18543956043956045 },
    { "hash01", { -1, 0, 23 }, 0.6313644688644688 },
    { "valueNoise", { 0.5, 0.5, 1729 }, 0.42679334554334547 },
    { "fractalNoise", { 0.5, 0.5, 1729 }, 0.4540415838459217 },
    { "fractalNoise", { 1.25, 2.75, 1729 }, 0.45447714242048237 },
    { "fractalNoise", { -0.25, 0.5, 23 }, 0.3765472024340493 },
}

for _, pin in ipairs(pins) do
    local name, args, expected = pin[1], pin[2], pin[3]
    local a = current[name](unpack(args))
    local b = sameLua[name](unpack(args))
    local c = generated[name](unpack(args))
    close(a, expected, "current Lua " .. name)
    close(b, a, "same-Lua " .. name)
    close(c, a, "generated Lua " .. name)
end

local layer = {
    type = "colorNoise",
    colorA = { 0.88, 0.94, 0.90 },
    colorB = { 0.96, 0.88, 0.93 },
    strength = 0.12,
    scale = 5,
    seed = 1729,
}
local cr, cg, cb = current.sample({ layer }, 2.5, 3.5)
local sr, sg, sb = sameLua.sample({ layer }, 2.5, 3.5)
local generatedSample = generated.sample({ layer }, 2.5, 3.5)
close(cr, 0.9897950411471678, "current Lua sample r")
close(cg, 0.9896537191396242, "current Lua sample g")
close(cb, 0.9895731404301878, "current Lua sample b")
close(sr, cr, "same-Lua sample r")
close(sg, cg, "same-Lua sample g")
close(sb, cb, "same-Lua sample b")
close(generatedSample[1], cr, "generated Lua sample r")
close(generatedSample[2], cg, "generated Lua sample g")
close(generatedSample[3], cb, "generated Lua sample b")

local invalid = {{
    type = "colorNoise", colorA = { 1, 1 }, colorB = { 1, 1, 1 },
    strength = 2, scale = 0, seed = 1.5,
}}
for _, api in ipairs({ current, sameLua, generated }) do
    local problems = api.validate(invalid, "map demo vertexShadingLayers")
    local joined = table.concat(problems, "\n")
    for _, term in ipairs({ "colorA", "strength", "scale", "seed" }) do
        if not joined:find(term, 1, true) then error("validation lost " .. term, 0) end
    end
    local ok = pcall(function() api.compile(invalid) end)
    if ok then error("invalid compile unexpectedly succeeded", 0) end
end

local files = {
    ["assets/smallBattlers/Pixie[fps=15].png"] = true,
    ["assets/system/Cursor.png"] = true,
}
local dirs = {
    ["assets/smallBattlers"] = { "Pixie[fps=15].png" },
    ["assets/sprites"] = {},
    ["assets/system"] = { "Cursor.png" },
}
local originalGetDirectoryItems = love.filesystem.getDirectoryItems
local originalGetInfo = love.filesystem.getInfo
love.filesystem.getDirectoryItems = function(dir) return dirs[dir] or {} end
love.filesystem.getInfo = function(path) return files[path] and { type = "file" } or nil end
package.loaded["presentation.sprite_sheet"] = nil
local currentSprite = require("presentation.sprite_sheet")

local fileList = {
    "assets/smallBattlers/Pixie[fps=15].png",
    "assets/system/Cursor.png",
}
local function assertSprite(key, fps, source, path)
    local currentDescription = currentSprite.describe(key)
    local sameDescription = sameLua.resolveSpriteKey(key, fileList)
    local generatedDescription = generated.resolveSpriteKey(key, fileList)
    eq(currentDescription.path, path, "current sprite path " .. key)
    eq(sameDescription.path, currentDescription.path, "same-Lua sprite path " .. key)
    eq(generatedDescription.path, currentDescription.path, "generated Lua sprite path " .. key)
    eq(currentDescription.timing.fps, fps, "current sprite fps " .. key)
    eq(sameDescription.timing.fps, currentDescription.timing.fps, "same-Lua sprite fps " .. key)
    eq(generatedDescription.timing.fps, currentDescription.timing.fps, "generated Lua sprite fps " .. key)
    eq(currentDescription.timing.source, source, "current sprite source " .. key)
    eq(sameDescription.timing.source, source, "same-Lua sprite source " .. key)
    eq(generatedDescription.timing.source, source, "generated Lua sprite source " .. key)
end

assertSprite("pixie", 15, "filename", "assets/smallBattlers/Pixie[fps=15].png")
assertSprite("pixie[fps=9]", 9, "key", "assets/smallBattlers/Pixie[fps=15].png")
assertSprite("pixie[speed=2]", 15, "filename", "assets/smallBattlers/Pixie[fps=15].png")
assertSprite("Cursor", 4, "default", "assets/system/Cursor.png")

local currentPath = currentSprite.describePath("assets/smallBattlers/Pixie[fps=15].png")
local samePath = sameLua.describeSpritePath("assets/smallBattlers/Pixie[fps=15].png")
local generatedPath = generated.describeSpritePath("assets/smallBattlers/Pixie[fps=15].png")
eq(currentPath.timing.fps, 15, "current path timing")
eq(samePath.timing.fps, 15, "same-Lua path timing")
eq(generatedPath.timing.fps, 15, "generated path timing")

-- Deliberately probe a non-canonical numeric spelling. The production Lua uses
-- tonumber; TypeScript/JavaScript Number has a broader literal grammar. This is
-- recorded as evidence rather than hidden behind a passing fixture set.
local currentEdge = currentSprite.describe("pixie[fps=0b10]")
local sameEdge = sameLua.resolveSpriteKey("pixie[fps=0b10]", fileList)
local generatedEdge = generated.resolveSpriteKey("pixie[fps=0b10]", fileList)
print("EDGE_TOKEN fps=0b10 current=" .. tostring(currentEdge.timing.fps)
    .. " sameLua=" .. tostring(sameEdge.timing.fps)
    .. " generated=" .. tostring(generatedEdge.timing.fps))

love.filesystem.getDirectoryItems = originalGetDirectoryItems
love.filesystem.getInfo = originalGetInfo
package.loaded["presentation.sprite_sheet"] = nil

local function benchFractal(api, count)
    local ms = elapsedMs(function()
        local sink = 0
        for _ = 1, count do sink = sink + api.fractalNoise(1.25, 2.75, 1729) end
        return sink
    end)
    return ms
end

local function benchGrid(api, width, height)
    local ms = elapsedMs(function() return api.grid({ layer }, width, height) end)
    return ms
end

local loveMajor, loveMinor, loveRevision = love.getVersion()
print("RUNTIME LOVE=" .. loveMajor .. "." .. loveMinor .. "." .. loveRevision
    .. " LUA=" .. tostring(_VERSION)
    .. " LUAJIT=" .. tostring(jit and jit.version or "none"))
print(string.format(
    "MEASURE_LUA current_fractal_100k_ms=%.6f same_lua_fractal_100k_ms=%.6f generated_lua_fractal_100k_ms=%.6f",
    benchFractal(current, 100000), benchFractal(sameLua, 100000), benchFractal(generated, 100000)))
for _, size in ipairs({ {17, 17, "map2"}, {23, 23, "map3"}, {128, 128, "max"} }) do
    print(string.format(
        "MEASURE_GRID %s_%dx%d current_ms=%.6f same_lua_ms=%.6f generated_lua_ms=%.6f",
        size[3], size[1], size[2],
        benchGrid(current, size[1], size[2]),
        benchGrid(sameLua, size[1], size[2]),
        benchGrid(generated, size[1], size[2])))
end

local traceback
xpcall(function() generated.compile(invalid) end, function(err)
    traceback = debug.traceback(tostring(err), 2)
end)
print("TRACEBACK_BEGIN")
print(traceback or "<no traceback>")
print("TRACEBACK_END")
print("LOVE PARITY OK")
love.event.quit(0)
