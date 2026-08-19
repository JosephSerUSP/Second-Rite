'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const test = require('node:test');
const semanticRoots = require('../../semantic-roots');

const root = path.resolve(__dirname, '..', '..', '..');
const read = (...parts) => fs.readFileSync(path.join(root, ...parts), 'utf8');

test('map authoring exposes only the runtime-consumed encounter rate', () => {
    const mapsDir = path.join(semanticRoots.DEFAULT_PROJECT_ROOT, 'data', 'maps');
    const mapIndex = JSON.parse(fs.readFileSync(path.join(mapsDir, 'index.json'), 'utf8'));
    for (const filename of mapIndex.files) {
        const map = JSON.parse(fs.readFileSync(path.join(mapsDir, filename), 'utf8'));
        assert.ok(!Object.hasOwn(map, 'encounterSteps'), `${filename} retains inert encounterSteps`);
    }

    const markup = read('tools', 'editor', 'index.html');
    const editor = read('tools', 'editor', 'js', 'map-editor.js');
    const prompt = read('tools', 'campaign-gen', 'prompts', 'maps.md');
    const formula = read('runtime', 'engine', 'formula.lua');
    assert.ok(!markup.includes('prop-map-enc-steps'), 'Studio still renders an inert cadence control');
    assert.ok(!editor.includes('encounterSteps'), 'Studio still writes an inert cadence field');
    assert.ok(!prompt.includes('encounterSteps'), 'campaign generation still asks for an inert cadence field');
    assert.match(formula, /currentMapData\.encounterRate/, 'formula context must retain the map rate authority');
});
