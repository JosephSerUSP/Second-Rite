import * as THREE from 'three';
import { OrbitControls } from '/vendor/three/OrbitControls.js';
import { OBJLoader } from '/vendor/three/OBJLoader.js';
import { MTLLoader } from '/vendor/three/MTLLoader.js';
import { createSelectionOverlay, createEventBox, createMoveGizmo, configureEventSpriteFrame, installNavigation } from '/js/three-authoring-tools.js';
import '/js/composition-authoring.js';
import '/js/spatial-interaction.js';

const View = globalThis.ThestraCompositionAuthoring;
if (!View) throw new Error('Shared world-view semantics failed to load.');
const SpatialInteraction = globalThis.ThestraSpatialInteraction;
if (!SpatialInteraction) throw new Error('Shared spatial interaction core failed to load.');

function projectAsset(path) {
    return path.startsWith('/') ? path : '/' + path;
}

function resolvePackageAsset(manifestPath, relativePath) {
    const base = new URL(projectAsset(manifestPath), globalThis.location.href);
    return new URL(relativePath, base).pathname;
}

function nearestSlice(positions, lane) {
    const target = Number(lane?.runtimeCenterY);
    if (!Number.isFinite(target)) return Math.floor(positions.length / 2);
    let best = 0, distance = Infinity;
    for (let index = 0; index < positions.length; index++) {
        const next = Math.abs(Number(positions[index]) - target);
        if (next < distance) { best = index; distance = next; }
    }
    return best;
}

function sourceEvent(record) {
    return record?.source || record;
}

// Source-specific display adapter. It loads authored plate layers directly and
// uses the generated WorldCamera projection leaf for Event placement. No LÖVE
// render or screenshot participates in plate editing.
export function createCompositionViewport(container, options) {
    const layer = document.createElement('div');
    layer.style.cssText = 'display:none;position:absolute;inset:0;z-index:2;';
    layer.setAttribute('aria-label', 'Editable plate composition');
    container.appendChild(layer);
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(window.devicePixelRatio || 1);
    renderer.setClearColor(0x24282d);
    renderer.domElement.style.cssText = 'width:100%;height:100%;display:block;touch-action:none;';
    renderer.domElement.tabIndex = 0;
    renderer.domElement.setAttribute('aria-label', 'Plate map viewport; drag Events along the authored lane, world Y.');
    renderer.domElement.title = 'Plate Events move along the authored lane (world Y).';
    layer.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 5000);
    camera.position.z = 1000;
    const controls = new OrbitControls(camera, renderer.domElement);
    const overlay = createSelectionOverlay();
    scene.add(overlay);
    // Plates do not own collision; their authored traversal lane is the walk
    // truth.  Keep its inspection surface separate and read-only so it cannot
    // be confused with editable Event transforms.
    const walkOverlay = new THREE.Group();
    walkOverlay.name = 'ThestraPlateWalkLane';
    walkOverlay.visible = false;
    scene.add(walkOverlay);
    const walkProfileControls = new THREE.Group();
    walkProfileControls.name = 'ThestraPlateWalkProfileAuthoring';
    walkProfileControls.visible = false;
    scene.add(walkProfileControls);
    const gizmo = createMoveGizmo(camera, renderer.domElement, ['X'], ['Z', 'Y', 'X']);
    scene.add(gizmo.getHelper());
    const scenePlane = new THREE.Mesh(new THREE.PlaneGeometry(1, 1),
        new THREE.MeshBasicMaterial({ transparent: true }));
    const foregroundPlane = new THREE.Mesh(new THREE.PlaneGeometry(1, 1),
        new THREE.MeshBasicMaterial({ transparent: true, depthWrite: false }));
    const playerPreview = new THREE.Group();
    playerPreview.name = 'ThestraPlatePlayerPreview';
    playerPreview.visible = false;
    scenePlane.renderOrder = -10;
    foregroundPlane.renderOrder = 10;
    scene.add(scenePlane, foregroundPlane, playerPreview);
    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    let model = null, plate = null, selectedId, serial = 0, disposed = false, visible = false, gesture = null;
    let modalProfileMove = null, lastPointerEvent = null;
    let walkMeshVisible = false, walkProfileEditing = false, walkProfileComponentMode = 'point';
    let walkProfileSelection = null, walkProfileHover = null;
    const events = new Map(), hitTargets = [];
    const walkProfileObjects = new Map(), walkProfileHitTargets = [];

    function semantic(event) { return { kind: 'event', key: `event:${event.id}`, id: event.id }; }
    function updatePointer(event) {
        const rect = renderer.domElement.getBoundingClientRect();
        pointer.set((event.clientX - rect.left) / rect.width * 2 - 1,
            1 - (event.clientY - rect.top) / rect.height * 2);
        raycaster.setFromCamera(pointer, camera);
    }
    function pick(event) {
        updatePointer(event);
        return raycaster.intersectObjects(hitTargets, false)[0]?.object.userData.event || null;
    }
    function pickWalkProfile(event) {
        if (!walkProfileEditing) return null;
        updatePointer(event);
        const wantedKind = walkProfileComponentMode === 'segment'
            ? 'walk-profile-segment' : 'walk-profile-point';
        const targets = walkProfileHitTargets.filter(object =>
            object.userData?.thestraSelection?.kind === wantedKind);
        return raycaster.intersectObjects(targets, false)[0]?.object.userData.thestraSelection || null;
    }

    function pointerSnapshot(event) {
        return event ? { clientX: event.clientX, clientY: event.clientY } : null;
    }

    function scenePointAtPointer(event, z = 4) {
        if (!event) return null;
        updatePointer(event);
        const plane = new THREE.Plane(new THREE.Vector3(0, 0, 1), -z);
        return raycaster.ray.intersectPlane(plane, new THREE.Vector3());
    }

    function beginModalProfileMove() {
        if (!walkProfileEditing || walkProfileSelection?.kind !== 'walk-profile-point') return false;
        const lane = model?.map?.source?.traversal?.lane;
        const profile = lane?.groundProfile;
        const activeObject = walkProfileObjects.get(walkProfileSelection.key);
        const activeSource = profile?.[walkProfileSelection.index];
        if (!lane || !activeObject || !activeSource) return false;

        const selections = (options.spatialInteraction?.snapshot?.().selectionSet || [])
            .filter(item => item?.kind === 'walk-profile-point');
        const effectiveSelections = selections.some(item => item.key === walkProfileSelection.key)
            ? selections : [walkProfileSelection];
        const targets = effectiveSelections.map(selection => {
            const object = walkProfileObjects.get(selection.key);
            const source = profile?.[selection.index];
            return object && source ? {
                selection,
                object,
                origin: object.position.clone(),
                source: { y: Number(source.y), z: Number(source.z) }
            } : null;
        }).filter(Boolean);
        const pointerPoint = scenePointAtPointer(lastPointerEvent, activeObject.position.z);
        modalProfileMove = {
            selection: walkProfileSelection,
            activeObject,
            activeSource: { y: Number(activeSource.y), z: Number(activeSource.z) },
            targets,
            grabOffset: pointerPoint
                ? activeObject.position.clone().sub(pointerPoint)
                : new THREE.Vector3()
        };
        gizmo.detach();
        controls.enabled = false;
        options.spatialInteraction?.beginMove?.();
        return true;
    }

    function beginModalProfileExtrude() {
        if (!walkProfileEditing || walkProfileSelection?.kind !== 'walk-profile-point') {
            return { ok: false, reason: 'no-profile-point-selected' };
        }
        const lane = model?.map?.source?.traversal?.lane;
        const profile = lane?.groundProfile;
        const index = walkProfileSelection.index;
        if (!Array.isArray(profile) || profile.length < 2) {
            return { ok: false, reason: 'missing-ground-profile' };
        }
        if (index !== 0 && index !== profile.length - 1) {
            return { ok: false, reason: 'profile-endpoint-required' };
        }
        const anchorObject = walkProfileObjects.get(walkProfileSelection.key);
        const source = profile[index];
        if (!anchorObject || !source) return { ok: false, reason: 'invalid-profile-point' };

        const previewPoint = new THREE.Mesh(
            new THREE.CircleGeometry(5, 16),
            new THREE.MeshBasicMaterial({
                color: 0xffa24d, depthTest: false, depthWrite: false
            })
        );
        previewPoint.position.copy(anchorObject.position);
        previewPoint.renderOrder = 31;
        const screen = { x: anchorObject.position.x, y: -anchorObject.position.y };
        const previewSegment = profileScreenSegment(
            screen, screen,
            { kind: 'walk-profile-extrude-preview', key: 'walk-profile-extrude-preview' });
        previewSegment.material.color.setHex(0xffa24d);
        previewSegment.renderOrder = 30;
        walkProfileControls.add(previewSegment, previewPoint);

        const pointerPoint = scenePointAtPointer(lastPointerEvent, previewPoint.position.z);
        modalProfileMove = {
            kind: 'extrude',
            selection: walkProfileSelection,
            endpointIndex: index,
            anchorObject,
            activeObject: previewPoint,
            activeSource: { y: Number(source.y), z: Number(source.z) },
            targets: [{
                selection: walkProfileSelection,
                object: previewPoint,
                origin: previewPoint.position.clone(),
                source: { y: Number(source.y), z: Number(source.z) }
            }],
            previewPoint,
            previewSegment,
            grabOffset: pointerPoint
                ? previewPoint.position.clone().sub(pointerPoint)
                : new THREE.Vector3()
        };
        gizmo.detach();
        controls.enabled = false;
        options.spatialInteraction?.beginMove?.();
        return { ok: true };
    }

    function clearModalExtrudePreview(move) {
        if (!move || move.kind !== 'extrude') return;
        for (const object of [move.previewSegment, move.previewPoint]) {
            if (!object) continue;
            walkProfileControls.remove(object);
            object.geometry?.dispose();
            object.material?.dispose();
        }
    }

    function updateModalProfileMove(event) {
        const move = modalProfileMove;
        if (!move) return false;
        const lane = model.map.source.traversal.lane;
        const hit = scenePointAtPointer(event, move.activeObject.position.z);
        if (!hit) return true;
        const desired = hit.add(move.grabOffset);
        let world;
        try {
            world = View.worldYZAtScreenOnDepthPlane(
                plate.camera, plate.width, plate.height, Number(lane.depthX),
                plate.sliceY, Number(lane.groundZ || 0),
                Number(plate.player.centerX), Number(plate.player.screenY),
                desired.x, -desired.y, move.activeSource.y, move.activeSource.z);
        } catch (error) {
            options.spatialInteraction?.reject?.('profile-view-underdetermined');
            return true;
        }
        const constraint = options.spatialInteraction?.snapshot?.().constraint || null;
        if (constraint === 'Y') world.z = move.activeSource.z;
        else if (constraint === 'Z') world.y = move.activeSource.y;
        const deltaY = world.y - move.activeSource.y;
        const deltaZ = world.z - move.activeSource.z;
        move.targets.forEach(target => {
            const screen = platePoint(
                Number(lane.depthX), target.source.y + deltaY, target.source.z + deltaZ);
            target.object.position.set(screen.x, -screen.y, 4);
        });
        syncWalkProfileSegmentsFromPoints();
        if (move.kind === 'extrude') {
            syncPlateSegmentObject(
                move.previewSegment, move.anchorObject.position, move.previewPoint.position);
        }
        refreshOverlay();
        options.spatialInteraction?.setValue?.({ Y: deltaY, Z: deltaZ });
        return true;
    }

    function endModalProfileMove(commit) {
        const move = modalProfileMove;
        if (!move) return false;
        modalProfileMove = null;
        controls.enabled = true;
        if (!commit) {
            move.targets.forEach(target => target.object.position.copy(target.origin));
            clearModalExtrudePreview(move);
            syncWalkProfileSegmentsFromPoints();
            refreshOverlay();
            options.spatialInteraction?.cancel?.();
            return true;
        }
        const state = options.spatialInteraction?.snapshot?.();
        const deltaY = Number(state?.value?.Y || 0);
        const deltaZ = Number(state?.value?.Z || 0);
        const indices = move.targets.map(target => target.selection.index);
        const result = move.kind === 'extrude'
            ? options.onExtrudeGroundProfileEndpoint?.(
                move.endpointIndex,
                move.activeSource.y + deltaY,
                move.activeSource.z + deltaZ)
            : indices.length > 1
                ? options.onMoveGroundProfilePoints?.(indices, deltaY, deltaZ)
                : options.onMoveGroundProfilePoint?.(
                    move.selection.index,
                    move.activeSource.y + deltaY,
                    move.activeSource.z + deltaZ);
        if (!result?.ok) {
            move.targets.forEach(target => target.object.position.copy(target.origin));
            clearModalExtrudePreview(move);
            syncWalkProfileSegmentsFromPoints();
            refreshOverlay();
            options.spatialInteraction?.cancel?.();
            options.spatialInteraction?.reject?.(result?.reason || 'invalid-profile-point');
            return true;
        }
        const before = { points: move.targets.map(target => ({
            index: target.selection.index, Y: target.source.y, Z: target.source.z
        })) };
        const after = { points: move.targets.map(target => ({
            index: target.selection.index,
            Y: target.source.y + deltaY,
            Z: target.source.z + deltaZ
        })) };
        const transaction = result.changed
            ? SpatialInteraction.createTransaction(
                move.kind === 'extrude' ? 'extrude' : 'move',
                move.selection, before, after)
            : null;
        options.spatialInteraction?.confirm?.();
        if (transaction) options.onSpatialTransaction?.(transaction);
        clearModalExtrudePreview(move);
        rebuildWalkOverlay();
        rebuildWalkProfileControls();
        rebuildPlayerPreview();
        rebuildEvents();
        if (move.kind === 'extrude') {
            const active = result.selection || move.selection;
            setSemanticSelection(active);
            options.onSelection?.(active);
        } else if (move.targets.length > 1) {
            const active = options.spatialInteraction?.snapshot?.().selection || move.selection;
            setSemanticSelection(active);
        } else {
            const active = result.selection || move.selection;
            setSemanticSelection(active);
            options.onSelection?.(active);
        }
        return true;
    }

    function handleModalProfileKey(event) {
        const state = options.spatialInteraction?.snapshot?.() || null;
        const action = SpatialInteraction.transformShortcut(
            event, document.activeElement === renderer.domElement, state.operation);
        if (!action) return false;
        if (action.kind === 'begin-move') return beginModalProfileMove();
        if (!modalProfileMove) return false;
        if (action.kind === 'constraint') {
            if (action.axis === 'X') {
                options.spatialInteraction?.reject?.('profile-fixed-depth');
                return true;
            }
            options.spatialInteraction?.constrain?.(action.axis);
            if (lastPointerEvent) updateModalProfileMove(lastPointerEvent);
            return true;
        }
        if (action.kind === 'confirm') return endModalProfileMove(true);
        if (action.kind === 'cancel') return endModalProfileMove(false);
        return false;
    }

    function refreshWalkProfileVisualState() {
        const spatial = options.spatialInteraction?.snapshot?.() || null;
        const selectedKeys = new Set((spatial?.selectionSet || []).map(item => item?.key).filter(Boolean));
        const activeKey = spatial?.selection?.key || walkProfileSelection?.key || null;
        const hoverKey = walkProfileHover?.key || null;
        for (const [key, object] of walkProfileObjects.entries()) {
            const semantic = object.userData.thestraSelection;
            const selected = selectedKeys.has(key) || key === activeKey;
            const active = key === activeKey;
            const hovered = key === hoverKey && !active;
            if (semantic?.kind === 'walk-profile-point') {
                const activeType = walkProfileComponentMode === 'point';
                object.material.transparent = !activeType;
                object.material.opacity = activeType ? 1 : 0.35;
                object.material.color.setHex(active ? 0xffa24d
                    : selected ? 0xffd45a : hovered ? 0xffffff : 0x8f8248);
                object.scale.setScalar(active ? 1.3 : selected ? 1.2 : hovered ? 1.15 : 1);
            } else if (semantic?.kind === 'walk-profile-segment') {
                const activeType = walkProfileComponentMode === 'segment';
                object.material.color.setHex(active ? 0xffa24d
                    : selected ? 0xffd45a : hovered ? 0xffffff : 0x38d0f4);
                object.material.opacity = selected ? 0.95 : hovered ? 0.8 : (activeType ? 0.5 : 0.2);
            }
        }
    }

    function setWalkProfileHover(next) {
        const hover = next || null;
        if (walkProfileHover?.key === hover?.key) return;
        walkProfileHover = hover;
        options.spatialInteraction?.setHover?.(hover);
        refreshWalkProfileVisualState();
    }
    const disposeNavigation = installNavigation(renderer.domElement, [controls], {
        planar: true,
        canPan: () => !gizmo.axis && !gizmo.dragging && !modalProfileMove
    });
    function refreshOverlay() {
        const profileObject = walkProfileEditing && walkProfileSelection
            ? walkProfileObjects.get(walkProfileSelection.key) : null;
        const record = !profileObject ? events.get(String(selectedId)) : null;
        const object = profileObject || record?.group || null;
        const profilePoint = !!(profileObject && walkProfileSelection?.kind === 'walk-profile-point');
        overlay.visible = !!object;
        const selectedProfilePoints = (options.spatialInteraction?.snapshot?.().selectionSet || [])
            .filter(item => item?.kind === 'walk-profile-point').length;
        gizmo.enabled = !!object && (!profileObject || profilePoint)
            && !(profilePoint && selectedProfilePoints > 1);
        gizmo.showX = !!object;
        gizmo.showY = profilePoint;
        gizmo.showZ = false;
        gizmo.showXY = profilePoint;
        gizmo.showXZ = false;
        gizmo.showYZ = false;
        if (!object) { gizmo.detach(); return; }
        const box = new THREE.Box3().setFromObject(object);
        box.getCenter(overlay.position);
        box.getSize(overlay.scale);
        overlay.scale.z = Math.max(overlay.scale.z, 0.2);
        if (profileObject && !profilePoint) gizmo.detach();
        else if (gizmo.object !== object) gizmo.attach(object);
    }
    function setSemanticSelection(selection) {
        if (selection && (selection.kind === 'walk-profile-point' || selection.kind === 'walk-profile-segment')) {
            walkProfileSelection = selection;
            selectedId = null;
        } else {
            walkProfileSelection = null;
            selectedId = selection?.kind === 'event' ? selection.id : null;
        }
        refreshWalkProfileVisualState();
        refreshOverlay();
    }
    function select(id) {
        walkProfileSelection = null;
        selectedId = id;
        refreshOverlay();
    }
    function resize() {
        const rect = container.getBoundingClientRect();
        renderer.setSize(Math.max(1, rect.width), Math.max(1, rect.height));
        camera.left = -rect.width / 2; camera.right = rect.width / 2;
        camera.top = rect.height / 2; camera.bottom = -rect.height / 2;
        camera.updateProjectionMatrix();
    }
    const observer = new ResizeObserver(resize);
    observer.observe(container);
    function fit() {
        if (!plate) return;
        resize();
        const rect = container.getBoundingClientRect();
        camera.zoom = Math.min(rect.width / plate.width, rect.height / plate.height) * 0.94;
        controls.target.set(plate.width / 2, -plate.height / 2, 0);
        camera.position.set(plate.width / 2, -plate.height / 2, 1000);
        camera.updateProjectionMatrix(); controls.update();
    }
    function clearEvents() {
        gizmo.detach();
        for (const { group } of events.values()) {
            group.traverse(object => { object.geometry?.dispose(); object.material?.dispose(); });
            scene.remove(group);
        }
        events.clear(); hitTargets.length = 0;
    }
    function clearWalkOverlay() {
        while (walkOverlay.children.length) {
            const child = walkOverlay.children[walkOverlay.children.length - 1];
            walkOverlay.remove(child);
            child.geometry?.dispose(); child.material?.dispose();
        }
    }
    function clearWalkProfileControls() {
        gizmo.detach();
        while (walkProfileControls.children.length) {
            const child = walkProfileControls.children[walkProfileControls.children.length - 1];
            walkProfileControls.remove(child);
            child.geometry?.dispose(); child.material?.dispose();
        }
        walkProfileObjects.clear();
        walkProfileHitTargets.length = 0;
    }

    function profileScreenSegment(start, end, semantic) {
        const dx = end.x - start.x, dy = end.y - start.y;
        const length = Math.max(Math.hypot(dx, dy), 1);
        const mesh = new THREE.Mesh(
            new THREE.PlaneGeometry(length, 7),
            new THREE.MeshBasicMaterial({
                color: 0x38d0f4, transparent: true, opacity: 0.5,
                depthTest: false, depthWrite: false, side: THREE.DoubleSide
            })
        );
        mesh.position.set((start.x + end.x) * 0.5, -(start.y + end.y) * 0.5, 3.6);
        mesh.rotation.z = -Math.atan2(dy, dx);
        mesh.renderOrder = 28;
        mesh.userData.thestraSelection = semantic;
        return mesh;
    }

    function syncPlateSegmentObject(segment, leftPosition, rightPosition) {
        if (!segment || !leftPosition || !rightPosition) return;
        const start = { x: leftPosition.x, y: -leftPosition.y };
        const end = { x: rightPosition.x, y: -rightPosition.y };
        const dx = end.x - start.x, dy = end.y - start.y;
        const length = Math.max(Math.hypot(dx, dy), 1);
        segment.geometry?.dispose();
        segment.geometry = new THREE.PlaneGeometry(length, 7);
        segment.position.set((start.x + end.x) * 0.5, -(start.y + end.y) * 0.5, 3.6);
        segment.rotation.z = -Math.atan2(dy, dx);
    }

    function syncWalkProfileSegmentsFromPoints() {
        const lane = model?.map?.source?.traversal?.lane;
        const profile = lane?.groundProfile;
        if (!Array.isArray(profile) || profile.length < 2) return;
        for (let index = 0; index < profile.length - 1; index++) {
            const segment = walkProfileObjects.get(`walk-profile-segment:${index}`);
            const left = walkProfileObjects.get(`walk-profile-point:${index}`);
            const right = walkProfileObjects.get(`walk-profile-point:${index + 1}`);
            if (!segment || !left || !right) continue;
            syncPlateSegmentObject(segment, left.position, right.position);
        }
    }

    function rebuildWalkProfileControls() {
        clearWalkProfileControls();
        if (!plate || !model) return;
        const lane = model.map.source.traversal.lane;
        const profile = lane && lane.groundProfile;
        if (!Array.isArray(profile) || profile.length < 2) {
            walkProfileControls.visible = walkProfileEditing;
            return;
        }
        const points = profile.map(point => platePoint(
            Number(lane.depthX), Number(point.y), Number(point.z)));
        for (let index = 0; index < points.length - 1; index++) {
            const semantic = {
                kind: 'walk-profile-segment',
                key: `walk-profile-segment:${index}`,
                index
            };
            const segment = profileScreenSegment(points[index], points[index + 1], semantic);
            walkProfileControls.add(segment);
            walkProfileHitTargets.push(segment);
            walkProfileObjects.set(semantic.key, segment);
        }
        points.forEach((screen, index) => {
            const semantic = {
                kind: 'walk-profile-point',
                key: `walk-profile-point:${index}`,
                index
            };
            const point = new THREE.Mesh(
                new THREE.CircleGeometry(5, 16),
                new THREE.MeshBasicMaterial({
                    color: 0xffd45a, depthTest: false, depthWrite: false
                })
            );
            point.position.set(screen.x, -screen.y, 4);
            point.renderOrder = 29;
            point.userData.thestraSelection = semantic;
            walkProfileControls.add(point);
            walkProfileHitTargets.push(point);
            walkProfileObjects.set(semantic.key, point);
        });
        walkProfileControls.visible = walkProfileEditing;
        refreshWalkProfileVisualState();
        refreshOverlay();
    }

    function setWalkProfileEditing(enabled) {
        walkProfileEditing = !!enabled;
        walkProfileControls.visible = walkProfileEditing;
        walkOverlay.visible = walkMeshVisible || walkProfileEditing;
        playerPreview.visible = walkProfileEditing;
        if (!walkProfileEditing) {
            walkProfileSelection = null;
            setWalkProfileHover(null);
        }
        rebuildPlayerPreview();
        refreshOverlay();
    }

    function setWalkProfileComponentMode(mode) {
        if (mode !== 'point' && mode !== 'segment') {
            throw new Error(`Unsupported Walk Profile component mode '${mode}'.`);
        }
        if (mode === walkProfileComponentMode) return;
        walkProfileComponentMode = mode;
        setWalkProfileHover(null);
        if ((mode === 'point' && walkProfileSelection?.kind === 'walk-profile-segment')
                || (mode === 'segment' && walkProfileSelection?.kind === 'walk-profile-point')) {
            setSemanticSelection(null);
            options.onSelection?.(null);
        }
        refreshWalkProfileVisualState();
        refreshOverlay();
    }

    function eventScreen(record) {
        const event = sourceEvent(record);
        const position = event.worldPosition;
        const lane = model.map.source.traversal.lane;
        const groundZ = Number(lane.groundZ || 0);
        // Town models are grounded by the runtime lane.  Some early plate
        // Events still carry a legacy Z (notably -1.5) which is deliberately
        // ignored by presentation/viewport_3d.lua.  Using it for the editor
        // box while the model uses the floor created two visible transforms.
        const modelPath = record.asset?.model;
        const modelScale = Number(event.modelScale) > 0 ? Number(event.modelScale) : 1;
        const groundedZ = View.groundHeight(lane.groundProfile, groundZ, Number(position[1]));
        const visualZ = modelPath
            ? groundedZ + (/transition_arrow\.obj$/i.test(modelPath) ? 0.22 * modelScale : 0)
            : Number(position[2] || 0);
        const projected = View.projectPerspective(plate.camera, plate.width, plate.height,
            Number(position[0]), Number(position[1]), visualZ);
        const base = View.projectPerspective(plate.camera, plate.width, plate.height,
            Number(lane.depthX), plate.sliceY, groundZ);
        const x = plate.player.centerX + projected.x - base.x;
        const sprite = !!event.sprite || record.asset?.provenance === 'sprite';
        const y = sprite
            ? plate.player.screenY - (View.groundHeight(lane.groundProfile, groundZ, Number(position[1])) - groundZ)
                * plate.player.pixelsPerRuntimeY
            : projected.y + plate.player.screenY - base.y;
        return { x, y };
    }
    function addEventSprite(group, event, asset, width, height) {
        if (!asset || typeof asset.sprite !== 'string' || !asset.sprite) return;
        new THREE.TextureLoader().load(projectAsset(asset.sprite), texture => {
            if (disposed || !group.parent) { texture.dispose(); return; }
            texture.colorSpace = THREE.SRGBColorSpace;
            texture.magFilter = texture.minFilter = THREE.NearestFilter;
            configureEventSpriteFrame(texture, event);
            const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: texture, transparent: true,
                depthTest: false, depthWrite: false }));
            // Plate Events share the same authored 24x48 footprint as their
            // editable box.  The sprite is visual evidence; selection and
            // movement still operate on the one common Event box/gizmo.
            sprite.position.set(0, height / 2, 0.3);
            sprite.scale.set(width, height, 1);
            // Runtime plate actors render above the background scene and below
            // their authored foreground cutout only where that cutout has
            // pixels.  Three has no alpha-mask compositor here, so keeping
            // authored Event evidence on top is the useful inspection order.
            sprite.renderOrder = 30;
            group.add(sprite);
        }, undefined, () => {});
    }
    function platePoint(worldX, worldY, worldZ) {
        const lane = model.map.source.traversal.lane;
        const groundZ = Number(lane.groundZ || 0);
        const projected = View.projectPerspective(plate.camera, plate.width, plate.height, worldX, worldY, worldZ);
        const base = View.projectPerspective(plate.camera, plate.width, plate.height,
            Number(lane.depthX), plate.sliceY, groundZ);
        return { x: plate.player.centerX + projected.x - base.x, y: projected.y + plate.player.screenY - base.y };
    }
    function projectedModelPoint(event, modelPath, source) {
        const lane = model.map.source.traversal.lane;
        const scale = Number(event.modelScale) > 0 ? Number(event.modelScale) : 1;
        // OBJLoader retains source Y-up.  This is the same Y-up -> runtime
        // Z-up conversion made by presentation/obj_model.lua before the town
        // plate compositor projects the vertex through WorldCamera.
        const localX = source.x * scale;
        const localY = -source.z * scale;
        const localZ = source.y * scale;
        const position = event.worldPosition;
        const eventY = Number(position[1]);
        const groundZ = View.groundHeight(lane.groundProfile, Number(lane.groundZ || 0), eventY);
        if (/transition_arrow\.obj$/i.test(modelPath || '')) {
            const point = View.transitionArrowWorldPoint(Number(position[0]), eventY,
                groundZ, scale, event.direction, source.x, -source.z, source.y);
            return platePoint(point.x, point.y, point.z);
        }
        return platePoint(Number(position[0]) + localX, eventY + localY, groundZ + localZ);
    }
    async function loadRuntimeObj(path) {
        const url = projectAsset(path);
        const response = await fetch(url);
        if (!response.ok) throw new Error(`OBJ ${path} returned HTTP ${response.status}.`);
        const text = await response.text();
        const loader = new OBJLoader();
        const library = text.match(/^\s*mtllib\s+(.+?)\s*$/m)?.[1];
        if (library) {
            const materialUrl = new URL(library, new URL(url, globalThis.location.href)).pathname;
            const materialResponse = await fetch(materialUrl);
            if (!materialResponse.ok) throw new Error(`MTL ${library} for ${path} returned HTTP ${materialResponse.status}.`);
            const baseUrl = new URL('.', new URL(url, globalThis.location.href)).pathname;
            const materials = new MTLLoader().parse(await materialResponse.text(), baseUrl);
            materials.preload();
            loader.setMaterials(materials);
        }
        return loader.parse(text);
    }
    function fitProjectedModelBounds(cube, edges, meshes) {
        const bounds = new THREE.Box3();
        // Mesh vertices are already in the Event group's local screen plane.
        // Do not use expandByObject here: that includes the group's event
        // anchor and would apply the anchor a second time to the hit box.
        for (const mesh of meshes) {
            mesh.geometry.computeBoundingBox();
            if (mesh.geometry.boundingBox) bounds.union(mesh.geometry.boundingBox);
        }
        if (bounds.isEmpty()) return;
        const size = bounds.getSize(new THREE.Vector3());
        const center = bounds.getCenter(new THREE.Vector3());
        const base = cube.geometry.parameters;
        cube.position.copy(center); edges.position.copy(center);
        cube.scale.set(Math.max(size.x, 2) / base.width, Math.max(size.y, 2) / base.height,
            Math.max(size.z, 0.2) / base.depth);
        edges.scale.copy(cube.scale);
    }
    async function addProjectedEventModel(group, event, asset, origin, revision, eventBox) {
        if (!asset?.model) return;
        try {
            const object = await loadRuntimeObj(asset.model);
            if (disposed || revision !== serial || !group.parent) return;
            object.updateMatrixWorld(true);
            const projectedMeshes = [];
            object.traverse(child => {
                if (!child.isMesh || !child.geometry?.getAttribute('position')) return;
                const source = child.geometry.index ? child.geometry.toNonIndexed() : child.geometry;
                const positions = source.getAttribute('position');
                const projected = new Float32Array(positions.count * 3);
                const vertex = new THREE.Vector3();
                for (let index = 0; index < positions.count; index++) {
                    vertex.fromBufferAttribute(positions, index).applyMatrix4(child.matrixWorld);
                    const point = projectedModelPoint(event, asset.model, vertex);
                    projected[index * 3] = point.x - origin.x;
                    projected[index * 3 + 1] = origin.y - point.y;
                    projected[index * 3 + 2] = 3;
                }
                const geometry = new THREE.BufferGeometry();
                geometry.setAttribute('position', new THREE.BufferAttribute(projected, 3));
                geometry.computeVertexNormals();
                const color = child.material?.color || new THREE.Color(/transition_arrow\.obj$/i.test(asset.model) ? 0xffc84a : 0xd2d8df);
                const material = new THREE.MeshBasicMaterial({ color, side: THREE.DoubleSide,
                    transparent: true, opacity: 0.94, depthTest: false, depthWrite: false });
                const mesh = new THREE.Mesh(geometry, material);
                mesh.renderOrder = 30;
                group.add(mesh);
                projectedMeshes.push(mesh);
                if (source !== child.geometry) source.dispose();
            });
            fitProjectedModelBounds(eventBox.cube, eventBox.edges, projectedMeshes);
            refreshOverlay();
        } catch (error) {
            console.warn(`Plate Event model '${asset.model}' could not be projected:`, error);
        }
    }
    function rebuildWalkOverlay() {
        clearWalkOverlay();
        if (!plate || !model) return;
        const lane = model.map.source.traversal.lane;
        const minimum = Number(lane.minY), maximum = Number(lane.maxY);
        if (!Number.isFinite(minimum) || !Number.isFinite(maximum) || maximum <= minimum) return;
        // A plate has no collision OBJ to edit: bounded_lane is its gameplay
        // walk truth. Project its full authored depth ribbon, not a flat
        // centreline, through the same pitched WorldCamera used by the runtime.
        const bounds = plate.bounds || [];
        const nearX = Number.isFinite(Number(bounds[0])) ? Number(bounds[0]) : Number(lane.depthX) - 1;
        const farX = Number.isFinite(Number(bounds[3])) ? Number(bounds[3]) : Number(lane.depthX) + 1;
        const ribbon = [], ribs = [], nearEdge = [], farEdge = [], centerLine = [];
        const samples = 48;
        for (let index = 0; index <= samples; index++) {
            const y = minimum + (maximum - minimum) * index / samples;
            const z = View.groundHeight(lane.groundProfile, Number(lane.groundZ || 0), y);
            const near = platePoint(nearX, y, z + 0.015);
            const far = platePoint(farX, y, z + 0.015);
            const center = platePoint(Number(lane.depthX), y, z + 0.02);
            nearEdge.push(near.x, -near.y, 2.8);
            farEdge.push(far.x, -far.y, 2.8);
            centerLine.push(center.x, -center.y, 2.9);
            if (index < samples) {
                const nextY = minimum + (maximum - minimum) * (index + 1) / samples;
                const nextZ = View.groundHeight(lane.groundProfile, Number(lane.groundZ || 0), nextY);
                const nextNear = platePoint(nearX, nextY, nextZ + 0.015);
                const nextFar = platePoint(farX, nextY, nextZ + 0.015);
                ribbon.push(near.x, -near.y, 2.7, far.x, -far.y, 2.7, nextFar.x, -nextFar.y, 2.7,
                    near.x, -near.y, 2.7, nextFar.x, -nextFar.y, 2.7, nextNear.x, -nextNear.y, 2.7);
                if (index % 4 === 0) ribs.push(near.x, -near.y, 2.85, far.x, -far.y, 2.85);
            }
        }
        const surface = new THREE.BufferGeometry();
        surface.setAttribute('position', new THREE.Float32BufferAttribute(ribbon, 3));
        const mesh = new THREE.Mesh(surface, new THREE.MeshBasicMaterial({ color: 0x168bb4,
            transparent: true, opacity: 0.22, side: THREE.DoubleSide, depthTest: false, depthWrite: false }));
        mesh.renderOrder = 24;
        walkOverlay.add(mesh);
        const wire = new THREE.BufferGeometry();
        wire.setAttribute('position', new THREE.Float32BufferAttribute(ribs, 3));
        const ribsLine = new THREE.LineSegments(wire, new THREE.LineBasicMaterial({ color: 0x38d0f4,
            transparent: true, opacity: 0.72, depthTest: false, depthWrite: false }));
        ribsLine.renderOrder = 25;
        walkOverlay.add(ribsLine);
        for (const points of [nearEdge, farEdge, centerLine]) {
            const geometry = new THREE.BufferGeometry();
            geometry.setAttribute('position', new THREE.Float32BufferAttribute(points, 3));
            const line = new THREE.Line(geometry, new THREE.LineBasicMaterial({ color: points === centerLine ? 0x55ef83 : 0x38d0f4,
                transparent: true, opacity: 0.92, depthTest: false, depthWrite: false }));
            line.renderOrder = 26;
            walkOverlay.add(line);
        }
        walkOverlay.visible = walkMeshVisible || walkProfileEditing;
    }
    function rebuildPlayerPreview() {
        while (playerPreview.children.length) {
            const child = playerPreview.children[playerPreview.children.length - 1];
            playerPreview.remove(child);
            child.geometry?.dispose();
            child.material?.dispose();
        }
        if (!model || !plate) return;
        const lane = model.map.source.traversal.lane;
        const groundZ = Number(lane.groundZ || 0);
        const ground = View.groundHeight(lane.groundProfile, groundZ, plate.sliceY);
        const footY = Number(plate.player.screenY)
            - (ground - groundZ) * Number(plate.player.pixelsPerRuntimeY || 0);
        const width = Number(plate.player.width || 12);
        const height = Number(plate.player.height || 28);
        const { cube, edges } = createEventBox(width, height, 0.16);
        cube.material.opacity = 0.08;
        cube.position.y = edges.position.y = height / 2;
        const group = new THREE.Group();
        group.position.set(Number(plate.player.centerX), -footY, 3.2);
        group.add(cube, edges);
        playerPreview.add(group);
        playerPreview.visible = walkProfileEditing;
    }

    function rebuildEvents() {
        clearEvents();
        if (!model || !plate) return;
        for (const record of model.events || []) {
            const event = sourceEvent(record);
            if (!Array.isArray(event.worldPosition)) continue;
            const heightScale = Number(event.worldHeight || 1.75) / 1.75;
            const width = plate.player.width * heightScale;
            const height = plate.player.height * heightScale;
            const screen = eventScreen(record);
            const group = new THREE.Group();
            group.position.set(screen.x, -screen.y, 0);
            const { cube, edges } = createEventBox(width, height, 0.2);
            cube.position.y = edges.position.y = height / 2;
            cube.userData.event = event;
            group.add(cube, edges); scene.add(group);
            addEventSprite(group, event, record.asset, width, height);
            addProjectedEventModel(group, event, record.asset, screen, serial, { cube, edges });
            hitTargets.push(cube);
            events.set(String(event.id), { event, record, group });
        }
        refreshOverlay();
    }
    function assignTexture(mesh, url, revision) {
        new THREE.TextureLoader().load(url, texture => {
            if (disposed || revision !== serial) { texture.dispose(); return; }
            texture.colorSpace = THREE.SRGBColorSpace;
            texture.magFilter = texture.minFilter = THREE.NearestFilter;
            mesh.material.map?.dispose(); mesh.material.map = texture; mesh.material.needsUpdate = true;
        });
    }
    async function setSceneModel(nextModel) {
        model = nextModel;
        const manifestPath = model?.map?.environmentPackage;
        const map = model?.map?.source;
        const revision = ++serial;
        if (!manifestPath || !map?.traversal?.camera) { plate = null; hide(); clearEvents(); return false; }
        const response = await fetch(projectAsset(manifestPath));
        if (!response.ok) throw new Error(`Environment package ${manifestPath} returned HTTP ${response.status}.`);
        const manifest = await response.json();
        if (revision !== serial) return false;
        const spec = manifest.preRendered;
        if (!spec) { plate = null; hide(); clearEvents(); return false; }
        if (spec.mode !== 'layered_2d' || !Array.isArray(spec.imageSize) || !Array.isArray(spec.slicePositions)
                || !Array.isArray(spec.scenes) || !Array.isArray(spec.foregrounds)) {
            throw new Error(`Environment package ${manifestPath} has an invalid preRendered contract.`);
        }
        const index = nearestSlice(spec.slicePositions, spec.lane);
        const width = Number(spec.imageSize[0]), height = Number(spec.imageSize[1]);
        const nextKey = `${map.id}/${manifestPath}/${index}`;
        const changedPlate = !plate || plate.key !== nextKey;
        plate = {
            key: nextKey, width, height, sliceY: Number(spec.slicePositions[index]),
            player: spec.playerProjection,
            camera: View.resolveTownCamera(map.traversal.camera),
            bounds: manifest.bounds,
            descriptor: { mapId: map.id, frames: [{ id: 'authoring/map', profile: 'authoring', location: 'map', width, height }] }
        };
        scenePlane.scale.set(width, height, 1); foregroundPlane.scale.set(width, height, 1);
        scenePlane.position.set(width / 2, -height / 2, -2); foregroundPlane.position.set(width / 2, -height / 2, 2);
        if (changedPlate) {
            assignTexture(scenePlane, resolvePackageAsset(manifestPath, spec.scenes[index]), revision);
            assignTexture(foregroundPlane, resolvePackageAsset(manifestPath, spec.foregrounds[index]), revision);
        }
        rebuildEvents();
        rebuildWalkOverlay();
        rebuildWalkProfileControls();
        rebuildPlayerPreview();
        if (changedPlate) fit();
        return true;
    }
    function show() {
        if (!plate) throw new Error('Plate composition is unavailable.');
        layer.style.display = 'block'; visible = true; refreshOverlay();
    }
    function hide() { visible = false; layer.style.display = 'none'; }
    renderer.domElement.addEventListener('pointermove', event => {
        lastPointerEvent = pointerSnapshot(event);
        if (modalProfileMove) {
            updateModalProfileMove(event);
            return;
        }
        if (!walkProfileEditing || gizmo.dragging || gizmo.axis) return;
        setWalkProfileHover(pickWalkProfile(event));
    });
    renderer.domElement.addEventListener('pointerleave', () => {
        if (walkProfileEditing) setWalkProfileHover(null);
    });
    renderer.domElement.addEventListener('pointerdown', event => {
        renderer.domElement.focus({ preventScroll: true });
        lastPointerEvent = pointerSnapshot(event);
        if (modalProfileMove) {
            if (event.button === 0) endModalProfileMove(true);
            else if (event.button === 2) endModalProfileMove(false);
            if (event.button === 0 || event.button === 2) {
                event.preventDefault();
                return;
            }
        }
        if (event.button !== 0 || gizmo.axis || gizmo.dragging) return;
        if (walkProfileEditing) {
            const selection = pickWalkProfile(event);
            if (event.shiftKey && selection && options.onToggleSelection) {
                options.onToggleSelection(selection);
                const active = options.spatialInteraction?.snapshot?.().selection || null;
                setSemanticSelection(active);
            } else {
                setSemanticSelection(selection);
                options.onSelection?.(selection);
            }
            return;
        }
        const hit = pick(event); select(hit?.id); options.onSelection?.(hit ? semantic(hit) : null);
    });
    renderer.domElement.addEventListener('dblclick', event => {
        if (walkProfileEditing) return;
        const hit = pick(event); if (hit) options.onOpenAt?.(semantic(hit));
    });
    renderer.domElement.addEventListener('keydown', event => {
        if (handleModalProfileKey(event)) {
            event.preventDefault();
            return;
        }
        if (event.code === 'Home') { event.preventDefault(); fit(); }
    });
    gizmo.addEventListener('mouseDown', () => {
        if (walkProfileEditing && walkProfileSelection?.kind === 'walk-profile-point') {
            const object = walkProfileObjects.get(walkProfileSelection.key);
            const source = model.map.source.traversal.lane.groundProfile?.[walkProfileSelection.index];
            if (object && source) {
                const selectedPoints = (options.spatialInteraction?.snapshot?.().selectionSet || [])
                    .filter(item => item?.kind === 'walk-profile-point');
                const effective = selectedPoints.some(item => item.key === walkProfileSelection.key)
                    ? selectedPoints : [walkProfileSelection];
                const profile = model.map.source.traversal.lane.groundProfile;
                const targets = effective.map(selection => {
                    const targetObject = walkProfileObjects.get(selection.key);
                    const targetSource = profile?.[selection.index];
                    return targetObject && targetSource ? {
                        selection,
                        object: targetObject,
                        origin: targetObject.position.clone(),
                        source: { y: Number(targetSource.y), z: Number(targetSource.z) }
                    } : null;
                }).filter(Boolean);
                gesture = {
                    kind: 'walk-profile-point',
                    selection: walkProfileSelection,
                    object,
                    source: { y: Number(source.y), z: Number(source.z) },
                    origin: object.position.clone(),
                    targets,
                    deltaY: 0,
                    deltaZ: 0
                };
                options.spatialInteraction?.beginMove?.();
            }
        } else {
            const record = events.get(String(selectedId));
            if (record) gesture = { kind: 'event', record, origin: record.group.position.clone() };
        }
        controls.enabled = false;
    });
    gizmo.addEventListener('objectChange', () => {
        if (walkProfileEditing && walkProfileSelection?.kind === 'walk-profile-point') {
            syncWalkProfileSegmentsFromPoints();
        }
        refreshOverlay();
    });
    gizmo.addEventListener('mouseUp', () => {
        controls.enabled = true;
        if (!gesture) return;
        const completed = gesture; gesture = null;
        const lane = model.map.source.traversal.lane;
        if (completed.kind === 'walk-profile-point') {
            const screenX = completed.object.position.x;
            const screenY = -completed.object.position.y;
            let world;
            try {
                world = View.worldYZAtScreenOnDepthPlane(
                    plate.camera, plate.width, plate.height, Number(lane.depthX),
                    plate.sliceY, Number(lane.groundZ || 0),
                    Number(plate.player.centerX), Number(plate.player.screenY),
                    screenX, screenY, completed.source.y, completed.source.z);
            } catch (error) {
                completed.object.position.copy(completed.origin);
                refreshOverlay();
                return;
            }
            const result = options.onMoveGroundProfilePoint?.(
                completed.selection.index, world.y, world.z);
            if (!result?.ok) {
                completed.object.position.copy(completed.origin);
            } else {
                walkProfileSelection = result.selection || completed.selection;
                rebuildWalkOverlay();
                rebuildWalkProfileControls();
                rebuildPlayerPreview();
                rebuildEvents();
                options.onSelection?.(walkProfileSelection);
            }
            refreshOverlay();
            return;
        }
        const { record, origin } = completed;
        const position = record.event.worldPosition.slice();
        const modelPath = record.record.asset?.model;
        if (modelPath) {
            const modelScale = Number(record.event.modelScale) > 0 ? Number(record.event.modelScale) : 1;
            const zOffset = /transition_arrow\.obj$/i.test(modelPath) ? 0.22 * modelScale : 0;
            position[1] = View.worldYAtScreenXOnGroundProfile(
                plate.camera, plate.width, plate.height, Number(lane.depthX),
                lane.groundProfile, Number(lane.groundZ || 0), plate.sliceY,
                Number(plate.player.centerX), record.group.position.x,
                Number(lane.minY), Number(lane.maxY), zOffset);
        } else {
            // Runtime plate sprites deliberately keep horizontal projection on
            // the base plane; elevation only changes their foot-line Y.
            const projection = View.horizontalProjection(plate.camera, plate.width, plate.height,
                Number(lane.depthX), Number(lane.groundZ || 0), plate.sliceY, Number(plate.player.centerX));
            position[1] = View.worldYAtScreenX(projection, record.group.position.x);
        }
        const result = options.onMoveWorldEvent?.(semantic(record.event), position);
        if (!result?.ok) record.group.position.copy(origin);
        else {
            record.event.worldPosition = position;
            const screen = eventScreen(record.record);
            record.group.position.set(screen.x, -screen.y, 0);
            rebuildEvents();
            options.onSelection?.(semantic(record.event));
        }
        refreshOverlay();
    });
    (function animate() {
        if (disposed) return;
        requestAnimationFrame(animate);
        if (!visible) return;
        controls.update(); renderer.render(scene, camera);
    }());
    return {
        setSceneModel, show, select, hide, setSemanticSelection,
        isPlate: () => !!plate,
        isVisible: () => visible,
        getCanvas: () => renderer.domElement,
        setWalkMeshVisible(visible) {
            walkMeshVisible = !!visible;
            walkOverlay.visible = walkMeshVisible || walkProfileEditing;
        },
        getWalkMeshVisible: () => walkMeshVisible,
        setWalkProfileEditing,
        getWalkProfileEditing: () => walkProfileEditing,
        setWalkProfileComponentMode,
        getWalkProfileComponentMode: () => walkProfileComponentMode,
        beginWalkProfileExtrude: beginModalProfileExtrude,
        getWalkProfileSelection: () => walkProfileSelection,
        refreshWalkProfile() {
            rebuildWalkOverlay();
            rebuildWalkProfileControls();
            rebuildPlayerPreview();
            rebuildEvents();
        },
        descriptor: () => plate?.descriptor || null,
        dispose() {
            disposed = true; serial += 1; disposeNavigation(); observer.disconnect();
            gizmo.dispose(); controls.dispose();
            scenePlane.material.map?.dispose(); foregroundPlane.material.map?.dispose();
            scene.traverse(object => { object.geometry?.dispose(); object.material?.dispose(); });
            renderer.dispose(); layer.remove();
        }
    };
}
