import * as THREE from 'three';
import { OrbitControls } from '/vendor/three/OrbitControls.js';
import { createThreeEditorViewport as createBaseViewport } from '/js/three-editor-viewport-base.js';
import '/js/world-presentation.js';
import '/js/world-presentation-studio.js';
import '/js/scene-timing-authoring.js';
import '/js/scene-timing-studio.js';

function copyVector(vector) {
    return [vector.x, vector.y, vector.z];
}

function copyQuaternion(quaternion) {
    return [quaternion.x, quaternion.y, quaternion.z, quaternion.w];
}

function restoreVector(vector, values) {
    vector.set(values[0], values[1], values[2]);
}

function restoreQuaternion(quaternion, values) {
    quaternion.set(values[0], values[1], values[2], values[3]);
}

function cameraState(camera, controls) {
    const state = {
        position: copyVector(camera.position),
        quaternion: copyQuaternion(camera.quaternion),
        up: copyVector(camera.up),
        target: copyVector(controls.target),
        enabled: controls.enabled,
        zoom: camera.zoom
    };
    if (camera.isPerspectiveCamera) {
        state.fov = camera.fov;
        state.aspect = camera.aspect;
        state.near = camera.near;
        state.far = camera.far;
    } else {
        state.left = camera.left;
        state.right = camera.right;
        state.top = camera.top;
        state.bottom = camera.bottom;
        state.near = camera.near;
        state.far = camera.far;
    }
    return state;
}

function restoreCamera(camera, controls, state) {
    restoreVector(camera.position, state.position);
    restoreQuaternion(camera.quaternion, state.quaternion);
    restoreVector(camera.up, state.up);
    restoreVector(controls.target, state.target);
    camera.zoom = state.zoom;
    camera.near = state.near;
    camera.far = state.far;
    if (camera.isPerspectiveCamera) {
        camera.fov = state.fov;
        camera.aspect = state.aspect;
    } else {
        camera.left = state.left;
        camera.right = state.right;
        camera.top = state.top;
        camera.bottom = state.bottom;
    }
    camera.updateProjectionMatrix();
    controls.enabled = state.enabled;
    controls.update();
}

function runtimeKey(event) {
    return event.code === 'Home' || event.code.startsWith('Numpad');
}

export function createThreeEditorViewport(container, options = {}) {
    // The original viewport intentionally kept camera implementation private.
    // #619 needs an adapter without forking the semantic scene or renderer.
    // Capture the two OrbitControls instances while the existing viewport is
    // constructed; controls publicly own the authoring cameras and targets.
    const controlsCreated = [];
    const nativeOrbitUpdate = OrbitControls.prototype.update;
    OrbitControls.prototype.update = function () {
        if (!controlsCreated.includes(this)) controlsCreated.push(this);
        return nativeOrbitUpdate.apply(this, arguments);
    };

    let base;
    try {
        base = createBaseViewport(container, options);
    } finally {
        OrbitControls.prototype.update = nativeOrbitUpdate;
    }

    const perspectiveControls = controlsCreated.find(controls => controls.object && controls.object.isPerspectiveCamera);
    const orthographicControls = controlsCreated.find(controls => controls.object && controls.object.isOrthographicCamera);
    if (!perspectiveControls || !orthographicControls) {
        base.dispose();
        throw new Error('Runtime camera adapter could not resolve the authoring cameras.');
    }
    const perspective = perspectiveControls.object;
    const orthographic = orthographicControls.object;
    let runtimeProjection = null;
    let runtimeLocked = false;
    let lastRuntimeCamera = null;

    const nativePerspectiveProjection = perspective.updateProjectionMatrix.bind(perspective);
    perspective.updateProjectionMatrix = function () {
        if (runtimeProjection && runtimeProjection.projection === 'perspective') {
            // Runtime #617 defines horizontal FOV and a 256:144 projection
            // calibration. The Studio preview is letterboxed to that aspect by
            // world-presentation-studio.js, so preserve the exact semantic
            // horizontal/vertical half extents here rather than inventing a
            // monitor-pixel zoom rule.
            perspective.aspect = runtimeProjection.fovHalfX / runtimeProjection.fovHalfY;
            perspective.fov = THREE.MathUtils.radToDeg(2 * Math.atan(runtimeProjection.fovHalfY));
        }
        nativePerspectiveProjection();
        if (runtimeProjection && runtimeProjection.projection === 'perspective') {
            perspective.projectionMatrix.elements[0] *= runtimeProjection.projectionScaleX || 1;
            perspective.projectionMatrix.elements[5] *= runtimeProjection.projectionScaleY || 1;
            perspective.projectionMatrixInverse.copy(perspective.projectionMatrix).invert();
        }
    };

    const nativeOrthographicProjection = orthographic.updateProjectionMatrix.bind(orthographic);
    orthographic.updateProjectionMatrix = function () {
        if (runtimeProjection && runtimeProjection.projection === 'orthographic') {
            orthographic.left = -runtimeProjection.orthoHalfX;
            orthographic.right = runtimeProjection.orthoHalfX;
            orthographic.top = runtimeProjection.orthoHalfY;
            orthographic.bottom = -runtimeProjection.orthoHalfY;
            orthographic.zoom = 1;
        }
        nativeOrthographicProjection();
        if (runtimeProjection && runtimeProjection.projection === 'orthographic') {
            orthographic.projectionMatrix.elements[0] *= runtimeProjection.projectionScaleX || 1;
            orthographic.projectionMatrix.elements[5] *= runtimeProjection.projectionScaleY || 1;
            orthographic.projectionMatrixInverse.copy(orthographic.projectionMatrix).invert();
        }
    };

    function captureCameraState() {
        return {
            mode: base.getMode(),
            viewState: base.getViewState(),
            perspective: cameraState(perspective, perspectiveControls),
            orthographic: cameraState(orthographic, orthographicControls)
        };
    }

    function applyResolvedCamera(resolved) {
        if (!resolved) throw new Error('Resolved runtime camera is required.');
        runtimeProjection = resolved;
        const mode = resolved.projection === 'orthographic' ? 'top' : 'perspective';
        base.setMode(mode);
        const camera = mode === 'top' ? orthographic : perspective;
        const controls = mode === 'top' ? orthographicControls : perspectiveControls;
        camera.position.set(resolved.x, resolved.z, resolved.y);
        controls.target.set(resolved.targetX, resolved.targetZ, resolved.targetY);
        camera.up.set(0, 1, 0);
        camera.near = 0.05;
        camera.far = resolved.projection === 'perspective' && resolved.focusDepth
            ? Math.max(64, resolved.focusDepth * 2) : 32;
        camera.lookAt(controls.target);
        camera.updateProjectionMatrix();
        perspectiveControls.enabled = false;
        orthographicControls.enabled = false;
        controls.update();
    }

    function applyRuntimeCamera(resolved) {
        runtimeLocked = true;
        lastRuntimeCamera = resolved;
        applyResolvedCamera(resolved);
        // If the author entered preview during an in-flight free-camera easing,
        // the private base transition can finish after this call. Re-assert the
        // semantic camera once after that bounded animation window.
        setTimeout(() => {
            if (runtimeLocked && lastRuntimeCamera === resolved) applyResolvedCamera(resolved);
        }, 240);
    }

    function restoreCameraState(snapshot) {
        if (!snapshot) return;
        runtimeLocked = false;
        lastRuntimeCamera = null;
        runtimeProjection = null;
        base.setMode(snapshot.mode);
        restoreCamera(perspective, perspectiveControls, snapshot.perspective);
        restoreCamera(orthographic, orthographicControls, snapshot.orthographic);
    }

    const canvas = container.querySelector('canvas');
    function suppressRuntimeNavigation(event) {
        if (!runtimeLocked || !runtimeKey(event)) return;
        event.preventDefault();
        event.stopImmediatePropagation();
    }
    if (canvas) canvas.addEventListener('keydown', suppressRuntimeNavigation, true);

    const rawSetMode = base.setMode;
    const rawTransitionToMode = base.transitionToMode;
    const rawDispose = base.dispose;
    const api = Object.assign({}, base, {
        setMode(mode) {
            if (runtimeLocked) return;
            return rawSetMode(mode);
        },
        transitionToMode(mode) {
            if (runtimeLocked) return Promise.resolve();
            return rawTransitionToMode(mode);
        },
        captureCameraState,
        applyRuntimeCamera,
        restoreCameraState,
        isRuntimeCameraPreview: () => runtimeLocked,
        dispose() {
            runtimeLocked = false;
            runtimeProjection = null;
            if (canvas) canvas.removeEventListener('keydown', suppressRuntimeNavigation, true);
            if (globalThis.ThestraRuntimeCameraViewport === api) delete globalThis.ThestraRuntimeCameraViewport;
            rawDispose();
        }
    });
    globalThis.ThestraRuntimeCameraViewport = api;
    window.dispatchEvent(new CustomEvent('thestra-runtime-camera-viewport-ready'));
    return api;
}
