-- #760 experiment-only instrumentation around the EXISTING geometry authority.
--
-- This module does not build geometry. It varies only the parsed/tileset plane
-- triangle ceiling, forces a cold cache identity for the experiment, then
-- records what engine.geometry + engine.geometry.plane actually produced.
local probe = {}

local installed = false
local rows = {}
local budget = nil
local runId = nil

local function now()
    if love and love.timer and love.timer.getTime then return love.timer.getTime() end
    return os.clock()
end

local function shallowCopy(source)
    local out = {}
    for key, value in pairs(source or {}) do out[key] = value end
    return out
end

local function counter(snapshot, key)
    local counters = snapshot and snapshot.counters or {}
    return tonumber(counters[key]) or 0
end

local function delta(before, after, key)
    return counter(after, key) - counter(before, key)
end

local function stageTotal(snapshot, key)
    local stage = snapshot and snapshot.stages and snapshot.stages[key]
    return tonumber(stage and stage.totalMs) or 0
end

local function stageDelta(before, after, key)
    return stageTotal(after, key) - stageTotal(before, key)
end

local function exactDisplacement(specs, heightOverride)
    local plane = require("engine.geometry.plane")
    local images = require("engine.geometry.images")
    local base = specs and specs[1]
    if not base or base.topology ~= "plane" then return nil, nil end

    local layers = {}
    if heightOverride then
        layers[1] = {
            data = heightOverride,
            scale = base.heightScale,
            operation = base.heightOperation,
        }
    else
        for index, spec in ipairs(specs) do
            layers[index] = {
                data = images.data(spec.heightPath),
                scale = spec.heightScale,
                operation = spec.heightOperation,
            }
        end
    end

    local minLift, maxLift = math.huge, -math.huge
    local columns = tonumber(base.sampleColumns) or 1
    local sampleRows = tonumber(base.sampleRows) or 1
    for row = 0, sampleRows do
        local rawV = row / sampleRows
        local sampleV = base.surface == "wall"
            and rawV or plane.periodicSampleCoordinate(rawV)
        for column = 0, columns do
            local rawU = column / columns
            local sampleU = plane.periodicSampleCoordinate(rawU)
            local lift = plane.sampleField(layers, sampleU, sampleV)
                + (tonumber(base.offset) or 0)
            if lift < minLift then minLift = lift end
            if lift > maxLift then maxLift = lift end
        end
    end
    return minLift, maxLift
end

local function record(kind, identity, spec, specs, heightOverride, model, before, after, elapsedMs)
    if not spec or spec.topology ~= "plane" then return end
    local denseTriangles = delta(before, after, "geometry.denseTriangles")
    -- Cached calls are legitimate runtime behaviour but are not cold-compilation
    -- evidence. Recording them would make final triangles look like post-QEM
    -- seals because the dense/reduced counters correctly remain unchanged.
    if denseTriangles <= 0 then return end

    local finalTriangles = math.floor((tonumber(model and model.vertexCount) or 0) / 3)
    local reliefTriangles = delta(before, after, "geometry.reducedTriangles")
    local minLift, maxLift = exactDisplacement(specs or { spec }, heightOverride)

    rows[#rows + 1] = {
        kind = kind,
        identity = tostring(identity),
        id = spec.id,
        surface = spec.surface,
        sampleColumns = spec.sampleColumns,
        sampleRows = spec.sampleRows,
        denseTriangles = denseTriangles,
        exposedReliefCeiling = budget,
        exposedReliefTriangles = reliefTriangles,
        -- `plane.build` adds backing/perimeter seal after the budgeted reduced
        -- surface. Wall skirts are intentionally part of the budgeted surface:
        -- they participate in the same dense topology/QEM pass.
        perimeterSealTriangles = math.max(0, finalTriangles - reliefTriangles),
        finalTriangles = finalTriangles,
        coldCompileMs = stageDelta(before, after, "geometry.compile.total"),
        loadCallMs = elapsedMs,
        minDisplacement = minLift,
        maxDisplacement = maxLift,
    }
end

local DIRECTIONS = {
    { id = "N", dx = 0, dy = -1 },
    { id = "E", dx = 1, dy = 0 },
    { id = "S", dx = 0, dy = 1 },
    { id = "W", dx = -1, dy = 0 },
}

-- Use the same floor truth as cli_tools.positionAtClearCorridor. Extend that
-- existing fixture rule only far enough to choose deterministic first-wall
-- depths for the geometry-resolution photographs.
local function chooseCorridorPose(session, targetWallStep)
    local grid = session.mapGrid or {}
    local originX, originY = session.playerX or 1, session.playerY or 1
    local originDir = session.playerDir
    local function cell(x, y)
        return grid[y] and grid[y][x] or nil
    end
    local function isFloor(x, y)
        return cell(x, y) == "."
    end
    local best = nil
    for y, row in ipairs(grid) do
        for x = 1, #row do
            if isFloor(x, y) then
                for _, direction in ipairs(DIRECTIONS) do
                    local wallStep = nil
                    for step = 1, 16 do
                        local value = cell(x + direction.dx * step, y + direction.dy * step)
                        if value == nil then break end
                        if value ~= "." then
                            wallStep = step
                            break
                        end
                    end
                    if wallStep then
                        local depthPenalty = math.abs(wallStep - targetWallStep) * 1000
                        local distance = math.abs(x - originX) + math.abs(y - originY)
                        local turnPenalty = direction.id == originDir and 0 or 1
                        local score = depthPenalty + distance * 4 + turnPenalty
                        if not best or score < best.score then
                            best = {
                                x = x, y = y, dir = direction.id,
                                wallStep = wallStep, score = score,
                            }
                        end
                    end
                end
            end
        end
    end
    if not best then
        error("#760 capture: map has no floor pose facing an in-grid wall", 0)
    end
    return best
end

local function captureFrame(viewport, session, label, targetWallStep)
    local pose = chooseCorridorPose(session, targetWallStep)
    session.playerX, session.playerY, session.playerDir = pose.x, pose.y, pose.dir
    session.transitionTimer = 0
    session.transitionDir = nil

    local canvas = love.graphics.newCanvas(256, 240)
    local previous = love.graphics.getCanvas()
    love.graphics.push("all")
    love.graphics.setCanvas({ canvas, depth = true, stencil = true })
    love.graphics.clear(0, 0, 0, 1, true, true)
    love.graphics.setColor(1, 1, 1, 1)
    viewport.draw(session)
    love.graphics.setCanvas(previous)
    love.graphics.pop()

    local imageData = canvas:newImageData()
    local png = imageData:encode("png")
    return {
        label = label,
        targetWallStep = targetWallStep,
        actualWallStep = pose.wallStep,
        playerX = pose.x,
        playerY = pose.y,
        playerDir = pose.dir,
        width = 256,
        height = 240,
        png = love.data.encode("string", "base64", png),
        rgba = love.data.encode("string", "base64", imageData:getString()),
    }
end

function probe.capture(viewport, session)
    local original = {
        x = session.playerX,
        y = session.playerY,
        dir = session.playerDir,
        transitionTimer = session.transitionTimer,
        transitionDir = session.transitionDir,
    }
    local ok, result = pcall(function()
        return {
            captureFrame(viewport, session, "near", 1),
            captureFrame(viewport, session, "mid", 3),
            captureFrame(viewport, session, "far", 8),
        }
    end)
    session.playerX, session.playerY, session.playerDir = original.x, original.y, original.dir
    session.transitionTimer, session.transitionDir = original.transitionTimer, original.transitionDir
    if not ok then error(result, 0) end
    return result
end

function probe.install(requestedBudget, requestedRunId)
    if installed then return end
    budget = assert(tonumber(requestedBudget), "#760 probe needs a numeric budget")
    if budget < 2 then error("#760 budget must be >= 2", 0) end
    runId = tostring(requestedRunId or "run")
    installed = true
    rows = {}

    local geometry = require("engine.geometry")
    local schema = require("engine.geometry.schema")
    local profiler = require("engine.map_build_profiler")

    -- Directory-backed plane assets parse their own metadata. Preserve every
    -- normalized field from the real parser and alter ONLY the QEM ceiling.
    local originalParse = schema.parse
    schema.parse = function(assetPath)
        local spec = originalParse(assetPath)
        if spec and spec.topology == "plane" then
            spec.triangleBudget = budget
        end
        return spec
    end

    -- The production composition key correctly identities authored source +
    -- compiler + quality, but the experiment is deliberately changing one
    -- parsed value without touching source files. Add the experimental ceiling
    -- and unique run id so the persistent compiled store cannot serve a mesh
    -- built for another ceiling or a prior benchmark run.
    local originalCompositionKey = geometry.compositionKey
    geometry.compositionKey = function(assetPaths)
        return originalCompositionKey(assetPaths)
            .. "|issue760:" .. runId .. ":" .. tostring(budget)
    end

    local originalLoad = geometry.load
    geometry.load = function(assetPaths)
        local before = profiler.snapshot()
        local started = now()
        local model = originalLoad(assetPaths)
        local elapsed = (now() - started) * 1000
        local after = profiler.snapshot()
        local spec = model and model.spec
        if spec and spec.topology == "plane" then
            local identity = type(assetPaths) == "table"
                and table.concat(assetPaths, "+") or assetPaths
            record("directory", identity, spec, model.specs, nil,
                model, before, after, elapsed)
        end
        return model
    end

    -- Atlas-authored surfaces already receive a fully normalized plane spec
    -- from viewport_3d. Copy it, alter only the exposed-relief ceiling, and
    -- similarly make the cache identity cold/ceiling-specific.
    local originalAtlas = geometry.loadAtlasSurface
    geometry.loadAtlasSurface = function(cacheKey, spec, heightData, texture, uv)
        local varied = shallowCopy(spec)
        varied.triangleBudget = budget
        local coldKey = tostring(cacheKey) .. "|issue760:" .. runId
            .. ":" .. tostring(budget)
        local before = profiler.snapshot()
        local started = now()
        local model = originalAtlas(coldKey, varied, heightData, texture, uv)
        local elapsed = (now() - started) * 1000
        local after = profiler.snapshot()
        record("atlas", cacheKey, varied, { varied }, heightData,
            model, before, after, elapsed)
        return model
    end
end

function probe.report()
    return {
        budget = budget,
        runId = runId,
        surfaces = rows,
        note = "exposedReliefTriangles includes integral wall skirt topology; perimeterSealTriangles is only geometry appended after QEM relief reduction",
    }
end

return probe
