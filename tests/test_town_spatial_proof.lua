-- Runtime half of the asymmetric Blender town spatial proof.
--
-- This test reads the current authored 3D town camera instead of copying its
-- values into a second fixture.  The screen-order assertions mirror the live
-- viewport consumer's horizontal term: horizontal = relative * cameraRight.
-- It intentionally does not become a second projection implementation.
local json = require("engine.data.json")
local world_camera = require("presentation.world_camera")
local loader = require("engine.data.loader")

local function check(condition, message)
    if not condition then error("CHECK FAILED: " .. message, 2) end
end

local map = assert(loader.maps[loader.getMapIndex(28)])

local authored = assert(map.traversal and map.traversal.camera)
local camera = world_camera.resolve({
    playerX = 0, playerY = 0, playerDir = "E",
}, {
    profile = "town_sideview",
    authoredCamera = authored,
    projectionFrame = {
        targetWidth = 256,
        targetHeight = 240,
        compositionWidth = 256,
        canonicalCenterX = 128,
        canonicalHorizonY = 66,
    },
})

-- The live town resolver is +Y screen-right.  This is intentionally different
-- from tools/blender/fixtures/town_sideview_camera.json, whose -Y basis is the
-- Blender authoring view used by the spatial PNG proof.
check(camera.rightX == 0 and camera.rightY == 1,
    "live town_sideview camera must expose +Y as screen-right")

local directLow, directHigh = 1.0, 2.0
local reflectedLow = authored.target.y - directLow
local reflectedHigh = authored.target.y - directHigh
local directDelta = (directHigh - directLow) * camera.rightY
local reflectedDelta = (reflectedHigh - reflectedLow) * camera.rightY
check(directDelta > 0, "exterior direct source +Y must move screen-right at runtime")
check(reflectedDelta < 0, "interior reflected source +Y must move screen-left at runtime")

-- Depth remains the camera-forward axis, so the adapter must not repair lane
-- handedness by touching X/depth or Z/elevation.
check(camera.dirX == 1 and camera.dirY == 0,
    "town sideview depth axis must remain +X")
check(camera.pitch < 0, "current adopted town camera pitch must reach the resolver")

print("THESTRA_TOWN_SPATIAL_RUNTIME OK " .. json.encode({
    map = map.id,
    rightY = camera.rightY,
    directSourceYScreenDeltaSign = directDelta > 0 and "positive" or "negative",
    reflectedSourceYScreenDeltaSign = reflectedDelta > 0 and "positive" or "negative",
    pitch = camera.pitch,
    transformContract = "engine_y = laneOriginY - blender_y",
}))
