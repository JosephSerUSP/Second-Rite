import * as THREE from 'three';
import { OrbitControls } from '/vendor/three/OrbitControls.js';
import { OBJLoader } from '/vendor/three/OBJLoader.js';
import { MTLLoader } from '/vendor/three/MTLLoader.js';
import { createSelectionOverlay, createEventBox, createMoveGizmo, configureEventSpriteFrame, installNavigation } from '/js/three-authoring-tools.js';
import '/js/composition-authoring.js';

const View = globalThis.ThestraCompositionAuthoring;
if (!View) throw new Error('Shared world-view semantics failed to load.');

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
    scenePlane.renderOrder = -10;
    foregroundPlane.renderOrder = 10;
    scene.add(scenePlane, foregroundPlane);
    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    let model = null, plate = null, selectedId, serial = 0, disposed = false, visible = false, gesture = null;
    let walkMeshVisible = false, walkProfileEditing = false, walkProfileSelection = null;
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
        return raycaster.intersectObjects(walkProfileHitTargets, false)[0]?.object.userData.thestraSelection || null;
    }
    const disposeNavigation = installNavigation(renderer.domElement, [controls], {
        planar: true, canPan: event => !gizmo.axis && !gizmo.dragging
            && !(walkProfileEditing ? pickWalkProfile(event) : pick(event))
    });
    function refreshOverlay() {
        const profileObject = walkProfileEditing && walkProfileSelection
            ? walkProfileObjects.get(walkProfileSelection.key) : null;
        const record = !profileObject ? events.get(String(selectedId)) : null;
        const object = profileObject || record?.group || null;
        const profilePoint = !!(profileObject && walkProfileSelection?.kind === 'walk-profile-point');
        overlay.visible = !!object;
        gizmo.enabled = !!object && (!profileObject || profilePoint);
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
        refreshOverlay();
    }

    function setWalkProfileEditing(enabled) {
        walkProfileEditing = !!enabled;
        walkProfileControls.visible = walkProfileEditing;
        walkOverlay.visible = walkMeshVisible || walkProfileEditing;
        if (!walkProfileEditing) walkProfileSelection = null;
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
        if (changedPlate) fit();
        return true;
    }
    function show() {
        if (!plate) throw new Error('Plate composition is unavailable.');
        layer.style.display = 'block'; visible = true; refreshOverlay();
    }
    function hide() { visible = false; layer.style.display = 'none'; }
    renderer.domElement.addEventListener('pointerdown', event => {
        renderer.domElement.focus({ preventScroll: true });
        if (event.button !== 0 || gizmo.axis || gizmo.dragging) return;
        if (walkProfileEditing) {
            const selection = pickWalkProfile(event);
            setSemanticSelection(selection);
            options.onSelection?.(selection);
            return;
        }
        const hit = pick(event); select(hit?.id); options.onSelection?.(hit ? semantic(hit) : null);
    });
    renderer.domElement.addEventListener('dblclick', event => {
        if (walkProfileEditing) return;
        const hit = pick(event); if (hit) options.onOpenAt?.(semantic(hit));
    });
    renderer.domElement.addEventListener('keydown', event => {
        if (event.code === 'Home') { event.preventDefault(); fit(); }
    });
    gizmo.addEventListener('mouseDown', () => {
        if (walkProfileEditing && walkProfileSelection?.kind === 'walk-profile-point') {
            const object = walkProfileObjects.get(walkProfileSelection.key);
            const source = model.map.source.traversal.lane.groundProfile?.[walkProfileSelection.index];
            if (object && source) {
                gesture = {
                    kind: 'walk-profile-point',
                    selection: walkProfileSelection,
                    object,
                    source: { y: Number(source.y), z: Number(source.z) },
                    origin: object.position.clone()
                };
            }
        } else {
            const record = events.get(String(selectedId));
            if (record) gesture = { kind: 'event', record, origin: record.group.position.clone() };
        }
        controls.enabled = false;
    });
    gizmo.addEventListener('objectChange', refreshOverlay);
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
        setWalkMeshVisible(visible) {
            walkMeshVisible = !!visible;
            walkOverlay.visible = walkMeshVisible || walkProfileEditing;
        },
        getWalkMeshVisible: () => walkMeshVisible,
        setWalkProfileEditing,
        getWalkProfileEditing: () => walkProfileEditing,
        getWalkProfileSelection: () => walkProfileSelection,
        refreshWalkProfile() {
            rebuildWalkOverlay();
            rebuildWalkProfileControls();
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
