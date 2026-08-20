-- Emit the exact calibration record used by the town gauntlet.
-- The values come from presentation.world_camera.resolve through the
-- world_camera_calibration serializer; Blender consumes this record one-way.
local n = arg and #arg or 0
local repoRoot = arg and (arg[n - 1] or arg[n])
local outputPath = arg and arg[n]
if not repoRoot or not outputPath or repoRoot == outputPath then
    error("usage: lovec tools/blender/town_camera_calibration <repoRoot> <output.json>", 0)
end

repoRoot = tostring(repoRoot):gsub("\\", "/")
package.path = repoRoot .. "/runtime/?.lua;" .. repoRoot .. "/runtime/?/init.lua;" .. package.path

local calibration = require("presentation.world_camera_calibration")
local session = { playerX = 5, playerY = 5, playerDir = "E" }
local record = calibration.resolve(session, {
    profile = "first_person",
    projectionWindowOffsetX = 0,
    projectionWindowOffsetY = 0,
    focusOverride = { pitch = math.rad(30) },
    projectionFrame = {
        targetWidth = 426,
        targetHeight = 240,
        compositionWidth = 256,
        canonicalCenterX = 213,
        canonicalHorizonY = 70,
    },
})

local file = assert(io.open(outputPath, "wb"))
file:write(require("engine.data.json").encode(record))
file:write("\n")
file:close()
print("THESTRA_TOWN_CAMERA_CALIBRATION OK")
love.event.quit(0)
