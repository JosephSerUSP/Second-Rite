const assert = require('assert');
const EventPresentation = require('../js/event_presentation.js');

console.log('=== RUNNING EDITOR PRESENTATION SERIALIZATION TESTS ===');

// 1. Map Event Presentation Serialization - Three States
let mapEv = {};

// State A: Inherit (absent)
EventPresentation.serializeEventPresentation({
    modelMode: 'inherit', focusMode: 'inherit', controllerMode: 'inherit'
}, mapEv);
assert.strictEqual(mapEv.model, undefined, 'Map event model mode inherit deletes field');
assert.strictEqual(mapEv.interactionFocus, undefined, 'Map event focus mode inherit deletes field');
assert.strictEqual(mapEv.animationController, undefined, 'Map event controller mode inherit deletes field');

// State B: Override (valid value)
const focusObj = { kind: 'low_prop' };
EventPresentation.serializeEventPresentation({
    modelMode: 'override',
    modelValue: 'assets/models/dungeon/dungeon_chest.obj',
    focusMode: 'override',
    focusValue: focusObj,
    controllerMode: 'override',
    controllerValue: 'townsperson'
}, mapEv);
assert.strictEqual(mapEv.model, 'assets/models/dungeon/dungeon_chest.obj', 'Map event model mode override sets string path');
assert.deepStrictEqual(mapEv.interactionFocus, { kind: 'low_prop' }, 'Map event focus mode override sets focus object');
assert.strictEqual(mapEv.animationController, 'townsperson', 'Map event controller mode override sets reusable controller id');

// State C: Suppress (explicit false)
EventPresentation.serializeEventPresentation({
    modelMode: 'suppress', focusMode: 'suppress', controllerMode: 'suppress'
}, mapEv);
assert.strictEqual(mapEv.model, false, 'Map event model mode suppress sets explicit false');
assert.strictEqual(mapEv.interactionFocus, false, 'Map event focus mode suppress sets explicit false');
assert.strictEqual(mapEv.animationController, false, 'Map event controller suppress sets explicit false');


// 2. Common Event Presentation Serialization - Canonical Absence ("None")
let commonEv = {
    model: 'assets/models/dungeon/dungeon_chest.obj',
    interactionFocus: { kind: 'low_prop' },
    animationController: 'townsperson'
};

// Set to value
EventPresentation.serializeCommonEventPresentation({
    modelValue: 'assets/models/dungeon/dungeon_chest.obj',
    focusValue: { kind: 'low_prop' },
    controllerValue: 'townsperson'
}, commonEv);
assert.strictEqual(commonEv.model, 'assets/models/dungeon/dungeon_chest.obj');
assert.deepStrictEqual(commonEv.interactionFocus, { kind: 'low_prop' });
assert.strictEqual(commonEv.animationController, 'townsperson');

// Set to None (canonical absence via delete)
EventPresentation.serializeCommonEventPresentation({
    modelValue: '', focusValue: null, controllerValue: ''
}, commonEv);
assert.strictEqual(Object.prototype.hasOwnProperty.call(commonEv, 'model'), false, 'Common event model set to none deletes key');
assert.strictEqual(Object.prototype.hasOwnProperty.call(commonEv, 'interactionFocus'), false, 'Common event focus set to none deletes key');
assert.strictEqual(Object.prototype.hasOwnProperty.call(commonEv, 'animationController'), false, 'Common event controller set to none deletes key');

console.log('[PASS] All editor event presentation serialization tests passed successfully.');