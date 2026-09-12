'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const r = require('./resolve');
const {read, products} = require('./build');
const clone = v => structuredClone(v);
test('all four physical contracts and committed products regenerate byte-identically', () => {
    const a = products(), b = products();
    assert.equal(r.dump(a), r.dump(b));
    for (const [name, value] of Object.entries(a)) {
        const committed = fs.readFileSync(path.join(__dirname, name), 'utf8').replace(/\r\n/g, '\n');
        assert.equal(r.dump(value), committed, name);
    }
    for (const name of ['dungeon', 'st_maria', 'tactics', 'metroidvania']) r.validate(a[`${name}/resolved_spatial.json`]);
});
test('closed common contract rejects gameplay, duplicate IDs, unknown shapes and invalid geometry', () => {
    const base = products()['metroidvania/resolved_spatial.json'];
    const mutations = [s => s.requiresDoubleJump = true, s => s.bodies[0].dialogue = 'bad',
        s => s.features.push(clone(s.features[0])), s => s.bodies[0].position[2] = NaN,
        s => s.bodies[0].shape.kind = 'isTacticalTile', s => s.bodies[0].shape.size[0] = -1,
        s => s.features[0].shape.requires = 'double_jump', s => s.coordinateSystem = 'XY-only'];
    for (const mutate of mutations) {const s = clone(base); mutate(s); assert.throws(() => r.validate(s));}
});
test('dungeon tokens, openings, rooms and every neighboring edge survive the real generator output', () => {
    const source = read('runtime-evidence.json').dungeon;
    const {physical, structure} = r.dungeon(source);
    assert(source.rooms.some(room => room.source === 'generated room'));
    assert(source.openings.length > 0);
    assert.deepEqual(structure.rooms, source.rooms);
    assert.deepEqual(structure.corridors, source.corridors);
    source.rows.forEach((row, y) => [...row].forEach((token, x) => {
        const c = structure.cells.find(c => c.id === `cell/${x}/${y}`);
        assert.equal(c.token, token); assert.deepEqual(c.position, [x + 0.5, y + 0.5, 0]);
        assert(physical.bodies.some(b => b.id === c.id));
        if (token === 'o') assert(physical.features.some(f => f.id === `opening/${x}/${y}`));
    }));
    const w = source.rows[0].length, h = source.rows.length;
    assert.equal(structure.edges.length, (w - 1)*h + (h - 1)*w);
    const byId = new Map(structure.cells.map(c => [c.id, c]));
    for (const edge of structure.edges) assert.equal(edge.open, byId.get(edge.a).token !== '#' && byId.get(edge.b).token !== '#');
    const open = structure.cells.filter(c => c.token !== '#');
    const visited = new Set([open[0].id]), queue = [open[0].id];
    while (queue.length) {const id = queue.shift(); for (const e of structure.edges.filter(e => e.open)) {
        const next = e.a === id ? e.b : e.b === id ? e.a : null;
        if (next && !visited.has(next)) {visited.add(next); queue.push(next);}
    }}
    assert.equal(visited.size, open.length, 'resolved open topology remains connected');
    assert(fs.statSync(path.join(__dirname, 'dungeon/source.json')).size < r.dump(structure).length / 3);
});
test('Event edits cannot alter geometry; anchor movement derives placement without changing Event source', () => {
    for (const name of ['dungeon', 'st_maria']) {
        const physical = products()[`${name}/resolved_spatial.json`];
        const before = r.dump(physical), events = read(`${name}/gameplay.json`).events;
        const original = r.placeEvents(physical, events);
        const changed = clone(events);
        if (changed[0].position) changed[0].position[0] += 2; else changed[0].offset[0] += 2;
        assert.equal(r.placeEvents(physical, changed)[0].position[0], original[0].position[0] + 2);
        assert.equal(r.dump(physical), before);
    }
    const p = products()['dungeon/resolved_spatial.json'], events = read('dungeon/gameplay.json').events;
    const before = r.dump(events), original = r.placeEvents(p, events);
    p.features.find(f => f.id === 'entry_room.center').position[2] += 1;
    assert.equal(r.placeEvents(p, events)[0].position[2], original[0].position[2] + 1);
    assert.equal(r.dump(events), before);
    assert.throws(() => r.placeEvents(p, [{id: 'bad', anchor: 'missing'}]));
    assert.throws(() => r.placeEvents(p, [{id: 'bad', anchor: 'entry_room.center', position: [0,0,0]}]));
});
test('Praca physical feature comes from parsed collision, never exported Event anchors', () => {
    const p = products()['st_maria/resolved_spatial.json'];
    assert.deepEqual(p.features.map(f => f.id), ['lane_surface.center']);
    const center = p.features[0].position;
    assert(Math.abs(center[0] - 7.8) < 1e-6);
    assert(Math.abs(center[1] - 11.8494995) < 1e-6);
    assert.equal(center[2], 0);
    const child = r.placeEvents(p, read('st_maria/gameplay.json').events)[0];
    assert.deepEqual(child.position, [7.8, 12.717, 0]);
    assert(!JSON.stringify(p).includes('child'));
});
test('tactical rules consume lattice elevation, explicit stairs, blocked sites and bridge; art has no vote', () => {
    const result = r.tactics(read('tactics/source.json'));
    const policy = read('tactics/gameplay.json').movement;
    const moves = r.tacticalMoves(result.structure, policy);
    const has = (a,b) => moves.some(m => m.from === a && m.to === b);
    assert(has('2/1', '3/1')); assert(!has('2/0', '3/0'));
    assert(has('1/3', 'bridge')); assert(has('bridge', '3/3'));
    assert(!moves.some(m => [m.from,m.to].some(id => ['1/1','2/2','2/4'].includes(id))));
    assert.equal(moves.find(m => m.from === '2/1' && m.to === '3/1').cost, 3);
    assert(r.tacticalMoves(result.structure, {...policy, maxStep: 1}).some(m => m.from === '2/0' && m.to === '3/0'));
    const before = r.dump(result.physical);
    r.tacticalMoves(result.structure, {...policy, climbCost: 99});
    assert.equal(r.dump(result.physical), before);
    result.physical.bodies = [];
    assert.deepEqual(r.tacticalMoves(result.structure, policy), moves);
});
test('planar gameplay preserves XYZ depth and physical output under camera/progression changes', () => {
    const source = read('metroidvania/source.json'), gameplay = read('metroidvania/gameplay.json');
    const p = r.metroidvania(source).physical;
    const upper = p.bodies.find(b => b.id === 'upper_platform'), rear = p.bodies.find(b => b.id === 'rear_platform');
    assert.equal(upper.position[2], rear.position[2]); assert.notEqual(upper.position[1], rear.position[1]);
    const before = r.dump(p); gameplay.transfers[0].requires = 'flight'; gameplay.camera.profile = 'ortho_oblique';
    assert.equal(r.dump(r.metroidvania(source).physical), before);
    const camera = read('runtime-evidence.json').camera;
    assert.equal(camera.projection, 'orthographic');
    assert(Math.abs(camera.projectionScale[0] - Math.sqrt(0.5)) < 1e-10);
    assert.equal(camera.projectionScale[1], 1);
});
test('typed tactical companion rejects broken references and invalid movement policy', () => {
    const structure = r.tactics(read('tactics/source.json')).structure;
    const policy = read('tactics/gameplay.json').movement;
    const dangling = clone(structure); dangling.connections.push(['0/0', 'missing']);
    assert.throws(() => r.tacticalMoves(dangling, policy));
    const duplicate = clone(structure); duplicate.sites.push(clone(duplicate.sites[0]));
    assert.throws(() => r.tacticalMoves(duplicate, policy));
    assert.throws(() => r.tacticalMoves(structure, {...policy, maxStep: NaN}));
    assert.throws(() => r.placeEvents(products()['dungeon/resolved_spatial.json'], [{id: 'bad', position: [0,0,0], offset: [0,NaN,0]}]));
});
