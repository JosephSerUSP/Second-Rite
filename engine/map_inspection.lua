-- Read-only semantic inspection of one resolved procedural Map instance.
--
-- This is deliberately a consumer of exploration.loadMap, not another map
-- generator. The transient session is never attached to the player's session
-- or save state. The scope identity is provisional: current main has one
-- generated scope per Map, while the response shape leaves room for future
-- independently generated scopes without naming an Area schema here.
local sessionModule = require("engine.session")
local exploration = require("engine.exploration")
local tilesetResolver = require("engine.tileset_resolver")

local inspection = {}

local function findMapIndex(loader, mapId)
    for index, map in ipairs(loader.maps or {}) do
        if tostring(map.id) == tostring(mapId) then return index end
    end
    return nil
end

local function copyEventFact(event)
    return {
        id = event.id,
        type = event.type,
        x = event.x,
        y = event.y,
        scriptId = event.scriptId,
        actorId = event.actorId,
        sprite = event.sprite,
        name = event.name,
        label = event.label,
        wallEvent = event.wallEvent,
        source = event.provenance and event.provenance.kind or "generated runtime event",
        reason = event.provenance and event.provenance.reason,
        authoredEventId = event.provenance and event.provenance.eventId,
    }
end

local function withTransientMap(loader, mapId, mapSnapshot, callback)
    local index = findMapIndex(loader, mapId)
    local appended = false
    if not index then
        index = #loader.maps + 1
        appended = true
    end
    local previous = loader.maps[index]
    loader.maps[index] = mapSnapshot
    local ok, result = pcall(callback, index)
    if appended then
        table.remove(loader.maps, index)
    else
        loader.maps[index] = previous
    end
    if not ok then error(result, 0) end
    return result
end

function inspection.resolve(loader, mapId, mapSnapshot, seed)
    if type(mapSnapshot) ~= "table" then error("map inspection needs a map snapshot", 0) end
    if mapSnapshot.safe == true then
        error("map inspection only supports procedural Maps", 0)
    end
    seed = tonumber(seed)
    if not seed then error("map inspection needs a numeric seed", 0) end

    local previousActiveSession = sessionModule.activeSession
    local ok, result = pcall(withTransientMap, loader, mapId, mapSnapshot, function(mapIndex)
        local trace = {}
        local previewSession = sessionModule.GameSession.new(loader)
        exploration.loadMap(previewSession, mapIndex, { seed = seed, inspection = trace })

        local mapData = previewSession.currentMapData
        local tileset = tilesetResolver.resolve(loader, mapData)
        if not tileset then
            error("map inspection could not resolve tileset '" .. tostring(mapData.tileset) .. "'", 0)
        end

        local generatedEvents = {}
        for _, event in ipairs(mapData.events or {}) do
            if event.provenance then
                generatedEvents[#generatedEvents + 1] = copyEventFact(event)
            end
        end

        local generatedGrid = {}
        for y, row in ipairs(previewSession.mapGrid or {}) do
            generatedGrid[y] = table.concat(row)
        end

        local authored = {
            anchors = mapSnapshot.anchors or {},
            events = mapSnapshot.events or {},
            zones = mapSnapshot.zones or {},
            spawn = mapSnapshot.spawn,
        }
        local generated = {
            grid = generatedGrid,
            rooms = trace.rooms or {},
            corridors = trace.corridors or {},
            openings = trace.openings or {},
            zones = trace.zones or {},
            events = generatedEvents,
            features = trace.featurePlacements or {},
            lights = trace.lights or {},
            protectedCells = trace.protectedCells or {},
            entrance = {
                x = (mapData.entranceX or 1) - 1,
                y = (mapData.entranceY or 1) - 1,
            },
            exit = {
                x = (mapData.exitX or 1) - 1,
                y = (mapData.exitY or 1) - 1,
            },
        }

        return {
            version = 1,
            kind = "generated-map-inspection",
            request = {
                transient = true,
                previewInstance = true,
                seed = seed,
                saveMutation = false,
            },
            map = {
                id = mapData.id,
                title = mapData.title or mapData.name,
                width = #generatedGrid[1],
                height = #generatedGrid,
                generationProfile = mapData.generationProfile,
            },
            scope = {
                id = "map:" .. tostring(mapData.id) .. ":generated",
                source = "Map",
                kind = "current-single-generated-scope",
            },
            authored = authored,
            generated = generated,
            resolved = {
                tileset = {
                    requestedId = mapData.tileset or "dungeon_default",
                    resolvedId = tileset.id or mapData.tileset or "dungeon_default",
                    hasMapOverride = type(mapData.tilesetOverride) == "table"
                        and next(mapData.tilesetOverride) ~= nil,
                    featureCount = #(tileset.features or {}),
                },
            },
        }
    end)
    sessionModule.activeSession = previousActiveSession
    if not ok then error(result, 0) end
    return result
end

inspection.findMapIndex = findMapIndex

return inspection
