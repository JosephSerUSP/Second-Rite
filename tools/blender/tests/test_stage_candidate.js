'use strict';
// stage_candidate.js builds the staged map without touching the Project.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {candidateMap, parse} = require('../stage_candidate');

// Expectations come from map 22 itself, so editing the map elsewhere (its
// destination, its direction) does not break these tests.
const source = JSON.parse(fs.readFileSync(path.resolve(__dirname,
    '../../../projects/hichaukitoden-game/data/maps/22.json'), 'utf8'));
const sourceExit = source.events.find(e => e.instanceId === 'st-maria-chapel-exit_door');

const manifest = {anchors: {
    exit_door: {position: [0, 6.8833, 0]},
    npc_agnes: {position: [0, 4.4833, 0]},
}};
const base = {mapId: 22, templateId: 28, manifest,
              packagePath: 'assets/environments/review/x/environment.json'};

test('exit and NPC move to package anchors; presentation comes from the template', () => {
    const {map, dropped} = candidateMap({...base, npcs: [['st-maria-chapel-agnes', 'npc_agnes']]});
    const exit = map.events.find(e => e.instanceId === 'st-maria-chapel-exit_door');
    assert.deepEqual(exit.worldPosition, [0, 6.8833, 0]);
    assert.deepEqual(exit.commands, sourceExit.commands, 'the map keeps its own exit destination');
    assert.deepEqual(map.traversal.doorways.map(d => d.eventInstanceId), ['st-maria-chapel-exit_door']);
    assert.equal(map.traversal.environmentPackage, base.packagePath);
    assert.equal(map.ceilingStyle, 'solid', 'a 2D plate map\'s sky ceiling must not leak into an interior');
    assert.deepEqual(map.fog, {minFactor: 1.0});
    assert.deepEqual(map.events.find(e => e.instanceId === 'st-maria-chapel-agnes').worldPosition,
                     [0, 4.4833, 0]);
    assert.deepEqual(dropped, []);
    assert.equal(map.title, source.title, 'the place keeps its own text');
});

test('unlisted events are dropped and reported', () => {
    const {map, dropped} = candidateMap({...base, npcs: []});
    assert.deepEqual(map.events.map(e => e.instanceId), ['st-maria-chapel-exit_door']);
    assert.deepEqual(dropped, ['st-maria-chapel-agnes']);
});

test('a missing anchor or event fails loudly', () => {
    assert.throws(() => candidateMap({...base, npcs: [['st-maria-chapel-agnes', 'npc_nobody']]}),
                  /npc_nobody anchor/);
    assert.throws(() => candidateMap({...base, npcs: [['no-such-event', 'npc_agnes']]}),
                  /no event no-such-event/);
    assert.throws(() => candidateMap({...base, manifest: {anchors: {}}, npcs: []}), /exit_door anchor/);
});

test('a scrolling hall overrides the lane and the camera tracking', () => {
    const {map} = candidateMap({...base, npcs: [], lane: [3.6, 15.5], track: [8, 78]});
    assert.deepEqual([map.traversal.lane.minY, map.traversal.lane.maxY], [3.6, 15.5]);
    assert.equal(map.traversal.camera.target.y, 8);
    assert.deepEqual([map.traversal.camera.tracking.center, map.traversal.camera.tracking.minOffsetX,
                      map.traversal.camera.tracking.maxOffsetX], [8, -78, 78]);
    const plain = candidateMap({...base, npcs: []}).map;
    assert.deepEqual([plain.traversal.lane.minY, plain.traversal.lane.maxY], [0.35, 7.4167],
                     'without --lane the template lane is kept');
});

test('--camera merges into the template camera key by key', () => {
    const {map} = candidateMap({...base, npcs: [], camera: {yawDegrees: -14, target: {y: 9}}});
    assert.equal(map.traversal.camera.yawDegrees, -14);
    assert.equal(map.traversal.camera.target.y, 9);
    assert.equal(map.traversal.camera.target.z, 2.2604, 'unlisted keys survive');
    assert.equal(map.traversal.camera.tracking.axis, 'y');
});

test('an end-wall exit can say it leads off the side of the screen', () => {
    const exit = m => m.events.find(e => e.instanceId === 'st-maria-chapel-exit_door');
    assert.equal(exit(candidateMap({...base, npcs: []}).map).direction, sourceExit.direction, 'kept by default');
    assert.equal(exit(candidateMap({...base, npcs: [], exitDirection: 'right'}).map).direction, 'right');
    assert.throws(() => candidateMap({...base, npcs: [], exitDirection: 'up'}), /exit-direction/);
});

test('arguments', () => {
    const options = parse(['--output', 'out/x', '--package', 'pkg', '--map-id', '22',
                           '--npc', 'st-maria-chapel-agnes=npc_agnes']);
    assert.equal(options.mapId, 22);
    assert.deepEqual(options.npcs, [['st-maria-chapel-agnes', 'npc_agnes']]);
    assert.throws(() => parse(['--output', 'out/x']), /--map-id/);
    assert.throws(() => parse(['--npc', 'broken']), /eventInstanceId/);
    const hall = parse(['--output', 'o', '--package', 'p', '--map-id', '22', '--lane', '3.6', '15.5', '--track', '8', '78']);
    assert.deepEqual([hall.lane, hall.track], [[3.6, 15.5], [8, 78]]);
    assert.throws(() => parse(['--lane', '3', 'x']), /two numbers/);
    assert.deepEqual(parse(['--output', 'o', '--package', 'p', '--map-id', '1', '--camera', '{"yawDegrees":-14}']).camera,
                     {yawDegrees: -14});
    assert.throws(() => parse(['--camera', '{bad']), /takes JSON/);
});

test('a ground profile lands on the lane and only there', () => {
    const profile = [[0, 2.3], [10.44, 2.3], [15.2, 0], [22, 0]];
    const {map} = candidateMap({...base, npcs: [], groundProfile: profile});
    assert.deepEqual(map.traversal.lane.groundProfile, profile);
    const plain = candidateMap({...base, npcs: []}).map;
    assert.equal(plain.traversal.lane.groundProfile, undefined, 'no profile unless asked for');
});

test('--ground-profile is parsed and validated', () => {
    const argv = ['--output', 'out/x', '--package', '.', '--map-id', '25'];
    assert.deepEqual(parse([...argv, '--ground-profile', '[[0,2.3],[5,0]]']).groundProfile, [[0, 2.3], [5, 0]]);
    assert.throws(() => parse([...argv, '--ground-profile', '[[0]]']), /\[\[engineY, z\]/);
    assert.throws(() => parse([...argv, '--ground-profile', 'nope']), /takes JSON/);
});
