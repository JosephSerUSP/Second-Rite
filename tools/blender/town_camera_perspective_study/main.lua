-- Emit transient candidate records for the camera-only perspective study.
-- Every record still comes from the real WorldCamera resolver and serializer;
-- Blender consumes these records through tools/blender/thestra_camera.py.
local n = arg and #arg or 0
local repoRoot = arg and (arg[n - 2] or arg[n])
local outputDir = arg and (arg[n - 1] or arg[n])
local focalX = tonumber(arg and arg[n])
if not repoRoot or not outputDir or not focalX or repoRoot == outputDir then
    error("usage: lovec tools/blender/town_camera_perspective_study <repoRoot> <outputDir> <focalX>", 0)
end

repoRoot = tostring(repoRoot):gsub("\\", "/")
outputDir = tostring(outputDir):gsub("\\", "/")
package.path = repoRoot .. "/runtime/?.lua;" .. repoRoot .. "/runtime/?/init.lua;" .. package.path

local json = require("engine.data.json")
local calibration = require("presentation.world_camera_calibration")
local session = { playerX = 5, playerY = 5, playerDir = "E" }
local frame = {
    targetWidth = 426,
    targetHeight = 240,
    compositionWidth = 256,
    canonicalCenterX = 213,
    canonicalHorizonY = 70,
}

-- The final town slice's focal doorway is at x=8.5. The current camera eye is
-- x=5.5, so the study's 3x/5x/7x optical distances are explicit 3.0-unit
-- multiples from that same walking-plane reference.
local base = calibration.resolve(session, {
    profile = "first_person",
    projectionWindowOffsetX = 0,
    projectionWindowOffsetY = 0,
    focusOverride = { pitch = math.rad(30) },
    projectionFrame = frame,
})
local referenceDepth = focalX - base.eye.x
if referenceDepth <= 0 then error("focal reference must be in front of the base eye", 0) end

local candidates = {
    { id = "A", name = "Moderate telephoto", scale = 3, pitchDegrees = 0 },
    { id = "B", name = "Target telephoto", scale = 5, pitchDegrees = 0 },
    { id = "B1", name = "Target telephoto / flat", scale = 5, pitchDegrees = 0 },
    { id = "B2", name = "Target telephoto / slight down", scale = 5, pitchDegrees = 2.5 },
    { id = "C", name = "Strong telephoto", scale = 7, pitchDegrees = 0 },
}

local rows = {
    contract = "thestra.town-camera-perspective-study",
    version = 1,
    reference = {
        focalX = focalX,
        baseEyeX = base.eye.x,
        referenceDepth = referenceDepth,
        targetWidth = frame.targetWidth,
        targetHeight = frame.targetHeight,
        viewportCenterX = 213,
        viewportCenterY = 70,
        projectionWindowOffsetX = 0,
        projectionWindowOffsetY = 0,
    },
    candidates = {},
}

for _, candidate in ipairs(candidates) do
    local scale = candidate.scale
    local record = calibration.resolve(session, {
        profile = "first_person",
        projectionWindowOffsetX = 0,
        projectionWindowOffsetY = 0,
        focusOverride = {
            pitch = math.rad(candidate.pitchDegrees),
            fovScale = 1 / scale,
            dollyX = -referenceDepth * (scale - 1),
        },
        projectionFrame = frame,
    })
    rows.candidates[#rows.candidates + 1] = {
        id = candidate.id,
        name = candidate.name,
        scale = scale,
        pitchDegrees = candidate.pitchDegrees,
        record = record,
    }
end

local file = assert(io.open(outputDir .. "/camera-study-records.json", "wb"))
file:write(json.encode(rows))
file:write("\n")
file:close()
print("THESTRA_TOWN_CAMERA_STUDY_CALIBRATION OK")
love.event.quit(0)
