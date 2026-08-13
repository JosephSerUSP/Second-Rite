import * as THREE from 'three';
import { OrbitControls } from '/vendor/three/OrbitControls.js';

const FALLBACK = { wall: 0x777777, floor: 0x323232, opening: 0x8a6b3f, event: 0x3aa6d8 };

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
    object.traverse(child => {
        if (child.geometry) child.geometry.dispose();
        if (child.material) {
            (Array.isArray(child.material) ? child.material : [child.material]).forEach(material => {
                if (material.map) material.map.dispose();
                if (material.emissiveMap) material.emissiveMap.dispose();
                material.dispose();
            });
        }
    });
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
    const runtimeOrigin = coordinateSystem && coordinateSystem.runtimeGridOrigin || { x: 1, y: 1 };
    const ox = Number(runtimeOrigin.x || 1);
    const oy = Number(runtimeOrigin.y || 1);
    const sourcePositions = surface.positions || [];
    const positions = new Float32Array(sourcePositions.length);
    for (let i = 0; i + 2 < sourcePositions.length; i += 3) {
        // Second Rite is right-handed Z-up. Thestra's editor scene is Y-up with
        // authored zero-based map coordinates. This explicit adapter transform
        // keeps the bundle renderer-neutral and leaves schema coordinates alone.
        positions[i] = Number(sourcePositions[i]) - ox;
        positions[i + 1] = Number(sourcePositions[i + 2]);
        positions[i + 2] = Number(sourcePositions[i + 1]) - oy;
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

    const sourceUvs = surface.uvs || [];
    if (sourceUvs.length === (positions.length / 3) * 2) {
        geometry.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(sourceUvs.map(Number)), 2));
    }

    const sourceNormals = surface.normals || [];
    if (sourceNormals.length === positions.length) {
        const normals = new Float32Array(sourceNormals.length);
        for (let i = 0; i + 2 < sourceNormals.length; i += 3) {
            normals[i] = Number(sourceNormals[i]);
            normals[i + 1] = Number(sourceNormals[i + 2]);
            normals[i + 2] = Number(sourceNormals[i + 1]);
        }
        geometry.setAttribute('normal', new THREE.BufferAttribute(normals, 3));
    } else {
        geometry.computeVertexNormals();
    }

    const sourceColors = surface.colors || [];
    if (sourceColors.length === (positions.length / 3) * 4) {
        const colors = new Float32Array((positions.length / 3) * 3);
        for (let src = 0, dst = 0; src + 3 < sourceColors.length; src += 4, dst += 3) {
            colors[dst] = Number(sourceColors[src]);
            colors[dst + 1] = Number(sourceColors[src + 1]);
            colors[dst + 2] = Number(sourceColors[src + 2]);
        }
        geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    } else {
        const colors = new Float32Array(positions.length).fill(1);
        geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
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
    renderer.domElement.style.cssText = 'width:100%;height:100%;display:block;cursor:default;';
    container.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x24282d);
    scene.add(new THREE.HemisphereLight(0xffffff, 0x30343a, 2.0));
    const keyLight = new THREE.DirectionalLight(0xffffff, 2.2);
    keyLight.position.set(4, 8, 3);
    scene.add(keyLight);

    const semanticContent = new THREE.Group();
    semanticContent.name = 'ThestraSemanticScene';
    scene.add(semanticContent);

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
    const perspectiveControls = new OrbitControls(perspective, renderer.domElement);
    const topControls = new OrbitControls(top, renderer.domElement);
    perspectiveControls.enableDamping = true;
    topControls.enableDamping = true;
    topControls.enableRotate = false;
    topControls.screenSpacePanning = true;
    topControls.enabled = false;

    let mode = 'perspective';
    let sceneModel = null;
    let selection = null;
    let disposed = false;
    let hasAuthoritativeBundle = false;
    const selectable = [];
    const semanticObjects = new Map();
    const proxyMaterials = [];
    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();

    function activeCamera() { return mode === 'top' ? top : perspective; }

    function frameScene(resetPerspective) {
        if (!sceneModel) return;
        const width = Math.max(1, sceneModel.bounds.width);
        const height = Math.max(1, sceneModel.bounds.height);
        const cx = width / 2, cz = height / 2, span = Math.max(width, height, 4);
        if (resetPerspective) {
            perspective.position.set(cx + span * 0.75, span * 0.72, cz + span * 0.85);
            perspectiveControls.target.set(cx, 0.15, cz);
        }
        top.position.set(cx, span * 2.2, cz);
        top.up.set(0, 0, -1);
        top.lookAt(cx, 0, cz);
        topControls.target.set(cx, 0, cz);
        top.zoom = 1;
        perspectiveControls.update();
        topControls.update();
        resize();
    }

    function addSelectable(object, semantic) {
        object.userData.thestraSelection = semantic;
        selectable.push(object);
        if (semantic && semantic.key && !semanticObjects.has(semantic.key)) semanticObjects.set(semantic.key, object);
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
        const material = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: hasAuthoritativeBundle ? 0 : 0.72 });
        material.depthWrite = !hasAuthoritativeBundle;
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

    function addEvent(event) {
        const semantic = { kind: 'event', key: event.key, id: event.id, cell: event.cell };
        const group = new THREE.Group();
        group.position.set(event.world.x, 0, event.world.z);
        semanticContent.add(group);

        const cube = new THREE.Mesh(
            new THREE.BoxGeometry(0.92, 0.92, 0.92),
            new THREE.MeshBasicMaterial({ color: FALLBACK.event, transparent: true, opacity: 0.16, depthWrite: false })
        );
        cube.position.y = 0.46;
        group.add(cube);
        addSelectable(cube, semantic);
        semanticObjects.set(event.key, group);

        const edges = new THREE.LineSegments(
            new THREE.EdgesGeometry(cube.geometry),
            new THREE.LineBasicMaterial({ color: 0x61cfff, transparent: true, opacity: 0.9 })
        );
        edges.position.copy(cube.position);
        group.add(edges);
    }

    function rebuild(model) {
        const priorSelection = selection;
        while (semanticContent.children.length) disposeObject(semanticContent.children.pop());
        selectable.length = 0;
        semanticObjects.clear();
        proxyMaterials.length = 0;
        sceneModel = model;
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
                addSelectable(mesh, semantic);
            } else {
                const mesh = new THREE.Mesh(floorGeometry, cell.role === 'opening' ? openingMaterial : floorMaterial);
                mesh.position.set(cell.world.x, 0.01, cell.world.z);
                semanticContent.add(mesh);
                addSelectable(mesh, semantic);
            }
        });
        addGrid(sceneModel);
        sceneModel.events.forEach(addEvent);
        syncProxyVisibility();
        frameScene(true);
        setSelection(priorSelection);
    }

    function setRenderableBundle(bundle) {
        while (renderableContent.children.length) disposeObject(renderableContent.children.pop());
        hasAuthoritativeBundle = !!(bundle && Array.isArray(bundle.surfaces));
        syncProxyVisibility();
        if (!hasAuthoritativeBundle) return;

        const materialById = new Map();
        (bundle.materials || []).forEach(spec => materialById.set(spec.id, createBundleMaterial(spec)));
        (bundle.surfaces || []).forEach(surface => {
            if (!surface || !Array.isArray(surface.positions) || surface.positions.length < 9) return;
            const geometry = createBundleGeometry(surface, bundle.coordinateSystem || {});
            const material = materialById.get(surface.material)
                || new THREE.MeshStandardMaterial({ color: 0x777777, roughness: 0.9, side: THREE.DoubleSide, vertexColors: true });
            const mesh = new THREE.Mesh(geometry, material);
            mesh.name = surface.name || surface.id || 'runtime-surface';
            renderableContent.add(mesh);
            const semantic = semanticFromSource(surface.source);
            if (semantic) addSelectable(mesh, semantic);
        });
        setSelection(selection);
    }

    function setSelection(next) {
        selection = next || null;
        selectionOverlay.visible = false;
        if (!selection || !sceneModel) return;
        const object = semanticObjects.get(selection.key);
        if (selection.kind === 'cell' && selection.cell) {
            const cell = sceneModel.cells.find(entry => entry.key === selection.key);
            if (!cell) return;
            selectionOverlay.position.set(cell.world.x, cell.role === 'wall' ? 0.5 : 0.035, cell.world.z);
            selectionOverlay.scale.set(1, cell.role === 'wall' ? 1 : 0.05, 1);
            selectionOverlay.visible = true;
        } else if (object) {
            const box = new THREE.Box3().setFromObject(object);
            const size = new THREE.Vector3(), center = new THREE.Vector3();
            box.getSize(size); box.getCenter(center);
            selectionOverlay.position.copy(center);
            selectionOverlay.scale.set(Math.max(size.x, 0.2), Math.max(size.y, 0.2), Math.max(size.z, 0.2));
            selectionOverlay.visible = true;
        }
    }

    function setMode(nextMode) {
        if (nextMode !== 'perspective' && nextMode !== 'top') throw new Error(`Unsupported editor camera mode '${nextMode}'.`);
        mode = nextMode;
        perspectiveControls.enabled = mode === 'perspective';
        topControls.enabled = mode === 'top';
        resize();
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

    function onPointerDown(event) {
        if (!sceneModel) return;
        const rect = renderer.domElement.getBoundingClientRect();
        pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
        raycaster.setFromCamera(pointer, activeCamera());
        const hit = raycaster.intersectObjects(selectable, false)[0];
        if (!hit || !hit.object.userData.thestraSelection) return;
        const semantic = hit.object.userData.thestraSelection;
        setSelection(semantic);
        if (options.onSelection) options.onSelection(semantic);
    }

    renderer.domElement.addEventListener('pointerdown', onPointerDown);
    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(container);
    (function animate() {
        if (disposed) return;
        perspectiveControls.update();
        topControls.update();
        renderer.render(scene, activeCamera());
        requestAnimationFrame(animate);
    }());

    return {
        setSceneModel: rebuild,
        setRenderableBundle,
        setMode,
        getMode: () => mode,
        getSelection: () => selection,
        setSelection,
        frameScene: () => frameScene(true),
        dispose() {
            disposed = true;
            resizeObserver.disconnect();
            renderer.domElement.removeEventListener('pointerdown', onPointerDown);
            perspectiveControls.dispose();
            topControls.dispose();
            disposeObject(semanticContent);
            disposeObject(renderableContent);
            renderer.dispose();
            renderer.domElement.remove();
        }
    };
}
