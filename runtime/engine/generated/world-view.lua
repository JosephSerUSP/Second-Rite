--[[ Generated with https://github.com/TypeScriptToLua/TypeScriptToLua ]]
-- Lua Library inline imports
local function __TS__Number(value)
    local valueType = type(value)
    if valueType == "number" then
        return value
    elseif valueType == "string" then
        local numberValue = tonumber(value)
        if numberValue then
            return numberValue
        end
        if value == "Infinity" then
            return math.huge
        end
        if value == "-Infinity" then
            return -math.huge
        end
        local stringWithoutSpaces = string.gsub(value, "%s", "")
        if stringWithoutSpaces == "" then
            return 0
        end
        return 0 / 0
    elseif valueType == "boolean" then
        return value and 1 or 0
    else
        return 0 / 0
    end
end

local function __TS__NumberIsFinite(value)
    return type(value) == "number" and value == value and value ~= math.huge and value ~= -math.huge
end

local function __TS__StringIncludes(self, searchString, position)
    if not position then
        position = 1
    else
        position = position + 1
    end
    local index = string.find(self, searchString, position, true)
    return index ~= nil
end

local function __TS__New(target, ...)
    local instance = setmetatable({}, target.prototype)
    instance:____constructor(...)
    return instance
end

local function __TS__Class(self)
    local c = {prototype = {}}
    c.prototype.__index = c.prototype
    c.prototype.constructor = c
    return c
end

local function __TS__ClassExtends(target, base)
    target.____super = base
    local staticMetatable = setmetatable({__index = base}, base)
    setmetatable(target, staticMetatable)
    local baseMetatable = getmetatable(base)
    if baseMetatable then
        if type(baseMetatable.__index) == "function" then
            staticMetatable.__index = baseMetatable.__index
        end
        if type(baseMetatable.__newindex) == "function" then
            staticMetatable.__newindex = baseMetatable.__newindex
        end
    end
    setmetatable(target.prototype, base.prototype)
    if type(base.prototype.__index) == "function" then
        target.prototype.__index = base.prototype.__index
    end
    if type(base.prototype.__newindex) == "function" then
        target.prototype.__newindex = base.prototype.__newindex
    end
    if type(base.prototype.__tostring) == "function" then
        target.prototype.__tostring = base.prototype.__tostring
    end
end

local Error, RangeError, ReferenceError, SyntaxError, TypeError, URIError
do
    local function getErrorStack(self, constructor)
        if debug == nil then
            return nil
        end
        local level = 1
        while true do
            local info = debug.getinfo(level, "f")
            level = level + 1
            if not info then
                level = 1
                break
            elseif info.func == constructor then
                break
            end
        end
        if __TS__StringIncludes(_VERSION, "Lua 5.0") then
            return debug.traceback(("[Level " .. tostring(level)) .. "]")
        elseif _VERSION == "Lua 5.1" then
            return string.sub(
                debug.traceback("", level),
                2
            )
        else
            return debug.traceback(nil, level)
        end
    end
    local function wrapErrorToString(self, getDescription)
        return function(self)
            local description = getDescription(self)
            local caller = debug.getinfo(3, "f")
            local isClassicLua = __TS__StringIncludes(_VERSION, "Lua 5.0")
            if isClassicLua or caller and caller.func ~= error then
                return description
            else
                return (description .. "\n") .. tostring(self.stack)
            end
        end
    end
    local function initErrorClass(self, Type, name)
        Type.name = name
        return setmetatable(
            Type,
            {__call = function(____, _self, message) return __TS__New(Type, message) end}
        )
    end
    local ____initErrorClass_1 = initErrorClass
    local ____class_0 = __TS__Class()
    ____class_0.name = ""
    function ____class_0.prototype.____constructor(self, message)
        if message == nil then
            message = ""
        end
        self.message = message
        self.name = "Error"
        self.stack = getErrorStack(nil, __TS__New)
        local metatable = getmetatable(self)
        if metatable and not metatable.__errorToStringPatched then
            metatable.__errorToStringPatched = true
            metatable.__tostring = wrapErrorToString(nil, metatable.__tostring)
        end
    end
    function ____class_0.prototype.__tostring(self)
        return self.message ~= "" and (self.name .. ": ") .. self.message or self.name
    end
    Error = ____initErrorClass_1(nil, ____class_0, "Error")
    local function createErrorClass(self, name)
        local ____initErrorClass_3 = initErrorClass
        local ____class_2 = __TS__Class()
        ____class_2.name = ____class_2.name
        __TS__ClassExtends(____class_2, Error)
        function ____class_2.prototype.____constructor(self, ...)
            ____class_2.____super.prototype.____constructor(self, ...)
            self.name = name
        end
        return ____initErrorClass_3(nil, ____class_2, name)
    end
    RangeError = createErrorClass(nil, "RangeError")
    ReferenceError = createErrorClass(nil, "ReferenceError")
    SyntaxError = createErrorClass(nil, "SyntaxError")
    TypeError = createErrorClass(nil, "TypeError")
    URIError = createErrorClass(nil, "URIError")
end
-- End of Lua Library inline imports
ThestraWorldViewSemantics = ThestraWorldViewSemantics or ({})
do
    local function finite(value, fallback, label)
        local resolved = value == nil and fallback or __TS__Number(value)
        if not __TS__NumberIsFinite(resolved) then
            error(
                __TS__New(Error, label .. " must be finite"),
                0
            )
        end
        return resolved
    end
    local function positive(value, fallback, label)
        local resolved = finite(value, fallback, label)
        if resolved <= 0 then
            error(
                __TS__New(Error, label .. " must be positive"),
                0
            )
        end
        return resolved
    end
    function ThestraWorldViewSemantics.clamp(value, minimum, maximum)
        return math.max(
            minimum,
            math.min(maximum, value)
        )
    end
    function ThestraWorldViewSemantics.transitionArrowAxis(direction)
        if direction == "left" then
            return {x = 0, y = -1}
        end
        if direction == "right" then
            return {x = 0, y = 1}
        end
        if direction == "away" then
            return {x = 1, y = 0}
        end
        if direction == "toward" then
            return {x = -1, y = 0}
        end
        error(
            __TS__New(Error, "transition arrow direction must be left, right, away, or toward"),
            0
        )
    end
    function ThestraWorldViewSemantics.transitionArrowWorldPoint(rootX, rootY, groundZ, scale, direction, localX, localY, localZ)
        scale = positive(scale, 1, "transition arrow model scale")
        local axis = ThestraWorldViewSemantics.transitionArrowAxis(direction)
        local rightX = axis.y
        local rightY = -axis.x
        return {
            x = finite(rootX, 0, "transition arrow root X") + (localX * rightX + localZ * axis.x) * scale,
            y = finite(rootY, 0, "transition arrow root Y") + (localX * rightY + localZ * axis.y) * scale,
            z = finite(groundZ, 0, "transition arrow ground Z") + (0.22 + localY) * scale
        }
    end
    function ThestraWorldViewSemantics.fovHalfExtentFromDegrees(degrees)
        degrees = positive(degrees, 1, "camera FOV degrees")
        if degrees >= 179 then
            error(
                __TS__New(Error, "camera FOV degrees must be < 179"),
                0
            )
        end
        return math.tan(degrees * math.pi / 360)
    end
    function ThestraWorldViewSemantics.resolveProjectionFrame(source)
        local frame = source.projectionFrame or ({})
        local targetWidth = positive(frame.targetWidth, 256, "camera target width")
        local targetHeight = positive(frame.targetHeight, 240, "camera target height")
        local compositionWidth = positive(frame.compositionWidth, 256, "camera composition width")
        local canonicalCenterX = finite(frame.canonicalCenterX, compositionWidth * 0.5, "camera canonical center X")
        local canonicalHorizonY = finite(frame.canonicalHorizonY, 70, "camera canonical horizon Y")
        local square = source.squareAuthoringCamera == true
        local baseViewportWidth = square and targetWidth or compositionWidth
        local baseViewportHeight = square and targetHeight or 144
        local defaultCenterX = square and targetWidth * 0.5 or canonicalCenterX
        local defaultCenterY = square and targetHeight * 0.5 or canonicalHorizonY
        local ____temp_1
        if source.projectionWindowOffsetX == nil then
            local ____temp_0
            if frame.projectionWindowOffsetX == nil then
                ____temp_0 = frame.offsetX
            else
                ____temp_0 = frame.projectionWindowOffsetX
            end
            ____temp_1 = ____temp_0
        else
            ____temp_1 = source.projectionWindowOffsetX
        end
        local rawX = ____temp_1
        local ____temp_3
        if source.projectionWindowOffsetY == nil then
            local ____temp_2
            if frame.projectionWindowOffsetY == nil then
                ____temp_2 = frame.offsetY
            else
                ____temp_2 = frame.projectionWindowOffsetY
            end
            ____temp_3 = ____temp_2
        else
            ____temp_3 = source.projectionWindowOffsetY
        end
        local rawY = ____temp_3
        local offsetX = finite(rawX, 0, "camera projection window offset X")
        local offsetY = finite(rawY, 0, "camera projection window offset Y")
        return {
            baseViewportWidth = baseViewportWidth,
            baseViewportHeight = baseViewportHeight,
            viewportCenterX = defaultCenterX + offsetX,
            viewportCenterY = defaultCenterY + offsetY,
            projectionWindowOffsetX = offsetX,
            projectionWindowOffsetY = offsetY
        }
    end
    function ThestraWorldViewSemantics.resolveTownCamera(source)
        local target = source.target or ({})
        local targetX = finite(target.x, 0, "town camera target x")
        local targetY = finite(target.y, 0, "town camera target y")
        local targetZ = finite(target.z, 0, "town camera target z")
        local distance = positive(source.distance, 1, "town camera distance")
        local angle = finite(source.yawDegrees, 0, "town camera yaw degrees") * math.pi / 180
        local pitch = finite(source.pitchDegrees, 0, "town camera pitch degrees") * math.pi / 180
        if pitch <= -math.pi / 2 or pitch >= math.pi / 2 then
            error(
                __TS__New(Error, "town camera pitch must be between -90 and 90 degrees"),
                0
            )
        end
        local dirX = math.cos(angle)
        local dirY = math.sin(angle)
        local rightX = -dirY
        local rightY = dirX
        local scale = source.projectionScale or ({})
        local scaleX = positive(scale.x, 1, "town camera projection scale x")
        local scaleY = positive(scale.y, 1, "town camera projection scale y")
        local aspectY = source.squareAuthoringCamera == true and 1 or 144 / 256
        local framingScale = positive(source.focusOverride and source.focusOverride.fovScale, 1, "town camera framing scale")
        local fovHalfX = ThestraWorldViewSemantics.fovHalfExtentFromDegrees(positive(source.fovDegrees, 28.072486935852957, "town camera FOV degrees")) * framingScale
        local fovHalfY = fovHalfX * aspectY
        local cameraX = targetX - dirX * distance
        local cameraY = targetY - dirY * distance
        local cameraZ = targetZ + (source.eyeHeight == nil and distance * math.tan(pitch) or finite(source.eyeHeight, 0, "town camera eye height"))
        local cosPitch = math.cos(pitch)
        local sinPitch = math.sin(pitch)
        local frame = ThestraWorldViewSemantics.resolveProjectionFrame(source)
        return {
            projection = "perspective",
            profile = "town_sideview",
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
            focusDepth = distance,
            groundDistance = distance,
            angle = angle,
            dirX = dirX,
            dirY = dirY,
            rightX = rightX,
            rightY = rightY,
            pitch = pitch,
            forwardX = dirX * cosPitch,
            forwardY = dirY * cosPitch,
            forwardZ = -sinPitch,
            upX = dirX * sinPitch,
            upY = dirY * sinPitch,
            upZ = cosPitch,
            fovScale = framingScale,
            fovHalfX = fovHalfX,
            fovHalfY = fovHalfY,
            orthoHalfX = 1,
            orthoHalfY = 1,
            projectionScaleX = scaleX,
            projectionScaleY = scaleY,
            nearPlane = positive(source.nearPlane, 0.05, "town camera near plane"),
            farPlane = positive(source.farPlane, 128, "town camera far plane"),
            visibilityProfile = source.visibilityProfile or "play-overhead",
            baseViewportWidth = frame.baseViewportWidth,
            baseViewportHeight = frame.baseViewportHeight,
            viewportCenterX = frame.viewportCenterX,
            viewportCenterY = frame.viewportCenterY,
            projectionWindowOffsetX = frame.projectionWindowOffsetX,
            projectionWindowOffsetY = frame.projectionWindowOffsetY
        }
    end
    function ThestraWorldViewSemantics.projectionCoefficients(camera, opticalScale, extraOffsetX, extraOffsetY)
        opticalScale = positive(opticalScale, 1, "camera optical scale")
        local baseWidth = positive(camera.baseViewportWidth, 256, "camera base viewport width")
        local baseHeight = positive(camera.baseViewportHeight, 144, "camera base viewport height")
        local centerX = finite(camera.viewportCenterX, baseWidth * 0.5, "camera viewport center X") + extraOffsetX
        local centerY = finite(camera.viewportCenterY, baseHeight * 0.5, "camera viewport center Y") + extraOffsetY
        local horizontalExtent = camera.projection == "orthographic" and positive(camera.orthoHalfX, 1, "camera ortho half X") or positive(camera.fovHalfX, 0.75, "camera FOV half X") * opticalScale
        local verticalExtent = camera.projection == "orthographic" and positive(camera.orthoHalfY, 1, "camera ortho half Y") * opticalScale or positive(camera.fovHalfY, 0.421875, "camera FOV half Y") * opticalScale
        return {
            xScale = positive(camera.projectionScaleX, 1, "camera projection scale X") / horizontalExtent,
            yScale = positive(camera.projectionScaleY, 1, "camera projection scale Y") / verticalExtent,
            centerNdcX = centerX * 2 / baseWidth - 1,
            centerNdcY = centerY * 2 / baseHeight - 1
        }
    end
    function ThestraWorldViewSemantics.panProjectionWindow(offsetX, offsetY, dragPixelsX, dragPixelsY, displayWidth, displayHeight, baseWidth, baseHeight)
        displayWidth = positive(displayWidth, 1, "camera navigation display width")
        displayHeight = positive(displayHeight, 1, "camera navigation display height")
        return {x = offsetX + dragPixelsX * baseWidth / displayWidth, y = offsetY + dragPixelsY * baseHeight / displayHeight}
    end
    function ThestraWorldViewSemantics.opticalScaleAfterWheel(current, deltaY)
        current = positive(current, 1, "camera optical scale")
        return ThestraWorldViewSemantics.clamp(
            current * math.exp(deltaY * 0.0015),
            0.125,
            8
        )
    end
    function ThestraWorldViewSemantics.zoomProjectionWindowAtCursor(camera, currentScale, offsetX, offsetY, deltaY, cursorX, cursorY, displayWidth, displayHeight)
        local scale = ThestraWorldViewSemantics.opticalScaleAfterWheel(currentScale, deltaY)
        displayWidth = positive(displayWidth, 1, "camera navigation display width")
        displayHeight = positive(displayHeight, 1, "camera navigation display height")
        local baseWidth = positive(camera.baseViewportWidth, 256, "camera base viewport width")
        local baseHeight = positive(camera.baseViewportHeight, 144, "camera base viewport height")
        local currentX = finite(camera.viewportCenterX, baseWidth * 0.5, "camera viewport center X") + offsetX
        local currentY = finite(camera.viewportCenterY, baseHeight * 0.5, "camera viewport center Y") + offsetY
        local currentCenterNdcX = currentX * 2 / baseWidth - 1
        local currentCenterNdcY = currentY * 2 / baseHeight - 1
        local cursorNdcX = cursorX / displayWidth * 2 - 1
        local cursorNdcY = 1 - cursorY / displayHeight * 2
        local ratio = currentScale / scale
        local nextCenterNdcX = ratio * currentCenterNdcX + (ratio - 1) * cursorNdcX
        local nextCenterNdcY = ratio * currentCenterNdcY + (ratio - 1) * cursorNdcY
        return {
            scale = scale,
            x = (nextCenterNdcX + 1) * baseWidth * 0.5 - finite(camera.viewportCenterX, baseWidth * 0.5, "camera viewport center X"),
            y = (nextCenterNdcY + 1) * baseHeight * 0.5 - finite(camera.viewportCenterY, baseHeight * 0.5, "camera viewport center Y")
        }
    end
    function ThestraWorldViewSemantics.trackedProjectionOffset(laneY, centerY, pixelsPerWorld, minimum, maximum)
        return ThestraWorldViewSemantics.clamp(-(laneY - centerY) * pixelsPerWorld, minimum, maximum)
    end
    function ThestraWorldViewSemantics.projectPerspective(camera, targetWidth, targetHeight, worldX, worldY, worldZ)
        local relativeX = worldX - camera.x
        local relativeY = worldY - camera.y
        local depth = relativeX * camera.dirX + relativeY * camera.dirY
        local horizontal = relativeX * camera.rightX + relativeY * camera.rightY
        local vertical = worldZ - camera.z
        local cosPitch = math.cos(camera.pitch or 0)
        local sinPitch = math.sin(camera.pitch or 0)
        local pitchedDepth = depth * cosPitch - vertical * sinPitch
        local pitchedVertical = vertical * cosPitch + depth * sinPitch
        local safeDepth = math.max(pitchedDepth, 0.001)
        local ndcX = camera.viewportCenterX * 2 / targetWidth - 1 + horizontal / (camera.fovHalfX * safeDepth) * camera.projectionScaleX * (camera.baseViewportWidth / targetWidth)
        local ndcY = camera.viewportCenterY * 2 / targetHeight - 1 + pitchedVertical / (camera.fovHalfY * safeDepth) * camera.projectionScaleY * (camera.baseViewportHeight / targetHeight)
        return {x = (ndcX + 1) * targetWidth * 0.5, y = (1 - ndcY) * targetHeight * 0.5, depth = safeDepth}
    end
    function ThestraWorldViewSemantics.groundHeight(profile, fallbackZ, laneY)
        if not profile or #profile == 0 then
            return fallbackZ
        end
        if laneY <= profile[1].y then
            return profile[1].z
        end
        do
            local index = 1
            while index < #profile do
                local previous = profile[index]
                local current = profile[index + 1]
                if laneY <= current.y then
                    local span = current.y - previous.y
                    if span <= 0 then
                        return current.z
                    end
                    local amount = (laneY - previous.y) / span
                    return previous.z + (current.z - previous.z) * amount
                end
                index = index + 1
            end
        end
        return profile[#profile].z
    end
    function ThestraWorldViewSemantics.horizontalProjection(camera, width, height, depthX, groundZ, sliceY, centerX)
        local base = ThestraWorldViewSemantics.projectPerspective(
            camera,
            width,
            height,
            depthX,
            sliceY,
            groundZ
        )
        local p0 = ThestraWorldViewSemantics.projectPerspective(
            camera,
            width,
            height,
            depthX,
            0,
            groundZ
        )
        local p1 = ThestraWorldViewSemantics.projectPerspective(
            camera,
            width,
            height,
            depthX,
            1,
            groundZ
        )
        local x0 = centerX + p0.x - base.x
        local x1 = centerX + p1.x - base.x
        return {x1 * p1.depth - x0 * p0.depth, x0 * p0.depth, p1.depth - p0.depth, p0.depth}
    end
    function ThestraWorldViewSemantics.worldYAtScreenX(projection, screenX)
        if #projection ~= 4 then
            error(
                __TS__New(Error, "Invalid resolved horizontal projection."),
                0
            )
        end
        local denominator = screenX * projection[3] - projection[1]
        if math.abs(denominator) < 1e-10 then
            error(
                __TS__New(Error, "Event projection cannot be inverted at this position."),
                0
            )
        end
        return (projection[2] - screenX * projection[4]) / denominator
    end
end
-- THES_SHARED_LUA_WORLD_VIEW: generated module adapter; do not edit.
return ThestraWorldViewSemantics
