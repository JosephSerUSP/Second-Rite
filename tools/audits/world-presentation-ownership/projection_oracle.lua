-- Pure-Lua numerical oracle for #841.
-- Runs under ordinary Lua/texlua; it does not require LÖVE or GPU access.

local WIDTH = 256
local FOV_HALF_X = 0.62
local CAMERA_Y = -2.0

local function projectX(worldX, worldY, cameraX, projectionOffsetX)
    local depth = worldY - CAMERA_Y
    assert(depth > 0)
    local ndc = (projectionOffsetX or 0) + (worldX - cameraX) / (FOV_HALF_X * depth)
    return (ndc + 1) * WIDTH * 0.5, depth, ndc
end

local function near(a, b, eps)
    return math.abs(a - b) <= (eps or 1e-9)
end

local failures = 0
local function check(name, condition, detail)
    if condition then
        io.write("PASS  ", name, detail and ("  " .. detail) or "", "\n")
    else
        failures = failures + 1
        io.write("FAIL  ", name, detail and ("  " .. detail) or "", "\n")
    end
end

io.write("#841 projection oracle\n\n")

-- Held environment snapshot: occluder and actor were both originally interpreted
-- through camera x=0. The actor may move in world space at 60 Hz, but its projection
-- must still use camera x=0 until the environment snapshot advances.
local heldCameraX = 0.0
local currentCameraX = 0.70
local occluderX, occluderY = 0.0, 4.0
local actorX, actorY = 0.25, 5.5

local occHeld = projectX(occluderX, occluderY, heldCameraX, 0)
local actorHeld = projectX(actorX, actorY, heldCameraX, 0)
local actorWrong = projectX(actorX, actorY, currentCameraX, 0)
local mismatchPixels = math.abs(actorWrong - actorHeld)

check("stale-camera negative control is detectable",
    mismatchPixels > 8,
    string.format("actor shifts %.2f px when interpreted with current camera over held environment", mismatchPixels))
check("held-camera actor stays in held optical frame",
    near(projectX(actorX, actorY, heldCameraX, 0), actorHeld),
    string.format("held actor x=%.2f px, held occluder x=%.2f px", actorHeld, occHeld))

-- #837: fixed optical viewpoint, shift the principal point so an actor at a known
-- depth is centered without translating the camera.
local playerX, playerY = 4.0, 5.7
local playerDepth = playerY - CAMERA_Y
local principalShift = -playerX / (FOV_HALF_X * playerDepth)
local playerShifted = projectX(playerX, playerY, 0, principalShift)
local playerFollow = projectX(playerX, playerY, playerX, 0)
check("projection-center shift can center player with fixed camera",
    near(playerShifted, WIDTH * 0.5, 1e-7),
    string.format("offset=%.6f NDC, player x=%.3f px", principalShift, playerShifted))
check("ordinary camera follow can also center player but changes view transform",
    near(playerFollow, WIDTH * 0.5, 1e-7),
    string.format("cameraX=%.2f, player x=%.3f px", playerX, playerFollow))

-- The two centering methods are not the same optical result for geometry at other
-- depths. This is the useful distinction #837 wants to preserve.
local landmarkX, landmarkY = 0.0, 10.0
local landmarkShifted = projectX(landmarkX, landmarkY, 0, principalShift)
local landmarkFollow = projectX(landmarkX, landmarkY, playerX, 0)
local opticalDifference = math.abs(landmarkShifted - landmarkFollow)
check("shifted projection differs from camera follow away from target depth",
    opticalDifference > 4,
    string.format("landmark differs by %.2f px (shifted %.2f vs follow %.2f)",
        opticalDifference, landmarkShifted, landmarkFollow))

-- #836 x #837: changing projection offset while holding an old environment snapshot
-- changes the ray mapping just like moving the camera does.
local oldOffset = 0.0
local newOffset = 0.18
local actorOldProjection = projectX(actorX, actorY, heldCameraX, oldOffset)
local actorNewProjection = projectX(actorX, actorY, heldCameraX, newOffset)
local projectionMismatch = math.abs(actorNewProjection - actorOldProjection)
check("stale-projection negative control is detectable",
    projectionMismatch > 20,
    string.format("0.18 NDC offset changes actor by %.2f px against stale environment", projectionMismatch))

io.write("\n")
if failures > 0 then
    io.write(string.format("RESULT: %d failure(s)\n", failures))
    os.exit(1)
end
io.write("RESULT: all numerical projection invariants passed\n")
