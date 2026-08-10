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

test('owned model asset fields use the preview itself as the picker control', () => {
    assert.match(integration,
        /function promoteModelFieldPreview\([\s\S]*?previewWrap\.onclick\s*=/,
        'shared owned model fields must open from a single click on the preview');
    assert.match(integration,
        /previewWrap\.setAttribute\(['"]role['"],\s*['"]button['"]\)/,
        'visual picker control should retain keyboard/button semantics');
    assert.match(integration,
        /button\.remove\(\)/,
        'redundant Pick buttons should be removed once the preview owns selection');
});

test('regular Event preview is editable only for an explicit model override', () => {
    assert.match(integration,
        /function openEventModelPicker\([\s\S]*?mode\.value\s*!==\s*['"]override['"][\s\S]*?root\.openModelPicker\(input\.value/,
        'Event picker must refuse inherit/suppress modes and open only the local override path');
    assert.match(integration,
        /function setEventModelFromPicker\([\s\S]*?mode\.value\s*!==\s*['"]override['"][\s\S]*?input\.value\s*=/,
        'picker selection must edit the path without silently changing ownership mode');
    assert.doesNotMatch(integration,
        /mode\.value\s*=\s*['"]override['"]/,
        'clicking/selecting a model must never silently switch Event ownership to override');
    assert.match(integration,
        /const ownsValue\s*=\s*!!mode\s*&&\s*mode\.value\s*===\s*['"]override['"][\s\S]*?model-picker-disabled/,
        'inherited/suppressed previews must visibly become non-interactive');
});

test('regular map-event preview renders the effective inherited 3D model', () => {
    assert.match(integration,
        /function effectiveEventModelPath\([\s\S]*?linkedCommonEventModel\(\)/,
        'event preview must resolve an inherited Common Event model');
    assert.match(integration,
        /new api\.ModelPreview\([\s\S]*?effectiveEventModelPath\(\)/,
        'regular Event preview must be driven by ModelPreview, not an image element');
    assert.match(integration,
        /modelRow\.style\.display\s*=\s*['"]flex['"]/,
        'effective model preview must stay visible while model mode is inherit');
    assert.match(integration,
        /Inherited 3D model — choose Override to edit/,
        'inherited preview should explain why it is read-only');
});

test('raw model asset paths are not primary preview UI', () => {
    assert.match(integration,
        /\.model-picker-path,\s*\n\s*\.model-field-path,\s*\n\s*#event-prop-model-path\s*\{\s*\n\s*display:\s*none\s*!important;/,
        'picker, compact field, and regular Event path strings should be hidden');
    assert.match(integration,
        /installMetadataPathScrubber/,
        'picker metadata should strip raw OBJ/MTL project paths');
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
