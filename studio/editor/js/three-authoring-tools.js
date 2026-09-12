import * as THREE from 'three';
import { TransformControls } from '/vendor/three/TransformControls.js';

export function createSelectionOverlay() {
    const overlay = new THREE.Mesh(new THREE.BoxGeometry(1.04, 1.04, 1.04),
        new THREE.MeshBasicMaterial({ color: 0xffd45a, wireframe: true, depthTest: false, transparent: true, opacity: 0.95 }));
    overlay.visible = false;
    overlay.renderOrder = 1000;
    return overlay;
}

export function createEventBox(width = 0.92, height = 0.92, depth = 0.92) {
    const cube = new THREE.Mesh(new THREE.BoxGeometry(width, height, depth),
        new THREE.MeshBasicMaterial({ color: 0x3aa6d8, transparent: true, opacity: 0.16, depthWrite: false }));
    const edges = new THREE.LineSegments(new THREE.EdgesGeometry(cube.geometry),
        new THREE.LineBasicMaterial({ color: 0x61cfff, transparent: true, opacity: 0.98, depthTest: false, depthWrite: false }));
    edges.renderOrder = 1000;
    return { cube, edges };
}

export function createMoveGizmo(camera, canvas, axes = ['X', 'Z'], axisSources = ['X', 'Y', 'Z']) {
    const gizmo = new TransformControls(camera, canvas);
    const helper = gizmo.getHelper();
    helper.traverse(object => {
        object.renderOrder = 1001;
        const materials = Array.isArray(object.material) ? object.material : [object.material];
        for (const material of materials) {
            if (!material) continue;
            material.depthTest = false;
            material.depthWrite = false;
            material.transparent = true;
        }
    });
    gizmo.setMode('translate');
    gizmo.space = 'world';
    gizmo.translationSnap = null;
    for (const axis of ['X', 'Y', 'Z', 'XY', 'YZ', 'XZ', 'XYZE']) gizmo[`show${axis}`] = axes.includes(axis);
    gizmo.showXZ = axes.includes('X') && axes.includes('Z');
    // These are the one shared transform grammar for plates and world
    // environments.  Keep the normal axis colours vivid enough to survive
    // textured scenery and a selected Event's sprite.
    gizmo.size = 1.25;
    const colors = { X: 0xff4d4f, Y: 0x42d66a, Z: 0x3d8cff };
    gizmo.setColors(...axisSources.map(axis => colors[axis]), 0xc8b77d);
    gizmo.enabled = false;
    return gizmo;
}

// Studio previews the runtime's selected sprite frame, never a whole sprite
// sheet squeezed into an actor-sized quad.  Both plate and environment views
// call this adapter so the frame aspect and crop are one editor fact.
export function configureEventSpriteFrame(texture, event = {}) {
    const imageWidth = Number(texture.image?.width);
    const imageHeight = Number(texture.image?.height);
    if (!(imageWidth > 0 && imageHeight > 0)) return { aspect: 0.5 };
    const frameWidth = Number(event.frameWidth) > 0 ? Number(event.frameWidth) : imageWidth;
    const frameHeight = Number(event.frameHeight) > 0 ? Number(event.frameHeight) : imageHeight;
    const columns = Math.max(1, Math.floor(imageWidth / frameWidth));
    const index = Number.isInteger(Number(event.frameIndex)) && Number(event.frameIndex) >= 0
        ? Number(event.frameIndex) : 0;
    const column = index % columns;
    const row = Math.floor(index / columns);
    const widthFraction = frameWidth / imageWidth;
    const heightFraction = frameHeight / imageHeight;
    texture.repeat.set(widthFraction, heightFraction);
    texture.offset.set(column * widthFraction, 1 - (row + 1) * heightFraction);
    texture.needsUpdate = true;
    return { aspect: frameWidth / frameHeight };
}

// One navigation policy for all spatial views. Authored interaction reserves
// its hit targets; empty-space drag pans in the screen plane. Alt+MMB orbits
// a 3D view, while plain MMB/RMB and the wheel always navigate the screen.
export function installNavigation(canvas, controls, {
    planar = false,
    canPan = () => false,
    getOpticalNavigation = null
} = {}) {
    for (const control of controls) {
        control.enableDamping = true;
        control.screenSpacePanning = true;
        control.mouseButtons.LEFT = null;
        control.mouseButtons.MIDDLE = THREE.MOUSE.PAN;
        control.mouseButtons.RIGHT = THREE.MOUSE.PAN;
        control.enableRotate = !planar;
    }
    let opticalGesture = null;
    function pointerDown(event) {
        const optical = getOpticalNavigation && getOpticalNavigation();
        if (optical && !(event.altKey && event.button === 1) && canPan(event)) {
            opticalGesture = { pointerId: event.pointerId, x: event.clientX, y: event.clientY, optical };
            canvas.setPointerCapture?.(event.pointerId);
            event.preventDefault();
            event.stopImmediatePropagation();
            return;
        }
        for (const control of controls) {
            control.mouseButtons.LEFT = canPan(event) ? THREE.MOUSE.PAN : null;
            control.mouseButtons.MIDDLE = event.altKey && !planar ? THREE.MOUSE.ROTATE : THREE.MOUSE.PAN;
        }
    }
    function pointerMove(event) {
        if (!opticalGesture || event.pointerId !== opticalGesture.pointerId) return;
        const dx = event.clientX - opticalGesture.x, dy = event.clientY - opticalGesture.y;
        opticalGesture.x = event.clientX; opticalGesture.y = event.clientY;
        opticalGesture.optical.pan(dx, dy, canvas.getBoundingClientRect());
        event.preventDefault(); event.stopImmediatePropagation();
    }
    function pointerUp(event) {
        if (!opticalGesture || event.pointerId !== opticalGesture.pointerId) return;
        opticalGesture = null;
        canvas.releasePointerCapture?.(event.pointerId);
        event.preventDefault(); event.stopImmediatePropagation();
    }
    function wheel(event) {
        const optical = getOpticalNavigation && getOpticalNavigation();
        if (!optical) return;
        const rect = canvas.getBoundingClientRect();
        optical.zoom(event.deltaY, event.clientX - rect.left, event.clientY - rect.top, rect);
        event.preventDefault(); event.stopImmediatePropagation();
    }
    canvas.addEventListener('pointerdown', pointerDown, true);
    if (getOpticalNavigation) {
        canvas.addEventListener('pointermove', pointerMove, true);
        canvas.addEventListener('pointerup', pointerUp, true);
        canvas.addEventListener('pointercancel', pointerUp, true);
        canvas.addEventListener('wheel', wheel, { capture: true, passive: false });
    }
    return () => {
        canvas.removeEventListener('pointerdown', pointerDown, true);
        if (getOpticalNavigation) {
            canvas.removeEventListener('pointermove', pointerMove, true);
            canvas.removeEventListener('pointerup', pointerUp, true);
            canvas.removeEventListener('pointercancel', pointerUp, true);
            canvas.removeEventListener('wheel', wheel, true);
        }
    };
}
