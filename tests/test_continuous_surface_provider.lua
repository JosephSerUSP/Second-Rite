local provider = require("engine.continuous_surface_provider")

local passed, failed = 0, 0
local function check(value, label)
    if value then
        passed = passed + 1
    else
        failed = failed + 1
        print("[FAIL] " .. label)
    end
end

-- Environment packages need a filesystem-backed fixture in full integration.
-- For the provider's world-space Event contract we can exercise the live state
-- directly: nearestEvent must remain a proximity query over ordinary Map Events,
-- independent from the Event program itself.
local session = {
    currentMapData = {
        id = 1,
        traversal = { provider = "continuous_surface" },
        events = {
            { id = 1, name = "near", worldPosition = { 1.0, 1.0, 0 }, interactionRadius = 1.0 },
            { id = 2, name = "far", worldPosition = { 4.0, 4.0, 0 }, interactionRadius = 1.0 },
            { id = 3, name = "grid-only", x = 1, y = 1 },
        },
    },
    continuousTraversal = {
        provider = "continuous_surface",
        mapId = 1,
        x = 1.2,
        y = 1.1,
        z = 0,
        interactionRadius = 1.15,
    },
}

-- Avoid provider.ensure's environment boot for this focused contract by
-- temporarily presenting the already-live state as authoritative.
local originalEnsure = provider.ensure
provider.ensure = function(s) return s.continuousTraversal end

local nearest = provider.nearestEvent(session)
check(nearest and nearest.id == 1, "nearestEvent resolves the closest world-space Event")

session.continuousTraversal.x = 3.3
session.continuousTraversal.y = 3.3
nearest = provider.nearestEvent(session)
check(nearest and nearest.id == 2, "nearestEvent respects per-Event interaction radius")

session.continuousTraversal.x = 0
session.continuousTraversal.y = 0
nearest = provider.nearestEvent(session, 0.2)
check(nearest == nil, "nearestEvent returns nil outside explicit radius")

provider.ensure = originalEnsure

require("tests.fail_fast")("test_continuous_surface_provider", failed, passed)
