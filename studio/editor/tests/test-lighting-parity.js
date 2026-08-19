'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const test = require('node:test');

const Adapter = require('../js/second-rite-editor-adapter.js');
const Contract = require('../js/thestra-viewport-contract.js');
const ROOT = path.resolve(__dirname, '..', '..', '..');
const fixture = JSON.parse(fs.readFileSync(
    path.join(ROOT, 'tests', 'fixtures', 'lighting_parity.json'), 'utf8'
));
const tolerance = Number(fixture.tolerance || 1e-8);

function sceneFromRows(rows) {
    const cells = [];
    rows.forEach((row, y) => {
        Array.from(row).forEach((cell, x) => {
            cells.push({ cell: { x, y }, role: cell === '#' ? 'wall' : 'floor' });
        });
    });
    return {
        bounds: { width: rows[0].length, height: rows.length },
        cells
    };
}

function assertRgb(caseName, label, actual, expected) {
    for (let channel = 0; channel < 3; channel++) {
        assert.ok(Math.abs(Number(actual[channel]) - Number(expected[channel])) <= tolerance,
            `${caseName} ${label} channel ${channel}: expected ${expected[channel]}, got ${actual[channel]}`);
    }
}

function orientationFactor(faceRole) {
    const source = faceRole === 'side-wall'
        ? { surface: 'north-wall' }
        : faceRole === 'front-wall'
            ? { surface: 'east-wall' }
            : { surface: 'floor' };
    return Adapter.surfaceOrientationFactor({ source });
}

test('shared JSON static-light corpus matches Studio bake and orientation semantics', () => {
    for (const fixtureCase of fixture.cases) {
        const field = Contract.bakeAuthoringLighting(
            sceneFromRows(fixtureCase.rows), fixtureCase.sources, fixtureCase.ambient
        );
        for (const sample of fixtureCase.samples || []) {
            assertRgb(fixtureCase.name, `vertex (${sample.x},${sample.y})`,
                field[sample.y][sample.x], sample.expect);
        }
        for (const sample of fixtureCase.surfaceSamples || []) {
            const base = field[sample.y][sample.x];
            const factor = orientationFactor(sample.faceRole);
            assert.ok(Math.abs(factor - Number(fixture.orientationFactors[sample.faceRole])) <= tolerance,
                `${sample.faceRole} production factor must match shared fixture`);
            assertRgb(fixtureCase.name, sample.faceRole,
                base.map(value => value * factor), sample.expect);
        }
    }
});
