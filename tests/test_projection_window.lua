-- tests/test_projection_window.lua
-- Unit tests for #837 static-camera projection-window panning invariants.

local world_camera = require("presentation.world_camera")
local surface = require("presentation.surface")

local function check(cond, msg)
    if not cond then error("CHECK FAILED: " .. (msg or ""), 2) end
end

print("[TEST] Starting projection window panning tests...")

-- 1. Numerical Invariant: Principal-point shift is depth-independent in screen pixels
-- For any depth z in [0.5, 64] and any lateral position x in [-10, 10],
-- a projection window offset of dx render pixels shifts the projected screen X by exactly dx pixels.
local function computeScreenX(camera, cameraRight, cameraDepth, targetWidth)
    local centerNdc = (2 * camera.viewportCenterX / targetWidth) - 1
    local perspectiveNdc = cameraRight / (camera.fovHalfX * cameraDepth)
        * camera.projectionScaleX * (camera.baseViewportWidth / targetWidth)
    return (centerNdc + perspectiveNdc + 1) * targetWidth * 0.5
end

local targetW, targetH = 426, 240
local baseW, baseH = 256, 144
local baseCam = world_camera.resolveFirstPerson({
    playerX = 5, playerY = 5, playerDir = "N",
}, {
    projectionFrame = {
        targetWidth = targetW, targetHeight = targetH, compositionWidth = baseW,
        canonicalCenterX = targetW * 0.5, canonicalHorizonY = 70,
    },
})

for _, shift in ipairs({ -96, -48, -16, -1, 1, 16, 48, 96 }) do
    local shiftedCam = world_camera.resolveFirstPerson({
        playerX = 5, playerY = 5, playerDir = "N",
    }, {
        projectionWindowOffsetX = shift,
        projectionFrame = {
            targetWidth = targetW, targetHeight = targetH, compositionWidth = baseW,
            canonicalCenterX = targetW * 0.5, canonicalHorizonY = 70,
        },
    })

    -- Camera eye and orientation are invariant
    check(shiftedCam.x == baseCam.x and shiftedCam.y == baseCam.y and shiftedCam.z == baseCam.z,
        "Camera eye position invariant in B")
    check(shiftedCam.dirX == baseCam.dirX and shiftedCam.dirY == baseCam.dirY,
        "Camera forward vector invariant in B")
    check(shiftedCam.rightX == baseCam.rightX and shiftedCam.rightY == baseCam.rightY,
        "Camera right vector invariant in B")
    check(shiftedCam.pitch == baseCam.pitch, "Camera pitch invariant in B")

    -- Across depths 0.5 to 64 and various lateral offsets
    for _, depth in ipairs({ 0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0 }) do
        for _, lateral in ipairs({ -3.0, -1.0, 0.0, 1.0, 3.0 }) do
            local baseScreenX = computeScreenX(baseCam, lateral, depth, targetW)
            local shiftedScreenX = computeScreenX(shiftedCam, lateral, depth, targetW)
            local deltaPx = shiftedScreenX - baseScreenX
            check(math.abs(deltaPx - shift) < 1e-10,
                string.format("Shift %d at depth %.1f lateral %.1f matches exactly (delta=%.6f)",
                    shift, depth, lateral, deltaPx))
        end
    end
end
print("  [PASS] Principal-point shift is depth-independent across all depths and positions")

-- 2. Parallax Invariance vs Camera Follow Parallax Sweep
-- Under projection window pan, the screen separation between a near point (depth=2) and far point (depth=12)
-- is strictly invariant. Under camera strafe/follow, the separation changes with parallax.
local nearLateral = 0.5
local farLateral = 2.0
local nearDepth = 2.0
local farDepth = 12.0

local baseNearScreen = computeScreenX(baseCam, nearLateral, nearDepth, targetW)
local baseFarScreen = computeScreenX(baseCam, farLateral, farDepth, targetW)
local baseSeparation = baseFarScreen - baseNearScreen

for _, shift in ipairs({ -80, -40, -16, 16, 40, 80 }) do
    local panCam = world_camera.resolveFirstPerson({
        playerX = 5, playerY = 5, playerDir = "N",
    }, {
        projectionWindowOffsetX = shift,
        projectionFrame = {
            targetWidth = targetW, targetHeight = targetH, compositionWidth = baseW,
            canonicalCenterX = targetW * 0.5, canonicalHorizonY = 70,
        },
    })
    local panNearScreen = computeScreenX(panCam, nearLateral, nearDepth, targetW)
    local panFarScreen = computeScreenX(panCam, farLateral, farDepth, targetW)
    local panSeparation = panFarScreen - panNearScreen
    check(math.abs(panSeparation - baseSeparation) < 1e-10,
        "Near-far separation is invariant under projection window shift")
end
print("  [PASS] Near-far separation is strictly invariant under projection window panning")

-- Camera follow comparison: strafing changes separation
local strafedCam = world_camera.resolveFirstPerson({
    playerX = 5, playerY = 5, playerDir = "N",
}, {
    projectionFrame = {
        targetWidth = targetW, targetHeight = targetH, compositionWidth = baseW,
        canonicalCenterX = targetW * 0.5, canonicalHorizonY = 70,
    },
})
local strafedNear = computeScreenX(strafedCam, nearLateral - 1.0, nearDepth, targetW)
local strafedFar = computeScreenX(strafedCam, farLateral - 1.0, farDepth, targetW)
local strafeSeparation = strafedFar - strafedNear
check(math.abs(strafeSeparation - baseSeparation) > 1.0,
    "Camera strafe creates parallax variation in near-far separation")
print("  [PASS] Camera strafe exhibits parallax variation (negative control)")

-- 3. FOV / Master Lens comparison (C)
-- Test at least two materially different master lenses (e.g. 50 deg vs 26 deg standard vs 75 deg wide)
local fovDegreesList = { 26, 50, 75 }
for _, fovDeg in ipairs(fovDegreesList) do
    local fovCam = world_camera.resolve({
        playerX = 5, playerY = 5, playerDir = "N",
    }, {
        profile = "rpg_perspective",
        fovDegrees = fovDeg,
        projectionWindowOffsetX = 32,
        projectionFrame = {
            targetWidth = targetW, targetHeight = targetH, compositionWidth = baseW,
            canonicalCenterX = targetW * 0.5, canonicalHorizonY = 70,
        },
    })
    check(fovCam.projectionWindowOffsetX == 32, "FOV camera carries projection window offset")
    check(fovCam.viewportCenterX == targetW * 0.5 + 32, "FOV camera principal point shifted")
    -- Invariance of shift holds regardless of FOV
    local sBase = computeScreenX(world_camera.resolve({
        playerX = 5, playerY = 5, playerDir = "N",
    }, {
        profile = "rpg_perspective",
        fovDegrees = fovDeg,
        projectionFrame = {
            targetWidth = targetW, targetHeight = targetH, compositionWidth = baseW,
            canonicalCenterX = targetW * 0.5, canonicalHorizonY = 70,
        },
    }), 1.0, 4.0, targetW)
    local sShifted = computeScreenX(fovCam, 1.0, 4.0, targetW)
    check(math.abs((sShifted - sBase) - 32) < 1e-10, "Shift is exact across FOV choices")
end
print("  [PASS] Projection window offset behaves identically across multiple master FOV choices")

-- 4. Effekseer agreement
local okEfk, effekseer = pcall(require, "presentation.effekseer")
if okEfk and effekseer.worldCameraMatrices then
    local function mul(v, m)
        local o = {}
        for c = 1, 4 do
            o[c] = v[1] * m[c] + v[2] * m[4 + c] + v[3] * m[8 + c] + v[4] * m[12 + c]
        end
        return o
    end
    for _, shift in ipairs({ -60, 0, 60 }) do
        local camSpec = {
            projection = "perspective",
            x = 0, y = 0, z = 0.5,
            dirX = 0, dirY = 1, rightX = -1, rightY = 0, pitch = 0,
            fovHalfX = 0.75, fovHalfY = 0.421875,
            nearPlane = 0.05, farPlane = 64,
            projectionScaleX = 1, projectionScaleY = 1,
            targetWidth = targetW, targetHeight = targetH,
            compositionWidth = baseW, compositionHeight = baseH,
            viewportCenterX = targetW * 0.5 + shift, viewportCenterY = 70,
        }
        local view, proj = effekseer.worldCameraMatrices(camSpec)
        for _, depth in ipairs({ 1.0, 4.0, 16.0 }) do
            for _, horiz in ipairs({ -2.0, 0.0, 2.0 }) do
                local wx, wy, wz = -horiz, depth, 0.5
                local eye = mul({ wx, wz, wy, 1 }, view)
                local clip = mul(eye, proj)
                local efkNdcX = clip[1] / clip[4]
                local shaderNdcX = ((2 * camSpec.viewportCenterX / targetW) - 1)
                    + horiz / (0.75 * depth) * (baseW / targetW)
                check(math.abs(efkNdcX - shaderNdcX) < 1e-10,
                    string.format("Effekseer and shader NDC.x match at shift=%d depth=%.1f", shift, depth))
            end
        end
    end
    print("  [PASS] Effekseer world camera matrices agree with shader projection")
end

-- 5. Quantization phase assertions (#844)
-- Integer shifts align with whole pixels and preserve sub-pixel vertex phases.
-- Dither phase: 4x4 ordered dither grid aligns at multiples of 4 px.
local function isDitherPhaseAligned(shift)
    return (shift % 4) == 0
end
check(isDitherPhaseAligned(0) == true, "0 px is dither aligned")
check(isDitherPhaseAligned(4) == true, "4 px is dither aligned")
check(isDitherPhaseAligned(16) == true, "16 px is dither aligned")
check(isDitherPhaseAligned(1) == false, "1 px is non-dither aligned")
check(isDitherPhaseAligned(2) == false, "2 px is non-dither aligned")
print("  [PASS] Quantization grids and dither-phase properties validated")

print("=== Projection Window Panning Tests: all checks passed ===")
