import * as THREE from 'three';
import { OrbitControls } from '/vendor/three/OrbitControls.js';
import { TransformControls } from '/vendor/three/TransformControls.js';
import { OBJLoader } from '/vendor/three/OBJLoader.js';
import '/js/thestra-viewport-contract.js';

const Contract = globalThis.ThestraViewportContract;
if (!Contract) throw new Error('Thestra viewport coordinate contract failed to load.');

const FALLBACK = {
    wall: 0x777777,
    floor: 0x323232,
    opening: 0x8a6b3f,
    event: 0x3aa6d8,
    light: 0xffa63d,
    override: 0xeab308,
    spawn: 0x35b75a
};

function assetUrl(path) {
    if (!path) return null;
    return path.startsWith('/') ? path : '/' + path;
}

function imageUrl(payload) {
    if (!payload) return null;
    if (payload.kind === 'project-asset') return assetUrl(payload.path);
    if (payload.kind === 'embedded-png' && payload.base64) {
        return `data:${payload.mime || 'image/png'};base64,${payload.base64}`;
    }
    return null;
}

function disposeObject(object) {
    const geometries = new Set();
    const materials = new Set();
    const textures = new Set();
    object.traverse(child => {
        if (child.geometry) geometries.add(child.geometry);
        if (child.material) {
            (Array.isArray(child.material) ? child.material : [child.material])
                .forEach(material => materials.add(material));
        }
    });
    materials.forEach(material => {
        if (material.map) textures.add(material.map);
        if (material.emissiveMap) textures.add(material.emissiveMap);
    });
    textures.forEach(texture => texture.dispose());
    materials.forEach(material => material.dispose());
    geometries.forEach(geometry => geometry.dispose());
}

function clearGroup(group) {
    const doomed = new THREE.Group();
    while (group.children.length) doomed.add(group.children.pop());
    disposeObject(doomed);
}

function semanticFromSource(source) {
    if (!source || typeof source !== 'object') return null;
    if (source.kind === 'cell' && Number.isFinite(Number(source.x)) && Number.isFinite(Number(source.y))) {
        const x = Number(source.x), y = Number(source.y);
        return {
            kind: 'cell',
            key: `cell:${x}:${y}`,
            cell: { x, y },
            role: source.surface || null
        };
    }
    if (source.kind === 'event' && source.id != null) {
        return { kind: 'event', key: `event:${source.id}`, id: source.id };
    }
    return null;
}

function colorFrom01(rgb, fallback) {
    if (!Array.isArray(rgb) || rgb.length < 3) return new THREE.Color(fallback);
    return new THREE.Color(
        Math.max(0, Math.min(1, Number(rgb[0]) || 0)),
        Math.max(0, Math.min(1, Number(rgb[1]) || 0)),
        Math.max(0, Math.min(1, Number(rgb[2]) || 0))
    );
}

function createBundleMaterial(spec) {
    const color = Array.isArray(spec && spec.color) ? spec.color : [1, 1, 1, 1];
    const material = new THREE.MeshStandardMaterial({
        color: new THREE.Color(Number(color[0] ?? 1), Number(color[1] ?? 1), Number(color[2] ?? 1)),
        opacity: Number(color[3] ?? 1),
        transparent: Number(color[3] ?? 1) < 1,
        roughness: 0.9,
        metalness: 0,
        side: THREE.DoubleSide,
        vertexColors: true
    });

    const albedoUrl = imageUrl(spec && spec.albedo);
    if (albedoUrl) {
        new THREE.TextureLoader().load(albedoUrl, texture => {
            texture.colorSpace = THREE.SRGBColorSpace;
            texture.magFilter = THREE.NearestFilter;
            texture.minFilter = THREE.NearestFilter;
            texture.flipY = false;
            material.map = texture;
            material.needsUpdate = true;
        }, undefined, () => {});
    }

    const emissionUrl = imageUrl(spec && spec.emission);
    if (emissionUrl) {
        material.emissive = new THREE.Color(1, 1, 1);
        material.emissiveIntensity = 1;
        new THREE.TextureLoader().load(emissionUrl, texture => {
            texture.colorSpace = THREE.SRGBColorSpace;
            texture.magFilter = THREE.NearestFilter;
            texture.minFilter = THREE.NearestFilter;
            texture.flipY = false;
            material.emissiveMap = texture;
            material.needsUpdate = true;
        }, undefined, () => {});
    }
    return material;
}

function createBundleGeometry(surface, coordinateSystem) {
    const sourcePositions = surface.positions || [];
    const positions = new Float32Array(Contract.transformTriangleStream(
        sourcePositions, 3, value => Contract.runtimePositionToThestra(value, coordinateSystem)
    ));

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

    const sourceUvs = surface.uvs || [];
    if (sourceUvs.length === (positions.length / 3) * 2) {
        geometry.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(
            Contract.transformTriangleStream(sourceUvs, 2)
        ), 2));
    }

    const sourceNormals = surface.normals || [];
    if (sourceNormals.length === positions.length) {
        const normals = new Float32Array(Contract.transformTriangleStream(
            sourceNormals, 3, Contract.runtimeNormalToThestra
        ));
        geometry.setAttribute('normal', new THREE.BufferAttribute(normals, 3));
    } else {
        geometry.computeVertexNormals();
    }

    const sourceColors = surface.colors || [];
    if (sourceColors.length === (positions.length / 3) * 4) {
        const transformed = Contract.transformTriangleStream(sourceColors, 4);
        const colors = new Float32Array((positions.length / 3) * 3);
        for (let src = 0, dst = 0; src + 3 < transformed.length; src += 4, dst += 3) {
            colors[dst] = transformed[src];
            colors[dst + 1] = transformed[src + 1];
            colors[dst + 2] = transformed[src + 2];
        }
        geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    } else {
        geometry.setAttribute('color', new THREE.BufferAttribute(new Float32Array(positions.length).fill(1), 3));
    }

    geometry.computeBoundingBox();
    geometry.computeBoundingSphere();
    return geometry;
}

export function createThreeEditorViewport(container, options = {}) {
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.setClearColor(0x24282d, 1);
    renderer.domElement.style.cssText = 'width:100%;height:100%;display:block;cursor:default;touch-action:none;';
    renderer.domElement.tabIndex = 0;
    renderer.domElement.setAttribute('aria-label', '3D map viewport. Numpad 1: perspective; Numpad 7: top; Numpad 5: toggle; Home: frame map; Numpad decimal: frame selection; Escape: cancel transition.');
    renderer.domElement.addEventListener('contextmenu', event => event.preventDefault());
    container.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x24282d);
    scene.add(new THREE.HemisphereLight(0xffffff, 0x30343a, 2.0));
    const keyLight = new THREE.DirectionalLight(0xffffff, 2.2);
    keyLight.position.set(4, 8, 3);
    scene.add(keyLight);

    // Semantic content is the editing/picking vocabulary. It persists
    // independently of the authoritative bundle and can update immediately.
    const semanticContent = new THREE.Group();
    semanticContent.name = 'ThestraSemanticScene';
    scene.add(semanticContent);

    // Resolved visible world surfaces arrive asynchronously from #287.
    const renderableContent = new THREE.Group();
    renderableContent.name = 'SecondRiteAuthoritativeRenderables';
    scene.add(renderableContent);

    const selectionOverlay = new THREE.Mesh(
        new THREE.BoxGeometry(1.04, 1.04, 1.04),
        new THREE.MeshBasicMaterial({ color: 0xffd45a, wireframe: true, depthTest: false, transparent: true, opacity: 0.95 })
    );
    selectionOverlay.visible = false;
    selectionOverlay.renderOrder = 1000;
    scene.add(selectionOverlay);

    const perspective = new THREE.PerspectiveCamera(45, 1, 0.05, 500);
    const top = new THREE.OrthographicCamera(-10, 10, 10, -10, 0.05, 500);
    const transitionCamera = new THREE.PerspectiveCamera(45, 1, 0.05, 500);
    const perspectiveControls = new OrbitControls(perspective, renderer.domElement);
    const topControls = new OrbitControls(top, renderer.domElement);
    const moveGizmo = new TransformControls(perspective, renderer.domElement);
    moveGizmo.setMode('translate');
    moveGizmo.space = 'world';
    // Authoring positions are cell centres (n + .5), not Three's integer
    // world grid. Snap object changes below rather than letting
    // TransformControls pull a live object onto a half-tile.
    moveGizmo.translationSnap = null;
    moveGizmo.showX = true;
    moveGizmo.showY = false;
    moveGizmo.showZ = true;
    moveGizmo.showXY = false;
    moveGizmo.showYZ = false;
    moveGizmo.showXZ = true;
    moveGizmo.showXYZE = false;
    // Keep the familiar axis distinction without importing the saturated
    // primary-color vocabulary of a generic 3D package into this editor.
    moveGizmo.setColors(0xb98278, 0x829679, 0x748fae, 0xc8b77d);
    moveGizmo.enabled = false;
    // Current Three exposes the rendered gizmo as a helper; the control
    // itself owns input and state but is not an Object3D.
    scene.add(moveGizmo.getHelper());
    perspectiveControls.enableDamping = true;
    topControls.enableDamping = true;
    topControls.enableRotate = false;
    topControls.screenSpacePanning = true;
    topControls.enabled = false;

    // Left mouse belongs to authored interaction. Navigation stays available
    // with right drag and middle/wheel so Perspective remains an editing mode.
    perspectiveControls.mouseButtons.LEFT = null;
    perspectiveControls.mouseButtons.MIDDLE = THREE.MOUSE.DOLLY;
    perspectiveControls.mouseButtons.RIGHT = THREE.MOUSE.ROTATE;
    topControls.mouseButtons.LEFT = null;
    topControls.mouseButtons.MIDDLE = THREE.MOUSE.DOLLY;
    topControls.mouseButtons.RIGHT = THREE.MOUSE.PAN;

    let mode = 'perspective';
    let sceneModel = null;
    let selection = null;
    let disposed = false;
    let hasAuthoritativeBundle = false;
    let editGesture = null;
    let moveGesture = null;
    let lastPaintKey = null;
    let priorMapIdentity = null;
    let cameraTransition = null;

    const semanticSelectable = [];
    const renderableSelectable = [];
    const cellSelectable = [];
    const semanticObjects = new Map();
    const proxyMaterials = [];
    const lightVisuals = [];
    const eventVisuals = [];
    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();

    function activeCamera() { return cameraTransition ? transitionCamera : (mode === 'top' ? top : perspective); }
    function interactionLayer() { return options.getInteractionMode ? options.getInteractionMode() : null; }
    function allSelectable() { return semanticSelectable.concat(renderableSelectable); }

    function setControlsEnabled(enabled) {
        perspectiveControls.enabled = enabled && mode === 'perspective';
        topControls.enabled = enabled && mode === 'top';
    }

    function mapIdentity(model) {
        if (!model) return null;
        return `${model.map && model.map.id}|${model.bounds.width}x${model.bounds.height}`;
    }

    function frameScene(reset) {
        if (!sceneModel) return;
        const width = Math.max(1, sceneModel.bounds.width);
        const height = Math.max(1, sceneModel.bounds.height);
        const cx = width / 2, cz = height / 2, span = Math.max(width, height, 4);
        if (reset) {
            perspective.position.set(cx + span * 0.75, span * 0.72, cz + span * 0.85);
            perspectiveControls.target.set(cx, 0.15, cz);
            top.position.set(cx, span * 2.2, cz);
            top.up.set(0, 0, -1);
            top.lookAt(cx, 0, cz);
            topControls.target.set(cx, 0, cz);
            top.zoom = 1;
            perspectiveControls.update();
            topControls.update();
        }
        resize();
    }

    function frameSelection() {
        const object = selection && semanticObjects.get(selection.key);
        if (!object) { frameScene(true); return; }
        const box = new THREE.Box3().setFromObject(object);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());
        const radius = Math.max(2, size.length() * 1.8);
        const camera = mode === 'top' ? top : perspective;
        const controls = mode === 'top' ? topControls : perspectiveControls;
        const offset = camera.position.clone().sub(controls.target);
        if (offset.lengthSq() < 0.001) offset.set(1, 1, 1);
        offset.setLength(radius);
        controls.target.copy(center);
        camera.position.copy(center).add(offset);
        camera.updateProjectionMatrix();
        controls.update();
    }

    function onCameraKeyDown(event) {
        const action = Contract.cameraShortcut(event, document.activeElement === renderer.domElement);
        if (!action || moveGizmo.dragging) return;
        event.preventDefault();
        if (action === 'toggle-projection') transitionToMode(mode === 'top' ? 'perspective' : 'top');
        else if (action === 'top') transitionToMode('top');
        else if (action === 'perspective') transitionToMode('perspective');
        else if (action === 'frame-all') frameScene(true);
        else if (action === 'frame-selection') frameSelection();
        else if (action === 'cancel-navigation' && cameraTransition) {
            const cancelled = cameraTransition;
            cameraTransition = null;
            setControlsEnabled(!editGesture);
            syncMoveGizmo();
            cancelled.resolve();
        }
    }

    function addSemanticSelectable(object, semantic, isCell) {
        object.userData.thestraSelection = semantic;
        semanticSelectable.push(object);
        if (isCell) cellSelectable.push(object);
        if (semantic && semantic.key && !semanticObjects.has(semantic.key)) semanticObjects.set(semantic.key, object);
    }

    function addRenderableSelectable(object, semantic) {
        object.userData.thestraSelection = semantic;
        renderableSelectable.push(object);
    }

    function addGrid(model) {
        const size = Math.max(model.bounds.width, model.bounds.height);
        const grid = new THREE.GridHelper(size, size, 0x7b8791, 0x515961);
        grid.position.set(size / 2, 0.006, size / 2);
        grid.material.transparent = true;
        grid.material.opacity = 0.35;
        grid.userData.editorOverlay = true;
        semanticContent.add(grid);
    }

    function makeProxyMaterial(color) {
        // Opacity zero still leaves the semantic mesh raycastable. This is
        // intentional: final triangles are presentation facts; these simple
        // authored-cell proxies remain the legal write targets.
        const material = new THREE.MeshBasicMaterial({
            color,
            transparent: true,
            opacity: hasAuthoritativeBundle ? 0 : 0.72,
            depthWrite: !hasAuthoritativeBundle
        });
        proxyMaterials.push(material);
        return material;
    }

    function syncProxyVisibility() {
        proxyMaterials.forEach(material => {
            material.opacity = hasAuthoritativeBundle ? 0 : 0.72;
            material.depthWrite = !hasAuthoritativeBundle;
            material.needsUpdate = true;
        });
    }

    function syncLayerVisuals() {
        const showingLights = interactionLayer() === 'light';
        lightVisuals.forEach(({ marker, ring }) => {
            // Lights are authored controls, not ordinary map decoration. Keep
            // the selectable marker quiet outside their own layer and reserve
            // the radius annotation for the layer where it can be edited.
            marker.visible = showingLights;
            ring.visible = showingLights;
        });
        eventVisuals.forEach(({ visual, fallback }) => {
            // Events are authored entities, not a temporary semantic proxy.
            // Keep their model/sprite billboards visible over real geometry;
            // the bundle only replaces floor/wall proxy surfaces.
            if (visual) visual.visible = true;
            if (fallback) fallback.visible = !visual || !visual.children.length;
        });
        syncMoveGizmo();
    }

    function selectedMovableObject() {
        if (!selection || (selection.kind !== 'event' && selection.kind !== 'light')) return null;
        if (interactionLayer() !== selection.kind) return null;
        return semanticObjects.get(selection.key) || null;
    }

    function syncMoveGizmo() {
        const object = selectedMovableObject();
        moveGizmo.camera = activeCamera();
        moveGizmo.enabled = !!object && !cameraTransition;
        if (object && moveGizmo.object !== object) moveGizmo.attach(object);
        if (!object && moveGizmo.object) moveGizmo.detach();
    }

    function fitEventModel(object) {
        const bounds = new THREE.Box3().setFromObject(object);
        const size = new THREE.Vector3();
        bounds.getSize(size);
        const largest = Math.max(size.x, size.y, size.z, 0.001);
        object.scale.multiplyScalar(0.86 / largest);
        bounds.setFromObject(object);
        const center = new THREE.Vector3();
        bounds.getCenter(center);
        object.position.sub(center);
        const grounded = new THREE.Box3().setFromObject(object);
        object.position.y -= grounded.min.y;
    }

    function addEventVisual(group, event, fallback) {
        const plan = Contract.eventVisualPlan(event.asset);
        if (plan.kind === 'fallback') return { visual: null, fallback };
        const visual = new THREE.Group();
        visual.name = `Effective event ${plan.kind}: ${plan.path}`;
        group.add(visual);
        if (plan.kind === 'sprite') {
            new THREE.TextureLoader().load(assetUrl(plan.path), texture => {
                texture.colorSpace = THREE.SRGBColorSpace;
                texture.magFilter = THREE.NearestFilter;
                texture.minFilter = THREE.NearestFilter;
                const aspect = texture.image && texture.image.width && texture.image.height
                    ? texture.image.width / texture.image.height : 1;
                const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: texture, transparent: true }));
                sprite.position.y = 0.48;
                sprite.scale.set(Math.min(0.9, 0.9 * aspect), 0.9, 1);
                visual.add(sprite);
            }, undefined, () => {
                visual.removeFromParent();
                const entry = eventVisuals.find(candidate => candidate.visual === visual);
                if (entry) entry.fallback.visible = true;
            });
        } else {
            new OBJLoader().load(assetUrl(plan.path), object => {
                object.traverse(child => {
                    if (!child.isMesh) return;
                    const materials = Array.isArray(child.material) ? child.material : [child.material];
                    materials.forEach(material => { material.side = THREE.DoubleSide; });
                });
                fitEventModel(object);
                object.position.y = 0.01;
                visual.add(object);
            }, undefined, () => {
                visual.removeFromParent();
                const entry = eventVisuals.find(candidate => candidate.visual === visual);
                if (entry) entry.fallback.visible = true;
            });
        }
        fallback.visible = false;
        return { visual, fallback };
    }

    function addEvent(event) {
        const semantic = {
            kind: 'event', key: event.key, id: event.id, index: event.index, cell: event.cell
        };
        const group = new THREE.Group();
        group.position.set(event.world.x, 0, event.world.z);
        semanticContent.add(group);

        const cube = new THREE.Mesh(
            new THREE.BoxGeometry(0.92, 0.92, 0.92),
            new THREE.MeshBasicMaterial({ color: FALLBACK.event, transparent: true, opacity: 0.16, depthWrite: false })
        );
        cube.position.y = 0.46;
        group.add(cube);
        addSemanticSelectable(cube, semantic, false);
        semanticObjects.set(event.key, group);

        const edges = new THREE.LineSegments(
            new THREE.EdgesGeometry(cube.geometry),
            new THREE.LineBasicMaterial({ color: 0x61cfff, transparent: true, opacity: 0.9 })
        );
        edges.position.copy(cube.position);
        group.add(edges);
        eventVisuals.push(addEventVisual(group, event, edges));
    }

    function addLight(light) {
        const semantic = { kind: 'light', key: light.key, index: light.index, cell: light.cell };
        const group = new THREE.Group();
        group.position.set(light.world.x, 0, light.world.z);
        semanticContent.add(group);

        const color = colorFrom01(light.color, FALLBACK.light);
        const marker = new THREE.Mesh(
            new THREE.SphereGeometry(0.16, 12, 8),
            new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: 0.9, roughness: 0.45 })
        );
        marker.position.y = 0.58;
        group.add(marker);
        addSemanticSelectable(marker, semantic, false);
        semanticObjects.set(light.key, group);

        const radius = Math.max(0.1, Number(light.radius) || 4);
        const inner = Math.max(0.01, radius - 0.025);
        const ring = new THREE.Mesh(
            new THREE.RingGeometry(inner, radius + 0.025, 64),
            new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.34, side: THREE.DoubleSide, depthWrite: false })
        );
        ring.rotation.x = -Math.PI / 2;
        ring.position.y = 0.022;
        group.add(ring);
        lightVisuals.push({ marker, ring });
    }

    function addOverride(override) {
        const semantic = { kind: 'override', key: override.key, index: override.index, cell: override.cell };
        const marker = new THREE.Mesh(
            new THREE.PlaneGeometry(0.78, 0.78),
            new THREE.MeshBasicMaterial({ color: FALLBACK.override, transparent: true, opacity: 0.32, side: THREE.DoubleSide, depthWrite: false })
        );
        marker.rotation.x = -Math.PI / 2;
        marker.position.set(override.world.x, override.world.y, override.world.z);
        semanticContent.add(marker);
        addSemanticSelectable(marker, semantic, false);
        semanticObjects.set(override.key, marker);
    }

    function addSpawn(spawn) {
        if (!spawn) return;
        const semantic = { kind: 'spawn', key: spawn.key, cell: spawn.cell };
        const marker = new THREE.Mesh(
            new THREE.ConeGeometry(0.18, 0.42, 8),
            new THREE.MeshBasicMaterial({ color: FALLBACK.spawn, transparent: true, opacity: 0.9 })
        );
        marker.position.set(spawn.world.x, 0.23, spawn.world.z);
        semanticContent.add(marker);
        addSemanticSelectable(marker, semantic, false);
        semanticObjects.set(spawn.key, marker);
    }

    function rebuild(model) {
        const priorSelection = selection;
        const nextIdentity = mapIdentity(model);
        const shouldFrame = priorMapIdentity !== nextIdentity;

        moveGizmo.detach();
        clearGroup(semanticContent);
        semanticSelectable.length = 0;
        cellSelectable.length = 0;
        semanticObjects.clear();
        proxyMaterials.length = 0;
        lightVisuals.length = 0;
        eventVisuals.length = 0;
        sceneModel = model;
        priorMapIdentity = nextIdentity;
        if (!sceneModel) return;

        const wallGeometry = new THREE.BoxGeometry(1, 1, 1);
        const floorGeometry = new THREE.PlaneGeometry(1, 1);
        floorGeometry.rotateX(-Math.PI / 2);
        const wallMaterial = makeProxyMaterial(FALLBACK.wall);
        const floorMaterial = makeProxyMaterial(FALLBACK.floor);
        const openingMaterial = makeProxyMaterial(FALLBACK.opening);

        sceneModel.cells.forEach(cell => {
            const semantic = { kind: 'cell', key: cell.key, cell: cell.cell, role: cell.role };
            if (cell.role === 'wall') {
                const mesh = new THREE.Mesh(wallGeometry, wallMaterial);
                mesh.position.set(cell.world.x, 0.5, cell.world.z);
                semanticContent.add(mesh);
                addSemanticSelectable(mesh, semantic, true);
            } else {
                const mesh = new THREE.Mesh(floorGeometry, cell.role === 'opening' ? openingMaterial : floorMaterial);
                mesh.position.set(cell.world.x, 0.01, cell.world.z);
                semanticContent.add(mesh);
                addSemanticSelectable(mesh, semantic, true);
            }
        });
        addGrid(sceneModel);
        (sceneModel.events || []).forEach(addEvent);
        (sceneModel.lights || []).forEach(addLight);
        ((sceneModel.annotations && sceneModel.annotations.overrides) || []).forEach(addOverride);
        addSpawn(sceneModel.annotations && sceneModel.annotations.spawn);
        syncProxyVisibility();
        syncLayerVisuals();
        frameScene(shouldFrame);
        setSelection(priorSelection);
    }

    function setRenderableBundle(bundle) {
        clearGroup(renderableContent);
        renderableSelectable.length = 0;
        hasAuthoritativeBundle = !!(bundle && Array.isArray(bundle.surfaces));
        syncProxyVisibility();
        syncLayerVisuals();
        if (!hasAuthoritativeBundle) {
            setSelection(selection);
            return;
        }

        const materialById = new Map();
        (bundle.materials || []).forEach(spec => materialById.set(spec.id, createBundleMaterial(spec)));
        (bundle.surfaces || []).forEach(surface => {
            if (!surface || !Array.isArray(surface.positions) || surface.positions.length < 9) return;
            const geometry = createBundleGeometry(surface, bundle.coordinateSystem || {});
            const material = materialById.get(surface.material)
                || new THREE.MeshStandardMaterial({
                    color: 0x777777, roughness: 0.9, side: THREE.DoubleSide, vertexColors: true
                });
            const mesh = new THREE.Mesh(geometry, material);
            mesh.name = surface.name || surface.id || 'runtime-surface';
            renderableContent.add(mesh);
            const semantic = semanticFromSource(surface.source);
            if (semantic) addRenderableSelectable(mesh, semantic);
        });
        setSelection(selection);
    }

    function setSelection(next) {
        selection = next || null;
        selectionOverlay.visible = false;
        if (!selection || !sceneModel) {
            syncMoveGizmo();
            return;
        }

        if (selection.kind === 'cell' && selection.cell) {
            const cell = sceneModel.cells.find(entry => entry.key === selection.key);
            if (!cell) {
                syncMoveGizmo();
                return;
            }
            selectionOverlay.position.set(cell.world.x, cell.role === 'wall' ? 0.5 : 0.035, cell.world.z);
            selectionOverlay.scale.set(1, cell.role === 'wall' ? 1 : 0.05, 1);
            selectionOverlay.visible = true;
            syncMoveGizmo();
            return;
        }

        const object = semanticObjects.get(selection.key);
        if (!object) {
            syncMoveGizmo();
            return;
        }
        const box = new THREE.Box3().setFromObject(object);
        const size = new THREE.Vector3(), center = new THREE.Vector3();
        box.getSize(size); box.getCenter(center);
        selectionOverlay.position.copy(center);
        selectionOverlay.scale.set(
            Math.max(size.x, 0.2), Math.max(size.y, 0.2), Math.max(size.z, 0.2)
        );
        selectionOverlay.visible = true;
        syncMoveGizmo();
    }

    function setMode(nextMode) {
        if (nextMode !== 'perspective' && nextMode !== 'top') {
            throw new Error(`Unsupported editor camera mode '${nextMode}'.`);
        }
        mode = nextMode;
        setControlsEnabled(!editGesture);
        syncMoveGizmo();
        resize();
    }

    function cameraFovFor(camera, target) {
        if (camera.isPerspectiveCamera) return camera.fov;
        const distance = Math.max(camera.position.distanceTo(target), 0.001);
        const visibleHeight = (camera.top - camera.bottom) / Math.max(camera.zoom, 0.001);
        return THREE.MathUtils.radToDeg(2 * Math.atan(visibleHeight / (2 * distance)));
    }

    function transitionToMode(nextMode) {
        if (nextMode !== 'perspective' && nextMode !== 'top') {
            throw new Error(`Unsupported editor camera mode '${nextMode}'.`);
        }
        if (nextMode === mode || !sceneModel
                || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            setMode(nextMode);
            return Promise.resolve();
        }

        const source = mode === 'top' ? top : perspective;
        const destination = nextMode === 'top' ? top : perspective;
        const sourceTarget = mode === 'top' ? topControls.target : perspectiveControls.target;
        const destinationTarget = nextMode === 'top' ? topControls.target : perspectiveControls.target;
        transitionCamera.position.copy(source.position);
        transitionCamera.quaternion.copy(source.quaternion);
        transitionCamera.fov = cameraFovFor(source, sourceTarget);
        transitionCamera.aspect = perspective.aspect;
        transitionCamera.updateProjectionMatrix();
        return new Promise(resolve => {
            cameraTransition = {
            nextMode,
            startedAt: performance.now(),
            duration: 240,
            startPosition: source.position.clone(),
            startQuaternion: source.quaternion.clone(),
            startFov: transitionCamera.fov,
            endPosition: destination.position.clone(),
            endQuaternion: destination.quaternion.clone(),
                endFov: cameraFovFor(destination, destinationTarget),
                resolve
            };
            setControlsEnabled(false);
        });
    }

    function updateCameraTransition(now) {
        if (!cameraTransition) return;
        const elapsed = Math.min(1, (now - cameraTransition.startedAt) / cameraTransition.duration);
        const eased = elapsed < 0.5
            ? 4 * elapsed * elapsed * elapsed
            : 1 - Math.pow(-2 * elapsed + 2, 3) / 2;
        transitionCamera.position.lerpVectors(cameraTransition.startPosition, cameraTransition.endPosition, eased);
        transitionCamera.quaternion.slerpQuaternions(
            cameraTransition.startQuaternion, cameraTransition.endQuaternion, eased
        );
        transitionCamera.fov = THREE.MathUtils.lerp(cameraTransition.startFov, cameraTransition.endFov, eased);
        transitionCamera.updateProjectionMatrix();
        if (elapsed >= 1) {
            const completed = cameraTransition;
            mode = completed.nextMode;
            cameraTransition = null;
            setControlsEnabled(!editGesture);
            syncMoveGizmo();
            completed.resolve();
        }
    }

    function resize() {
        const rect = container.getBoundingClientRect();
        const width = Math.max(1, Math.floor(rect.width));
        const height = Math.max(1, Math.floor(rect.height));
        renderer.setSize(width, height, false);
        perspective.aspect = width / height;
        perspective.updateProjectionMatrix();
        const span = sceneModel ? Math.max(sceneModel.bounds.width, sceneModel.bounds.height, 4) : 10;
        const halfH = span * 0.6, halfW = halfH * (width / height);
        top.left = -halfW; top.right = halfW; top.top = halfH; top.bottom = -halfH;
        top.updateProjectionMatrix();
    }

    function updatePointer(event) {
        const rect = renderer.domElement.getBoundingClientRect();
        pointer.x = ((event.clientX - rect.left) / Math.max(rect.width, 1)) * 2 - 1;
        pointer.y = -((event.clientY - rect.top) / Math.max(rect.height, 1)) * 2 + 1;
        raycaster.setFromCamera(pointer, activeCamera());
    }

    function pickSemantic(event, acceptedKinds) {
        if (!sceneModel) return null;
        updatePointer(event);
        const hits = raycaster.intersectObjects(allSelectable(), false);
        for (const hit of hits) {
            const semantic = hit.object.userData.thestraSelection;
            if (!semantic) continue;
            if (!acceptedKinds || acceptedKinds.includes(semantic.kind)) return semantic;
        }
        return null;
    }

    function pickCell(event) {
        if (!sceneModel) return null;
        updatePointer(event);
        const hit = raycaster.intersectObjects(cellSelectable, false)[0];
        return hit && hit.object.userData.thestraSelection || null;
    }

    function emitSelection(semantic) {
        setSelection(semantic);
        if (options.onSelection) options.onSelection(semantic);
    }

    function paintSelection(cell) {
        if (!cell || cell.key === lastPaintKey) return;
        lastPaintKey = cell.key;
        emitSelection(cell);
        if (options.onPaintCell) options.onPaintCell(cell);
    }

    function canDrop(kind, semantic, cell) {
        if (!cell) return { ok: false, reason: 'no-cell' };
        if (kind === 'event' && options.canMoveEvent) {
            return options.canMoveEvent(semantic, cell) || { ok: false };
        }
        if (kind === 'light' && options.canMoveLight) {
            return options.canMoveLight(semantic, cell) || { ok: false };
        }
        return { ok: true, changed: true };
    }

    function onPointerDown(event) {
        if (!sceneModel || event.button !== 0) return;
        // TransformControls consumes the next left press once a selected
        // event/light exposes its X/Z handles. A normal object click merely
        // selects: only the visible gizmo can begin an authored move.
        if (moveGizmo.dragging || moveGizmo.axis) return;
        const layer = interactionLayer();
        const kinds = {
            map: event.shiftKey ? ['spawn', 'cell'] : ['cell'],
            event: ['event', 'cell'],
            light: ['light', 'cell'],
            override: ['override', 'cell']
        }[layer] || null;
        const semantic = pickSemantic(event, kinds) || pickCell(event);
        if (!semantic) return;
        emitSelection(semantic);

        if (layer === 'map' && semantic.kind === 'cell') {
            editGesture = { kind: 'paint' };
            lastPaintKey = null;
            setControlsEnabled(false);
            paintSelection(semantic);
        }
    }

    function onPointerMove(event) {
        if (!editGesture) return;
        paintSelection(pickCell(event));
    }

    function onPointerUp() {
        if (!editGesture) return;
        editGesture = null;
        lastPaintKey = null;
        setControlsEnabled(true);
    }

    moveGizmo.addEventListener('mouseDown', () => {
        const object = selectedMovableObject();
        if (!object || !selection) return;
        moveGesture = { semantic: selection, origin: object.position.clone() };
        setControlsEnabled(false);
    });

    moveGizmo.addEventListener('objectChange', () => {
        if (!moveGesture || !moveGizmo.object) return;
        // Preserve the authored ground plane and show the final legal cell
        // centre throughout the drag, not only after the mutation commits.
        moveGizmo.object.position.x = Contract.cellCenter(moveGizmo.object.position.x);
        moveGizmo.object.position.y = moveGesture.origin.y;
        moveGizmo.object.position.z = Contract.cellCenter(moveGizmo.object.position.z);
    });

    moveGizmo.addEventListener('mouseUp', () => {
        const gesture = moveGesture;
        moveGesture = null;
        setControlsEnabled(true);
        if (!gesture) return;
        const object = selectedMovableObject();
        if (!object) return;
        const x = Contract.cellCoordinate(object.position.x);
        const y = Contract.cellCoordinate(object.position.z);
        const cell = (sceneModel.cells || []).find(entry => entry.cell.x === x && entry.cell.y === y);
        const validation = canDrop(gesture.semantic.kind, gesture.semantic, cell && {
            kind: 'cell', key: cell.key, cell: cell.cell, role: cell.role
        });
        if (!validation.ok || !validation.changed) {
            object.position.copy(gesture.origin);
            return;
        }
        let result = null;
        if (gesture.semantic.kind === 'event' && options.onMoveEvent) {
            result = options.onMoveEvent(gesture.semantic, cell);
        } else if (gesture.semantic.kind === 'light' && options.onMoveLight) {
            result = options.onMoveLight(gesture.semantic, cell);
        }
        if (result && result.selection) emitSelection(result.selection);
        else object.position.copy(gesture.origin);
    });

    function onDoubleClick(event) {
        if (!sceneModel) return;
        const layer = interactionLayer();
        const kinds = {
            event: ['event', 'cell'],
            light: ['light', 'cell'],
            override: ['override', 'cell']
        }[layer];
        if (!kinds) return;
        const semantic = pickSemantic(event, kinds) || pickCell(event);
        if (semantic && options.onOpenAt) options.onOpenAt(semantic);
    }

    function onCanvasPointerDown(event) {
        renderer.domElement.focus({ preventScroll: true });
        onPointerDown(event);
    }
    renderer.domElement.addEventListener('pointerdown', onCanvasPointerDown);
    renderer.domElement.addEventListener('pointermove', onPointerMove);
    renderer.domElement.addEventListener('dblclick', onDoubleClick);
    renderer.domElement.addEventListener('keydown', onCameraKeyDown);
    window.addEventListener('pointerup', onPointerUp);
    window.addEventListener('pointercancel', onPointerUp);

    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(container);
    (function animate(now) {
        if (disposed) return;
        updateCameraTransition(now);
        moveGizmo.camera = activeCamera();
        syncLayerVisuals();
        perspectiveControls.update();
        topControls.update();
        renderer.render(scene, activeCamera());
        requestAnimationFrame(animate);
    }());

    return {
        setSceneModel: rebuild,
        setRenderableBundle,
        setMode,
        transitionToMode,
        getMode: () => mode,
        getSelection: () => selection,
        setSelection,
        frameScene: () => frameScene(true),
        dispose() {
            disposed = true;
            resizeObserver.disconnect();
            renderer.domElement.removeEventListener('pointerdown', onCanvasPointerDown);
            renderer.domElement.removeEventListener('pointermove', onPointerMove);
            renderer.domElement.removeEventListener('dblclick', onDoubleClick);
            renderer.domElement.removeEventListener('keydown', onCameraKeyDown);
            window.removeEventListener('pointerup', onPointerUp);
            window.removeEventListener('pointercancel', onPointerUp);
            perspectiveControls.dispose();
            topControls.dispose();
            disposeObject(semanticContent);
            disposeObject(renderableContent);
            selectionOverlay.geometry.dispose();
            selectionOverlay.material.dispose();
            moveGizmo.detach();
            moveGizmo.dispose();
            renderer.dispose();
            renderer.domElement.remove();
        }
    };
}
