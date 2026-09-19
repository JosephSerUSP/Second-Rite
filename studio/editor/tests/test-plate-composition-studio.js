'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..', '..', '..');
const panel = fs.readFileSync(path.join(root, 'studio', 'editor', 'js', 'plate-composition-studio.js'), 'utf8');
const server = fs.readFileSync(path.join(root, 'studio', 'editor', 'server.js'), 'utf8');

assert.match(panel, /Map camera — Save Changes/, 'Map traversal camera must retain normal bulk-data save ownership');
assert.match(panel, /Plate calibration — Save package/, 'environment package calibration needs its own explicit save boundary');
assert.match(panel, /Player X and camera Frame X are intentionally independent/, 'the panel must not normalize distinct camera and player anchors');
assert.match(panel, /Read-only references: .*package anchors/, 'anchors and Events remain references, not duplicate transforms');
assert.match(panel, /Image assistance is review-only/, 'manual controls precede any candidate assistance');
assert.match(panel, /setPlateManifestOverride/, 'staged calibration must update the plate preview before package save');
assert.match(server, /plateManifestStorage\.write/, 'package writes must pass the constrained storage boundary');
assert.match(server, /STALE_PLATE_MANIFEST/, 'package writes must reject a stale editor view');
console.log('Plate Composition Studio authority tests OK');
