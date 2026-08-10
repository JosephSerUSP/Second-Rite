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

test('model asset fields use the preview itself as the picker control', () => {
    assert.match(integration,
        /function promoteModelFieldPreview\([\s\S]*?previewWrap\.onclick\s*=/,
        'shared model fields must open from a single click on the preview');
    assert.match(integration,
        /previewWrap\.setAttribute\(['"]role['"],\s*['"]button['"]\)/,
        'visual picker control should retain keyboard/button semantics');
    assert.match(integration,
        /button\.remove\(\)/,
        'redundant Pick buttons should be removed once the preview owns selection');
});

test('regular map-event preview is the 3D picker control and selection creates an override', () => {
    assert.match(integration,
        /function openEventModelPicker\([\s\S]*?root\.openModelPicker\(effectiveEventModelPath\(\),\s*setEventModelFromPicker/,
        'regular Event preview must open the shared 3D picker from the effective model');
    assert.match(integration,
        /if \(path\) \{\s*\n\s*mode\.value\s*=\s*['"]override['"]/,
        'choosing a model from an inherited Event must author a local override');
    assert.match(integration,
        /previewWrap\.onclick\s*=\s*event\s*=>\s*\{[\s\S]*?openEventModelPicker\(\)/,
        'regular Event preview itself must be clickable');
    assert.match(integration,
        /root\.openAssetPickerForEventModel\s*=\s*openEventModelPicker/,
        'legacy Event browse action should remain a compatibility alias');
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
