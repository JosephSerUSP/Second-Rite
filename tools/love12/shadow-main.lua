-- Shadow-only wrapper used by .github/workflows/love12-shadow.yml.
-- The workflow temporarily copies the real root main.lua to
-- main.shadow-real.lua and installs this file as main.lua, so LÖVE 11.5 and
-- LÖVE 12 execute the exact same production game code before these callbacks
-- observe it. This file is never part of the production launch path.

dofile("main.shadow-real.lua")

local json = require("engine.data.json")
local originalLoad = love.load
local originalDraw = love.draw
local originalUpdate = love.update
local requestedMapId = os.getenv and os.getenv("SECOND_RITE_SHADOW_MAP_ID") or "2"
local warmupFrames = tonumber(os.getenv and os.getenv("SECOND_RITE_SHADOW_WARMUP")) or 60
local measuredFrames = tonumber(os.getenv and os.getenv("SECOND_RITE_SHADOW_FRAMES")) or 180
local frame = 0
local drawTimes = {}
local maxTextureMemory = 0
local maxBufferMemory = nil
local maxBuffers = nil
local renderer = nil

local function percentile(values, p)
    if #values == 0 then return 0 end
    local sorted = {}
    for index, value in ipairs(values) do sorted[index] = value end
    table.sort(sorted)
    local position = math.max(1, math.min(#sorted, math.ceil(#sorted * p)))
    return sorted[position]
end

local function median(values)
    return percentile(values, 0.5)
end

local function rendererInfo()
    local name, version, vendor, device = love.graphics.getRendererInfo()
    return { name = name, version = version, vendor = vendor, device = device }
end

local function forceMap()
    if not activeSession then return false, "activeSession unavailable after production love.load" end
    local loader = require("engine.data.loader")
    local exploration = require("engine.exploration")
    for index, map in ipairs(loader.maps or {}) do
        if tostring(map.id) == tostring(requestedMapId) then
            local originalTime = os.time
            os.time = function() return 1735689600 end
            local ok, err = pcall(exploration.loadMap, activeSession, index, { seed = 1735689600 })
            os.time = originalTime
            return ok, err
        end
    end
    return false, "map id not found: " .. tostring(requestedMapId)
end

function love.load(args)
    originalLoad(args)
    local ok, err = forceMap()
    if not ok then error("shadow map setup failed: " .. tostring(err), 0) end
    renderer = rendererInfo()
end

if originalUpdate then
    function love.update(dt)
        -- Keep normal update semantics. The probe changes only observation and
        -- deterministic map choice, not the production update loop.
        originalUpdate(dt)
    end
end

function love.draw()
    local started = love.timer.getTime()
    originalDraw()
    local elapsedMs = (love.timer.getTime() - started) * 1000
    frame = frame + 1

    local stats = love.graphics.getStats()
    maxTextureMemory = math.max(maxTextureMemory, tonumber(stats.texturememory) or 0)
    if stats.buffermemory ~= nil then
        maxBufferMemory = math.max(maxBufferMemory or 0, tonumber(stats.buffermemory) or 0)
    end
    if stats.buffers ~= nil then
        maxBuffers = math.max(maxBuffers or 0, tonumber(stats.buffers) or 0)
    end

    if frame > warmupFrames then drawTimes[#drawTimes + 1] = elapsedMs end
    if frame >= warmupFrames + measuredFrames then
        local finalStats = love.graphics.getStats()
        local payload = {
            love = tostring(love.getVersion()),
            mapId = tostring(requestedMapId),
            warmupFrames = warmupFrames,
            measuredFrames = #drawTimes,
            renderer = renderer,
            drawCpuMs = {
                min = math.min(unpack(drawTimes)),
                p50 = median(drawTimes),
                p95 = percentile(drawTimes, 0.95),
                max = math.max(unpack(drawTimes)),
            },
            graphics = {
                drawcalls = finalStats.drawcalls,
                drawcallsbatched = finalStats.drawcallsbatched,
                canvasswitches = finalStats.canvasswitches,
                texturememory = finalStats.texturememory,
                maxTextureMemory = maxTextureMemory,
                buffers = finalStats.buffers,
                maxBuffers = maxBuffers,
                buffermemory = finalStats.buffermemory,
                maxBufferMemory = maxBufferMemory,
                images = finalStats.images,
                canvases = finalStats.canvases,
                fonts = finalStats.fonts,
            },
        }
        print("LOVE12 SHADOW BEGIN")
        print(json.encode(payload))
        print("LOVE12 SHADOW END")
        love.event.quit(0)
    end
end
