-- tests/test_projection_window_precedence.lua
-- #837: projection-window offsets remain camera framing state, with the
-- ordinary authored < session < direct-resolver precedence.

local world_camera = require("presentation.world_camera")

local function check(cond, msg)
    if not cond then error("CHECK FAILED: " .. (msg or ""), 2) end
end

local frame = {
    targetWidth = 426,
    targetHeight = 240,
    compositionWidth = 256,
    canonicalCenterX = 213,
    canonicalHorizonY = 70,
}

local authored = {
    profile = "rpg_perspective",
    projectionWindowOffsetX = 10,
    projectionWindowOffsetY = -4,
}

local authoredOnly = world_camera.resolve({
    playerX = 4, playerY = 5, playerDir = "N",
}, {
    authoredCamera = authored,
    projectionFrame = frame,
})
check(authoredOnly.projectionWindowOffsetX == 10
        and authoredOnly.projectionWindowOffsetY == -4
        and authoredOnly.viewportCenterX == 223
        and authoredOnly.viewportCenterY == 66,
    "Authored projection-window offset resolves onto the principal point")

local sessionState = {
    playerX = 4, playerY = 5, playerDir = "N",
    worldCameraProfile = "rpg_perspective",
    worldCameraProjectionWindowOffsetX = 30,
    worldCameraProjectionWindowOffsetY = 8,
}
local sessionResolved = world_camera.resolve(sessionState, {
    authoredCamera = authored,
    projectionFrame = frame,
})
check(sessionResolved.projectionWindowOffsetX == 30
        and sessionResolved.projectionWindowOffsetY == 8
        and sessionResolved.viewportCenterX == 243
        and sessionResolved.viewportCenterY == 78,
    "Session projection-window offset overrides authored camera framing")

local directResolved = world_camera.resolve(sessionState, {
    authoredCamera = authored,
    projectionWindowOffsetX = 50,
    projectionWindowOffsetY = -12,
    projectionFrame = frame,
})
check(directResolved.projectionWindowOffsetX == 50
        and directResolved.projectionWindowOffsetY == -12
        and directResolved.viewportCenterX == 263
        and directResolved.viewportCenterY == 58,
    "Direct resolver projection-window offset overrides session framing")

check(directResolved.x == sessionResolved.x
        and directResolved.y == sessionResolved.y
        and directResolved.z == sessionResolved.z
        and directResolved.dirX == sessionResolved.dirX
        and directResolved.dirY == sessionResolved.dirY
        and directResolved.rightX == sessionResolved.rightX
        and directResolved.rightY == sessionResolved.rightY
        and directResolved.pitch == sessionResolved.pitch,
    "Projection-window precedence never moves or rotates the camera eye")

print("  [PASS] Projection-window authored/session/direct precedence")
