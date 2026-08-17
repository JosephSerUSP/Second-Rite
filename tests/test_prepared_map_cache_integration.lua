-- Production-lifecycle reproduction for #312's capacity-2 revisit path.
-- This deliberately uses the real loader, GameSession, exploration.loadMap,
-- and viewport_3d.prepareStructure rather than fabricated identity tables.
local loader = require("engine.data.loader")
local sessionModule = require("engine.session")
local exploration = require("engine.exploration")
local viewport = require("presentation.viewport_3d")
local cache = require("presentation.prepared_map_cache")

print("[TEST] Starting prepared-map production lifecycle integration test...")

loader.init()
local session = sessionModule.GameSession.new(loader)
session:initializeStartingParty()
local manager = cache.install(viewport, { capacity = 2 })

local function mapIndex(id)
    for index, map in ipairs(loader.maps or {}) do
        if tostring(map.id) == tostring(id) then return index end
    end
    error("integration fixture map not found: " .. tostring(id))
end

local function loadAndPrepare(targetSession, id)
    exploration.loadMap(targetSession, mapIndex(id), { seed = 1735689600 + tonumber(id) })
    return viewport.prepareStructure(targetSession)
end

local firstEight = loadAndPrepare(session, 8)
local afterFirst = manager.stats(session)
local twelve = loadAndPrepare(session, 12)
local afterTwelve = manager.stats(session)
local returningEight = loadAndPrepare(session, 8)
local afterReturn = manager.stats(session)

assert(afterFirst.misses == 1 and afterFirst.hits == 0,
    "production map 8 first visit is one prepared-map miss")
assert(afterTwelve.misses == 2 and afterTwelve.hits == 0,
    "production map 12 visit is the second prepared-map miss")
assert(returningEight == firstEight,
    "production 8 -> 12 -> 8 returns the original prepared structure")
assert(afterReturn.misses == 2 and afterReturn.hits == 1
        and afterReturn.evictions == 0 and afterReturn.invalidations == 0,
    "production 8 -> 12 -> 8 is exactly two builds and one hit")

viewport.invalidateStructure(session)

-- A real active-map mutation must still invalidate the resident structure.
local mutationSession = sessionModule.GameSession.new(loader)
mutationSession:initializeStartingParty()
local mutationOld = loadAndPrepare(mutationSession, 8)
exploration.mutateTile(mutationSession, 0, 0, ".")
local mutationNew = viewport.prepareStructure(mutationSession)
local mutationStats = manager.stats(mutationSession)
assert(mutationNew ~= mutationOld and mutationStats.invalidations >= 1,
    "real same-map structural mutation cannot reuse prepared geometry")
viewport.invalidateStructure(mutationSession)

-- A mutation after transfer but before the first destination prepare must also
-- prevent reuse of the resident destination structure.
local delayedMutationSession = sessionModule.GameSession.new(loader)
delayedMutationSession:initializeStartingParty()
local delayedOld = loadAndPrepare(delayedMutationSession, 8)
loadAndPrepare(delayedMutationSession, 12)
exploration.loadMap(delayedMutationSession, mapIndex(8))
exploration.mutateTile(delayedMutationSession, 0, 0, ".")
local delayedNew = viewport.prepareStructure(delayedMutationSession)
local delayedStats = manager.stats(delayedMutationSession)
assert(delayedNew ~= delayedOld and delayedStats.invalidations >= 1,
    "transfer then pre-draw mutation cannot reuse stale prepared geometry")
viewport.invalidateStructure(delayedMutationSession)

print("test_prepared_map_cache_integration: OK")
