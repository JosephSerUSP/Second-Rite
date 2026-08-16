'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const EDITOR = path.resolve(__dirname, '..');
const widgets = fs.readFileSync(path.join(EDITOR, 'js', 'widgets.js'), 'utf8');
const modelPicker = fs.readFileSync(path.join(EDITOR, 'js', 'model-picker.js'), 'utf8');
const state = fs.readFileSync(path.join(EDITOR, 'js', 'state.js'), 'utf8');
const golden = path.resolve(EDITOR, '..', 'golden');
const harnessFront = fs.readFileSync(path.join(golden, 'editor-screens.py'), 'utf8');
const harnessCorePath = path.join(golden, 'editor-screens-core.py');
const harness = harnessFront + '\n' + (fs.existsSync(harnessCorePath)
    ? fs.readFileSync(harnessCorePath, 'utf8') : '');

assert.match(widgets, /img\.onload\s*=\s*\(\)\s*=>\s*markReadyAfterPaint/,
    'image previews publish readiness from the actual visible image load');
assert.match(widgets, /box\.setAttribute\(['"]data-preview-ready['"],\s*['"]1['"]\)/,
    'asset picker has a positive painted-preview marker');
assert.match(widgets, /assetPickerRequestId\s*\+=\s*1/,
    'closing the asset picker invalidates late inventory responses');
assert.match(widgets, /assetPickerDirectoryRequestId\s*=\s*0/,
    'asset directory loads have their own request generation');
assert.match(widgets, /const requestId\s*=\s*\+\+assetPickerDirectoryRequestId/,
    'late asset directory responses cannot replace a newer directory');
assert.match(widgets, /assetPreviewGeneration\s*\+=\s*1/,
    'closing the asset picker invalidates late preview paints');

assert.match(modelPicker, /this\.canvas\.setAttribute\(['"]data-preview-ready['"],\s*['"]1['"]\)/,
    'model picker readiness is published by the renderer after drawing faces');
assert.match(modelPicker, /!this\.model\.triangleCount\s*\?\s*['"]No drawable faces['"]/,
    'model readiness cannot be claimed for a non-drawable OBJLoader result');
assert.match(modelPicker, /pickerRequestId\s*\+=\s*1/,
    'closing the model picker invalidates late inventory responses');
assert.match(modelPicker, /!prefersReducedMotion\(\)/,
    'production turntable animation remains enabled outside reduced-motion capture');
assert.match(state, /\['model-picker-modal',\s*\(\)\s*=>\s*typeof closeModelPicker/,
    'Escape closes the dynamically-created model picker through its owner');

// #579 inserts a dependency preflight in front of the byte-preserved capture
// implementation. Treat the front + delegated core as one canonical G6 driver
// for source-level inventory assertions; do not weaken the required frames.
assert.match(harnessFront, /editor-screens-core\.py/,
    'G6 dependency front explicitly delegates to the capture inventory core');
assert.match(harness, /asset-picker\/sprite\.png/,
    'G6 inventory includes the shared asset picker');
assert.match(harness, /model-picker\/item-model\.png/,
    'G6 inventory includes the shared model picker');
assert.match(harness, /data-preview-ready/,
    'G6 waits on positive preview readiness rather than a picker sleep');
assert.match(harness, /ready_wait=/,
    'G6 supports a distinct post-selection readiness condition');

console.log('[PASS] Picker readiness and lifecycle contracts passed.');
