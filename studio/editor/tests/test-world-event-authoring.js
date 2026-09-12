'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const Commands = require('../js/second-rite-editor-commands');
const Scene = require('../js/thestra-editor-scene');
const Coordinates = require('../js/thestra-viewport-contract');

function fixture() {
    return { maps: [{ id: 17, safe: true, layout: ['.'], events: [
        { id: 1, instanceId: 'first', x: 0, y: 0, name: 'First', worldPosition: [7.8, 4, 0], commands: [] },
        { id: 2, instanceId: 'second', x: 0, y: 0, name: 'Second', worldPosition: [7.8, 12, 2],
            worldHeight: 1.75, frameWidth: 24, frameHeight: 48, commands: [] }
    ] }] };
}

test('world Event movement retains depth, identity and all other authored facts', () => {
    const payload = fixture();
    const first = JSON.stringify(payload.maps[0].events[0]);
    const position = [8.125, 13.75, 3.5];
    const display = Coordinates.runtimePositionToThestra(position);
    assert.deepEqual(Coordinates.thestraPositionToRuntime(display), position);
    assert.equal(Commands.moveWorldEvent(payload, 0, 2, position).changed, true);
    assert.equal(JSON.stringify(payload.maps[0].events[0]), first);
    assert.equal(payload.maps[0].events[1].instanceId, 'second');
    assert.equal(payload.maps[0].events[1].x, 0);
    const rebuilt = Scene.buildScene(payload, payload.maps[0]).events[1];
    assert.deepEqual(rebuilt.worldPosition, position);
    assert.deepEqual([rebuilt.worldHeight, rebuilt.frameWidth, rebuilt.frameHeight], [1.75, 24, 48],
        'the 3D preview must receive the authored billboard dimensions');
    assert.equal(Commands.moveWorldEvent(payload, 0, 2, [NaN, 0, 0]).ok, false);
    assert.deepEqual(payload.maps[0].events[1].worldPosition, position);
    assert.deepEqual(JSON.parse(JSON.stringify(payload)).maps[0].events[1].worldPosition, position);
});

// Execute the actual modal entry/apply/delete functions with only DOM widgets
// stubbed. This catches coordinate-based edits of a different colocated Event.
function modalHarness(payload) {
    const source = fs.readFileSync(require.resolve('../js/events.js'), 'utf8');
    const elements = new Map();
    const element = id => {
        if (!elements.has(id)) elements.set(id, { value: '', checked: false,
            appendChild() {}, classList: { add() {}, remove() {} } });
        return elements.get(id);
    };
    const noOp = () => {};
    const ctx = { dbPayload: payload, currentMapIndex: 0, window: {},
        document: { getElementById: element, createElement: () => ({}) },
        EventSelfStateAuthoring: { createInstanceId: () => 'new', ensureInstanceId: e => e.instanceId },
        updateEventGraphicPreview: noOp, setEventColorFields: noOp,
        updateEventPageModeUI: noOp, renderEventPageTabs: noOp, toggleEventLogicType: noOp,
        eventModalSnapshotHelper: { capture: noOp }, closeEventModal: noOp,
        renderGridCells: noOp, setDirty: noOp };
    vm.createContext(ctx);
    for (const name of ['openEventModal', 'applyEventProperties', 'deleteEventAtCoords']) {
        const start = source.indexOf(`        function ${name}(`);
        const end = source.indexOf('\n        function ', start + 1);
        vm.runInContext(source.slice(start, end), ctx);
    }
    return { ctx, element };
}

test('colocated Event modal opens and applies the selected identity, then deletes only that Event', () => {
    const payload = fixture();
    const { ctx, element } = modalHarness(payload);
    const original = JSON.stringify(payload.maps[0].events[0]);
    ctx.openEventModal(0, 0, 2);
    assert.equal(element('event-prop-name').value, 'Second');
    element('event-prop-name').value = 'Edited second';
    ctx.applyEventProperties();
    assert.equal(payload.maps[0].events[1].name, 'Edited second');
    assert.equal(JSON.stringify(payload.maps[0].events[0]), original);
    ctx.deleteEventAtCoords();
    assert.equal(payload.maps[0].events.length, 1);
    assert.equal(JSON.stringify(payload.maps[0].events[0]), original);
});

test('ambiguous cell selection fails without choosing the first Event', () => {
    const { ctx } = modalHarness(fixture());
    assert.throws(() => ctx.openEventModal(0, 0), /Multiple Events/);
    assert.throws(() => ctx.openEventModal(0, 0, 99), /no longer exists/);
});

test('spatial Event selection opens by identity without a grid-cell selection', () => {
    const source = fs.readFileSync(require.resolve('../js/event_presentation.js'), 'utf8');
    const start = source.indexOf('            openAt(selection) {');
    const end = source.indexOf('\n            }', start) + '\n            }'.length;
    const calls = [];
    const ctx = { dbPayload: fixture(), currentMapIndex: 0, editingMode: 'map',
        openEventModal: (...args) => calls.push(args) };
    vm.createContext(ctx);
    vm.runInContext('function ' + source.slice(start, end).trim(), ctx);
    ctx.openAt({ kind: 'event', id: 2 });
    assert.deepEqual(calls, [[0, 0, 2]]);
    assert.throws(() => ctx.openAt({ kind: 'event', id: 999 }), /no longer/);
});

test('runtime and both Studio surfaces consume the same authored transition transform', () => {
    const root = path.resolve(__dirname, '..', '..', '..');
    const runtime = fs.readFileSync(path.join(root, 'runtime', 'presentation', 'viewport_3d.lua'), 'utf8');
    const threeDStudio = fs.readFileSync(path.join(root, 'studio', 'editor', 'js', 'three-editor-viewport-base.js'), 'utf8');
    const plateStudio = fs.readFileSync(path.join(root, 'studio', 'editor', 'js', 'three-composition-viewport.js'), 'utf8');
    assert.match(runtime, /worldView\.transitionArrowWorldPoint\(imageX, imageY,/);
    assert.match(runtime, /worldView\.transitionArrowWorldPoint\(originX, originY,/);
    assert.match(runtime, /spec\.transitionArrowAxis/);
    assert.match(threeDStudio, /WorldView\.transitionArrowAxis\(event\.direction\)/);
    assert.match(plateStudio, /View\.transitionArrowWorldPoint\(Number\(position\[0\]\), eventY,/);
    assert.doesNotMatch(runtime, /local arrowDirection = rawEv\.direction/,
        'runtime must not recover an arrow direction from its label');
});

test('runtime models retain an authored height and ground horizontal arrows on it', () => {
    const runtime = fs.readFileSync(path.resolve(__dirname, '..', '..', '..', 'runtime', 'presentation', 'viewport_3d.lua'), 'utf8');
    const plateStudio = fs.readFileSync(path.resolve(__dirname, '..', '..', '..', 'studio', 'editor', 'js', 'three-composition-viewport.js'), 'utf8');
    assert.match(runtime, /local function ensurePlacedModel\(spec, cacheKey, originX, originY, axis, normalX, normalY, originZ\)/);
    assert.match(runtime, /local wx, wy, wz = originX \+ lx, originY \+ ly, originZ \+ lz/);
    assert.match(runtime, /worldZ = worldZ \+ 0\.22 \* modelScale/,
        'a horizontal arrow must lift by its source radius instead of clipping through the floor');
    assert.match(runtime, /groundAt\(session, worldY\)/,
        'town event models must resolve against the authoritative lane floor');
    assert.match(plateStudio, /const groundedZ = View\.groundHeight\(lane\.groundProfile, groundZ, Number\(position\[1\]\)\)/,
        'the plate Event box must use the same lane floor as the runtime model, not a legacy authored Z');
    assert.match(plateStudio, /MTLLoader/,
        'plate models must preserve the OBJ material-library diffuse colour');
    assert.match(plateStudio, /fitProjectedModelBounds/,
        'the shared Event box must surround projected model geometry instead of an unrelated sprite footprint');
    assert.match(runtime, /transitionArrowWorldPoint\(imageX, imageY,/,
        'runtime transition-arrow geometry must use the shared Event transform origin exactly');
    assert.match(plateStudio, /transitionArrowWorldPoint\(Number\(position\[0\]\), eventY,/,
        'Studio must project the same transform origin as the runtime');
    assert.doesNotMatch(runtime, /worldY = math\.min\(worldY, lane\.maxY/,
        'lane bounds must not silently translate an outward exit marker');
    assert.match(plateStudio, /Project its full authored depth ribbon, not a flat/,
        'the plate walk overlay must be a camera-projected traversal surface');
});

test('fully 3D interior exits carry their authored transition-marker model', () => {
    const mapsRoot = path.resolve(__dirname, '..', '..', '..', 'projects', 'hichaukitoden-game', 'data', 'maps');
    const maps = fs.readdirSync(mapsRoot)
        .filter(name => /^\d+\.json$/.test(name))
        .map(name => JSON.parse(fs.readFileSync(path.join(mapsRoot, name), 'utf8')))
        .filter(map => /_3d\/environment\.json$/.test(map.traversal?.environmentPackage || ''));
    assert.ok(maps.length > 0, 'the fixture must contain a fully 3D interior');
    for (const map of maps) {
        for (const event of map.events || []) {
            if (event.trigger !== 'bump') continue;
            assert.equal(event.model, 'assets/models/st_maria/transition_arrow.obj',
                `${map.title}: exit '${event.name}' must expose the authored transition marker`);
            assert.match(event.direction || '', /^(left|right|away|toward)$/,
                `${map.title}: exit '${event.name}' must carry an explicit transition direction`);
        }
    }
});
