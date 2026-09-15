import * as THREE from 'three';
import { createThreeEditorViewport as createBaseViewport } from '/js/three-editor-viewport-base.js';
import '/js/world-presentation.js';
import '/js/world-presentation-studio.js';
import { createCompositionViewport } from '/js/three-composition-viewport.js';
import '/js/scene-timing-authoring.js';
import '/js/scene-timing-studio.js';
import '/js/spatial-interaction.js';

const View = globalThis.ThestraWorldViewSemantics;
if (!View) throw new Error('Generated shared world-view semantics failed to load.');
const SpatialInteraction = globalThis.ThestraSpatialInteraction;
if (!SpatialInteraction) throw new Error('Shared spatial interaction core failed to load.');

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
    const opticalSlot = { current: null };
    const spatialInteraction = SpatialInteraction.createState(snapshot => {
        options.onSpatialStateChange?.(snapshot);
    });
    function emitSelection(selection) {
        spatialInteraction.setSelection(selection);
        options.onSelection?.(selection);
    }
    function syncSelectionViews(snapshot) {
        base?.setSelection?.(snapshot.selection || null);
        compositionAuthoring?.setSemanticSelection?.(snapshot.selection || null);
        options.onSelection?.(snapshot.selection || null);
        return snapshot;
    }
    function toggleSpatialSelection(selection) {
        return syncSelectionViews(spatialInteraction.toggleSelection(selection));
    }
    function setSpatialSelectionSet(selections, activeSelection) {
        return syncSelectionViews(spatialInteraction.setSelectionSet(selections, activeSelection));
    }
    const base = createBaseViewport(container, {
        ...options,
        spatialInteraction,
        onSelection: emitSelection,
        onToggleSelection: toggleSpatialSelection,
        getOpticalNavigation: () => opticalSlot.current?.active() ? opticalSlot.current : null
    });
    const cameraRig = base.getCameraRig?.();
    const perspectiveControls = cameraRig?.perspective?.controls;
    const orthographicControls = cameraRig?.orthographic?.controls;
    if (!perspectiveControls || !orthographicControls
            || !cameraRig.perspective.camera || !cameraRig.orthographic.camera) {
        base.dispose();
        throw new Error('Runtime camera adapter could not resolve the authoring cameras.');
    }
    const perspective = cameraRig.perspective.camera;
    const orthographic = cameraRig.orthographic.camera;
    let runtimeProjection = null;
    let runtimeLocked = false;
    let lastRuntimeCamera = null;
    let opticalState = { x: 0, y: 0, scale: 1 };

    const nativePerspectiveProjection = perspective.updateProjectionMatrix.bind(perspective);
    perspective.updateProjectionMatrix = function () {
        nativePerspectiveProjection();
        if (runtimeProjection && runtimeProjection.projection === 'perspective') {
            const projection = View.projectionCoefficients(runtimeProjection,
                opticalState.scale, opticalState.x, opticalState.y);
            perspective.projectionMatrix.elements[0] = projection.xScale;
            perspective.projectionMatrix.elements[5] = projection.yScale;
            perspective.projectionMatrix.elements[8] = -projection.centerNdcX;
            // Shared semantics expresses Y in screen space (down is positive);
            // Three's clip-space Y points up, and perspective divides this
            // matrix column by -cameraZ.
            perspective.projectionMatrix.elements[9] = projection.centerNdcY;
            perspective.projectionMatrixInverse.copy(perspective.projectionMatrix).invert();
        }
    };

    const nativeOrthographicProjection = orthographic.updateProjectionMatrix.bind(orthographic);
    orthographic.updateProjectionMatrix = function () {
        if (runtimeProjection && runtimeProjection.projection === 'orthographic') {
            orthographic.left = -1;
            orthographic.right = 1;
            orthographic.top = 1;
            orthographic.bottom = -1;
            orthographic.zoom = 1;
        }
        nativeOrthographicProjection();
        if (runtimeProjection && runtimeProjection.projection === 'orthographic') {
            const projection = View.projectionCoefficients(runtimeProjection,
                opticalState.scale, opticalState.x, opticalState.y);
            orthographic.projectionMatrix.elements[0] = projection.xScale;
            orthographic.projectionMatrix.elements[5] = projection.yScale;
            orthographic.projectionMatrix.elements[12] = projection.centerNdcX;
            orthographic.projectionMatrix.elements[13] = -projection.centerNdcY;
            orthographic.projectionMatrixInverse.copy(orthographic.projectionMatrix).invert();
        }
    };

    function captureCameraState() {
        return {
            mode: base.getMode(),
            viewState: base.getViewState(),
            perspective: cameraState(perspective, perspectiveControls),
            orthographic: cameraState(orthographic, orthographicControls),
            projection: runtimeProjection,
            optical: { ...opticalState }
        };
    }

    function applyResolvedCamera(resolved) {
        if (!resolved) throw new Error('Resolved runtime camera is required.');
        runtimeProjection = resolved;
        const mode = resolved.projection === 'orthographic' ? 'top' : 'perspective';
        base.setMode(mode);
        const camera = mode === 'top' ? orthographic : perspective;
        const controls = mode === 'top' ? orthographicControls : perspectiveControls;
        const runtimeCoordinates = resolved === spatialCamera;
        const position = runtimeCoordinates
            ? globalThis.ThestraViewportContract.runtimePositionToThestra([resolved.x, resolved.y, resolved.z])
            : [resolved.x, resolved.z, resolved.y];
        camera.position.fromArray(position);

        if (Number.isFinite(resolved.forwardX) && Number.isFinite(resolved.forwardY)
                && Number.isFinite(resolved.forwardZ) && Number.isFinite(resolved.upX)
                && Number.isFinite(resolved.upY) && Number.isFinite(resolved.upZ)) {
            // The runtime camera target is an optical anchor. It does not
            // define the view direction when eyeHeight and pitch are authored
            // independently. Build the Three camera frame from the same
            // direction and pitch basis used by the runtime projector.
            const forward = new THREE.Vector3(
                resolved.forwardX,
                resolved.forwardZ,
                resolved.forwardY
            );
            const up = new THREE.Vector3(
                resolved.upX,
                resolved.upZ,
                resolved.upY
            );
            const focusDepth = Number.isFinite(resolved.focusDepth) && resolved.focusDepth > 0
                ? resolved.focusDepth : 1;
            camera.up.copy(up);
            controls.target.copy(camera.position).addScaledVector(forward, focusDepth);
        } else {
            const target = runtimeCoordinates
                ? globalThis.ThestraViewportContract.runtimePositionToThestra([
                    resolved.targetX, resolved.targetY, resolved.targetZ
                ])
                : [resolved.targetX, resolved.targetZ, resolved.targetY];
            camera.up.set(0, 1, 0);
            controls.target.fromArray(target);
        }
        camera.near = resolved.nearPlane || 0.05;
        camera.far = resolved.farPlane || (resolved.projection === 'perspective' && resolved.focusDepth
            ? Math.max(64, resolved.focusDepth * 2) : 32);
        camera.lookAt(controls.target);
        camera.updateProjectionMatrix();
        perspectiveControls.enabled = !runtimeLocked;
        orthographicControls.enabled = !runtimeLocked;
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
        compositionAuthoring.hide();
        if (!snapshot) return;
        runtimeLocked = false;
        lastRuntimeCamera = null;
        runtimeProjection = snapshot.projection || null;
        opticalState = snapshot.optical || { x: 0, y: 0, scale: 1 };
        base.setMode(snapshot.mode);
        restoreCamera(perspective, perspectiveControls, snapshot.perspective);
        restoreCamera(orthographic, orthographicControls, snapshot.orthographic);
    }

    const canvas = container.querySelector('canvas');
    const compositionAuthoring = createCompositionViewport(container, {
        ...options,
        spatialInteraction,
        onSelection(selection) { base.setSelection(selection); emitSelection(selection); },
        onToggleSelection: toggleSpatialSelection
    });
    const compositionCanvas = compositionAuthoring.getCanvas?.() || null;
    opticalSlot.current = {
        // Runtime preview fixes the camera pose, but its projection window is
        // still the in-game camera's pan/zoom surface.  Do not make a locked
        // pose swallow that authored navigation.
        active: () => !!runtimeProjection && !compositionAuthoring.isPlate(),
        pan(dx, dy, rect) {
            if (!runtimeProjection || compositionAuthoring.isPlate()) return;
            const next = View.panProjectionWindow(opticalState.x, opticalState.y, dx, dy,
                Math.max(1, rect.width), Math.max(1, rect.height),
                runtimeProjection.baseViewportWidth || 256,
                runtimeProjection.baseViewportHeight || 144);
            opticalState.x = next.x; opticalState.y = next.y;
            (runtimeProjection.projection === 'orthographic' ? orthographic : perspective).updateProjectionMatrix();
        },
        zoom(deltaY, cursorX, cursorY, rect) {
            if (!runtimeProjection || compositionAuthoring.isPlate()) return;
            const next = View.zoomProjectionWindowAtCursor(runtimeProjection,
                opticalState.scale, opticalState.x, opticalState.y, deltaY,
                cursorX, cursorY, Math.max(1, rect?.width || 1), Math.max(1, rect?.height || 1));
            opticalState = next;
            (runtimeProjection.projection === 'orthographic' ? orthographic : perspective).updateProjectionMatrix();
        }
    };
    function suppressRuntimeNavigation(event) {
        if (!runtimeLocked || !runtimeKey(event)) return;
        event.preventDefault();
        event.stopImmediatePropagation();
    }
    if (canvas) canvas.addEventListener('keydown', suppressRuntimeNavigation, true);

    const rawSetMode = base.setMode;
    const rawTransitionToMode = base.transitionToMode;
    const rawDispose = base.dispose;
    let spatialCamera = null;
    let compositionFrameId = 'authoring/map';
    let currentSceneModel = null;
    const api = Object.assign({}, base, {
        async setSceneModel(model) {
            currentSceneModel = model;
            base.setSceneModel(model);
            await compositionAuthoring.setSceneModel(model);
            window.dispatchEvent(new CustomEvent('thestra-composition-preview-ready'));
        },
        setSelection(selection) {
            base.setSelection(selection);
            compositionAuthoring.setSemanticSelection(selection);
            spatialInteraction.setSelection(selection);
        },
        getSpatialInteractionState: () => spatialInteraction.snapshot(),
        getWalkProfileSelections: () => spatialInteraction.snapshot().selectionSet.filter(selection =>
            selection?.kind === 'walk-profile-point' || selection?.kind === 'walk-profile-segment'),
        setRenderableBundle(bundle) {
            spatialCamera = bundle && bundle.spatialCamera || null;
            // An environment bundle has a resolved runtime camera.  Letting
            // the base viewport additionally frame collision bounds starts an
            // asynchronous generic camera transition which overwrites that
            // exact basis a frame later.  The runtime adapter owns initial
            // framing whenever this authoritative record is present.
            const result = base.setRenderableBundle(bundle, { preserveCamera: !!spatialCamera });
            if (spatialCamera && !compositionAuthoring.isPlate() && !runtimeLocked) {
                opticalState = { x: 0, y: 0, scale: 1 };
                applyResolvedCamera(spatialCamera);
            }
            return result;
        },
        getSpatialCamera: () => spatialCamera,
        getCompositionPreview: () => compositionAuthoring.descriptor(),
        getCompositionFrame: () => compositionAuthoring.descriptor()?.frames.find(frame => frame.id === compositionFrameId),
        isPlateComposition: () => compositionAuthoring.isPlate(),
        setWalkMeshVisible(visible) {
            if (compositionAuthoring.isPlate()) compositionAuthoring.setWalkMeshVisible(visible);
            else base.setCollisionVisible(visible);
        },
        getWalkMeshVisible() {
            return compositionAuthoring.isPlate()
                ? compositionAuthoring.getWalkMeshVisible()
                : base.getCollisionVisible();
        },
        setWalkProfileEditing(enabled) {
            const active = !!enabled;
            if (active) api.setWalkMeshVisible(false);
            base.setWalkProfileEditing?.(active);
            compositionAuthoring.setWalkProfileEditing?.(active);
            if (!active) emitSelection(null);
        },
        getWalkProfileEditing() {
            return compositionAuthoring.isVisible?.()
                ? !!compositionAuthoring.getWalkProfileEditing?.()
                : !!base.getWalkProfileEditing?.();
        },
        setWalkProfileComponentMode(mode) {
            base.setWalkProfileComponentMode?.(mode);
            compositionAuthoring.setWalkProfileComponentMode?.(mode);
        },
        getWalkProfileComponentMode() {
            return compositionAuthoring.isVisible?.()
                ? compositionAuthoring.getWalkProfileComponentMode?.() || 'point'
                : base.getWalkProfileComponentMode?.() || 'point';
        },
        getWalkProfileSelection() {
            return compositionAuthoring.isVisible?.()
                ? compositionAuthoring.getWalkProfileSelection?.() || null
                : base.getWalkProfileSelection?.() || null;
        },
        getWalkProfileStatus() {
            const traversal = currentSceneModel?.map?.source?.traversal;
            const lane = traversal?.provider === 'bounded_lane' ? traversal.lane : null;
            const profile = lane?.groundProfile;
            const selection = api.getWalkProfileSelection();
            const selections = api.getWalkProfileSelections();
            const activePoint = selection?.kind === 'walk-profile-point'
                && Array.isArray(profile) && profile[selection.index]
                ? {
                    index: selection.index,
                    y: Number(profile[selection.index].y),
                    z: Number(profile[selection.index].z)
                } : null;
            const interaction = spatialInteraction.snapshot();
            return {
                available: !!lane,
                authored: Array.isArray(profile) && profile.length >= 2,
                pointCount: Array.isArray(profile) ? profile.length : 0,
                editing: api.getWalkProfileEditing(),
                componentMode: api.getWalkProfileComponentMode(),
                selection,
                selections,
                selectionCount: selections.length,
                activePoint,
                operation: interaction.operation,
                constraint: interaction.constraint,
                feedback: interaction.feedback
            };
        },
        createGroundProfile() {
            const result = options.onCreateGroundProfile?.();
            if (result?.changed) {
                base.refreshWalkProfile?.();
                compositionAuthoring.refreshWalkProfile?.();
            }
            if (result?.selection) api.setSelection(result.selection);
            return result;
        },
        setSelectedGroundProfilePoint(y, z) {
            const selection = api.getWalkProfileSelection();
            if (!selection || selection.kind !== 'walk-profile-point') {
                return { ok: false, reason: 'no-profile-point-selected' };
            }
            const result = options.onMoveGroundProfilePoint?.(selection.index, Number(y), Number(z));
            if (result?.changed) {
                base.refreshWalkProfile?.();
                compositionAuthoring.refreshWalkProfile?.();
            }
            if (result?.selection) api.setSelection(result.selection);
            return result;
        },
        splitSelectedGroundProfileSegment(amount = 0.5) {
            const selection = api.getWalkProfileSelection();
            if (!selection || selection.kind !== 'walk-profile-segment') {
                return { ok: false, reason: 'no-profile-segment-selected' };
            }
            const result = options.onSplitGroundProfileSegment?.(selection.index, amount);
            if (result?.changed) {
                base.refreshWalkProfile?.();
                compositionAuthoring.refreshWalkProfile?.();
            }
            if (result?.selection) api.setSelection(result.selection);
            return result;
        },
        subdivideSelectedGroundProfileSegments(cuts = 1) {
            const segments = api.getWalkProfileSelections()
                .filter(selection => selection.kind === 'walk-profile-segment')
                .map(selection => selection.index);
            if (!segments.length) return { ok: false, reason: 'no-profile-segment-selected' };
            const result = options.onSubdivideGroundProfileSegments?.(segments, cuts);
            if (result?.changed) {
                base.refreshWalkProfile?.();
                compositionAuthoring.refreshWalkProfile?.();
            }
            if (result?.selections?.length) {
                setSpatialSelectionSet(result.selections, result.selection);
            } else if (result?.selection) {
                api.setSelection(result.selection);
            }
            return result;
        },
        extrudeSelectedGroundProfileEndpoint(y, z) {
            const selection = api.getWalkProfileSelection();
            if (!selection || selection.kind !== 'walk-profile-point') {
                return { ok: false, reason: 'no-profile-point-selected' };
            }
            const result = options.onExtrudeGroundProfileEndpoint?.(selection.index, y, z);
            if (result?.changed) {
                base.refreshWalkProfile?.();
                compositionAuthoring.refreshWalkProfile?.();
            }
            if (result?.selection) api.setSelection(result.selection);
            return result;
        },
        beginSelectedGroundProfileExtrude() {
            const editor = compositionAuthoring.isVisible?.() ? compositionAuthoring : base;
            return editor.beginWalkProfileExtrude?.()
                || { ok: false, reason: 'no-profile-point-selected' };
        },
        moveGroundProfilePoints(pointIndices, deltaY, deltaZ) {
            const result = options.onMoveGroundProfilePoints?.(pointIndices, deltaY, deltaZ);
            if (result?.changed) {
                base.refreshWalkProfile?.();
                compositionAuthoring.refreshWalkProfile?.();
            }
            if (result?.selections?.length) {
                setSpatialSelectionSet(result.selections, result.selection);
            } else if (result?.selection) {
                api.setSelection(result.selection);
            }
            return result;
        },
        deleteGroundProfilePoints(pointIndices) {
            const result = options.onDeleteGroundProfilePoints?.(pointIndices);
            if (result?.changed) {
                base.refreshWalkProfile?.();
                compositionAuthoring.refreshWalkProfile?.();
            }
            if (result?.selection) api.setSelection(result.selection);
            return result;
        },
        deleteSelectedGroundProfilePoints() {
            const indices = api.getWalkProfileSelections()
                .filter(selection => selection.kind === 'walk-profile-point')
                .map(selection => selection.index);
            if (!indices.length) return { ok: false, reason: 'no-profile-point-selected' };
            return api.deleteGroundProfilePoints(indices);
        },
        selectAllWalkProfileComponents() {
            const status = api.getWalkProfileStatus();
            if (!status.authored || !status.editing) return null;
            const selections = [];
            if (status.componentMode === 'segment') {
                for (let index = 0; index < Math.max(0, status.pointCount - 1); index++) {
                    selections.push({
                        kind: 'walk-profile-segment',
                        key: `walk-profile-segment:${index}`,
                        index
                    });
                }
            } else {
                for (let index = 0; index < status.pointCount; index++) {
                    selections.push({
                        kind: 'walk-profile-point',
                        key: `walk-profile-point:${index}`,
                        index
                    });
                }
            }
            return setSpatialSelectionSet(selections, selections[selections.length - 1] || null);
        },
        deleteSelectedGroundProfilePoint() {
            const selection = api.getWalkProfileSelection();
            if (!selection || selection.kind !== 'walk-profile-point') {
                return { ok: false, reason: 'no-profile-point-selected' };
            }
            const result = options.onDeleteGroundProfilePoint?.(selection.index);
            if (result?.changed) {
                base.refreshWalkProfile?.();
                compositionAuthoring.refreshWalkProfile?.();
            }
            if (result?.selection) api.setSelection(result.selection);
            return result;
        },
        showComposition(frameId) {
            const frame = compositionAuthoring.descriptor()?.frames.find(candidate => candidate.id === frameId);
            if (!frame) throw new Error(`Plate composition unavailable: ${frameId}`);
            compositionFrameId = frameId;
            compositionAuthoring.show();
        },
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
            compositionAuthoring.dispose();
            runtimeLocked = false;
            runtimeProjection = null;
            opticalSlot.current = null;
            if (canvas) {
                canvas.removeEventListener('keydown', suppressRuntimeNavigation, true);
                canvas.removeEventListener('keydown', onWalkProfileKeyDown);
            }
            if (compositionCanvas && compositionCanvas !== canvas) {
                compositionCanvas.removeEventListener('keydown', onWalkProfileKeyDown);
            }
            if (globalThis.ThestraRuntimeCameraViewport === api) delete globalThis.ThestraRuntimeCameraViewport;
            rawDispose();
        }
    });

    function rejectProfileAction(result) {
        if (result?.ok === false) spatialInteraction.reject(result.reason);
        return result;
    }

    function onWalkProfileKeyDown(event) {
        if (runtimeLocked || event.metaKey || event.altKey || event.ctrlKey) return;
        const status = api.getWalkProfileStatus();
        if (!status.available) return;

        if (event.code === 'Tab') {
            event.preventDefault();
            api.setWalkProfileEditing(!status.editing);
            return;
        }
        if (!status.editing) return;

        if (event.code === 'Digit1') {
            event.preventDefault();
            api.setWalkProfileComponentMode('point');
            return;
        }
        if (event.code === 'Digit2') {
            event.preventDefault();
            api.setWalkProfileComponentMode('segment');
            return;
        }
        if (event.code === 'KeyA') {
            event.preventDefault();
            api.selectAllWalkProfileComponents();
            return;
        }
        if (event.code === 'KeyE' && status.componentMode === 'point') {
            event.preventDefault();
            rejectProfileAction(api.beginSelectedGroundProfileExtrude());
            return;
        }
        if ((event.code === 'KeyX' || event.code === 'Delete')
                && status.componentMode === 'point') {
            event.preventDefault();
            rejectProfileAction(api.deleteSelectedGroundProfilePoints());
        }
    }

    if (canvas) canvas.addEventListener('keydown', onWalkProfileKeyDown);
    if (compositionCanvas && compositionCanvas !== canvas) {
        compositionCanvas.addEventListener('keydown', onWalkProfileKeyDown);
    }
    globalThis.ThestraRuntimeCameraViewport = api;
    window.dispatchEvent(new CustomEvent('thestra-runtime-camera-viewport-ready'));
    return api;
}
