local config = require("engine.config")
local ui = require("presentation.ui")

local world_camera = {}

world_camera.PROJECTION_PERSPECTIVE = 0
world_camera.PROJECTION_ORTHOGRAPHIC = 1
world_camera.FOG_CAMERA_DEPTH = 0
world_camera.FOG_GROUND_DISTANCE = 1

-- Runtime Map camera vocabulary. These directions remain presentation facts:
-- movement/collision continue to belong to exploration even when a camera
-- profile stops following the player's facing.
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

local OVERHEAD_PROFILES = {
    ortho_oblique = { projection = "orthographic", rpgCorrection = false },
    rpg_ortho = { projection = "orthographic", rpgCorrection = true },
    -- Perspective overhead defaults are intentionally long-lens. `tilesAcross`
    -- preserves target framing while the narrow FOV derives a farther optical
    -- distance, avoiding the miniature/wide-angle distortion of the Phase 3 spike.
    perspective_oblique = {
        projection = "perspective", rpgCorrection = false,
        fovDegrees = 26, tilesAcross = 18,
    },
    rpg_perspective = {
        projection = "perspective", rpgCorrection = true,
        fovDegrees = 26, tilesAcross = 18,
    },
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

local function movementInterpolatedCenter(session)
    local x, y = session.playerX + 0.5, session.playerY + 0.5
    if session.transitionTimer and session.transitionTimer > 0 then
        local duration = session.transitionDuration or 0.15
        local frac = duration > 0 and session.transitionTimer / duration or 1
        local forward = DIRS[session.playerDir]
        local right = DIRS[turnRightDir(session.playerDir)]
        if session.transitionDir == "forward" then
            x, y = x - forward.dx * frac, y - forward.dy * frac
        elseif session.transitionDir == "backward" then
            x, y = x + forward.dx * frac, y + forward.dy * frac
        elseif session.transitionDir == "strafe_left" then
            x, y = x + right.dx * frac, y + right.dy * frac
        elseif session.transitionDir == "strafe_right" then
            x, y = x - right.dx * frac, y - right.dy * frac
        end
    end
    return x, y
end

function world_camera.projectionKindId(projection)
    if projection == "perspective" then return world_camera.PROJECTION_PERSPECTIVE end
    if projection == "orthographic" then return world_camera.PROJECTION_ORTHOGRAPHIC end
    error("unknown world camera projection: " .. tostring(projection), 0)
end

function world_camera.fogMetricId(metric)
    if metric == "camera_depth" then return world_camera.FOG_CAMERA_DEPTH end
    if metric == "ground_distance" then return world_camera.FOG_GROUND_DISTANCE end
    error("unknown world camera fog metric: " .. tostring(metric), 0)
end

-- Fog distance is a presentation/view fact, not Map topology. The
-- first-person dungeon view preserves historical camera-forward depth;
-- overhead views measure atmosphere around the followed gameplay focus
-- so moving or raising the eye does not move the fog through the world.
function world_camera.fogDistanceAt(camera, wx, wy, wz)
    local metric = camera and camera.fogMetric
    if metric == "camera_depth" then
        return world_camera.cameraSpaceDepth(
            wx, wy, wz or 0,
            camera.x, camera.y, camera.z,
            camera.dirX, camera.dirY, camera.pitch)
    end
    if metric == "ground_distance" then
        local dx = wx - camera.fogOriginX
        local dy = wy - camera.fogOriginY
        return math.sqrt(dx * dx + dy * dy)
    end
    world_camera.fogMetricId(metric)
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

local function positiveFinite(value, label)
    value = tonumber(value)
    if not value or value <= 0 or value ~= value or value == math.huge then
        error(label .. " must be a positive finite number", 0)
    end
    return value
end

local function finiteNumber(value, fallback, label)
    if value == nil then return fallback end
    value = tonumber(value)
    if not value or value ~= value or value == math.huge or value == -math.huge then
        error(label .. " must be a finite number", 0)
    end
    return value
end

-- Resolve the pixel framing which turns the oriented WorldCamera into the
-- projection consumed by world meshes and world-space Effekseer. The render
-- surface still owns its dimensions/origin; once those facts are supplied,
-- their optical interpretation belongs to the resolved camera record.
--
-- Defaults are the historical Classic framing so direct resolver users and
-- numerical tests retain the same contract without needing a live surface.
local function resolveProjectionFrame(opts)
    opts = opts or {}
    local frame = type(opts.projectionFrame) == "table" and opts.projectionFrame or {}
    local targetWidth = positiveFinite(frame.targetWidth or 256, "camera target width")
    local targetHeight = positiveFinite(frame.targetHeight or 240, "camera target height")
    local compositionWidth = positiveFinite(
        frame.compositionWidth or 256, "camera composition width")
    local canonicalCenterX = finiteNumber(
        frame.canonicalCenterX, compositionWidth * 0.5, "camera canonical center X")
    local canonicalHorizonY = finiteNumber(
        frame.canonicalHorizonY, 70, "camera canonical horizon Y")
    local squareAuthoringCamera = opts.squareAuthoringCamera == true

    local baseViewportWidth = squareAuthoringCamera and targetWidth or compositionWidth
    local baseViewportHeight = squareAuthoringCamera and targetHeight or 144
    local defaultCenterX = squareAuthoringCamera and targetWidth * 0.5 or canonicalCenterX
    local defaultCenterY = squareAuthoringCamera and targetHeight * 0.5 or canonicalHorizonY

    local rawOffsetX = opts.projectionWindowOffsetX
    if rawOffsetX == nil and frame.projectionWindowOffsetX ~= nil then
        rawOffsetX = frame.projectionWindowOffsetX
    end
    if rawOffsetX == nil and opts.projectionOffsetX ~= nil then
        rawOffsetX = opts.projectionOffsetX
    end
    if rawOffsetX == nil and frame.offsetX ~= nil then
        rawOffsetX = frame.offsetX
    end
    local offsetX = finiteNumber(rawOffsetX, 0, "camera projection window offset X")

    local rawOffsetY = opts.projectionWindowOffsetY
    if rawOffsetY == nil and frame.projectionWindowOffsetY ~= nil then
        rawOffsetY = frame.projectionWindowOffsetY
    end
    if rawOffsetY == nil and opts.projectionOffsetY ~= nil then
        rawOffsetY = opts.projectionOffsetY
    end
    if rawOffsetY == nil and frame.offsetY ~= nil then
        rawOffsetY = frame.offsetY
    end
    local offsetY = finiteNumber(rawOffsetY, 0, "camera projection window offset Y")

    return {
        baseViewportWidth = baseViewportWidth,
        baseViewportHeight = baseViewportHeight,
        viewportCenterX = defaultCenterX + offsetX,
        viewportCenterY = defaultCenterY + offsetY,
        projectionWindowOffsetX = offsetX,
        projectionWindowOffsetY = offsetY,
    }
end

local function attachProjectionFrame(camera, opts)
    local frame = resolveProjectionFrame(opts)
    camera.baseViewportWidth = frame.baseViewportWidth
    camera.baseViewportHeight = frame.baseViewportHeight
    camera.viewportCenterX = frame.viewportCenterX
    camera.viewportCenterY = frame.viewportCenterY
    camera.projectionWindowOffsetX = frame.projectionWindowOffsetX
    camera.projectionWindowOffsetY = frame.projectionWindowOffsetY
    return camera
end

-- Human-facing perspective lens vocabulary. The renderer/shader keeps its
-- established half-extent contract (tan(FOV/2)); authored data never needs to
-- know that representation.
function world_camera.fovHalfExtentFromDegrees(degrees)
    degrees = positiveFinite(degrees, "camera FOV degrees")
    if degrees >= 179 then error("camera FOV degrees must be < 179", 0) end
    return math.tan(math.rad(degrees) * 0.5)
end

function world_camera.fovDegreesFromHalfExtent(halfExtent)
    halfExtent = positiveFinite(halfExtent, "camera FOV half extent")
    return math.deg(2 * math.atan(halfExtent))
end

-- At the optical target, a horizontal world tile projects with local scale
-- proportional to projectionScaleX / (fovHalfX * depth). Solving for depth
-- lets lens and framing vary independently: narrower lens => farther camera,
-- while the requested tile span at the target stays unchanged.
function world_camera.focusDepthForTilesAcross(tilesAcross, projectionScaleX, fovHalfX)
    tilesAcross = positiveFinite(tilesAcross, "camera tilesAcross")
    projectionScaleX = positiveFinite(projectionScaleX or 1, "camera projectionScaleX")
    fovHalfX = positiveFinite(fovHalfX, "camera FOV half extent")
    return tilesAcross * projectionScaleX / (2 * fovHalfX)
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

-- Pixel scales of the two cardinal ground basis vectors around the optical
-- target. For perspective this is the local differential at focusDepth; for
-- orthographic it is exact everywhere. This is deliberately a pure numerical
-- oracle for the shader/Effekseer projection contract.
function world_camera.localGroundPixelScales(camera, baseWidth, baseHeight, focusDepth)
    baseWidth, baseHeight = baseWidth or 256, baseHeight or 144
    local pitch = camera.pitch or 0
    local scaleX = camera.projectionScaleX or 1
    local scaleY = camera.projectionScaleY or 1
    local right, forward
    if camera.projection == "orthographic" then
        right = baseWidth * 0.5 * scaleX / camera.orthoHalfX
        forward = baseHeight * 0.5 * math.sin(pitch) * scaleY / camera.orthoHalfY
    elseif camera.projection == "perspective" then
        focusDepth = focusDepth or camera.focusDepth
        if type(focusDepth) ~= "number" or focusDepth <= 0 then
            error("perspective ground scale requires positive focusDepth", 0)
        end
        right = baseWidth * 0.5 * scaleX / (camera.fovHalfX * focusDepth)
        forward = baseHeight * 0.5 * math.sin(pitch) * scaleY
            / (camera.fovHalfY * focusDepth)
    else
        world_camera.projectionKindId(camera.projection)
    end
    return right, forward
end

-- Resolve the current production first-person Map camera into one explicit
-- record. This preserves the renderer's pre-#589 camera policy exactly.
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
        if key == "DOWN" or key == "down" or key == "s" then
            nx, ny = -forward.dx, -forward.dy
        elseif key == "L" or key == "q" then
            local left = DIRS[turnLeftDir(pdir)]
            nx, ny = left.dx, left.dy
        elseif key == "R" or key == "e" then
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

    return attachProjectionFrame({
        projection = "perspective",
        profile = "first_person",
        x = cx + 1,
        y = cy + 1,
        z = 0.5,
        -- Compatibility: first-person historically anchored the player light
        -- to camera XY, including bump/door/focus camera motion. State it
        -- explicitly so other camera profiles do not inherit camera==player.
        playerLightX = cx + 1,
        playerLightY = cy + 1,
        fogMetric = "camera_depth",
        fogOriginX = cx + 1,
        fogOriginY = cy + 1,
        angle = angle,
        dirX = dirX,
        dirY = dirY,
        rightX = rightX,
        rightY = rightY,
        pitch = tonumber(focus.pitch) or 0.0,
        fovScale = fovScale,
        fovHalfX = 0.75 * fovScale,
        fovHalfY = (squareAuthoringCamera and 0.75 or 0.421875) * fovScale,
        orthoHalfX = 1,
        orthoHalfY = 1,
        projectionScaleX = 1,
        projectionScaleY = 1,
        nearPlane = 0.05,
        farPlane = 32.0,
        visibilityProfile = "play",
    }, opts)
end

function world_camera.resolveOverhead(session, opts)
    requireSessionCameraState(session)
    opts = opts or {}
    local projection = opts.projection or "orthographic"
    world_camera.projectionKindId(projection)

    local focus = opts.focusOverride or {}
    local basePitch = tonumber(opts.pitch) or math.rad(45)
    local pitch = basePitch + (tonumber(focus.pitch) or 0)
    if pitch <= 0 or pitch >= math.pi / 2 then
        error("overhead camera pitch must be > 0 and < pi/2", 0)
    end
    local angle = tonumber(opts.yaw) or DIR_ANGLES.N
    local dirX, dirY = math.cos(angle), math.sin(angle)
    local rightX, rightY = -dirY, dirX
    local targetX, targetY = movementInterpolatedCenter(session)
    local targetZ = tonumber(opts.targetZ) or 0.0

    local projectionScaleX = 1.0
    local projectionScaleY = 1.0
    if opts.rpgCorrection == true then
        projectionScaleX = world_camera.rpgGridHorizontalScale(pitch)
    end
    if type(opts.projectionScale) == "table" then
        projectionScaleX = tonumber(opts.projectionScale[1]) or projectionScaleX
        projectionScaleY = tonumber(opts.projectionScale[2]) or projectionScaleY
    end

    local squareAuthoringCamera = opts.squareAuthoringCamera == true
    local aspectY = squareAuthoringCamera and 1.0 or (144 / 256)
    local baseFovHalfX = opts.fovDegrees ~= nil
        and world_camera.fovHalfExtentFromDegrees(opts.fovDegrees) or 0.75
    local baseFovHalfY = baseFovHalfX * aspectY
    local tilesAcross = opts.tilesAcross ~= nil
        and positiveFinite(opts.tilesAcross, "camera tilesAcross") or nil

    local focusDepth, height, groundDistance
    if projection == "perspective" and tilesAcross then
        focusDepth = world_camera.focusDepthForTilesAcross(
            tilesAcross, projectionScaleX, baseFovHalfX)
        height = focusDepth * math.sin(pitch)
        groundDistance = focusDepth * math.cos(pitch)
    else
        height = tonumber(opts.height) or 6.0
        if height <= 0 then error("overhead camera height must be positive", 0) end
        groundDistance = height / math.tan(pitch)
        focusDepth = math.sqrt(groundDistance * groundDistance + height * height)
    end

    local cameraX = targetX - dirX * groundDistance
    local cameraY = targetY - dirY * groundDistance
    local cameraZ = targetZ + height
    if (focus.dollyX or 0) ~= 0 or (focus.dollyY or 0) ~= 0 then
        cameraX = cameraX + (focus.dollyX or 0)
        cameraY = cameraY + (focus.dollyY or 0)
    end

    -- world_focus remains a temporary optical zoom over the resolved base
    -- camera. It must not re-derive pose, otherwise changing FOV would cancel
    -- itself by moving the camera to preserve framing.
    local framingScale = tonumber(focus.fovScale) or 1.0
    local orthoHalfX = (tonumber(opts.orthoHalfX) or 6.0) * framingScale
    local orthoHalfY = (tonumber(opts.orthoHalfY) or (orthoHalfX * aspectY))
    local fovHalfX = baseFovHalfX * framingScale
    local fovHalfY = baseFovHalfY * framingScale
    -- Preserve the historical 32-unit overhead range unless perspective
    -- framing has deliberately pulled the camera farther away. Very narrow
    -- authored lenses scale their default range with the derived optical depth.
    local defaultFarPlane = 32.0
    if projection == "perspective" and tilesAcross then
        defaultFarPlane = math.max(64.0, focusDepth * 2)
    end

    return attachProjectionFrame({
        projection = projection,
        profile = opts.profile or "overhead",
        x = cameraX,
        y = cameraY,
        z = cameraZ,
        targetX = targetX,
        targetY = targetY,
        targetZ = targetZ,
        playerLightX = targetX,
        playerLightY = targetY,
        fogMetric = "ground_distance",
        fogOriginX = targetX,
        fogOriginY = targetY,
        focusDepth = focusDepth,
        height = height,
        groundDistance = groundDistance,
        tilesAcross = tilesAcross,
        fovDegrees = world_camera.fovDegreesFromHalfExtent(fovHalfX),
        angle = angle,
        dirX = dirX,
        dirY = dirY,
        rightX = rightX,
        rightY = rightY,
        pitch = pitch,
        fovScale = framingScale,
        fovHalfX = fovHalfX,
        fovHalfY = fovHalfY,
        orthoHalfX = orthoHalfX,
        orthoHalfY = orthoHalfY,
        projectionScaleX = projectionScaleX,
        projectionScaleY = projectionScaleY,
        nearPlane = tonumber(opts.nearPlane) or 0.05,
        farPlane = tonumber(opts.farPlane) or defaultFarPlane,
        visibilityProfile = opts.visibilityProfile or "play-overhead",
    }, opts)
end

-- Resolve a world-camera profile from durable Scene presentation plus
-- ephemeral runtime overrides. Direct resolver/session values remain useful
-- for cinematics, tests and capture harnesses, but they never rewrite the
-- authored Scene or Map/gameplay state.
function world_camera.resolve(session, opts)
    opts = opts or {}
    local authored = type(opts.authoredCamera) == "table" and opts.authoredCamera or {}
    local profile = opts.profile or session.worldCameraProfile or authored.profile or "first_person"

    local projectionWindowOffsetX = authored.projectionWindowOffsetX or authored.projectionOffsetX
    local projectionWindowOffsetY = authored.projectionWindowOffsetY or authored.projectionOffsetY

    if session.worldCameraProjectionWindowOffsetX ~= nil then
        projectionWindowOffsetX = session.worldCameraProjectionWindowOffsetX
    elseif session.worldCameraProjectionOffsetX ~= nil then
        projectionWindowOffsetX = session.worldCameraProjectionOffsetX
    end
    if session.worldCameraProjectionWindowOffsetY ~= nil then
        projectionWindowOffsetY = session.worldCameraProjectionWindowOffsetY
    elseif session.worldCameraProjectionOffsetY ~= nil then
        projectionWindowOffsetY = session.worldCameraProjectionOffsetY
    end

    if opts.projectionWindowOffsetX ~= nil then
        projectionWindowOffsetX = opts.projectionWindowOffsetX
    elseif opts.projectionOffsetX ~= nil then
        projectionWindowOffsetX = opts.projectionOffsetX
    end
    if opts.projectionWindowOffsetY ~= nil then
        projectionWindowOffsetY = opts.projectionWindowOffsetY
    elseif opts.projectionOffsetY ~= nil then
        projectionWindowOffsetY = opts.projectionOffsetY
    end

    local resolvedOpts = {}
    for key, value in pairs(opts) do resolvedOpts[key] = value end
    resolvedOpts.projectionWindowOffsetX = projectionWindowOffsetX
    resolvedOpts.projectionWindowOffsetY = projectionWindowOffsetY

    if profile == "first_person" then
        return world_camera.resolveFirstPerson(session, resolvedOpts)
    end
    local preset = OVERHEAD_PROFILES[profile]
    if not preset then error("unknown world camera profile: " .. tostring(profile), 0) end

    local overheadOpts = {}
    for key, value in pairs(preset) do overheadOpts[key] = value end
    if authored.pitchDegrees ~= nil then overheadOpts.pitch = math.rad(authored.pitchDegrees) end
    if authored.yawDegrees ~= nil then overheadOpts.yaw = math.rad(authored.yawDegrees) end
    if authored.fovDegrees ~= nil then overheadOpts.fovDegrees = authored.fovDegrees end
    if authored.tilesAcross ~= nil then overheadOpts.tilesAcross = authored.tilesAcross end
    if authored.visibilityProfile ~= nil then overheadOpts.visibilityProfile = authored.visibilityProfile end

    if session.worldCameraPitch ~= nil then overheadOpts.pitch = session.worldCameraPitch end
    if session.worldCameraYaw ~= nil then overheadOpts.yaw = session.worldCameraYaw end
    if session.worldCameraFovDegrees ~= nil then overheadOpts.fovDegrees = session.worldCameraFovDegrees end
    if session.worldCameraTilesAcross ~= nil then overheadOpts.tilesAcross = session.worldCameraTilesAcross end
    if session.worldCameraVisibilityProfile ~= nil then
        overheadOpts.visibilityProfile = session.worldCameraVisibilityProfile
    end

    for key, value in pairs(resolvedOpts) do
        if key ~= "authoredCamera" and key ~= "profile" then overheadOpts[key] = value end
    end
    overheadOpts.profile = profile
    overheadOpts.projection = preset.projection
    overheadOpts.rpgCorrection = preset.rpgCorrection
    return world_camera.resolveOverhead(session, overheadOpts)
end

return world_camera
