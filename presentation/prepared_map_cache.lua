-- Bounded prepared-map residency for the 3D viewport (#161A).
--
-- viewport_3d already owns the authoritative prepared structure and its GPU
-- release routine. Its built-in cache is intentionally one entry per session,
-- however, so normal A -> B -> A travel destroys A as soon as B is prepared.
-- This adapter preserves that ownership: each resident map identity receives a
-- small proxy session, which gives viewport_3d's existing cache one independent
-- slot. This module only owns which proxy slots remain resident (LRU), active-
-- map effect suspension, identity/invalidation, and profiling/accounting.
--
-- Identity is deliberately runtime/exact rather than a guessed "map id":
--   * session owner (the outer weak-key table; entries never cross sessions)
--   * current map index + authored loader map table identity
--   * runtime grid identity + an observed in-place structure mutation epoch
--   * effective tileset id, base definition and map override identities
--   * generated feature/zone/light collections and event/material/light identities
--   * baked runtime-light identity
--   * engine.geometry.quality.key()
--
-- The authored/tileset table identities change when loader/editor data is
-- reloaded/replaced. Generated grids/features/lights are restored by
-- exploration.mapStates, so A -> B -> A keeps the same identities inside an
-- expedition; a new procedural generation does not. mapStructureRevision is
-- activation-scoped today (loadMap increments it on every transfer), so it
-- cannot itself be a cross-map key. Instead, while one map/grid remains active,
-- a change in that revision is treated as an in-place structural mutation and
-- bumps the grid's local epoch. This preserves the existing mutation signal
-- without turning every revisit into a false miss.
local prepared_map_cache = {}

prepared_map_cache.DEFAULT_CAPACITY = 2
prepared_map_cache.WORLD_VERTEX_FLOATS = 13
prepared_map_cache.WORLD_VERTEX_GPU_BYTES = prepared_map_cache.WORLD_VERTEX_FLOATS * 4
prepared_map_cache.CPU_NUMBER_BYTES = 8

local installed = setmetatable({}, { __mode = "k" })

local IDENTITY_FIELDS = {
    "mapIndex", "authoredMap", "grid", "structureEpoch",
    "tilesetId", "tilesetBase", "tilesetOverride",
    "generatedFeatures", "generatedZones", "generatedLightObjects",
    "events", "materials", "lightObjects", "runtimeLight", "qualityKey",
}

local NON_QUALITY_FIELDS = {
    "mapIndex", "authoredMap", "grid", "structureEpoch",
    "tilesetId", "tilesetBase", "tilesetOverride",
    "generatedFeatures", "generatedZones", "generatedLightObjects",
    "events", "materials", "lightObjects", "runtimeLight",
}

local function sameFields(a, b, fields)
    if not a or not b then return false end
    for _, key in ipairs(fields) do
        if a[key] ~= b[key] then return false end
    end
    return true
end

local function sameIdentity(a, b)
    return sameFields(a, b, IDENTITY_FIELDS)
end

local function sameNonQualityIdentity(a, b)
    return sameFields(a, b, NON_QUALITY_FIELDS)
end

local function configuredCapacity(session)
    -- Environment override exists primarily for #161 profiling/control runs.
    -- Runtime tuning follows the renderer's existing dungeon settings owner
    -- (`loader.system.dungeon`), rather than inventing a second config surface.
    local env = os and os.getenv and os.getenv("SECOND_RITE_PREPARED_MAP_CACHE_CAPACITY")
    local value = tonumber(env)
    if value == nil then
        local dungeon = session and session.loader and session.loader.system
            and session.loader.system.dungeon
        value = tonumber(dungeon and dungeon.preparedMapCacheCapacity)
    end
    if value == nil then value = prepared_map_cache.DEFAULT_CAPACITY end
    return math.max(0, math.floor(value))
end

local function tableCount(value)
    local count = 0
    for _ in pairs(value or {}) do count = count + 1 end
    return count
end

-- Effects are active-map state, not cached static geometry. Retaining their
-- handles while another map is current would let off-map weather/fixtures keep
-- updating in Effekseer. Stop only those handles and mark effects uninitialized;
-- the next hit recreates them from the then-current map while all GPU geometry
-- remains resident.
local function suspendEffects(prepared, stopEffect)
    if not prepared then return end
    stopEffect = stopEffect or function(handle)
        local effekseer = require("presentation.effekseer")
        effekseer.stop(handle)
    end
    for _, handle in ipairs(prepared.worldEffectHandles or {}) do
        stopEffect(handle)
    end
    if prepared.ambientEffectHandle then stopEffect(prepared.ambientEffectHandle) end
    prepared.worldEffectHandles = nil
    prepared.ambientEffectHandle = nil
    prepared.worldEffectsInitialized = nil
end

-- Approximate retained payload. LÖVE does not expose exact driver VRAM use, so
-- this reports the data we can account for: triangle-list mesh vertices using
-- viewport_3d's 13-float WORLD_MESH_FORMAT, plus the corresponding Lua numeric
-- vertex payload lower bound. Textures are shared by other caches and excluded.
local function estimatePrepared(prepared)
    local estimate = {
        meshes = 0,
        vertices = 0,
        cpuVertices = 0,
        indices = 0, -- these prepared meshes are unindexed triangle lists
        gpuBytesEstimate = 0,
        cpuVertexPayloadBytesEstimate = 0,
    }
    if not prepared then return estimate end
    local seen = setmetatable({}, { __mode = "k" })

    local function add(mesh, vertices, capacity)
        if not mesh or seen[mesh] then return end
        seen[mesh] = true
        local count = nil
        if mesh.getVertexCount then
            local ok, value = pcall(mesh.getVertexCount, mesh)
            if ok then count = tonumber(value) end
        end
        count = count or (type(vertices) == "table" and #vertices) or tonumber(capacity) or 0
        estimate.meshes = estimate.meshes + 1
        estimate.vertices = estimate.vertices + count
        if type(vertices) == "table" then
            estimate.cpuVertices = estimate.cpuVertices + #vertices
        end
    end

    local function meshTree(node)
        if not node then return end
        add(node.mesh, node.vertices, node.vertexCapacity or node.capacity)
        for _, child in ipairs(node.children or {}) do meshTree(child) end
    end

    for _, faces in pairs(prepared.resolvedWallFaces or {}) do
        for _, face in ipairs(faces) do meshTree(face.meshTree) end
    end
    for _, cell in ipairs(prepared.floorCells or {}) do
        meshTree(cell.floorSurface and cell.floorSurface.meshTree)
        meshTree(cell.floorFeatureSurface and cell.floorFeatureSurface.meshTree)
        meshTree(cell.ceilingSurface and cell.ceilingSurface.meshTree)
    end
    for _, batch in pairs(prepared.surfaceBatches or {}) do
        add(batch.mesh, batch.vertices, batch.capacity)
    end
    for _, groups in pairs(prepared.modelSurfaces or {}) do
        for _, placed in ipairs(groups) do
            add(placed.mesh, placed.vertices, placed.capacity)
            add(placed.clippedMesh, nil, placed.clippedCapacity)
        end
    end
    for _, pool in pairs(prepared.dynamicMeshPool or {}) do
        for _, entry in pairs(pool) do add(entry.mesh, nil, entry.capacity) end
    end

    estimate.gpuBytesEstimate = estimate.vertices * prepared_map_cache.WORLD_VERTEX_GPU_BYTES
    estimate.cpuVertexPayloadBytesEstimate = estimate.cpuVertices
        * prepared_map_cache.WORLD_VERTEX_FLOATS * prepared_map_cache.CPU_NUMBER_BYTES
    return estimate
end

local function makeProxy(session, identity)
    -- Snapshot the session rather than forwarding through __index. A cache entry
    -- must not hold its owning session strongly through the weak owner table;
    -- otherwise abandoning a campaign could keep the whole session + GPU cache
    -- alive. prepareStructure consumes these fields synchronously, and all later
    -- drawing uses the real session passed to viewport_3d.draw.
    local proxy = {}
    for key, value in pairs(session) do proxy[key] = value end
    local mt = getmetatable(session)
    if mt then setmetatable(proxy, mt) end
    proxy.__preparedMapCacheProxy = true
    proxy.mapGrid = session.mapGrid
    proxy.currentMapData = session.currentMapData
    proxy.currentMapIndex = session.currentMapIndex
    -- viewport_3d's internal one-slot validity check still runs. Feed it the
    -- cache identity's structural epoch rather than the activation-scoped
    -- revision and keep presentation at a stable token: all presentation
    -- facts baked into a prepared structure are explicit in our identity.
    proxy.mapStructureRevision = identity.structureEpoch
    proxy.mapPresentationRevision = 0
    return proxy
end

local function publishCounters(profiler, state)
    if not profiler then return end
    if profiler.isActive and not profiler.isActive() then return end
    local retained = {
        meshes = 0, vertices = 0, cpuVertices = 0, indices = 0,
        gpuBytesEstimate = 0, cpuVertexPayloadBytesEstimate = 0,
    }
    for _, entry in ipairs(state.entries) do
        for key, value in pairs(entry.estimate or {}) do retained[key] = retained[key] + value end
    end
    profiler.set("preparedMap.capacity", state.capacity)
    profiler.set("preparedMap.residentCount", #state.entries)
    profiler.set("preparedMap.retainedMeshes", retained.meshes)
    profiler.set("preparedMap.retainedVertices", retained.vertices)
    profiler.set("preparedMap.retainedIndices", retained.indices)
    profiler.set("preparedMap.retainedGpuBytesEstimate", retained.gpuBytesEstimate)
    profiler.set("preparedMap.retainedCpuVertexPayloadBytesEstimate",
        retained.cpuVertexPayloadBytesEstimate)
end

function prepared_map_cache.install(viewport, opts)
    opts = opts or {}
    if installed[viewport] then return installed[viewport] end
    if type(viewport) ~= "table" or type(viewport.prepareStructure) ~= "function"
            or type(viewport.invalidateStructure) ~= "function" then
        error("prepared_map_cache.install needs viewport prepare/invalidate functions", 0)
    end

    local originalPrepare = viewport.prepareStructure
    local originalInvalidate = viewport.invalidateStructure
    local profiler = opts.profiler
    if profiler == nil then
        local ok, resolved = pcall(require, "engine.map_build_profiler")
        if ok then profiler = resolved end
    end
    local qualityKey = opts.qualityKey
    if qualityKey == nil then
        qualityKey = function() return require("engine.geometry.quality").key() end
    end
    local capacityProvider = opts.capacity
    if type(capacityProvider) ~= "function" then
        local fixed = capacityProvider
        capacityProvider = function(session)
            return fixed ~= nil and math.max(0, math.floor(tonumber(fixed) or 0))
                or configuredCapacity(session)
        end
    end
    local stopEffect = opts.stopEffect

    local owners = setmetatable({}, { __mode = "k" })
    local manager = { activeSession = nil }

    local function stateFor(session)
        local state = owners[session]
        if state then return state end
        state = {
            entries = {}, clock = 0,
            capacity = capacityProvider(session),
            gridEpoch = setmetatable({}, { __mode = "k" }),
            observation = nil,
            activeEntry = nil, disabledIdentity = nil,
            stats = { hits = 0, misses = 0, evictions = 0, invalidations = 0 },
        }
        owners[session] = state
        return state
    end

    local function releaseEntry(state, index, reason)
        local entry = table.remove(state.entries, index)
        if not entry then return end
        if state.activeEntry == entry then
            suspendEffects(entry.prepared, stopEffect)
            state.activeEntry = nil
        end
        originalInvalidate(entry.proxy)
        if reason == "eviction" then
            state.stats.evictions = state.stats.evictions + 1
            if profiler then profiler.add("preparedMap.evictions", 1) end
        else
            state.stats.invalidations = state.stats.invalidations + 1
            if profiler then profiler.add("preparedMap.invalidations", 1) end
        end
    end

    local function enforceCapacity(state, session)
        state.capacity = capacityProvider(session)
        while #state.entries > state.capacity do
            local oldestIndex, oldestAccess
            for index, entry in ipairs(state.entries) do
                if not oldestAccess or entry.access < oldestAccess then
                    oldestIndex, oldestAccess = index, entry.access
                end
            end
            releaseEntry(state, oldestIndex, "eviction")
        end
    end

    local function clearOwner(session, reason)
        local state = owners[session]
        if not state then
            originalInvalidate(session)
            return
        end
        for index = #state.entries, 1, -1 do
            releaseEntry(state, index, reason or "session-switch")
        end
        originalInvalidate(session) -- native disabled/control slot, if any
        owners[session] = nil
    end

    local function observeStructureRevision(session, state)
        local mapIndex, grid = session.currentMapIndex, session.mapGrid
        local rawRevision = session.mapStructureRevision or 0
        local previous = state.observation
        if previous and previous.mapIndex == mapIndex and previous.grid == grid
                and previous.rawRevision ~= rawRevision then
            state.gridEpoch[grid] = (state.gridEpoch[grid] or 0) + 1
            -- Same active map + same grid + revision change means an in-place
            -- structural mutation. Release every resident quality variant for
            -- that grid now; none may ever be reused after the mutation.
            for index = #state.entries, 1, -1 do
                local identity = state.entries[index].identity
                if identity.mapIndex == mapIndex and identity.grid == grid then
                    releaseEntry(state, index, "structure-revision")
                end
            end
        elseif previous and previous.rawRevision ~= rawRevision
                and rawRevision ~= previous.rawRevision + 1 then
            -- loadMap itself advances the global revision exactly once. A larger
            -- jump between two rendered maps means structural work happened
            -- while no viewport observation was possible (for example transfer
            -- -> mutateTile -> first draw). We cannot attribute that mutation
            -- to one resident map from this activation-scoped counter, so the
            -- only exact policy is to invalidate the deliberately tiny set.
            -- False misses after several no-draw transfers are acceptable; a
            -- stale GPU structure is not.
            state.gridEpoch[grid] = (state.gridEpoch[grid] or 0) + 1
            for index = #state.entries, 1, -1 do
                releaseEntry(state, index, "unobserved-structure-revision")
            end
        end
        state.observation = { mapIndex = mapIndex, grid = grid, rawRevision = rawRevision }
        return state.gridEpoch[grid] or 0
    end

    local function identityFor(session, state)
        local mapData = session.currentMapData or {}
        local loader = session.loader
        local mapIndex = session.currentMapIndex
        local authoredMap = loader and loader.maps and mapIndex and loader.maps[mapIndex] or nil
        local tilesetId = mapData.tileset or "dungeon_default"
        local tilesetBase = loader and loader.getTileset and loader.getTileset(tilesetId) or nil
        return {
            mapIndex = mapIndex,
            authoredMap = authoredMap,
            grid = session.mapGrid,
            structureEpoch = observeStructureRevision(session, state),
            tilesetId = tilesetId,
            tilesetBase = tilesetBase,
            tilesetOverride = mapData.tilesetOverride,
            generatedFeatures = session.generatedFeatures,
            generatedZones = session.generatedZones,
            generatedLightObjects = session.generatedLightObjects,
            events = mapData.events,
            materials = mapData.materials,
            lightObjects = mapData.lightObjects,
            runtimeLight = mapData.runtimeLight or mapData.light,
            qualityKey = qualityKey(),
        }
    end

    local function incompatibleLineage(a, b)
        if a.mapIndex ~= b.mapIndex then return false end
        -- Quality alone is an intentionally retained variant. Any other change
        -- to this map index is a new source/runtime/presentation lineage and
        -- makes old prepared GPU data unreachable/stale.
        return not sameNonQualityIdentity(a, b)
    end

    local function acquire(session)
        if not session or not session.mapGrid then return nil end
        if manager.activeSession and manager.activeSession ~= session then
            clearOwner(manager.activeSession, "session-switch")
        end
        manager.activeSession = session
        local state = stateFor(session)
        enforceCapacity(state, session)
        local identity = identityFor(session, state)

        for index = #state.entries, 1, -1 do
            if incompatibleLineage(state.entries[index].identity, identity) then
                releaseEntry(state, index, "identity-change")
            end
        end

        local hit
        for _, entry in ipairs(state.entries) do
            if sameIdentity(entry.identity, identity) then hit = entry break end
        end

        state.clock = state.clock + 1
        if hit then
            local lifecycleHit = state.activeEntry ~= hit
            if state.activeEntry and lifecycleHit then
                state.activeEntry.estimate = estimatePrepared(state.activeEntry.prepared)
                suspendEffects(state.activeEntry.prepared, stopEffect)
            end
            hit.access = state.clock
            state.activeEntry = hit
            if lifecycleHit then
                state.stats.hits = state.stats.hits + 1
                if profiler then
                    profiler.cache("preparedMap", true)
                    profiler.add("preparedMap.skipped.structureIndex", 1)
                    if (hit.estimate and hit.estimate.vertices or 0) > 0 then
                        profiler.add("preparedMap.skipped.transformLightingBounds", 1)
                        profiler.add("preparedMap.skipped.placedGpuMeshCreate", 1)
                        profiler.add("preparedMap.avoidedPlacedVerticesEstimate",
                            hit.estimate.vertices)
                        profiler.add("preparedMap.avoidedGpuUploadBytesEstimate",
                            hit.estimate.gpuBytesEstimate or 0)
                    end
                end
            end
            local prepared = originalPrepare(hit.proxy)
            hit.prepared = prepared
            publishCounters(profiler, state)
            return prepared
        end

        if state.activeEntry then
            state.activeEntry.estimate = estimatePrepared(state.activeEntry.prepared)
            suspendEffects(state.activeEntry.prepared, stopEffect)
        end
        if state.capacity <= 0 then
            -- Disabled/control mode: preserve viewport_3d's native one-slot
            -- lifecycle on the real session instead of creating an unretained
            -- proxy whose GPU resources would have no owner. Count only a map
            -- lifecycle acquisition, not every frame's prepare call.
            if not sameIdentity(state.disabledIdentity, identity) then
                state.stats.misses = state.stats.misses + 1
                if profiler then profiler.cache("preparedMap", false) end
                state.disabledIdentity = identity
            end
            local prepared = originalPrepare(session)
            publishCounters(profiler, state)
            return prepared
        end

        state.disabledIdentity = nil
        state.stats.misses = state.stats.misses + 1
        if profiler then profiler.cache("preparedMap", false) end
        local proxy = makeProxy(session, identity)
        local prepared = originalPrepare(proxy)
        local entry = {
            identity = identity,
            proxy = proxy,
            prepared = prepared,
            access = state.clock,
            estimate = estimatePrepared(prepared),
        }
        state.entries[#state.entries + 1] = entry
        state.activeEntry = entry
        enforceCapacity(state, session)
        publishCounters(profiler, state)
        return prepared
    end

    viewport.prepareStructure = function(session)
        if session and rawget(session, "__preparedMapCacheProxy") then
            return originalPrepare(session)
        end
        return acquire(session)
    end

    viewport.invalidateStructure = function(session)
        if not session then return originalInvalidate(session) end
        if rawget(session, "__preparedMapCacheProxy") then return originalInvalidate(session) end
        local state = owners[session]
        if not state then return originalInvalidate(session) end
        for index = #state.entries, 1, -1 do releaseEntry(state, index, "explicit") end
        state.observation = nil
        state.gridEpoch = setmetatable({}, { __mode = "k" })
        originalInvalidate(session) -- release native disabled-mode slot, if any
        if manager.activeSession == session then manager.activeSession = nil end
        publishCounters(profiler, state)
    end

    function manager.stats(session)
        local state = owners[session]
        if not state then
            return { capacity = capacityProvider(session), residentCount = 0,
                hits = 0, misses = 0, evictions = 0, invalidations = 0,
                retainedMeshes = 0, retainedVertices = 0,
                retainedGpuBytesEstimate = 0,
                retainedCpuVertexPayloadBytesEstimate = 0 }
        end
        local out = {
            capacity = state.capacity,
            residentCount = #state.entries,
            hits = state.stats.hits,
            misses = state.stats.misses,
            evictions = state.stats.evictions,
            invalidations = state.stats.invalidations,
            retainedMeshes = 0,
            retainedVertices = 0,
            retainedGpuBytesEstimate = 0,
            retainedCpuVertexPayloadBytesEstimate = 0,
        }
        for _, entry in ipairs(state.entries) do
            entry.estimate = estimatePrepared(entry.prepared)
            out.retainedMeshes = out.retainedMeshes + entry.estimate.meshes
            out.retainedVertices = out.retainedVertices + entry.estimate.vertices
            out.retainedGpuBytesEstimate = out.retainedGpuBytesEstimate
                + entry.estimate.gpuBytesEstimate
            out.retainedCpuVertexPayloadBytesEstimate = out.retainedCpuVertexPayloadBytesEstimate
                + entry.estimate.cpuVertexPayloadBytesEstimate
        end
        return out
    end

    function manager.clear(session)
        viewport.invalidateStructure(session)
    end

    function manager.ownerCount()
        return tableCount(owners)
    end

    viewport.getPreparedMapCacheStats = manager.stats
    installed[viewport] = manager
    return manager
end

return prepared_map_cache
