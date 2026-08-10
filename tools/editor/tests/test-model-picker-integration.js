'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const test = require('node:test');

const EDITOR = path.resolve(__dirname, '..');
const integration = fs.readFileSync(path.join(EDITOR, 'js', 'model-picker-integration.js'), 'utf8');
const iconField = fs.readFileSync(path.join(EDITOR, 'js', 'icon-field.js'), 'utf8');

test('model picker list is constrained to the modal instead of growing by min-content', () => {
    assert.match(integration,
        /\.model-picker-left,\s*\n\s*\.model-picker-right\s*\{[\s\S]*?min-height:\s*0;[\s\S]*?overflow:\s*hidden;/,
        'picker grid columns must be allowed to shrink inside the modal');
    assert.match(integration,
        /\.model-picker-list\s*\{[\s\S]*?min-height:\s*0;[\s\S]*?overflow:\s*auto;/,
        'long model inventories must scroll inside the list box');
});

test('regular map-event model browse action is bridged to the shared 3D picker', () => {
    assert.match(integration,
        /root\.openAssetPickerForEventModel\s*=\s*function[\s\S]*?root\.openModelPicker\(/,
        'map-event ... button must open the 3D model picker');
});

test('model previews reuse the Studio transparent checker rather than defining another one', () => {
    assert.match(integration, /transparent-checker/,
        'model preview wrappers must opt into the canonical checker class');
    assert.match(integration, /removeProperty\(['"]background['"]\)/,
        'hard-coded model preview backgrounds must be released');
    assert.doesNotMatch(integration, /repeating-conic-gradient/,
        'integration must not duplicate the checkerboard definition');
});

test('Studio integration loads only after the model picker primitive', () => {
    assert.match(iconField, /script\.onload\s*=\s*loadStudioIntegration/,
        'integration must load after model-picker.js is available');
});
