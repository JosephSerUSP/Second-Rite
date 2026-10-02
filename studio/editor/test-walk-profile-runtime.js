'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const roots = require('../../tools/semantic-roots');
const Commands = require('./js/second-rite-editor-commands');

function captureTownFrames(previewExe, gameRoot) {
    const result = spawnSync(previewExe, [gameRoot, 'town-proof-frames'], {
        cwd: gameRoot,
        encoding: 'utf8',
        maxBuffer: 64 * 1024 * 1024,
        timeout: 120000,
    });
    assert.equal(result.status, 0, result.stdout + result.stderr);
    const match = result.stdout.match(/TOWN PROOF BEGIN\s*([\s\S]*?)\s*TOWN PROOF END/);
    assert.ok(match, 'town proof emitted its framed payload');
    return JSON.parse(match[1]).frames;
}

// This proof compares compositor pixels produced by two separate LÖVE
// processes. Presentation-only animation (for example the continuously rolling
// transfer arrows) must not turn wall-clock phase into an apparent spatial edit.
// Pin time only inside the disposable staged town-proof harness: the runtime
// under test is otherwise unchanged, while ordinary play keeps its live clock.
function pinTownProofPresentationClock(gameRoot) {
    const cliPath = path.join(gameRoot, 'engine', 'cli_tools.lua');
    const source = fs.readFileSync(cliPath, 'utf8');
    const begin = 'function cli.runTownProofFrames(loader)\n';
    const nextFunction = '\n-- An automated playthrough.';
    const start = source.indexOf(begin);
    const finish = source.indexOf(nextFunction, start);
    assert.ok(start >= 0 && finish > start,
        'staged runtime exposes the town-proof harness boundary');

    let proof = source.slice(start, finish);
    assert.equal(proof.split(begin).length - 1, 1,
        'town-proof harness has one function entry');
    proof = proof.replace(begin, begin
        + '    local __townProofGetTime = love.timer.getTime\n'
        + '    love.timer.getTime = function() return 0 end\n');
    const tail = '    print("TOWN PROOF END")\nend\n';
    assert.equal(proof.split(tail).length - 1, 1,
        'town-proof harness has one completion boundary');
    proof = proof.replace(tail,
        '    print("TOWN PROOF END")\n'
        + '    love.timer.getTime = __townProofGetTime\n'
        + 'end\n');
    fs.writeFileSync(cliPath, source.slice(0, start) + proof + source.slice(finish));
}

test('a Port walk-profile edit changes runtime grounding and only its affected compositor sample',
        { timeout: 180000 }, () => {
    const previewExe = process.env.LOVEC || process.env.LOVE_PATH;
    assert.ok(previewExe && fs.existsSync(previewExe), 'Set LOVEC to the console LÖVE executable.');
    const stage = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-town-profile-'));
    try {
        const stageResult = spawnSync(process.execPath, [
            path.join(roots.DEFAULT_INSTALL_ROOT, 'tools', 'ci', 'stage-project-gates.js'),
            '--output', stage,
        ], { cwd: roots.DEFAULT_INSTALL_ROOT, encoding: 'utf8',
            maxBuffer: 32 * 1024 * 1024, timeout: 120000 });
        assert.equal(stageResult.status, 0, stageResult.stdout + stageResult.stderr);
        const staged = stageResult.stdout.match(/PROJECT GATE STAGE OK\s+(\{.*\})/);
        assert.ok(staged, 'the canonical exporter reported its staged Project root');
        const gameRoot = JSON.parse(staged[1]).stageDir;
        pinTownProofPresentationClock(gameRoot);

        const before = captureTownFrames(previewExe, gameRoot);
        const mapPath = path.join(gameRoot, 'data', 'maps.json');
        const maps = JSON.parse(fs.readFileSync(mapPath, 'utf8'));
        const mapIndex = maps.findIndex(candidate => candidate.id === 31);
        const port = maps[mapIndex];
        assert.ok(port?.traversal?.lane?.groundProfile?.length >= 4,
            'the staged Project retains Port as the existing non-flat profile specimen');
        const lane = port.traversal.lane;
        const profile = lane.groundProfile;
        assert.ok(profile[0].y < lane.minY && profile.at(-1).y > lane.maxY,
            'Port calibration points deliberately extend outside the playable lane interval');

        const eastY = Number(lane.minY) + (Number(lane.maxY) - Number(lane.minY)) * 0.9;
        assert.ok(eastY > Number(profile[1].y) && eastY < Number(profile[2].y),
            'the east proof sample lies on Port\'s authored climb');

        // Use the same commands the Studio host invokes: split the actual
        // climb, preserving its current interpolated height, then lift that
        // newly-authored control point. The staged runtime consumes exactly
        // the resulting Map JSON.
        const payload = { maps };
        const split = Commands.splitGroundProfileSegment(payload, mapIndex, 1, 0.5);
        assert.equal(split.ok, true, 'Studio command splits the Port climb');
        const splitIndex = split.selection.index;
        const splitY = Number(split.point.y);
        assert.ok(eastY < splitY, 'east proof sample lies in the first half of the split climb');
        const lift = 0.5;
        const moved = Commands.moveGroundProfilePoint(
            payload, mapIndex, splitIndex, splitY, Number(split.point.z) + lift);
        assert.equal(moved.ok, true, 'Studio command raises the inserted Port profile point');
        const interpolation = (eastY - Number(profile[1].y))
            / (splitY - Number(profile[1].y));
        const expectedLift = interpolation * lift;
        fs.writeFileSync(mapPath, JSON.stringify(maps, null, 2) + '\n');

        const after = captureTownFrames(previewExe, gameRoot);
        const frame = (frames, label) => {
            const found = frames.find(candidate => candidate.label === label);
            assert.ok(found, `town proof includes ${label}`);
            return found;
        };
        const beforeWest = frame(before, '31-west');
        const beforeCentre = frame(before, '31-centre');
        const beforeEast = frame(before, '31-east');
        const afterWest = frame(after, '31-west');
        const afterCentre = frame(after, '31-centre');
        const afterEast = frame(after, '31-east');

        assert.equal(afterWest.actor.z, beforeWest.actor.z,
            'an edit confined to the climb must not move Port west grounding');
        assert.equal(afterCentre.actor.z, beforeCentre.actor.z,
            'an edit confined to the climb must not move Port centre grounding');
        assert.ok(Math.abs((afterEast.actor.z - beforeEast.actor.z) - expectedLift) < 1e-6,
            `Port east actor root must rise by the profile interpolation delta ${expectedLift}`);
        assert.equal(afterEast.actor.y, beforeEast.actor.y,
            'editing floor elevation must not move the actor along the lane');
        assert.equal(afterWest.image, beforeWest.image,
            'unaffected west compositor pixels remain byte-identical');
        assert.equal(afterCentre.image, beforeCentre.image,
            'unaffected centre compositor pixels remain byte-identical');
        assert.notEqual(afterEast.image, beforeEast.image,
            'the actual Port east compositor frame changes when its grounded actor rises');
    } finally {
        fs.rmSync(stage, { recursive: true, force: true });
    }
});