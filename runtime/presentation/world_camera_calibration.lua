-- Serialized authoring-calibration view of a resolved WorldCamera.
--
-- This module is deliberately downstream of presentation.world_camera. It does
-- not resolve camera pose, FOV, principal point, or projection-window motion on
-- its own: callers hand those questions to the real resolver first, then this
-- module copies only the resolved optical facts Blender needs.
local world_camera = require("presentation.world_camera")

local calibration = {}
calibration.VERSION = 1

local COORDINATE_SYSTEM = {
    handedness = "right-handed",
    worldUp = "+Z",
    worldHorizontal = "XY",
    cameraForward = "+depth",
    cameraRight = "+right",
    screenOrigin = "top-left",
    screenY = "+down",
    blenderCameraForward = "-Z",
    blenderCameraUp = "+Y",
}

local function positiveFinite(value, label)
    value = tonumber(value)
    if not value or value <= 0 or value ~= value or value == math.huge then
        error(label .. " must be a positive finite number", 0)
    end
    return value
end

local function finite(value, label)
    value = tonumber(value)
    if not value or value ~= value or value == math.huge or value == -math.huge then
        error(label .. " must be a finite number", 0)
    end
    return value
end

local function copyCoordinateSystem()
    local result = {}
    for key, value in pairs(COORDINATE_SYSTEM) do result[key] = value end
    return result
end

function calibration.fromResolved(camera, projectionFrame)
    if type(camera) ~= "table" then error("camera calibration requires a resolved WorldCamera", 0) end
    projectionFrame = projectionFrame or {}
    local targetWidth = positiveFinite(projectionFrame.targetWidth, "camera calibration targetWidth")
    local targetHeight = positiveFinite(projectionFrame.targetHeight, "camera calibration targetHeight")

    local record = {
        contract = "thestra.world-camera-calibration",
        version = calibration.VERSION,
        projection = camera.projection,
        eye = {
            x = finite(camera.x, "camera eye x"),
            y = finite(camera.y, "camera eye y"),
            z = finite(camera.z, "camera eye z"),
        },
        orientation = {
            forwardX = finite(camera.dirX, "camera forward x"),
            forwardY = finite(camera.dirY, "camera forward y"),
            rightX = finite(camera.rightX, "camera right x"),
            rightY = finite(camera.rightY, "camera right y"),
            pitchRadians = finite(camera.pitch or 0, "camera pitch"),
        },
        projectionScale = {
            x = positiveFinite(camera.projectionScaleX or 1, "camera projection scale x"),
            y = positiveFinite(camera.projectionScaleY or 1, "camera projection scale y"),
        },
        nearPlane = positiveFinite(camera.nearPlane, "camera near plane"),
        farPlane = positiveFinite(camera.farPlane, "camera far plane"),
        targetWidth = targetWidth,
        targetHeight = targetHeight,
        baseViewportWidth = positiveFinite(camera.baseViewportWidth, "camera base viewport width"),
        baseViewportHeight = positiveFinite(camera.baseViewportHeight, "camera base viewport height"),
        viewportCenterX = finite(camera.viewportCenterX, "camera viewport center x"),
        viewportCenterY = finite(camera.viewportCenterY, "camera viewport center y"),
        projectionWindowOffsetX = finite(camera.projectionWindowOffsetX or 0,
            "camera projection window offset x"),
        projectionWindowOffsetY = finite(camera.projectionWindowOffsetY or 0,
            "camera projection window offset y"),
        coordinateSystem = copyCoordinateSystem(),
    }

    if record.projection == "perspective" then
        record.fovHalfX = positiveFinite(camera.fovHalfX, "camera FOV half x")
        record.fovHalfY = positiveFinite(camera.fovHalfY, "camera FOV half y")
    elseif record.projection == "orthographic" then
        record.orthoHalfX = positiveFinite(camera.orthoHalfX, "camera ortho half x")
        record.orthoHalfY = positiveFinite(camera.orthoHalfY, "camera ortho half y")
    else
        world_camera.projectionKindId(record.projection)
    end

    return record
end

function calibration.resolve(session, opts)
    opts = opts or {}
    local frame = opts.projectionFrame
    if type(frame) ~= "table" or frame.targetWidth == nil or frame.targetHeight == nil then
        error("camera calibration requires explicit projectionFrame.targetWidth/targetHeight", 0)
    end
    return calibration.fromResolved(world_camera.resolve(session, opts), frame)
end

function calibration.encode(session, opts)
    return require("engine.data.json").encode(calibration.resolve(session, opts))
end

return calibration
