"use strict";
/*
 * Shared executable semantic authority for WorldCamera optics and bounded-lane
 * composition. LÖVE owns rendering and Studio owns interaction, but neither
 * host may independently redefine projection-window movement, optical scale,
 * or the mapping between lane world positions and plate pixels.
 */
var ThestraWorldViewSemantics;
(function (ThestraWorldViewSemantics) {
    function finite(value, fallback, label) {
        const resolved = value === undefined ? fallback : Number(value);
        if (!Number.isFinite(resolved))
            throw new Error(label + ' must be finite');
        return resolved;
    }
    function positive(value, fallback, label) {
        const resolved = finite(value, fallback, label);
        if (resolved <= 0)
            throw new Error(label + ' must be positive');
        return resolved;
    }
    function clamp(value, minimum, maximum) {
        return Math.max(minimum, Math.min(maximum, value));
    }
    ThestraWorldViewSemantics.clamp = clamp;
    // Transition-arrow models are authored with their shaft along local +Y.
    // This is the one meaning of an event's explicit direction: an axis in the
    // runtime ground plane. Hosts may adapt that axis to their own coordinates,
    // but must not infer it from a label or reimplement the rotation.
    function transitionArrowAxis(direction) {
        if (direction === 'left')
            return { x: 0, y: -1 };
        if (direction === 'right')
            return { x: 0, y: 1 };
        if (direction === 'away')
            return { x: 1, y: 0 };
        if (direction === 'toward')
            return { x: -1, y: 0 };
        throw new Error('transition arrow direction must be left, right, away, or toward');
    }
    ThestraWorldViewSemantics.transitionArrowAxis = transitionArrowAxis;
    // Runtime OBJ vertices have already been converted from source Y-up into
    // the engine's Z-up space. This is the authoritative Event transform for
    // a transition arrow: its root sits at the authored world position, the
    // shaft follows its explicit ground-plane direction, and the cylinder
    // rests on the resolved lane floor. Studio adapts its source vertices to
    // this local frame before calling it; neither host may reimplement the
    // root/rotation/grounding calculation.
    function transitionArrowWorldPoint(rootX, rootY, groundZ, scale, direction, localX, localY, localZ) {
        scale = positive(scale, 1, 'transition arrow model scale');
        const axis = transitionArrowAxis(direction);
        const rightX = axis.y, rightY = -axis.x;
        return {
            x: finite(rootX, 0, 'transition arrow root X')
                + (localX * rightX + localZ * axis.x) * scale,
            y: finite(rootY, 0, 'transition arrow root Y')
                + (localX * rightY + localZ * axis.y) * scale,
            // The OBJ's shaft radius is 0.22 world units. Its center must be
            // raised by that amount before the local vertical coordinate.
            z: finite(groundZ, 0, 'transition arrow ground Z')
                + (0.22 + localY) * scale
        };
    }
    ThestraWorldViewSemantics.transitionArrowWorldPoint = transitionArrowWorldPoint;
    function fovHalfExtentFromDegrees(degrees) {
        degrees = positive(degrees, 1, 'camera FOV degrees');
        if (degrees >= 179)
            throw new Error('camera FOV degrees must be < 179');
        return Math.tan(degrees * Math.PI / 360);
    }
    ThestraWorldViewSemantics.fovHalfExtentFromDegrees = fovHalfExtentFromDegrees;
    function resolveProjectionFrame(source) {
        const frame = source.projectionFrame || {};
        const targetWidth = positive(frame.targetWidth, 256, 'camera target width');
        const targetHeight = positive(frame.targetHeight, 240, 'camera target height');
        const compositionWidth = positive(frame.compositionWidth, 256, 'camera composition width');
        const canonicalCenterX = finite(frame.canonicalCenterX, compositionWidth * 0.5, 'camera canonical center X');
        const canonicalHorizonY = finite(frame.canonicalHorizonY, 70, 'camera canonical horizon Y');
        const square = source.squareAuthoringCamera === true;
        const baseViewportWidth = square ? targetWidth : compositionWidth;
        const baseViewportHeight = square ? targetHeight : 144;
        const defaultCenterX = square ? targetWidth * 0.5 : canonicalCenterX;
        const defaultCenterY = square ? targetHeight * 0.5 : canonicalHorizonY;
        const rawX = source.projectionWindowOffsetX === undefined
            ? (frame.projectionWindowOffsetX === undefined ? frame.offsetX : frame.projectionWindowOffsetX)
            : source.projectionWindowOffsetX;
        const rawY = source.projectionWindowOffsetY === undefined
            ? (frame.projectionWindowOffsetY === undefined ? frame.offsetY : frame.projectionWindowOffsetY)
            : source.projectionWindowOffsetY;
        const offsetX = finite(rawX, 0, 'camera projection window offset X');
        const offsetY = finite(rawY, 0, 'camera projection window offset Y');
        return {
            baseViewportWidth, baseViewportHeight,
            viewportCenterX: defaultCenterX + offsetX,
            viewportCenterY: defaultCenterY + offsetY,
            projectionWindowOffsetX: offsetX,
            projectionWindowOffsetY: offsetY
        };
    }
    ThestraWorldViewSemantics.resolveProjectionFrame = resolveProjectionFrame;
    function resolveTownCamera(source) {
        const target = source.target || {};
        const targetX = finite(target.x, 0, 'town camera target x');
        const targetY = finite(target.y, 0, 'town camera target y');
        const targetZ = finite(target.z, 0, 'town camera target z');
        const distance = positive(source.distance, 1, 'town camera distance');
        const angle = finite(source.yawDegrees, 0, 'town camera yaw degrees') * Math.PI / 180;
        const pitch = finite(source.pitchDegrees, 0, 'town camera pitch degrees') * Math.PI / 180;
        if (pitch <= -Math.PI / 2 || pitch >= Math.PI / 2) {
            throw new Error('town camera pitch must be between -90 and 90 degrees');
        }
        const dirX = Math.cos(angle), dirY = Math.sin(angle);
        const rightX = -dirY, rightY = dirX;
        const scale = source.projectionScale || {};
        const scaleX = positive(scale.x, 1, 'town camera projection scale x');
        const scaleY = positive(scale.y, 1, 'town camera projection scale y');
        const aspectY = source.squareAuthoringCamera === true ? 1 : 144 / 256;
        const framingScale = positive(source.focusOverride && source.focusOverride.fovScale, 1, 'town camera framing scale');
        const fovHalfX = fovHalfExtentFromDegrees(positive(source.fovDegrees, 28.072486935852957, 'town camera FOV degrees')) * framingScale;
        const fovHalfY = fovHalfX * aspectY;
        const cameraX = targetX - dirX * distance;
        const cameraY = targetY - dirY * distance;
        const cameraZ = targetZ + (source.eyeHeight === undefined
            ? distance * Math.tan(pitch) : finite(source.eyeHeight, 0, 'town camera eye height'));
        const cosPitch = Math.cos(pitch), sinPitch = Math.sin(pitch);
        const frame = resolveProjectionFrame(source);
        return {
            projection: 'perspective', profile: 'town_sideview',
            x: cameraX, y: cameraY, z: cameraZ,
            targetX, targetY, targetZ,
            playerLightX: targetX, playerLightY: targetY,
            fogMetric: 'ground_distance', fogOriginX: targetX, fogOriginY: targetY,
            focusDepth: distance, groundDistance: distance,
            angle, dirX, dirY, rightX, rightY, pitch,
            forwardX: dirX * cosPitch, forwardY: dirY * cosPitch, forwardZ: -sinPitch,
            upX: dirX * sinPitch, upY: dirY * sinPitch, upZ: cosPitch,
            fovScale: framingScale, fovHalfX, fovHalfY,
            orthoHalfX: 1, orthoHalfY: 1,
            projectionScaleX: scaleX, projectionScaleY: scaleY,
            nearPlane: positive(source.nearPlane, 0.05, 'town camera near plane'),
            farPlane: positive(source.farPlane, 128, 'town camera far plane'),
            visibilityProfile: source.visibilityProfile || 'play-overhead',
            baseViewportWidth: frame.baseViewportWidth,
            baseViewportHeight: frame.baseViewportHeight,
            viewportCenterX: frame.viewportCenterX,
            viewportCenterY: frame.viewportCenterY,
            projectionWindowOffsetX: frame.projectionWindowOffsetX,
            projectionWindowOffsetY: frame.projectionWindowOffsetY
        };
    }
    ThestraWorldViewSemantics.resolveTownCamera = resolveTownCamera;
    function projectionCoefficients(camera, opticalScale, extraOffsetX, extraOffsetY) {
        opticalScale = positive(opticalScale, 1, 'camera optical scale');
        const baseWidth = positive(camera.baseViewportWidth, 256, 'camera base viewport width');
        const baseHeight = positive(camera.baseViewportHeight, 144, 'camera base viewport height');
        const centerX = finite(camera.viewportCenterX, baseWidth * 0.5, 'camera viewport center X') + extraOffsetX;
        const centerY = finite(camera.viewportCenterY, baseHeight * 0.5, 'camera viewport center Y') + extraOffsetY;
        const horizontalExtent = camera.projection === 'orthographic'
            ? positive(camera.orthoHalfX, 1, 'camera ortho half X')
            : positive(camera.fovHalfX, 0.75, 'camera FOV half X') * opticalScale;
        const verticalExtent = camera.projection === 'orthographic'
            ? positive(camera.orthoHalfY, 1, 'camera ortho half Y') * opticalScale
            : positive(camera.fovHalfY, 0.421875, 'camera FOV half Y') * opticalScale;
        return {
            xScale: positive(camera.projectionScaleX, 1, 'camera projection scale X') / horizontalExtent,
            yScale: positive(camera.projectionScaleY, 1, 'camera projection scale Y') / verticalExtent,
            centerNdcX: centerX * 2 / baseWidth - 1,
            centerNdcY: centerY * 2 / baseHeight - 1
        };
    }
    ThestraWorldViewSemantics.projectionCoefficients = projectionCoefficients;
    function panProjectionWindow(offsetX, offsetY, dragPixelsX, dragPixelsY, displayWidth, displayHeight, baseWidth, baseHeight) {
        displayWidth = positive(displayWidth, 1, 'camera navigation display width');
        displayHeight = positive(displayHeight, 1, 'camera navigation display height');
        return {
            x: offsetX + dragPixelsX * baseWidth / displayWidth,
            // Match the shared screen-plane policy: dragging the viewport
            // down carries its composition down, whether it is a plate or a
            // perspective environment.  The perspective projection adapter
            // owns the clip-space inversion, so it does not belong here.
            y: offsetY + dragPixelsY * baseHeight / displayHeight
        };
    }
    ThestraWorldViewSemantics.panProjectionWindow = panProjectionWindow;
    function opticalScaleAfterWheel(current, deltaY) {
        current = positive(current, 1, 'camera optical scale');
        return clamp(current * Math.exp(deltaY * 0.0015), 0.125, 8);
    }
    ThestraWorldViewSemantics.opticalScaleAfterWheel = opticalScaleAfterWheel;
    // Studio zoom is an optical change to the same projection window the
    // runtime uses.  Keep the point below the cursor stationary while the
    // scale changes by solving the new principal-point offset from the old
    // projection coefficients.  This is an interaction adapter, not a second
    // camera: both hosts continue to consume `projectionCoefficients`.
    function zoomProjectionWindowAtCursor(camera, currentScale, offsetX, offsetY, deltaY, cursorX, cursorY, displayWidth, displayHeight) {
        const scale = opticalScaleAfterWheel(currentScale, deltaY);
        displayWidth = positive(displayWidth, 1, 'camera navigation display width');
        displayHeight = positive(displayHeight, 1, 'camera navigation display height');
        const baseWidth = positive(camera.baseViewportWidth, 256, 'camera base viewport width');
        const baseHeight = positive(camera.baseViewportHeight, 144, 'camera base viewport height');
        const currentX = finite(camera.viewportCenterX, baseWidth * 0.5, 'camera viewport center X') + offsetX;
        const currentY = finite(camera.viewportCenterY, baseHeight * 0.5, 'camera viewport center Y') + offsetY;
        const currentCenterNdcX = currentX * 2 / baseWidth - 1;
        const currentCenterNdcY = currentY * 2 / baseHeight - 1;
        const cursorNdcX = (cursorX / displayWidth) * 2 - 1;
        // Cursor Y is DOM screen space while the camera projection is Y-up.
        const cursorNdcY = 1 - (cursorY / displayHeight) * 2;
        const ratio = currentScale / scale;
        const nextCenterNdcX = ratio * currentCenterNdcX + (ratio - 1) * cursorNdcX;
        const nextCenterNdcY = ratio * currentCenterNdcY + (ratio - 1) * cursorNdcY;
        return {
            scale,
            x: (nextCenterNdcX + 1) * baseWidth * 0.5
                - finite(camera.viewportCenterX, baseWidth * 0.5, 'camera viewport center X'),
            y: (nextCenterNdcY + 1) * baseHeight * 0.5
                - finite(camera.viewportCenterY, baseHeight * 0.5, 'camera viewport center Y')
        };
    }
    ThestraWorldViewSemantics.zoomProjectionWindowAtCursor = zoomProjectionWindowAtCursor;
    function trackedProjectionOffset(laneY, centerY, pixelsPerWorld, minimum, maximum) {
        return clamp(-(laneY - centerY) * pixelsPerWorld, minimum, maximum);
    }
    ThestraWorldViewSemantics.trackedProjectionOffset = trackedProjectionOffset;
    function projectPerspective(camera, targetWidth, targetHeight, worldX, worldY, worldZ) {
        const relativeX = worldX - camera.x, relativeY = worldY - camera.y;
        const depth = relativeX * camera.dirX + relativeY * camera.dirY;
        const horizontal = relativeX * camera.rightX + relativeY * camera.rightY;
        const vertical = worldZ - camera.z;
        const cosPitch = Math.cos(camera.pitch || 0), sinPitch = Math.sin(camera.pitch || 0);
        const pitchedDepth = depth * cosPitch - vertical * sinPitch;
        const pitchedVertical = vertical * cosPitch + depth * sinPitch;
        const safeDepth = Math.max(pitchedDepth, 0.001);
        const ndcX = camera.viewportCenterX * 2 / targetWidth - 1
            + horizontal / (camera.fovHalfX * safeDepth) * camera.projectionScaleX
                * (camera.baseViewportWidth / targetWidth);
        const ndcY = camera.viewportCenterY * 2 / targetHeight - 1
            + pitchedVertical / (camera.fovHalfY * safeDepth) * camera.projectionScaleY
                * (camera.baseViewportHeight / targetHeight);
        return { x: (ndcX + 1) * targetWidth * 0.5, y: (1 - ndcY) * targetHeight * 0.5, depth: safeDepth };
    }
    ThestraWorldViewSemantics.projectPerspective = projectPerspective;
    function groundHeight(profile, fallbackZ, laneY) {
        if (!profile || profile.length === 0)
            return fallbackZ;
        if (laneY <= profile[0].y)
            return profile[0].z;
        for (let index = 1; index < profile.length; index++) {
            const previous = profile[index - 1], current = profile[index];
            if (laneY <= current.y) {
                const span = current.y - previous.y;
                if (span <= 0)
                    return current.z;
                const amount = (laneY - previous.y) / span;
                return previous.z + (current.z - previous.z) * amount;
            }
        }
        return profile[profile.length - 1].z;
    }
    ThestraWorldViewSemantics.groundHeight = groundHeight;
    function horizontalProjection(camera, width, height, depthX, groundZ, sliceY, centerX) {
        const base = projectPerspective(camera, width, height, depthX, sliceY, groundZ);
        const p0 = projectPerspective(camera, width, height, depthX, 0, groundZ);
        const p1 = projectPerspective(camera, width, height, depthX, 1, groundZ);
        const x0 = centerX + p0.x - base.x, x1 = centerX + p1.x - base.x;
        return [x1 * p1.depth - x0 * p0.depth, x0 * p0.depth, p1.depth - p0.depth, p0.depth];
    }
    ThestraWorldViewSemantics.horizontalProjection = horizontalProjection;
    function worldYAtScreenX(projection, screenX) {
        if (projection.length !== 4)
            throw new Error('Invalid resolved horizontal projection.');
        const denominator = screenX * projection[2] - projection[0];
        if (Math.abs(denominator) < 1e-10)
            throw new Error('Event projection cannot be inverted at this position.');
        return (projection[1] - screenX * projection[3]) / denominator;
    }
    ThestraWorldViewSemantics.worldYAtScreenX = worldYAtScreenX;
})(ThestraWorldViewSemantics || (ThestraWorldViewSemantics = {}));
// THES_SHARED_COMMONJS_WORLD_VIEW: generated host adapter; do not edit.
if (typeof module === 'object' && module.exports) module.exports = ThestraWorldViewSemantics;
