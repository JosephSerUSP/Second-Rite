package.path = package.path .. ";./?.lua;./presentation/?.lua"

local cacheModule = require("presentation.prepared_map_cache")

print("[TEST] Starting current-main prepared-map cache seam tests...")

local function fakeMesh(count)
    return {
        count = count,
        released = false,
        getVertexCount = function(self) return self.count end,
        release = function(self) self.released = true end,
    }
end

local function vertexArray(count)
    local vertices = {}
    for i = 1, count do
        vertices[i] = { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 }
    end
    return vertices
end

local function fakeViewport()
    local viewport = { builds = 0, internals = setmetatable({}, { __mode = "k" }) }
    function viewport.prepareStructure(session)
        local cached = viewport.internals[session]
        if cached and cached.grid == session.mapGrid
                and cached.mapData == session.currentMapData
                and cached.structureRevision == (session.mapStructureRevision or 0) then
            return cached
        end
        if cached then
            cached.released = true
            if cached.wallMesh then cached.wallMesh:release() end
        end
        viewport.builds = viewport.builds + 1
        local wallMesh = fakeMesh(3)
        local prepared = {
            token = tostring(session.currentMapIndex) .. ":" .. tostring(viewport.builds),
            grid = session.mapGrid,
            mapData = session.currentMapData,
            structureRevision = session.mapStructureRevision or 0,
            presentationRevision = session.mapPresentationRevision or 0,
            floorCells = {},
            wallMesh = wallMesh,
            -- #300 stores wall faces by atlas, then by visibility profile.
            resolvedWallFaces = {
                atlas = {
                    play = {
                        faces = {
                            { meshTree = { mesh = wallMesh, vertices = vertexArray(3) } },
                        },
                        stats = { profile = "play" },
                    },
                },
            },
        }
        viewport.internals[session] = prepared
        return prepared
    end
    function viewport.invalidateStructure(session)
        local cached = viewport.internals[session]
        if cached then
            cached.released = true
            if cached.wallMesh and not cached.wallMesh.released then cached.wallMesh:release() end
            viewport.internals[session] = nil
        end
    end
    return viewport
end

local tileset = { id = "stone" }
local rawMap = { id = "A", tileset = "stone", events = {}, materials = {}, lightObjects = {} }
local loader = {
    maps = { rawMap },
    getTileset = function(id) return id == "stone" and tileset or nil end,
}
local session = {
    loader = loader,
    currentMapIndex = 1,
    mapGrid = { { ".", "#" } },
    currentMapData = {
        id = "A", tileset = "stone", events = rawMap.events,
        materials = rawMap.materials, lightObjects = rawMap.lightObjects,
        runtimeLight = {},
    },
    generatedFeatures = {}, generatedZones = {}, generatedLightObjects = {},
    mapStructureRevision = 1, mapPresentationRevision = 0,
}

local viewport = fakeViewport()
local manager = cacheModule.install(viewport, {
    capacity = 2,
    qualityKey = function() return "normal" end,
    stopEffect = function() end,
})

local first = viewport.prepareStructure(session)
local stats = manager.stats(session)
assert(stats.retainedMeshes == 1 and stats.retainedVertices == 3,
    "#300 nested resolvedWallFaces must participate in retained-memory accounting")
assert(stats.retainedCpuVertexPayloadBytesEstimate == 3 * 13 * 8,
    "nested wall CPU vertex payload must be included in the lower-bound estimate")

-- Replacing the authoritative base tileset is a source reload boundary even
-- when map/grid/override identities are otherwise unchanged.
tileset = { id = "stone" }
local afterTilesetReplace = viewport.prepareStructure(session)
assert(afterTilesetReplace ~= first and first.released,
    "base tileset source replacement must invalidate resident prepared geometry")

-- Resident sets are session-owned. Entering another authoritative session must
-- release the old session rather than keeping GPU state alive behind a weak key.
local rawMapB = { id = "B", tileset = "stone", events = {}, materials = {}, lightObjects = {} }
local loaderB = {
    maps = { rawMapB },
    getTileset = function(id) return id == "stone" and tileset or nil end,
}
local sessionB = {
    loader = loaderB,
    currentMapIndex = 1,
    mapGrid = { { "#", "." } },
    currentMapData = {
        id = "B", tileset = "stone", events = rawMapB.events,
        materials = rawMapB.materials, lightObjects = rawMapB.lightObjects,
        runtimeLight = {},
    },
    generatedFeatures = {}, generatedZones = {}, generatedLightObjects = {},
    mapStructureRevision = 1, mapPresentationRevision = 0,
}
local oldSessionPrepared = afterTilesetReplace
viewport.prepareStructure(sessionB)
assert(oldSessionPrepared.released,
    "session replacement releases the previous session's resident prepared set")
assert(manager.stats(session).residentCount == 0 and manager.stats(sessionB).residentCount == 1,
    "session replacement leaves residency only under the new owner")

print("test_prepared_map_cache_current_main: OK")