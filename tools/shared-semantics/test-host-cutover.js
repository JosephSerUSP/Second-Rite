'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const repoRoot = path.resolve(__dirname, '..', '..');
const read = relative => fs.readFileSync(path.join(repoRoot, relative), 'utf8').replace(/\r\n/g, '\n');

const index = read('tools/editor/index.html');
const widgets = read('tools/editor/js/widgets.js');
const studioVertex = read('tools/editor/js/vertex-shading.js');
const runtimeVertex = read('runtime/engine/vertex_shading.lua');
const runtimeSprites = read('runtime/presentation/sprite_sheet.lua');

const timingScript = index.indexOf('js/generated/sprite-timing.js');
const widgetsScript = index.indexOf('js/widgets.js');
assert.ok(timingScript >= 0, 'Studio must load generated sprite timing semantics');
assert.ok(widgetsScript >= 0, 'Studio must still load widgets.js');
assert.ok(timingScript < widgetsScript,
    'generated sprite timing semantics must load before widgets.js executes');

assert.match(widgets, /const spriteTimingAuthority = window\.ThestraSpriteTimingSemantics;/);
assert.equal(
    widgets.split('spriteTimingAuthority.effectiveFps(parsedTiming.tokens)').length - 1,
    2,
    'both local animated preview paths must consume the same generated timing authority');
assert.doesNotMatch(widgets, /tokens\.fps \|\| \(tokens\.speed \? 4 \* tokens\.speed : 4\)/,
    'Studio must not reintroduce the handwritten fps/speed/default expression');
assert.doesNotMatch(widgets, /tokens\[k\] = parseFloat\(v\)/,
    'Studio must not reintroduce the handwritten sprite-token parser');

assert.match(runtimeSprites, /require\("engine\.generated\.sprite-timing"\)/,
    'runtime sprite presentation must consume generated timing semantics');
assert.match(runtimeSprites, /sprite_timing\.parseKey/,
    'runtime sprite key parsing must delegate to shared semantics');
assert.match(runtimeSprites, /sprite_timing\.resolveTiming/,
    'runtime timing provenance must delegate to shared semantics');
assert.match(runtimeSprites, /sprite_timing\.effectiveFps/,
    'runtime frame rate must delegate to shared semantics');
assert.doesNotMatch(runtimeSprites, /ss\.fps or \(ss\.speed and 4 \* ss\.speed or 4\)/,
    'runtime must not carry a second fps/speed/default implementation');

assert.match(runtimeVertex, /require\("engine\.generated\.vertex-shading"\)/,
    'runtime vertex shading must consume generated semantics');
assert.match(studioVertex, /require\('\.\/generated\/vertex-shading\.js'\)/,
    'Studio vertex adapter must consume generated semantics in Node');
assert.doesNotMatch(runtimeVertex, /local MODULUS = 65521/,
    'runtime vertex adapter must not carry the old handwritten hash algorithm');
assert.doesNotMatch(studioVertex, /const MODULUS = 65521/,
    'Studio vertex adapter must not carry the old handwritten hash algorithm');

// The runtime HTTP request remains a provenance/inspection side channel. Local
// animation must not wait for it: both preview paths above synchronously use the
// generated leaf and requestSpriteTiming stays an async tooltip metadata helper.
assert.match(widgets, /\/api\/sprite-resolution\?/);
assert.match(widgets, /requestSpriteTiming\(\{ path \}\)\.then/);

console.log('SHARED SEMANTICS HOST CUTOVER OK');
