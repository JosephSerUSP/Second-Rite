const assert = require('assert');
const ModelPicker = require('../js/model-picker.js');

console.log('=== RUNNING EDITOR MODEL PICKER TESTS ===');

const obj = ModelPicker.parseOBJ(`
# triangle + quad, including a negative index
mtllib sample.mtl
v -1 0 0
v  1 0 0
v  1 2 0
v -1 2 0
usemtl stone
f 1/1/1 2/2/1 3/3/1 4/4/1
usemtl brass
f -4 -3 -2
`);

assert.strictEqual(obj.vertexCount, 4, 'OBJ parser counts vertices');
assert.strictEqual(obj.triangleCount, 3, 'OBJ parser fan-triangulates quads');
assert.deepStrictEqual(obj.mtllibs, ['sample.mtl'], 'OBJ parser retains material library path');
assert.deepStrictEqual(obj.materialNames.sort(), ['brass', 'stone'], 'OBJ parser records used materials');
assert.deepStrictEqual(obj.bounds.min, [-1, 0, 0], 'OBJ parser calculates minimum bounds');
assert.deepStrictEqual(obj.bounds.max, [1, 2, 0], 'OBJ parser calculates maximum bounds');

const mtl = ModelPicker.parseMTL(`
newmtl stone
Kd 0.25 0.5 0.75
newmtl brass
Kd 1.2 -0.2 0.4
`);
assert.deepStrictEqual(mtl.stone, [0.25, 0.5, 0.75], 'MTL parser reads diffuse colour');
assert.deepStrictEqual(mtl.brass, [1, 0, 0.4], 'MTL parser clamps diffuse colour to renderable range');

assert.strictEqual(
    ModelPicker.resolveSibling('assets/models/items/potion.obj', '../shared/materials.mtl'),
    'assets/models/shared/materials.mtl',
    'relative mtllib paths resolve beside the OBJ'
);
assert.strictEqual(
    ModelPicker.normalizePath('\\assets\\models\\items\\potion.obj'),
    'assets/models/items/potion.obj',
    'model paths normalize to project-style forward slashes'
);

console.log('[PASS] Model picker OBJ/MTL parsing and path helpers passed.');
