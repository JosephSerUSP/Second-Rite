-- runtime/presentation/camera_calibration.lua
-- Serializes resolved Thestra WorldCamera states into portable calibration records
-- for external authoring tools (e.g. Blender) and provides authoritative projection math.

local world_camera = require("presentation.world_camera")

local camera_calibration = {}

-- Create a complete, portable calibration record from a resolved WorldCamera table
-- or directly from (session, opts) via world_camera.resolve.
function camera_calibration.createRecord(cameraOrSession, opts)
    local cam
    if cameraOrSession and cameraOrSession.projection then
        cam = cameraOrSession
    else
        cam = world_camera.resolve(cameraOrSession or {}, opts or {})
    end

    local pitch = cam.pitch or 0.0
    local cosP = math.cos(pitch)
    local sinP = math.sin(pitch)

    local dirX = cam.dirX or 0.0
    local dirY = cam.dirY or -1.0
    local rightX = cam.rightX or 1.0
    local rightY = cam.rightY or 0.0

    -- 3D orthonormal basis in Thestra world space (Z is Up):
    -- Forward: camera looking direction pitched by pitch (positive pitch tilts downward toward ground)
    local forwardX = dirX * cosP
    local forwardY = dirY * cosP
    local forwardZ = -sinP

    -- Right: camera lateral direction (perpendicular to forward in ground XY)
    local rX = rightX
    local rY = rightY
    local rZ = 0.0

    -- Up: camera vertical direction in camera space
    local upX = dirX * sinP
    local upY = dirY * sinP
    local upZ = cosP

    local targetWidth = cam.targetWidth or (opts and opts.projectionFrame and opts.projectionFrame.targetWidth) or 426
    local targetHeight = cam.targetHeight or (opts and opts.projectionFrame and opts.projectionFrame.targetHeight) or 240
    local baseWidth = cam.baseViewportWidth or 256
    local baseHeight = cam.baseViewportHeight or 144

    return {
        coordinateSystem = "thestra_world_z_up",
        projection = cam.projection,
        profile = cam.profile or "custom",
        eye = { cam.x or 0.0, cam.y or 0.0, cam.z or 0.0 },
        target = cam.targetX and { cam.targetX, cam.targetY, cam.targetZ or 0.0 } or nil,
        forward = { forwardX, forwardY, forwardZ },
        right = { rX, rY, rZ },
        up = { upX, upY, upZ },
        yaw = cam.angle or math.atan2(dirY, dirX),
        pitch = pitch,
        dirX = dirX,
        dirY = dirY,
        rightX = rightX,
        rightY = rightY,
        fovHalfX = cam.fovHalfX or 0.75,
        fovHalfY = cam.fovHalfY or 0.421875,
        fovDegrees = cam.fovDegrees or (cam.fovHalfX and world_camera.fovDegreesFromHalfExtent(cam.fovHalfX)),
        orthoHalfX = cam.orthoHalfX or 6.0,
        orthoHalfY = cam.orthoHalfY or 3.375,
        projectionScaleX = cam.projectionScaleX or 1.0,
        projectionScaleY = cam.projectionScaleY or 1.0,
        nearPlane = cam.nearPlane or 0.05,
        farPlane = cam.farPlane or 64.0,
        targetWidth = targetWidth,
        targetHeight = targetHeight,
        baseViewportWidth = baseWidth,
        baseViewportHeight = baseHeight,
        viewportCenterX = cam.viewportCenterX or (targetWidth * 0.5),
        viewportCenterY = cam.viewportCenterY or 70.0,
        projectionWindowOffsetX = cam.projectionWindowOffsetX or 0.0,
        projectionWindowOffsetY = cam.projectionWindowOffsetY or 0.0,
        visibilityProfile = cam.visibilityProfile or "play",
    }
end

-- Authoritative projection of a 3D world point (wx, wy, wz) to screen pixel coordinates (screenX, screenY, cameraDepth)
-- Exactly matches the mathematical contract of retro_mesh_shader.lua / WorldCamera.
function camera_calibration.projectWorldPoint(record, wx, wy, wz)
    wz = wz or 0.0
    local eye = record.eye
    local relX = wx - eye[1]
    local relY = wy - eye[2]
    local relZ = wz - eye[3]

    local f = record.forward
    local r = record.right
    local u = record.up

    local depth = relX * f[1] + relY * f[2] + relZ * f[3]
    local horizontal = relX * r[1] + relY * r[2] + relZ * r[3]
    local vertical = relX * u[1] + relY * u[2] + relZ * u[3]

    local screenX, screenY
    if record.projection == "orthographic" then
        screenX = record.viewportCenterX + (horizontal / record.orthoHalfX) * record.projectionScaleX * (record.baseViewportWidth * 0.5)
        screenY = record.viewportCenterY - (vertical / record.orthoHalfY) * record.projectionScaleY * (record.baseViewportHeight * 0.5)
    else
        screenX = record.viewportCenterX + (horizontal / (record.fovHalfX * depth)) * record.projectionScaleX * (record.baseViewportWidth * 0.5)
        screenY = record.viewportCenterY - (vertical / (record.fovHalfY * depth)) * record.projectionScaleY * (record.baseViewportHeight * 0.5)
    end

    return screenX, screenY, depth
end

return camera_calibration
