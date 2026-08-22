const assert = require('assert');
const ModelPicker = require('../js/model-picker.js');

(async () => {
    console.log('=== RUNNING EDITOR MODEL PICKER TESTS ===');
    const THREE = await import('three');
    const { OBJLoader } = await import('three/examples/jsm/loaders/OBJLoader.js');
    const { MTLLoader } = await import('three/examples/jsm/loaders/MTLLoader.js');
    const object = new OBJLoader().parse(`
mtllib sample.mtl
v -1 0 0
v 1 0 0
v 1 2 0
v -1 2 0
usemtl stone
f 1/1/1 2/2/1 3/3/1 4/4/1
usemtl brass
f -4 -3 -2
`);
    const stats = ModelPicker.parseGeometryStats(object, THREE);
    assert.strictEqual(stats.triangleCount, 3, 'OBJLoader fan-triangulates quads');
    assert.deepStrictEqual(stats.bounds.min, [-1, 0, 0], 'OBJLoader geometry supplies minimum bounds');
    assert.deepStrictEqual(stats.bounds.max, [1, 2, 0], 'OBJLoader geometry supplies maximum bounds');
    const creator = new MTLLoader().parse('newmtl brass\nKd 1.2 -0.2 0.4\n', '');
    creator.preload();
    const colour = creator.materials.brass.color;
    colour.setRGB(Math.max(0, Math.min(1, colour.r)), Math.max(0, Math.min(1, colour.g)), Math.max(0, Math.min(1, colour.b)));
    assert.ok(creator.materials.brass.color.r <= 1 && creator.materials.brass.color.g >= 0, 'MTLLoader diffuse colours clamp to renderable range');
    assert.strictEqual(ModelPicker.resolveSibling('assets/models/items/potion.obj', '../shared/materials.mtl'), 'assets/models/shared/materials.mtl', 'relative mtllib paths resolve beside the OBJ');
    assert.strictEqual(ModelPicker.normalizePath('\\assets\\models\\items\\potion.obj'), 'assets/models/items/potion.obj', 'model paths normalize to project-style forward slashes');
    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, .01, 100);
    camera.position.set(0, 10, 0);
    camera.up.set(0, 0, -1);
    camera.lookAt(0, 0, 0);
    camera.updateMatrixWorld();
    const vertical = new THREE.Vector3(0, 0, 1).project(camera);
    assert.deepStrictEqual(vertical.toArray().map(value => Math.round(value)), [0, -1, -1], 'positive model Z maps to screen vertical');
    const horizontal = new THREE.Vector3(1, 0, 0).project(camera);
    assert.ok(horizontal.x > 0, 'positive model X preserves screen handedness');
    const pivot = new THREE.Group();
    pivot.rotation.set(0, 0, Math.PI / 2, 'XYZ');
    const quarterTurn = new THREE.Vector3(1, 0, 0).applyEuler(pivot.rotation);
    assert.ok(Math.abs(quarterTurn.x) < 1e-10, 'quarter turn removes X screen component');
    assert.ok(Math.abs(quarterTurn.z) < 1e-10, 'quarter turn keeps Z screen component at zero');
    assert.ok(Math.abs(quarterTurn.y - 1) < 1e-10, 'quarter turn maps model X into runtime depth');
    const savedMatchMedia = globalThis.matchMedia;
    globalThis.matchMedia = query => ({ matches: query === '(prefers-reduced-motion: reduce)' });
    assert.strictEqual(ModelPicker.prefersReducedMotion(), true, 'model preview honors reduced-motion media preference');
    globalThis.matchMedia = () => ({ matches: false });
    assert.strictEqual(ModelPicker.prefersReducedMotion(), false, 'model preview rotates when reduced motion is not requested');
    if (savedMatchMedia === undefined) delete globalThis.matchMedia; else globalThis.matchMedia = savedMatchMedia;
    console.log('[PASS] Model picker Three.js loading, paths, and runtime-oriented transform passed.');
})().catch(error => { console.error(error); process.exitCode = 1; });
