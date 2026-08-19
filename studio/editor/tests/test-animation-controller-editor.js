const assert = require('assert');
const ControllerEditor = require('../js/animation-controller-editor.js');

console.log('=== RUNNING ANIMATION CONTROLLER EDITOR TESTS ===');

const definition = {
    id: 'townsperson',
    initial: 'idle',
    states: {
        idle: { animation: 'idle', loop: true },
        move: { animation: 'walk', loop: true },
        interact: { animation: 'talk', loop: false }
    },
    transitions: [
        { from: 'idle', to: 'move', when: 'event.moving' },
        { from: 'move', to: 'idle', when: 'not event.moving' },
        { from: '*', to: 'interact', when: 'signal.interact' },
        { from: 'interact', to: 'idle', when: 'animation.finished' }
    ]
};

assert.deepStrictEqual(ControllerEditor.validateController(definition), []);
const preview = ControllerEditor.createPreview(definition);
assert.strictEqual(ControllerEditor.snapshotPreview(preview, definition).state, 'idle');

let snap = ControllerEditor.stepPreview(preview, definition, 1 / 60, {
    event: { moving: true, enabled: true }
});
assert.strictEqual(snap.state, 'move');
assert.strictEqual(snap.animation, 'walk');

// Deliberate signals interrupt ambient locomotion facts just like the Lua FSM.
ControllerEditor.signalPreview(preview, 'interact');
snap = ControllerEditor.stepPreview(preview, definition, 0, {
    event: { moving: true, enabled: true }
});
assert.strictEqual(snap.state, 'interact');
assert.strictEqual(snap.animation, 'talk');
assert.strictEqual(snap.loop, false);

ControllerEditor.completePreview(preview);
snap = ControllerEditor.stepPreview(preview, definition, 1 / 60, {
    event: { moving: true, enabled: true }
});
assert.strictEqual(snap.state, 'idle', 'completion returns through the authored transition');

const invalid = JSON.parse(JSON.stringify(definition));
invalid.transitions.push({ from: 'idle', to: 'move', when: 'npc.startedWalking' });
assert.ok(ControllerEditor.validateController(invalid).some(error => error.includes('unsupported condition')));

console.log('[PASS] Animation controller editor preview matches runtime controller semantics.');