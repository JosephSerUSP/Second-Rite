const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

test('plate and 3D controls share screen pan while preserving authored hit targets', () => {
    const source = fs.readFileSync(require.resolve('../js/three-authoring-tools.js'), 'utf8');
    const context = { THREE: { MOUSE: { PAN: 2, ROTATE: 0 } } };
    vm.createContext(context);
    vm.runInContext(source.slice(source.indexOf('export function installNavigation')).replace('export ', ''), context);
    for (const planar of [true, false]) {
        let down, removed = false, authoredHit = false;
        const canvas = {
            addEventListener(type, fn, capture) { assert.equal(type, 'pointerdown'); assert.equal(capture, true); down = fn; },
            removeEventListener(type, fn) { assert.equal(fn, down); removed = true; }
        };
        const controls = [{ mouseButtons: {} }, { mouseButtons: {} }];
        const dispose = context.installNavigation(canvas, controls, { planar, canPan: () => !authoredHit });
        down({ altKey: false });
        for (const control of controls) {
            assert.equal(control.screenSpacePanning, true);
            assert.equal(control.mouseButtons.LEFT, 2);
            assert.equal(control.mouseButtons.MIDDLE, 2);
            assert.equal(control.mouseButtons.RIGHT, 2);
        }
        authoredHit = true;
        down({ altKey: true });
        for (const control of controls) {
            assert.equal(control.mouseButtons.LEFT, null, 'selection/painting/gizmo must retain left drag');
            assert.equal(control.mouseButtons.MIDDLE, planar ? 2 : 0);
        }
        dispose(); assert.ok(removed);
    }
});

test('plate and 3D previews crop the authored sprite frame before sizing it', () => {
    const source = fs.readFileSync(require.resolve('../js/three-authoring-tools.js'), 'utf8');
    const start = source.indexOf('export function configureEventSpriteFrame');
    const end = source.indexOf('// One navigation policy', start);
    const context = {};
    vm.createContext(context);
    vm.runInContext(source.slice(start, end).replace('export ', ''), context);
    let repeat, offset;
    const texture = {
        image: { width: 96, height: 96 }, needsUpdate: false,
        repeat: { set: (x, y) => { repeat = [x, y]; } },
        offset: { set: (x, y) => { offset = [x, y]; } }
    };
    const frame = context.configureEventSpriteFrame(texture,
        { frameWidth: 24, frameHeight: 48, frameIndex: 5 });
    assert.equal(frame.aspect, 0.5);
    assert.deepEqual(repeat, [0.25, 0.5]);
    assert.deepEqual(offset, [0.25, 0], 'frame five is column one of the lower row');
    assert.equal(texture.needsUpdate, true);
});
