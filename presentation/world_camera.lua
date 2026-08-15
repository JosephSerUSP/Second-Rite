local config = require("engine.config")
local ui = require("presentation.ui")

local world_camera = {}

-- Runtime Map camera vocabulary. These directions remain presentation facts:
-- movement/collision continue to belong to exploration even when a future
-- camera profile stops following the player's facing.
local DIRS = {
    N = { dx = 0,  dy = -1 },
    E = { dx = 1,  dy = 0  },
    S = { dx = 0,  dy = 1  },
    W = { dx = -1, dy = 0  },
}

local DIR_ORDER = { "N", "E", "S", "W" }
local DIR_ANGLES = {
    N = -math.pi / 2,
    E = 0,
    S = math.pi / 2,
    W = math.pi,
}

local function turnLeftDir(dir)
    local idx = 1
    for i, d in ipairs(DIR_ORDER) do
        if d == dir then idx = i break end
    end
    return DIR_ORDER[(idx - 2) % 4 + 1]
end

local function turnRightDir(dir)
    local idx = 1
    for i, d in ipairs(DIR_ORDER) do
        if d == dir then idx = i break end
    end
    return DIR_ORDER[idx % 4 + 1]
end

local function requireSessionCameraState(session)
    if type(session) ~= "table" then
        error("world camera requires a session", 0)
    end
    if type(session.playerX) ~= "number" or type(session.playerY) ~= "number" then
        error("world camera requires numeric playerX/playerY", 0)
    end
    if not DIR_ANGLES[session.playerDir] then
        error("world camera requires cardinal playerDir", 0)
    end
end

-- Exact traditional-RPG ground-grid correction for a cardinal oblique camera.
-- A unit along the camera-forward ground axis projects at sin(pitch) relative
-- to the perpendicular ground axis. Compressing projected X by that factor (or
-- stretching projected Y by its reciprocal) makes square ground cells read as
-- screen squares in orthographic projection. Perspective can use the same
-- factor as a local calibration around its optical target.
function world_camera.rpgGridHorizontalScale(pitch)
    if type(pitch) ~= "number" or pitch <= 0 or pitch > math.pi / 2 then
        error("RPG grid correction pitch must be > 0 and <= pi/2", 0)
    end
    return math.sin(pitch)
end

function world_camera.rpgGridVerticalStretch(pitch)
    return 1 / world_camera.rpgGridHorizontalScale(pitch)
end

-- Once ground cells have been corrected to screen squares, a unit of world
-- height occupies cot(pitch) tile-heights on screen. At 45 degrees this is 1.
function world_camera.rpgWallHeightInTiles(pitch)
    local groundScale = world_camera.rpgGridHorizontalScale(pitch)
    return math.cos(pitch) / groundScale
end

-- Unified camera-space depth used by CPU visibility checks. Kept independent
-- from projection kind: perspective and orthographic cameras share the same
-- oriented camera frame even though they map that frame to clip space
-- differently.
function world_camera.cameraSpaceDepth(wx, wy, wz, cameraX, cameraY, cameraZ, dirX, dirY, cameraPitch)
    local horizDepth = (wx - cameraX) * dirX + (wy - cameraY) * dirY
    local pitch = cameraPitch or 0
    if pitch == 0 then return horizDepth end
    local vert = (wz or 0) - cameraZ
    return horizDepth * math.cos(pitch) - vert * math.sin(pitch)
end

-- Resolve the current production first-person Map camera into one explicit
-- record. This first slice intentionally preserves the renderer's existing
-- camera policy byte-for-byte; later #589 slices can choose different profile
-- inputs without putting another camera implementation inside viewport_3d.
--
-- opts are presentation inputs already owned outside the renderer loop:
--   doorProgress          current door approach interpolation (default 0)
--   focusOverride         world_focus camera override (default neutral)
--   squareAuthoringCamera room-bake square camera framing
function world_camera.resolveFirstPerson(session, opts)
    requireSessionCameraState(session)
    opts = opts or {}

    local px, py, pdir = session.playerX, session.playerY, session.playerDir
    local cx, cy = px - 0.5, py - 0.5
    local angle = DIR_ANGLES[pdir]

    if session.transitionTimer and session.transitionTimer > 0 then
        local duration = session.transitionDuration or 0.15
        local frac = duration > 0 and session.transitionTimer / duration or 1
        local forward = DIRS[pdir]
        local right = DIRS[turnRightDir(pdir)]
        if session.transitionDir == "forward" then
            cx, cy = cx - forward.dx * frac, cy - forward.dy * frac
        elseif session.transitionDir == "backward" then
            cx, cy = cx + forward.dx * frac, cy + forward.dy * frac
        elseif session.transitionDir == "strafe_left" then
            cx, cy = cx + right.dx * frac, cy + right.dy * frac
        elseif session.transitionDir == "strafe_right" then
            cx, cy = cx - right.dx * frac, cy - right.dy * frac
        elseif session.transitionDir == "turn_left" then
            angle = ui.lerpAngle(DIR_ANGLES[turnRightDir(pdir)], angle, 1 - frac)
        elseif session.transitionDir == "turn_right" then
            angle = ui.lerpAngle(DIR_ANGLES[turnLeftDir(pdir)], angle, 1 - frac)
        end
    end

    if session.bumpTimer and session.bumpTimer > 0 then
        local bumpDur = (config.ui and config.ui.bumpDuration) or 0.12
        local frac = bumpDur > 0 and session.bumpTimer / bumpDur or 1
        local nudge = frac * ((config.ui and config.ui.bumpNudge) or 0.12)
        local forward = DIRS[pdir]
        local key = session.bumpNudgeKey
        local nx, ny = forward.dx, forward.dy
        if key == "down" or key == "s" then
            nx, ny = -forward.dx, -forward.dy
        elseif key == "q" then
            local left = DIRS[turnLeftDir(pdir)]
            nx, ny = left.dx, left.dy
        elseif key == "e" then
            local right = DIRS[turnRightDir(pdir)]
            nx, ny = right.dx, right.dy
        end
        cx, cy = cx + nx * nudge, cy + ny * nudge
    end

    local dirX, dirY = math.cos(angle), math.sin(angle)
    local rightX, rightY = -dirY, dirX

    local doorProgress = tonumber(opts.doorProgress) or 0
    if doorProgress > 0 then
        cx, cy = cx + dirX * doorProgress * 0.22, cy + dirY * doorProgress * 0.22
    end

    local focus = opts.focusOverride or {}
    if (focus.dollyX or 0) ~= 0 or (focus.dollyY or 0) ~= 0 then
        cx = cx + (focus.dollyX or 0)
        cy = cy + (focus.dollyY or 0)
    end

    local fovScale = tonumber(focus.fovScale) or 1.0
    local squareAuthoringCamera = opts.squareAuthoringCamera == true

    return {
        projection = "perspective",
        profile = "first_person",
        x = cx + 1,
        y = cy + 1,
        z = 0.5,
        angle = angle,
        dirX = dirX,
        dirY = dirY,
        rightX = rightX,
        rightY = rightY,
        pitch = tonumber(focus.pitch) or 0.0,
        fovScale = fovScale,
        fovHalfX = 0.75 * fovScale,
        fovHalfY = (squareAuthoringCamera and 0.75 or 0.421875) * fovScale,
        nearPlane = 0.05,
        farPlane = 32.0,
        visibilityProfile = "play",
    }
end

return world_camera
