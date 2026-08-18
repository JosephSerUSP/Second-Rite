-- Presentation/tool-host bridge for Thestra Studio's authoritative map renderables.
--
-- The editor submits a transient map snapshot to a short-lived request file.
-- This module temporarily substitutes that authored map in the already-loaded
-- project data, asks exploration.loadMap + viewport_3d + map_renderable_bundle
-- to resolve it through the real runtime path, prints one JSON bundle, then
-- restores loader state. It never saves authored data and never implements map
-- or geometry semantics itself.
local bridge = {}

local function readRequest(path)
    local json = require("engine.data.json")
    local text, err = love.filesystem.read(path)
    if not text then error("renderable request could not be read: " .. tostring(err), 0) end
    local decoded = json.decode(text)
    if type(decoded) ~= "table" then error("renderable request must be a JSON object", 0) end
    if type(decoded.map) ~= "table" then error("renderable request needs a map snapshot", 0) end
    return decoded
end

local function findMapIndex(loader, mapId)
    for index, map in ipairs(loader.maps or {}) do
        if tostring(map.id) == tostring(mapId) then return index end
    end
    return nil
end

local function withTransientMap(loader, mapId, mapSnapshot, fn)
    loader.maps = loader.maps or {}
    local index = findMapIndex(loader, mapId)
    local appended = false
    if not index then
        index = #loader.maps + 1
        appended = true
    end
    local previous = loader.maps[index]
    loader.maps[index] = mapSnapshot
    local ok, a, b = pcall(fn, index)
    if appended then
        table.remove(loader.maps, index)
    else
        loader.maps[index] = previous
    end
    if not ok then error(a, 0) end
    return a, b
end

function bridge.run(requestPath, mapId, loader, cliTools)
    local json = require("engine.data.json")
    local request = readRequest(requestPath)
    local requestedId = request.map.id
    if requestedId == nil then requestedId = mapId end
    if tostring(requestedId) ~= tostring(mapId) then
        error("renderable request map id does not match preview-map id", 0)
    end

    local payload
    local ok, err = pcall(function()
        payload = withTransientMap(loader, mapId, request.map, function(mapIndex)
            local exploration = require("engine.exploration")
            local viewport_3d = require("presentation.viewport_3d")
            local renderables = require("presentation.map_renderable_bundle")
            local vSession = cliTools.makeHarnessSession(loader)
            local seed = tonumber(request.seed) or 1735689600

            -- Generated maps consult wall-clock time in their default path.
            -- Pin both explicit seed and os.time so the same snapshot produces
            -- the same bundle on repeated editor requests.
            local originalTime = os.time
            os.time = function() return seed end
            local loaded, loadErr = pcall(exploration.loadMap, vSession, mapIndex, { seed = seed })
            os.time = originalTime
            if not loaded then error(loadErr, 0) end

            -- Wall composites use viewport-owned reusable canvases/quads. Init
            -- creates those exact runtime resources before the collector asks
            -- prepareResolvedStructure() for final wall materials.
            viewport_3d.init()
            local result, collectErr = renderables.collect(vSession, "authoring")
            if not result then error(collectErr or "runtime produced no renderable bundle", 0) end
            -- Encoding is a property of THIS transport, not of the bundle.
            -- map_geometry_export consumes the same collector and indexes the
            -- float streams directly, so quantizing inside collect() would
            -- silently empty every OBJ/.blend export (#736/#739).
            local int16 = require("presentation.renderable_int16_transport")
            if int16.requested() then result = int16.encode(result) end

            -- Lighting and vertex shading remain separate resolved presentation
            -- facts. Browser authoring composes them over the collector's source
            -- colours so moving a lamp cannot erase the environmental tint.
            local resolvedMap = vSession.currentMapData
            result.light = resolvedMap and (resolvedMap.runtimeLight or resolvedMap.light) or nil
            result.vertexShadingLayers = resolvedMap and resolvedMap.vertexShadingLayers or nil
            result.request = { transient = true, seed = seed }
            return result
        end)
    end)
    if not ok then payload = { error = tostring(err) } end

    print("RENDERABLE BEGIN")
    print(json.encode(payload))
    print("RENDERABLE END")
end

return bridge