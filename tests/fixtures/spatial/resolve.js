'use strict';
// Experimental derived artifact, never a persisted Map schema or runtime fallback.
const assert = require('node:assert/strict');
const coordinateSystem = 'XYZ: right-handed, Z-up, XY-ground, world-units';
const canonical = value => Array.isArray(value) ? value.map(canonical)
    : value && typeof value === 'object' ? Object.fromEntries(Object.keys(value).sort().map(k => [k, canonical(value[k])])) : value;
const dump = value => JSON.stringify(canonical(value), null, 2) + '\n';
const scene = () => ({coordinateSystem, bodies: [], features: []});
const body = (id, position, size) => ({id, position, shape: {kind: 'box', size}});
const feature = (id, position, shape = {kind: 'point'}) => ({id, position, shape});

function dungeon(input) {
    const physical = scene(), cells = [], edges = [];
    input.rows.forEach((row, y) => [...row].forEach((token, x) => {
        const id = `cell/${x}/${y}`;
        cells.push({id, position: [x + 0.5, y + 0.5, 0], token});
        physical.bodies.push(body(id, [x + 0.5, y + 0.5, token === '#' ? 1 : -0.1], [1, 1, token === '#' ? 2 : 0.2]));
        if (token === 'o') physical.features.push(feature(`opening/${x}/${y}`, [x + 0.5, y + 0.5, 0], {kind: 'box', size: [1, 1, 2]}));
        for (const [dx, dy] of [[1, 0], [0, 1]]) {
            const other = input.rows[y + dy]?.[x + dx];
            if (other !== undefined) edges.push({id: `edge/${x}/${y}/${dx}/${dy}`, a: id,
                b: `cell/${x + dx}/${y + dy}`, open: token !== '#' && other !== '#'});
        }
    }));
    const entry = input.rooms.find(r => r.anchorIndex === 1);
    assert(entry, 'real generated anchor room required');
    physical.features.push(feature('entry_room.center', [entry.center.x + 0.5, entry.center.y + 0.5, 0]));
    return {physical, structure: {kind: 'grid-topology-v1', cells, edges, rooms: input.rooms, corridors: input.corridors}};
}
function stMaria(input) {
    const physical = scene();
    physical.bodies.push({id: 'praca', position: [0, 0, 0], shape: {kind: 'mesh',
        render: input.render, collision: input.collision}});
    const v = input.collisionVertices;
    const min = [0, 1, 2].map(i => Math.min(...v.map(p => p[i])));
    const max = [0, 1, 2].map(i => Math.max(...v.map(p => p[i])));
    // A geometry-local physical feature, never TH_ANCHORS / an Event proxy.
    physical.features.push(feature('lane_surface.center', [(min[0]+max[0])/2, (min[1]+max[1])/2, max[2]]));
    return {physical};
}
function tactics(input) {
    const physical = scene(), sites = [];
    for (let y = 0; y < input.size; y++) for (let x = 0; x < input.size; x++) {
        const id = `${x}/${y}`;
        if (input.gaps.includes(id)) continue;
        const z = x >= input.elevation.splitX ? input.elevation.high : input.elevation.low;
        sites.push({id, position: [x, y, z], blocked: input.blocked.includes(id)});
        physical.bodies.push(body(`site/${id}`, [x, y, z - 0.1], [1, 1, 0.2]));
    }
    const bridge = input.bridge;
    physical.bodies.push(body('bridge', [bridge.position[0], bridge.position[1], bridge.position[2] - bridge.size[2]/2], [...bridge.size]));
    sites.push({id: 'bridge', position: [...bridge.position], blocked: false});
    physical.features.push(feature('deployment', [...input.deployment.position], {kind: 'box', size: [...input.deployment.size]}));
    // Structural slope endpoints; costs and ability policy belong to the consumer.
    const stair = input.stair;
    physical.features.push(feature('ramp', [...stair.start], {kind: 'segment', end: [...stair.end]}));
    for (let i = 1; i <= stair.steps; i++) {
        const position = stair.start.map((v, axis) => v + (stair.end[axis] - v) * i / (stair.steps + 1));
        position[2] -= 0.1;
        physical.bodies.push(body(`stair/${i}`, position, [1/(stair.steps + 1), 1, 0.2]));
    }
    return {physical, structure: {kind: 'lattice-sites-v1', sites, connections: input.connections}};
}
function tacticalMoves(structure, policy) {
    assert.equal(structure.kind, 'lattice-sites-v1');
    const ids = new Set();
    for (const site of structure.sites) {
        assert(typeof site.id === 'string' && !ids.has(site.id), 'unique lattice identity required'); ids.add(site.id);
        assert(site.position.length === 3 && site.position.every(Number.isFinite));
        assert.equal(typeof site.blocked, 'boolean');
    }
    for (const edge of structure.connections) assert(edge.length === 2 && edge[0] !== edge[1] && edge.every(id => ids.has(id)), 'connection must join existing distinct sites');
    for (const field of ['maxStep', 'baseCost', 'climbCost']) assert(Number.isFinite(policy[field]) && policy[field] >= 0, 'invalid tactical policy');
    const result = [];
    for (const a of structure.sites) for (const b of structure.sites) {
        if (a.id === b.id || a.blocked || b.blocked) continue;
        const explicit = structure.connections.some(([u,v]) => (u === a.id && v === b.id) || (v === a.id && u === b.id));
        const distance = Math.abs(a.position[0]-b.position[0])+Math.abs(a.position[1]-b.position[1]);
        const rise = Math.abs(a.position[2]-b.position[2]);
        if (explicit || (distance === 1 && rise <= policy.maxStep)) result.push({from: a.id, to: b.id, cost: policy.baseCost + rise * policy.climbCost});
    }
    return result;
}
function metroidvania(input) {
    const physical = scene();
    for (const p of input.platforms) physical.bodies.push(body(p.id, p.position, p.size));
    physical.features = structuredClone(input.features);
    return {physical};
}
function validate(s) {
    assert.deepEqual(Object.keys(s).sort(), ['bodies', 'coordinateSystem', 'features']);
    assert.equal(s.coordinateSystem, coordinateSystem);
    const ids = new Set();
    const vector = v => assert(Array.isArray(v) && v.length === 3 && v.every(Number.isFinite), 'finite XYZ vector required');
    for (const [collection, entries] of [['bodies', s.bodies], ['features', s.features]]) for (const e of entries) {
        assert.deepEqual(Object.keys(e).sort(), ['id', 'position', 'shape']);
        assert(typeof e.id === 'string' && e.id.length && !ids.has(e.id), 'unique stable identity required'); ids.add(e.id);
        vector(e.position);
        const shape = e.shape;
        assert((collection === 'bodies' ? ['box', 'mesh'] : ['point', 'box', 'segment']).includes(shape.kind), 'shape unsupported for this collection');
        const keys = {point: ['kind'], box: ['kind', 'size'], segment: ['end', 'kind'], mesh: ['collision', 'kind', 'render']}[shape.kind];
        assert(keys, 'unknown spatial shape'); assert.deepEqual(Object.keys(shape).sort(), keys);
        if (shape.kind === 'box') { vector(shape.size); assert(shape.size.every(n => n > 0)); }
        if (shape.kind === 'segment') { vector(shape.end); assert(shape.end.some((v, i) => v !== e.position[i]), 'segment must have length'); }
        if (shape.kind === 'mesh') for (const ref of [shape.render, shape.collision]) {
            assert.deepEqual(Object.keys(ref).sort(), ['path', 'sha256']);
            assert(typeof ref.path === 'string' && /^[a-f0-9]{64}$/.test(ref.sha256));
            assert(ref.path.endsWith('.obj') && !ref.path.split('/').includes('..'), 'probe supports exported OBJ assets only');
        }
    }
    return s;
}
function placeEvents(physical, events) {
    const ids = new Set();
    return events.map(e => {
        assert(typeof e.id === 'string' && e.id.length && !ids.has(e.id), 'unique Event identity required'); ids.add(e.id);
        assert(!(e.position && e.anchor), 'placement has exactly one authority');
        const base = e.anchor ? physical.features.find(f => f.id === e.anchor)?.position : e.position;
        assert(base, `unresolved Event placement ${e.id}`);
        assert(base.length === 3 && base.every(Number.isFinite));
        const offset = e.offset === undefined ? [0, 0, 0] : e.offset;
        assert(Array.isArray(offset) && offset.length === 3 && offset.every(Number.isFinite), 'finite XYZ offset required');
        return {id: e.id, position: base.map((v, i) => v + offset[i])};
    });
}
module.exports = {dump, dungeon, stMaria, tactics, tacticalMoves, metroidvania, validate, placeEvents};
