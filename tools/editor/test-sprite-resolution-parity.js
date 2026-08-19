'use strict';

// #794 parity gate: Studio's local sprite resolver and the LÖVE runtime must
// answer identically for every sprite in the Project.
//
// This is the check that makes removing the subprocess safe. Before #794 the
// runtime WAS the oracle, so agreement was trivially guaranteed and cost ~4 s
// per sprite. Now both hosts execute the same generated leaves, and this test
// is what proves that claim rather than asserting it.
//
// Run:  node tools/editor/test-sprite-resolution-parity.js
// Needs a staged Project and LOVE; skips loudly if either is unavailable.

const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const projectRoot = require('./project-root');
const { createLocalSpriteResolver } = require('./sprite-resolution-local');
const spriteResolution = require('./js/generated/sprite-resolution');

function resolveLove() {
    const configured = process.env.LOVE_PATH;
    if (configured && fs.existsSync(configured)) return configured;
    const fallback = 'C:/Program Files/LOVE/lovec.exe';
    return fs.existsSync(fallback) ? fallback : null;
}

function stageProject(outDir) {
    const result = spawnSync(process.execPath,
        [path.join(__dirname, '..', 'ci', 'stage-project-gates.js'), '--output', outDir],
        { cwd: projectRoot.INSTALL_ROOT, encoding: 'utf8', windowsHide: true });
    return result.status === 0;
}

function runtimeDescribe(love, stageDir, spec) {
    const result = spawnSync(love, [stageDir, 'sprite-meta', JSON.stringify(spec)],
        { cwd: stageDir, encoding: 'utf8', windowsHide: true, timeout: 120000, maxBuffer: 4 * 1024 * 1024 });
    const match = String(result.stdout || '').match(/SPRITE META BEGIN\s*\r?\n([\s\S]*?)\r?\nSPRITE META END/);
    if (!match) throw new Error('runtime produced no sprite metadata');
    return JSON.parse(match[1]);
}

// Two Lua/JSON impedance mismatches, neither of which is a resolution
// difference. Normalizing them is what keeps this test about the rules:
//
//   1. An empty Lua table encodes as `[]`, a populated one as an object.
//   2. A Lua table cannot hold nil, so `timing.token = nil` simply vanishes,
//      where the JavaScript host emits `"token": null`.
//
// Anything that survives both is a real disagreement about which file a key
// means or what its timing is.
function dropNulls(value) {
    if (value === null || typeof value !== 'object' || Array.isArray(value)) return value;
    const out = {};
    for (const key of Object.keys(value)) {
        if (value[key] === null) continue;
        out[key] = dropNulls(value[key]);
    }
    return out;
}

function normalize(payload) {
    const copy = JSON.parse(JSON.stringify(payload));
    for (const field of ['keyTokens', 'filenameTokens', 'tokens']) {
        const value = copy[field];
        if (Array.isArray(value) && value.length === 0) copy[field] = {};
    }
    return dropNulls(copy);
}

function sampleKeys(root) {
    const keys = [];
    for (const dir of spriteResolution.ASSET_DIRS) {
        let names = [];
        try { names = fs.readdirSync(path.join(root, ...dir.split('/'))); } catch (e) { continue; }
        for (const name of names.filter(n => /\.png$/i.test(n)).sort()) {
            keys.push(name.replace(/\.png$/i, ''));
        }
    }
    return keys;
}

const love = resolveLove();
if (!love) {
    console.log('sprite resolution parity: SKIPPED (LOVE not found; set LOVE_PATH)');
    process.exit(0);
}

const stageDir = path.join(require('node:os').tmpdir(), 'thestra-sprite-parity');
fs.rmSync(stageDir, { recursive: true, force: true });
if (!stageProject(stageDir)) {
    console.log('sprite resolution parity: SKIPPED (Project staging failed)');
    process.exit(0);
}

const local = createLocalSpriteResolver({ projectRoot: projectRoot.PROJECT_ROOT });
const stems = sampleKeys(projectRoot.PROJECT_ROOT);
assert.ok(stems.length > 0, 'the Project must contain sprites to compare');

// Every real sprite, plus keys that exercise the parts most likely to diverge:
// case folding in the candidate list, a key-level token overriding a filename
// token, and a key that resolves to nothing at all.
const cases = [];
for (const stem of stems) cases.push({ key: stem });
const withToken = stems.find(s => s.includes('['));
if (withToken) {
    const base = withToken.substring(0, withToken.indexOf('['));
    cases.push({ key: base });
    cases.push({ key: base + '[fps=30]' });
    cases.push({ key: base.toLowerCase() });
    cases.push({ key: base.toUpperCase() });
}
cases.push({ key: 'definitely-not-a-sprite' });
cases.push({ key: '' });

(async () => {
    let compared = 0;
    const divergences = [];
    for (const spec of cases) {
        const mine = normalize(await local(spec));
        const theirs = normalize(runtimeDescribe(love, stageDir, spec));
        compared++;
        try {
            assert.deepStrictEqual(mine, theirs);
        } catch (e) {
            divergences.push({ spec, mine, theirs });
        }
    }

    if (divergences.length) {
        for (const d of divergences.slice(0, 5)) {
            console.error('DIVERGENCE for ' + JSON.stringify(d.spec));
            console.error('  studio : ' + JSON.stringify(d.mine));
            console.error('  runtime: ' + JSON.stringify(d.theirs));
        }
        console.error(`sprite resolution parity: ${divergences.length}/${compared} diverged`);
        process.exit(1);
    }

    console.log(`sprite resolution parity: OK (${compared} keys agree between Studio and LOVE)`);
})().catch(error => { console.error(error); process.exit(1); });
