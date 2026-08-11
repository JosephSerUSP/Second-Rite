package.path = package.path .. ";./?.lua;./presentation/?.lua"

local cacheModule = require("presentation.prepared_map_cache")

print("[TEST] Starting prepared-map cache tests...")

local passed, failed = 0, 0
local function check(cond, msg)
    if cond then passed = passed + 1 print("  [PASS] " .. msg)
    else failed = failed + 1 print("  [FAIL] " .. msg) end
end

local function fakeMesh(count)
    return {
        count = count, released = false,
        getVertexCount = function(self) return self.count end,
        release = function(self) self.released = true end,
    }
end

local function fakeProfiler()
    local out = { counters = {} }
    function out.add(name, amount)
        out.counters[name] = (out.counters[name] or 0) + (amount or 1)
    end
    function out.set(name, value) out.counters[name] = value end
    function out.cache(name, hit) out.add(name .. (hit and ".hits" or ".misses"), 1) end
    return out
end

-- Faithful enough fake of viewport_3d's existing one-entry-per-session cache:
-- proxy sessions are the whole point of the adapter, so this fake deliberately
-- releases a previous structure when the SAME proxy changes identity.
local function fakeViewport()
    local viewport = { builds = 0, releases = {}, internals = setmetatable({}, { __mode = "k" }) }
    function viewport.prepareStructure(session)
        local cached = viewport.internals[session]
        local quality = session.__qualityForFake and session.__qualityForFake() or "ignored"
        if cached and cached.grid == session.mapGrid
                and cached.mapData == session.currentMapData
                and cached.structureRevision == (session.mapStructureRevision or 0)
                and cached.presentationRevision == (session.mapPresentationRevision or 0)
                and cached.quality == quality then
            return cached
        end
        if cached then
            cached.released = true
            viewport.releases[#viewport.releases + 1] = cached.token
        end
        viewport.builds = viewport.builds + 1
        local token = tostring(session.currentMapIndex) .. ":" .. tostring(viewport.builds)
        local vertices = {}
        for i = 1, 6 do vertices[i] = { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 } end
        local prepared = {
            token = token,
            grid = session.mapGrid,
            mapData = session.currentMapData,
            structureRevision = session.mapStructureRevision or 0,
            presentationRevision = session.mapPresentationRevision or 0,
            quality = quality,
            modelSurfaces = {
                fixture = { { mesh = fakeMesh(6), vertices = vertices } },
            },
            floorCells = {},
        }
        viewport.internals[session] = prepared
        return prepared
    end
    function viewport.invalidateStructure(session)
        local cached = viewport.internals[session]
        if cached then
            cached.released = true
            viewport.releases[#viewport.releases + 1] = cached.token
            viewport.internals[session] = nil
        end
    end
    return viewport
end

local function fixture(capacity)
    local rawA = { id = "A", tileset = "stone", events = {}, materials = {}, lightObjects = {} }
    local rawB = { id = "B", tileset = "stone", events = {}, materials = {}, lightObjects = {} }
    local rawC = { id = "C", tileset = "stone", events = {}, materials = {}, lightObjects = {} }
    local grids = {
        [1] = { { ".", "#" } },
        [2] = { { ".", "." } },
        [3] = { { "#", "." } },
    }
    local features = { [1] = {}, [2] = {}, [3] = {} }
    local zones = { [1] = {}, [2] = {}, [3] = {} }
    local lights = { [1] = {}, [2] = {}, [3] = {} }
    local runtimeLights = { [1] = {}, [2] = {}, [3] = {} }
    local tileset = { id = "stone" }
    local quality = "normal"
    local profiler = fakeProfiler()
    local stopped = {}
    local loader = {
        maps = { rawA, rawB, rawC },
        getTileset = function(id) return id == "stone" and tileset or nil end,
    }
    local session = {
        loader = loader,
        mapStructureRevision = 0,
        mapPresentationRevision = 0,
    }
    session.__qualityForFake = function() return quality end

    local function activate(index)
        session.currentMapIndex = index
        session.mapGrid = grids[index]
        local raw = loader.maps[index]
        local copy = {}
        for key, value in pairs(raw) do copy[key] = value end
        copy.runtimeLight = runtimeLights[index]
        session.currentMapData = copy
        session.generatedFeatures = features[index]
        session.generatedZones = zones[index]
        session.generatedLightObjects = lights[index]
        -- Match exploration.loadMap: activation bumps this even if restored.
        session.mapStructureRevision = session.mapStructureRevision + 1
    end

    local viewport = fakeViewport()
    local manager = cacheModule.install(viewport, {
        capacity = capacity,
        profiler = profiler,
        qualityKey = function() return quality end,
        stopEffect = function(handle) stopped[#stopped + 1] = handle end,
    })
    return {
        viewport = viewport, manager = manager, profiler = profiler,
        session = session, activate = activate, grids = grids,
        raw = { rawA, rawB, rawC }, stopped = stopped,
        setQuality = function(value) quality = value end,
    }
end

-- A -> B -> A: map activation increments the engine revision, but the restored
-- grid/source/runtime identities are stable, so the third leg must be an LRU hit.
do
    local f = fixture(2)
    f.activate(1)
    local firstA = f.viewport.prepareStructure(f.session)
    f.activate(2)
    f.viewport.prepareStructure(f.session)
    f.activate(1)
    local secondA = f.viewport.prepareStructure(f.session)
    local stats = f.manager.stats(f.session)
    check(firstA == secondA, "A -> B -> A reuses A's prepared structure")
    check(f.viewport.builds == 2, "A -> B -> A builds only A and B")
    check(stats.hits == 1 and stats.misses == 2,
        "lifecycle counters report two misses and the third-leg hit")
    -- A repeated prepare in the same active map is normal frame reuse, not a
    -- second lifecycle cache hit.
    f.viewport.prepareStructure(f.session)
    check(f.manager.stats(f.session).hits == 1,
        "same-map render frames do not inflate prepared-map hit counters")
end

-- True LRU: touching A after A,B makes B the victim when C arrives.
do
    local f = fixture(2)
    f.activate(1); local a = f.viewport.prepareStructure(f.session)
    f.activate(2); local b = f.viewport.prepareStructure(f.session)
    f.activate(1); f.viewport.prepareStructure(f.session)
    f.activate(3); f.viewport.prepareStructure(f.session)
    local stats = f.manager.stats(f.session)
    check(b.released == true and a.released ~= true,
        "LRU eviction removes B after A was touched most recently")
    check(stats.evictions == 1 and stats.residentCount == 2,
        "LRU stays bounded at capacity two")
end

-- Explicit structural invalidation releases every resident GPU structure owned
-- by the session and prevents subsequent stale reuse.
do
    local f = fixture(2)
    f.activate(1); local oldA = f.viewport.prepareStructure(f.session)
    f.activate(2); local oldB = f.viewport.prepareStructure(f.session)
    f.viewport.invalidateStructure(f.session)
    check(oldA.released and oldB.released,
        "explicit structure invalidation releases all resident resources")
    check(f.manager.stats(f.session).residentCount == 0,
        "explicit invalidation leaves no resident prepared structures")
    f.activate(1); local newA = f.viewport.prepareStructure(f.session)
    check(newA ~= oldA, "explicit invalidation cannot reuse a stale structure")
end

-- Same active grid + mapStructureRevision change is the engine's mutation
-- signal. Unlike transfer-time increments, this must invalidate immediately.
do
    local f = fixture(2)
    f.activate(1)
    local oldA = f.viewport.prepareStructure(f.session)
    f.session.mapGrid[1][1] = "#"
    f.session.mapStructureRevision = f.session.mapStructureRevision + 1
    local newA = f.viewport.prepareStructure(f.session)
    local stats = f.manager.stats(f.session)
    check(newA ~= oldA and oldA.released,
        "map mutation invalidates and releases the prior prepared structure")
    check(stats.invalidations >= 1,
        "map mutation is observable as a prepared-map invalidation")
end

-- A structural revision can occur after transfer but before the first render.
-- The activation-scoped revision then jumps by more than loadMap's single bump;
-- because the cache cannot attribute that hidden mutation to one resident entry,
-- it must conservatively invalidate rather than returning stale A.
do
    local f = fixture(2)
    f.activate(1); local oldA = f.viewport.prepareStructure(f.session)
    f.activate(2); f.viewport.prepareStructure(f.session)
    f.activate(1)
    f.session.mapGrid[1][1] = "#"
    f.session.mapStructureRevision = f.session.mapStructureRevision + 1
    local newA = f.viewport.prepareStructure(f.session)
    check(newA ~= oldA and oldA.released,
        "pre-draw map mutation cannot reuse a resident stale structure")
end

-- Material/light lookup source collections are part of prepared identity. A
-- loader/editor replacement must invalidate even when topology did not change.
do
    local f = fixture(2)
    f.activate(1)
    local oldA = f.viewport.prepareStructure(f.session)
    f.session.currentMapData.materials = { { "moss" } }
    local newA = f.viewport.prepareStructure(f.session)
    check(newA ~= oldA and oldA.released,
        "material source replacement invalidates prepared lookup/geometry state")
end

-- Quality is a canonical separate identity dimension. Retaining both variants
-- is safe; returning to the first quality may reuse its still-valid GPU data.
do
    local f = fixture(2)
    f.activate(1)
    local normal = f.viewport.prepareStructure(f.session)
    f.setQuality("fine")
    local fine = f.viewport.prepareStructure(f.session)
    f.setQuality("normal")
    local normalAgain = f.viewport.prepareStructure(f.session)
    check(normal ~= fine, "geometry quality change never reuses incompatible GPU geometry")
    check(normalAgain == normal, "quality variants remain safely separated in the LRU")
end

-- Replacing authored loader data is a reload/edit boundary. Even if the map
-- index and runtime grid happen to be unchanged, its old prepared structure is
-- invalid and must be released rather than found by id alone.
do
    local f = fixture(2)
    f.activate(1)
    local oldA = f.viewport.prepareStructure(f.session)
    local replacement = { id = "A", tileset = "stone", events = {}, materials = {}, lightObjects = {} }
    f.session.loader.maps[1] = replacement
    f.session.currentMapData = {
        id = "A", tileset = "stone", events = replacement.events,
        materials = replacement.materials, lightObjects = replacement.lightObjects,
        runtimeLight = f.session.currentMapData.runtimeLight,
    }
    local newA = f.viewport.prepareStructure(f.session)
    check(newA ~= oldA and oldA.released,
        "authored map replacement invalidates same-index prepared geometry")
end

-- Bounded capacity one is the benchmark control: A is necessarily evicted by B,
-- so the third A is a miss and resource destruction is explicit.
do
    local f = fixture(1)
    f.activate(1); local firstA = f.viewport.prepareStructure(f.session)
    local clipped = fakeMesh(3)
    firstA.modelSurfaces.fixture[1].clippedMesh = clipped
    firstA.modelSurfaces.fixture[1].clippedCapacity = 3
    f.activate(2); f.viewport.prepareStructure(f.session)
    check(clipped.released,
        "eviction explicitly releases the placed near-clip stream mesh")
    f.activate(1); local secondA = f.viewport.prepareStructure(f.session)
    local stats = f.manager.stats(f.session)
    check(firstA ~= secondA and firstA.released,
        "capacity-one control forces A eviction before A -> B -> A revisit")
    check(stats.evictions == 2 and stats.hits == 0 and stats.misses == 3,
        "forced-eviction control reports deterministic miss/eviction counters")
end

-- Effects are not static residency. They must stop when their map becomes
-- inactive, while its prepared GPU structure itself remains cached.
do
    local f = fixture(2)
    f.activate(1)
    local a = f.viewport.prepareStructure(f.session)
    a.worldEffectsInitialized = true
    a.worldEffectHandles = { "torch" }
    a.ambientEffectHandle = "mist"
    f.activate(2)
    f.viewport.prepareStructure(f.session)
    check(#f.stopped == 2 and a.released ~= true,
        "map switch suspends effect handles without releasing cached geometry")
    check(a.worldEffectsInitialized == nil and a.worldEffectHandles == nil,
        "cached map effects are marked for clean reinitialization on revisit")
end

-- Memory accounting is explicitly an estimate: 13 float32 GPU attributes per
-- retained vertex, with Lua-number CPU payload counted only where vertex arrays
-- are still retained. Persistent surface batches also retain their last vertex
-- map; its bytes are conservatively estimated as uint32 entries.
do
    local f = fixture(2)
    f.activate(1)
    local prepared = f.viewport.prepareStructure(f.session)
    local indexedVertices = {}
    for i = 1, 6 do indexedVertices[i] = { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 } end
    prepared.surfaceBatches = {
        floor = {
            mesh = fakeMesh(6), vertices = indexedVertices,
            selected = { { indices = { 1, 2, 3 } } },
        },
    }
    local stats = f.manager.stats(f.session)
    check(stats.retainedMeshes == 2 and stats.retainedVertices == 12,
        "retained mesh/vertex counts are exposed")
    check(stats.retainedIndices == 3,
        "retained surface-batch vertex-map indices are exposed")
    check(stats.retainedGpuVertexBytesEstimate == 12 * 13 * 4,
        "GPU vertex byte estimate follows the 13-float world vertex format")
    check(stats.retainedGpuIndexBytesEstimate == 3 * 4,
        "GPU index byte estimate is reported separately")
    check(stats.retainedGpuBytesEstimate == 12 * 13 * 4 + 3 * 4,
        "combined GPU bytes remain explicitly approximate")
    check(stats.retainedCpuVertexPayloadBytesEstimate == 12 * 13 * 8,
        "CPU vertex payload estimate is reported separately")
    check(#stats.residentEntries == 1 and stats.residentEntries[1].mapIndex == 1
            and stats.residentEntries[1].vertices == 12,
        "retained payload is reported per resident map entry")
end

print(string.format("=== Prepared Map Cache Tests: %d passed, %d failed ===", passed, failed))
if failed > 0 then require("tests.fail_fast")(failed .. " prepared-map cache test(s) failed", failed) end
