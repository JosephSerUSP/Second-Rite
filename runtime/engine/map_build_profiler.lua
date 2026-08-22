-- Passive timing/counter collector for issue #161.
--
-- This module deliberately owns no map, geometry, or renderer implementation.
-- The real subsystem which owns a stage opens/closes a span around its existing
-- work; when profiling is inactive the calls are cheap no-ops. The CLI profiler
-- does bypass normal scene bootstrap, however, so `begin` may install the same
-- production runtime adapter that gameplay would already have installed. This
-- keeps the diagnostic on the real codepath rather than creating a parallel
-- build/cache pipeline.
local profiler = {}

local active = false
local startedAt = nil
local metadata = {}
local stages = {}
local counters = {}

local function now()
    if love and love.timer and love.timer.getTime then return love.timer.getTime() end
    return os.clock()
end

local function copyTable(source)
    local out = {}
    for k, v in pairs(source or {}) do
        if type(v) == "table" then out[k] = copyTable(v) else out[k] = v end
    end
    return out
end

local function installProfiledRuntimeAdapters()
    -- profile-map-build requires viewport_3d directly rather than entering a
    -- world scene, so presentation.world_renderer never gets a chance to install
    -- the prepared-map LRU. If the viewport is already loaded, install that same
    -- production adapter before the first profiled prepareStructure call. A
    -- failure is intentionally loud: silently benchmarking the old one-slot path
    -- would produce authoritative-looking but invalid #161 numbers.
    local viewport = package.loaded["presentation.viewport_3d"]
    if type(viewport) ~= "table" then return end
    local cache = require("presentation.prepared_map_cache")
    cache.install(viewport)
end

function profiler.isActive()
    return active
end

function profiler.begin(meta)
    installProfiledRuntimeAdapters()
    active = true
    startedAt = now()
    metadata = copyTable(meta or {})
    stages = {}
    counters = {}
end

function profiler.stop()
    active = false
end

-- `bucket` is intentionally descriptive rather than inferred from the stage
-- name. Only `cpu` and `graphics` buckets participate in CPU-scaling estimates;
-- `aggregate`/`detail` spans are useful diagnostics but may overlap children.
function profiler.span(name, bucket)
    if not active then return function() end end
    local t0 = now()
    local closed = false
    return function()
        if closed then return end
        closed = true
        local ms = (now() - t0) * 1000
        local row = stages[name]
        if not row then
            row = { calls = 0, totalMs = 0, minMs = math.huge, maxMs = 0,
                bucket = bucket or "detail" }
            stages[name] = row
        end
        row.calls = row.calls + 1
        row.totalMs = row.totalMs + ms
        if ms < row.minMs then row.minMs = ms end
        if ms > row.maxMs then row.maxMs = ms end
    end
end

function profiler.add(name, amount)
    if not active then return end
    counters[name] = (counters[name] or 0) + (amount or 1)
end

function profiler.set(name, value)
    if not active then return end
    counters[name] = value
end

function profiler.cache(name, hit)
    profiler.add(name .. (hit and ".hits" or ".misses"), 1)
end

function profiler.snapshot(extra)
    local stageCopy = copyTable(stages)
    local cpuMs, graphicsMs = 0, 0
    for _, row in pairs(stageCopy) do
        row.meanMs = row.calls > 0 and row.totalMs / row.calls or 0
        if row.minMs == math.huge then row.minMs = 0 end
        if row.bucket == "cpu" then cpuMs = cpuMs + row.totalMs end
        if row.bucket == "graphics" then graphicsMs = graphicsMs + row.totalMs end
    end

    local elapsedMs = startedAt and (now() - startedAt) * 1000 or 0
    local projections = {}
    for _, scale in ipairs({ 1.5, 2.0, 3.0 }) do
        -- These are explicitly projections, not promises: only spans marked as
        -- non-overlapping CPU work are scaled. Graphics/API time is left fixed.
        projections[string.format("%.1fx", scale)] = {
            cpuScale = scale,
            observedCpuMs = cpuMs,
            observedGraphicsMs = graphicsMs,
            projectedObservedMs = cpuMs * scale + graphicsMs,
        }
    end

    local out = {
        metadata = copyTable(metadata),
        elapsedMs = elapsedMs,
        stages = stageCopy,
        counters = copyTable(counters),
        cpuObservedMs = cpuMs,
        graphicsObservedMs = graphicsMs,
        cpuScalingProjection = projections,
    }
    for k, v in pairs(extra or {}) do out[k] = v end
    return out
end

return profiler