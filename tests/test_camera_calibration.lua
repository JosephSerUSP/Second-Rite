-- tests/test_camera_calibration.lua
-- Unit tests for Thestra WorldCamera calibration record serialization and projection mathematics.

local world_camera = require("presentation.world_camera")
local camera_calibration = require("presentation.camera_calibration")

local function check(cond, msg)
    if not cond then error("CHECK FAILED: " .. (msg or ""), 2) end
end

print("[TEST] Starting camera calibration tests...")

-- 1. Orthonormal basis validation
local function checkBasis(rec, label)
    local r = rec.right
    local u = rec.up
    local f = rec.forward

    local rLen = math.sqrt(r[1]^2 + r[2]^2 + r[3]^2)
    local uLen = math.sqrt(u[1]^2 + u[2]^2 + u[3]^2)
    local fLen = math.sqrt(f[1]^2 + f[2]^2 + f[3]^2)

    check(math.abs(rLen - 1.0) < 1e-7, label .. " Right unit length")
    check(math.abs(uLen - 1.0) < 1e-7, label .. " Up unit length")
    check(math.abs(fLen - 1.0) < 1e-7, label .. " Forward unit length")

    local dotRU = r[1]*u[1] + r[2]*u[2] + r[3]*u[3]
    local dotRF = r[1]*f[1] + r[2]*f[2] + r[3]*f[3]
    local dotUF = u[1]*f[1] + u[2]*f[2] + u[3]*f[3]

    check(math.abs(dotRU) < 1e-7, label .. " Right . Up == 0")
    check(math.abs(dotRF) < 1e-7, label .. " Right . Forward == 0")
    check(math.abs(dotUF) < 1e-7, label .. " Up . Forward == 0")

    -- Cross product R x U should equal F
    local crossX = r[2]*u[3] - r[3]*u[2]
    local crossY = r[3]*u[1] - r[1]*u[3]
    local crossZ = r[1]*u[2] - r[2]*u[1]

    check(math.abs(crossX - f[1]) < 1e-7, label .. " Cross(R, U).x == Forward.x")
    check(math.abs(crossY - f[2]) < 1e-7, label .. " Cross(R, U).y == Forward.y")
    check(math.abs(crossZ - f[3]) < 1e-7, label .. " Cross(R, U).z == Forward.z")
end

-- 2. First Person Wide (426x240) record creation & basis checks
local fpCam = world_camera.resolveFirstPerson({
    playerX = 5, playerY = 5, playerDir = "N",
}, {
    projectionFrame = {
        targetWidth = 426, targetHeight = 240, compositionWidth = 256,
        canonicalCenterX = 213, canonicalHorizonY = 70,
    },
    projectionWindowOffsetX = 48,
})
local fpRec = camera_calibration.createRecord(fpCam)
check(fpRec.coordinateSystem == "thestra_world_z_up", "Coordinate system is declared")
check(fpRec.projection == "perspective", "First person projection is perspective")
check(fpRec.viewportCenterX == 213 + 48, "Viewport center X carries shift")
check(fpRec.viewportCenterY == 70, "Viewport center Y carries canonical horizon")
checkBasis(fpRec, "First Person")
print("  [PASS] First Person calibration record and orthonormal basis valid")

-- 3. Overhead Oblique & Pitched Basis checks
for _, pitchDeg in ipairs({ 30, 45, 60 }) do
    local overheadRec = camera_calibration.createRecord({
        playerX = 10, playerY = 10, playerDir = "E",
    }, {
        profile = "perspective_oblique",
        pitch = math.rad(pitchDeg),
        projectionFrame = {
            targetWidth = 426, targetHeight = 240, compositionWidth = 256,
            canonicalCenterX = 213, canonicalHorizonY = 70,
        },
    })
    checkBasis(overheadRec, "Overhead pitch " .. pitchDeg)
end
print("  [PASS] Pitched overhead orthonormal basis valid across pitch angles")

-- 4. Projection Mathematical Equivalence with shader math
for _, shift in ipairs({ -96, -48, 0, 48, 96 }) do
    local rec = camera_calibration.createRecord({
        playerX = 5, playerY = 5, playerDir = "N",
    }, {
        projectionWindowOffsetX = shift,
        projectionFrame = {
            targetWidth = 426, targetHeight = 240, compositionWidth = 256,
            canonicalCenterX = 213, canonicalHorizonY = 70,
        },
    })

    -- Optical center point at depth 4.0 looking North from eye (5.5, 5.5, 0.5):
    local eyeX, eyeY, eyeZ = rec.eye[1], rec.eye[2], rec.eye[3]
    local optX, optY, optZ = eyeX, eyeY - 4.0, eyeZ
    local sx, sy, d = camera_calibration.projectWorldPoint(rec, optX, optY, optZ)
    check(math.abs(sx - (213 + shift)) < 1e-7, "Optical center X matches viewportCenterX")
    check(math.abs(sy - 70) < 1e-7, "Optical center Y matches viewportCenterY")
    check(math.abs(d - 4.0) < 1e-7, "Depth matches 4.0")

    -- Lateral points: +2.0 and -2.0
    local sxR, syR = camera_calibration.projectWorldPoint(rec, optX + 2.0, optY, optZ)
    local sxL, syL = camera_calibration.projectWorldPoint(rec, optX - 2.0, optY, optZ)
    local expectedDelta = (2.0 / (0.75 * 4.0)) * 1.0 * 128.0
    check(math.abs((sxR - sx) - expectedDelta) < 1e-7, "Right point screen delta exact")
    check(math.abs((sx - sxL) - expectedDelta) < 1e-7, "Left point screen delta exact")
end
print("  [PASS] Camera calibration mathematical projection matches shader contract")

print("=== Camera Calibration Tests: all checks passed ===")
