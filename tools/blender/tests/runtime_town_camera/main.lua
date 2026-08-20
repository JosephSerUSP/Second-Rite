-- Generate the next-town-gauntlet Blender calibration through Thestra runtime code.
--
-- This is deliberately an authoring-study adapter. The human-facing source lives
-- in town-camera-next.json; this harness turns it into the existing resolved
-- WorldCamera shape and delegates serialization to world_camera_calibration.
-- It does NOT define a new Scene schema and Blender never writes camera facts back.
local n = arg and #arg or 0
local repoRoot = arg and arg[n - 2]
local specPath = arg and arg[n - 1]
local outputPath = arg and arg[n]
if not repoRoot or not specPath or not outputPath then
    error("usage: lovec tools/blender/tests/runtime_town_camera <repoRoot> <spec.json> <output.json>", 0)
end

repoRoot = tostring(repoRoot):gsub("\\", "/")
package.path = repoRoot .. "/runtime/?.lua;" .. repoRoot .. "/runtime/?/init.lua;" .. package.path

local world_camera = require("presentation.world_camera")
local calibration = require("presentation.world_camera_calibration")
local json = require("engine.data.json")

local function finite(value, label)
    value = tonumber(value)
    if not value or value ~= value or value == math.huge or value == -math.huge then
        error(label .. " must be finite", 0)
    end
    return value
end

local function positive(value, label)
    value = finite(value, label)
    if value <= 0 then error(label .. " must be positive", 0) end
    return value
end

local file = assert(io.open(specPath, "rb"))
local spec = assert(json.decode(file:read("*a")))
file:close()

if spec.contract ~= "second-gate.town-camera-gauntlet" or spec.version ~= 1 then
    error("unsupported town camera gauntlet contract/version", 0)
end

local camera = assert(spec.camera, "town camera spec missing camera")
local frame = assert(spec.projectionFrame, "town camera spec missing projectionFrame")
if camera.projection ~= "perspective" then
    error("next town gauntlet currently requires perspective projection", 0)
end

local pitchDegrees = finite(camera.pitchDegrees or 0, "town camera pitchDegrees")
if math.abs(pitchDegrees) > 1e-10 then
    error("next town gauntlet baseline must remain level (pitchDegrees = 0)", 0)
end
local pitch = math.rad(pitchDegrees)
local yaw = math.rad(finite(camera.yawDegrees or 0, "town camera yawDegrees"))
local dirX, dirY = math.cos(yaw), math.sin(yaw)
local rightX, rightY = -dirY, dirX
local distance = positive(camera.distance, "town camera distance")
local target = assert(camera.target, "town camera spec missing target")
local targetX = finite(target.x, "town camera target.x")
local targetY = finite(target.y, "town camera target.y")
local targetZ = finite(target.z, "town camera target.z")
local fovHalfX = world_camera.fovHalfExtentFromDegrees(
    positive(camera.fovDegrees, "town camera fovDegrees"))
local baseViewportWidth = positive(frame.baseViewportWidth, "town camera baseViewportWidth")
local baseViewportHeight = positive(frame.baseViewportHeight, "town camera baseViewportHeight")
local fovHalfY = fovHalfX * (baseViewportHeight / baseViewportWidth)
local projectionScale = camera.projectionScale or {}
local scaleX = positive(projectionScale.x or 1, "town camera projectionScale.x")
local scaleY = positive(projectionScale.y or 1, "town camera projectionScale.y")

local resolved = {
    projection = "perspective",
    profile = "town_gauntlet_sideview",
    x = targetX - dirX * distance,
    y = targetY - dirY * distance,
    z = targetZ,
    targetX = targetX,
    targetY = targetY,
    targetZ = targetZ,
    angle = yaw,
    dirX = dirX,
    dirY = dirY,
    rightX = rightX,
    rightY = rightY,
    pitch = pitch,
    focusDepth = distance,
    fovHalfX = fovHalfX,
    fovHalfY = fovHalfY,
    projectionScaleX = scaleX,
    projectionScaleY = scaleY,
    orthoHalfX = 1,
    orthoHalfY = 1,
    nearPlane = positive(camera.nearPlane or 0.05, "town camera nearPlane"),
    farPlane = positive(camera.farPlane or 64, "town camera farPlane"),
    baseViewportWidth = baseViewportWidth,
    baseViewportHeight = baseViewportHeight,
    viewportCenterX = finite(frame.canonicalCenterX, "town camera canonicalCenterX"),
    viewportCenterY = finite(frame.canonicalHorizonY, "town camera canonicalHorizonY"),
    projectionWindowOffsetX = 0,
    projectionWindowOffsetY = 0,
}

local record = calibration.fromResolved(resolved, {
    targetWidth = positive(frame.targetWidth, "town camera targetWidth"),
    targetHeight = positive(frame.targetHeight, "town camera targetHeight"),
})

local out = assert(io.open(outputPath, "wb"))
out:write(json.encode(record))
out:write("\n")
out:close()

print(string.format(
    "THESTRA_TOWN_CAMERA_CALIBRATION OK eye=(%.6f,%.6f,%.6f) pitch=%.6f fovHalfX=%.9f",
    record.eye.x, record.eye.y, record.eye.z,
    record.orientation.pitchRadians, record.fovHalfX))
if io and io.stdout and io.stdout.flush then io.stdout:flush() end
love.event.quit(0)
