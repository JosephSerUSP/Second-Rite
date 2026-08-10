import * as THREE from 'three';
import { OrbitControls } from '/vendor/three/OrbitControls.js';
import { OBJLoader } from '/vendor/three/OBJLoader.js';

const FALLBACK = { wall: 0x777777, floor: 0x323232, opening: 0x8a6b3f, event: 0x3aa6d8 };

function assetUrl(path) { return path ? (path.startsWith('/') ? path : '/' + path) : null; }

function createAtlasMaterial(sceneModel, role, fallbackColor) {
    const material = new THREE.MeshStandardMaterial({ color: fallbackColor, roughness: 0.9, metalness: 0 });
    const texturePath = sceneModel.assets && sceneModel.assets.texture;
    const def = sceneModel.assets && sceneModel.assets[role];
    const atlas = def && (def.atlas || def.middle);
    const tileWidth = sceneModel.assets && sceneModel.assets.tileWidth;
    const tileHeight = sceneModel.assets && sceneModel.assets.tileHeight;
    if (!texturePath || !atlas || !tileWidth || !tileHeight) return material;

    new THREE.TextureLoader().load(assetUrl(texturePath), texture => {
        texture.colorSpace = THREE.SRGBColorSpace;
        texture.magFilter = THREE.NearestFilter;
        texture.minFilter = THREE.NearestFilter;
        texture.wrapS = THREE.ClampToEdgeWrapping;
        texture.wrapT = THREE.ClampToEdgeWrapping;
        const image = texture.image;
        if (image && image.width && image.height) {
            const rx = tileWidth / image.width;
            const ry = tileHeight / image.height;
            texture.repeat.set(rx, ry);
            texture.offset.set(Number(atlas[0] || 0) * rx, 1 - (Number(atlas[1] || 0) + 1) * ry);
        }
        material.map = texture;
        material.color.setHex(0xffffff);
        material.needsUpdate = true;
    }, undefined, () => {});
    return material;
}

function disposeObject(object) {
    object.traverse(child => {
        if (child.geometry) child.geometry.dispose();
        if (child.material) {
            (Array.isArray(child.material) ? child.material : [child.material]).forEach(material => {
                if (material.map) material.map.dispose();
                material.dispose();
            });
        }
    });
}

function fitObjectIntoCell(object) {
    const box = new THREE.Box3().setFromObject(object);
    const size = new THREE.Vector3();
    const center = new THREE.Vector3();
    box.getSize(size);
    box.getCenter(center);
    const scale = 0.78 / Math.max(size.x, size.y, size.z, 0.0001);
    object.scale.setScalar(scale);
    object.position.sub(center.multiplyScalar(scale));
    object.position.y += 0.1;
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

    const content = new THREE.Group();
    content.name = 'ThestraEditorSceneContent';
    scene.add(content);

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
    const selectable = [];
    const semanticObjects = new Map();
    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    const objLoader = new OBJLoader();

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
        content.add(grid);
    }

    function addEvent(event) {
        const semantic = { kind: 'event', key: event.key, id: event.id, cell: event.cell };
        const group = new THREE.Group();
        group.position.set(event.world.x, 0, event.world.z);
        content.add(group);

        const cube = new THREE.Mesh(
            new THREE.BoxGeometry(0.92, 0.92, 0.92),
            new THREE.MeshBasicMaterial({ color: FALLBACK.event, transparent: true, opacity: 0.16, depthWrite: false })
        );
        cube.position.y = 0.46;
        group.add(cube);
        addSelectable(cube, semantic);
        semanticObjects.set(event.key, group);

        const edges = new THREE.LineSegments(new THREE.EdgesGeometry(cube.geometry), new THREE.LineBasicMaterial({ color: 0x61cfff, transparent: true, opacity: 0.9 }));
        edges.position.copy(cube.position);
        group.add(edges);

        if (event.asset && event.asset.model) {
            objLoader.load(assetUrl(event.asset.model), object => {
                fitObjectIntoCell(object);
                object.position.y += 0.08;
                object.traverse(child => { if (child.isMesh) addSelectable(child, semantic); });
                group.add(object);
            }, undefined, () => {});
        } else if (event.asset && event.asset.sprite) {
            new THREE.TextureLoader().load(assetUrl(event.asset.sprite), texture => {
                texture.colorSpace = THREE.SRGBColorSpace;
                texture.magFilter = THREE.NearestFilter;
                texture.minFilter = THREE.NearestFilter;
                const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: texture, transparent: true, alphaTest: 0.05 }));
                sprite.scale.set(0.72, 0.72, 0.72);
                sprite.position.y = 0.48;
                addSelectable(sprite, semantic);
                group.add(sprite);
            }, undefined, () => {});
        }
    }

    function rebuild(model) {
        const priorSelection = selection;
        while (content.children.length) {
            const child = content.children.pop();
            disposeObject(child);
        }
        selectable.length = 0;
        semanticObjects.clear();
        sceneModel = model;
        if (!sceneModel) return;

        const wallMaterial = createAtlasMaterial(sceneModel, 'wall', FALLBACK.wall);
        const floorMaterial = createAtlasMaterial(sceneModel, 'floor', FALLBACK.floor);
        const openingMaterial = createAtlasMaterial(sceneModel, 'door', FALLBACK.opening);
        const wallGeometry = new THREE.BoxGeometry(1, 1, 1);
        const floorGeometry = new THREE.PlaneGeometry(1, 1);
        floorGeometry.rotateX(-Math.PI / 2);

        sceneModel.cells.forEach(cell => {
            const semantic = { kind: 'cell', key: cell.key, cell: cell.cell, role: cell.role };
            if (cell.role === 'wall') {
                const mesh = new THREE.Mesh(wallGeometry, wallMaterial);
                mesh.position.set(cell.world.x, 0.5, cell.world.z);
                content.add(mesh);
                addSelectable(mesh, semantic);
            } else {
                const mesh = new THREE.Mesh(floorGeometry, cell.role === 'opening' ? openingMaterial : floorMaterial);
                mesh.position.set(cell.world.x, 0.01, cell.world.z);
                content.add(mesh);
                addSelectable(mesh, semantic);
            }
        });
        addGrid(sceneModel);
        sceneModel.events.forEach(addEvent);
        frameScene(true);
        setSelection(priorSelection);
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
        perspectiveControls.update(); topControls.update();
        renderer.render(scene, activeCamera());
        requestAnimationFrame(animate);
    }());

    return {
        setSceneModel: rebuild,
        setMode,
        getMode: () => mode,
        getSelection: () => selection,
        setSelection,
        frameScene: () => frameScene(true),
        dispose() {
            disposed = true;
            resizeObserver.disconnect();
            renderer.domElement.removeEventListener('pointerdown', onPointerDown);
            perspectiveControls.dispose(); topControls.dispose();
            disposeObject(content); renderer.dispose(); renderer.domElement.remove();
        }
    };
}
