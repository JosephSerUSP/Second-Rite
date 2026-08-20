-- Runtime half of the WorldCamera -> Blender parity fixture.
-- Invoked by tools/blender/check_thestra_camera.py before Blender itself.
local n = arg and #arg or 0
local repoRoot = arg and (arg[n - 1] or arg[n])
local fixturePath = arg and arg[n]
if not repoRoot or not fixturePath then
    error("usage: lovec tools/blender/tests/runtime_camera_parity <repoRoot> <fixture.json>", 0)
end

repoRoot = tostring(repoRoot):gsub("\\", "/")
package.path = repoRoot .. "/runtime/?.lua;" .. repoRoot .. "/runtime/?/init.lua;" .. package.path

local world_camera = require("presentation.world_camera")
local calibration = require("presentation.world_camera_calibration")
local json = require("engine.data.json")

local function check(cond, msg)
    if not cond then error("CHECK FAILED: " .. (msg or ""), 2) end
end

local function close(a, b, eps)
    return math.abs(a - b) <= (eps or 1e-10)
end

local file = assert(io.open(fixturePath, "rb"))
local fixtureText = file:read("*a")
file:close()
local fixture = assert(json.decode(fixtureText))

local projectionFrame = {
    targetWidth = 426,
    targetHeight = 240,
    compositionWidth = 256,
    canonicalCenterX = 213,
    canonicalHorizonY = 70,
}
local session = { playerX = 5, playerY = 5, playerDir = "E" }
local pitch = math.rad(30)

local function assertRecord(actual, expected, name)
    check(actual.contract == "thestra.world-camera-calibration", name .. " contract")
    check(actual.version == 1, name .. " version")
    check(actual.projection == expected.projection, name .. " projection")
    for _, axis in ipairs({ "x", "y", "z" }) do
        check(close(actual.eye[axis], expected.eye[axis]), name .. " eye " .. axis)
    end
    for _, key in ipairs({ "forwardX", "forwardY", "rightX", "rightY", "pitchRadians" }) do
        check(close(actual.orientation[key], expected.orientation[key]), name .. " orientation " .. key)
    end
    for _, key in ipairs({ "x", "y" }) do
        check(close(actual.projectionScale[key], expected.projectionScale[key]), name .. " projectionScale " .. key)
    end
    for _, key in ipairs({
        "fovHalfX", "fovHalfY", "nearPlane", "farPlane",
        "targetWidth", "targetHeight", "baseViewportWidth", "baseViewportHeight",
        "viewportCenterX", "viewportCenterY",
        "projectionWindowOffsetX", "projectionWindowOffsetY",
    }) do
        check(close(actual[key], expected[key]), name .. " " .. key)
    end
    for key, value in pairs(expected.coordinateSystem) do
        check(actual.coordinateSystem[key] == value, name .. " coordinate system " .. key)
    end
end

-- Numerical oracle exists only in this parity harness. The art-pipeline record
-- itself contains no second resolver and Python never reimplements Thestra's
-- camera resolution.
local function project(camera, point)
    local rx = point[1] - camera.eye.x
    local ry = point[2] - camera.eye.y
    local rz = point[3] - camera.eye.z
    local o = camera.orientation
    local depth = rx * o.forwardX + ry * o.forwardY
    local horizontal = rx * o.rightX + ry * o.rightY
    local vertical = rz
    local cp, sp = math.cos(o.pitchRadians), math.sin(o.pitchRadians)
    local pitchedDepth = depth * cp - vertical * sp
    vertical = vertical * cp + depth * sp
    depth = pitchedDepth
    local ndcX = (2 * camera.viewportCenterX / camera.targetWidth) - 1
        + horizontal / (camera.fovHalfX * depth) * camera.projectionScale.x
            * (camera.baseViewportWidth / camera.targetWidth)
    local ndcY = 1 - (2 * camera.viewportCenterY / camera.targetHeight)
        + vertical / (camera.fovHalfY * depth) * camera.projectionScale.y
            * (camera.baseViewportHeight / camera.targetHeight)
    return (ndcX + 1) * camera.targetWidth * 0.5,
        (1 - ndcY) * camera.targetHeight * 0.5
end

local basePose = nil
for _, offset in ipairs(fixture.offsets) do
    local name = string.format("offset_%+d", offset)
    local actual = calibration.resolve(session, {
        profile = "first_person",
        projectionWindowOffsetX = offset,
        projectionWindowOffsetY = 0,
        focusOverride = { pitch = pitch },
        projectionFrame = projectionFrame,
    })
    local expected = fixture.camera
    local expectedCase = {}
    for key, value in pairs(expected) do expectedCase[key] = value end
    expectedCase.viewportCenterX = expected.viewportCenterX + offset
    expectedCase.projectionWindowOffsetX = offset
    assertRecord(actual, expectedCase, name)

    local pose = {
        actual.eye.x, actual.eye.y, actual.eye.z,
        actual.orientation.forwardX, actual.orientation.forwardY,
        actual.orientation.rightX, actual.orientation.rightY,
        actual.orientation.pitchRadians,
    }
    if not basePose then
        basePose = pose
    else
        for index, value in ipairs(pose) do
            check(close(value, basePose[index]), name .. " projection-window offset changed camera transform")
        end
    end

    for _, sample in ipairs(fixture.samples) do
        local sx, sy = project(actual, sample.world)
        check(close(sx, sample.screenAtZero[1] + offset, 1e-8), name .. " " .. sample.name .. " screen X")
        check(close(sy, sample.screenAtZero[2], 1e-8), name .. " " .. sample.name .. " screen Y")
    end
end

local ortho = calibration.fromResolved({
    projection = "orthographic",
    x = 1, y = 2, z = 3,
    dirX = 1, dirY = 0, rightX = 0, rightY = 1, pitch = math.rad(45),
    projectionScaleX = 0.75, projectionScaleY = 1,
    orthoHalfX = 6, orthoHalfY = 3.375,
    nearPlane = 0.05, farPlane = 32,
    baseViewportWidth = 256, baseViewportHeight = 144,
    viewportCenterX = 213, viewportCenterY = 70,
    projectionWindowOffsetX = 0, projectionWindowOffsetY = 0,
}, projectionFrame)
check(ortho.orthoHalfX == 6 and ortho.orthoHalfY == 3.375, "orthographic extents serialized")
check(ortho.fovHalfX == nil and ortho.fovHalfY == nil, "orthographic record does not invent FOV")

print("THESTRA_CAMERA_RUNTIME_PARITY OK")
if io and io.stdout and io.stdout.flush then io.stdout:flush() end
love.event.quit(0)
