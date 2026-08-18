'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const source = fs.readFileSync(path.join(__dirname, 'js', 'widgets.js'), 'utf8');
const start = source.indexOf('const STAT_DEFS = [');
const end = source.indexOf("} else if (activeUnitSubTab === 'combat')", start);
assert.ok(start >= 0 && end > start, 'Unit Stats authoring block should remain discoverable');
const stats = source.slice(start, end);

assert.match(stats, /function redrawUnitStatCurve\s*\(/,
    'Unit Stats should own a curve-only redraw primitive');
assert.match(stats, /input\.oninput\s*=\s*\(\)\s*=>\s*\{[\s\S]*?redrawUnitStatCurve\(cell, key, label\);[\s\S]*?\}/,
    'base-stat input should redraw only its own curve');

const handler = stats.match(/input\.oninput\s*=\s*\(\)\s*=>\s*\{([\s\S]*?)\n\s*\};/);
assert.ok(handler, 'base-stat input handler should remain present');
assert.doesNotMatch(handler[1], /renderUnitStatCurves\s*\(/,
    'a keystroke must not destroy and rebuild the six focused stat inputs');

console.log('Unit stat input lifecycle contract: OK');
