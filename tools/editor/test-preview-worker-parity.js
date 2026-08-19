'use strict';

// Parity gate for the persistent preview worker.
//
// Moving the preview commands off a cold subprocess trades process isolation
// for speed. A cold `lovec . preview-font` could not possibly leak state into
// the next request; a warm worker can -- animation_player, ui, Effekseer and
// the canvas all persist across requests now.
//
// So the claim that has to be proven is not "it is faster", which is obvious,
// but "it still answers the same". Every command is run cold once and warm
// twice, and all three payloads must be identical. The second warm run is what
// catches state that only bleeds after a request has already happened.
//
// Run:  node tools/editor/test-preview-worker-parity.js

const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const projectRoot = require('./project-root');
const projectPlay = require('./project-play');
const { createRuntimePreviewWorker } = require('./runtime-preview-worker');

function resolveLove() {
    const configured = process.env.LOVE_PATH;
    if (configured && fs.existsSync(configured)) return configured;
    const fallback = 'C:/Program Files/LOVE/lovec.exe';
    return fs.existsSync(fallback) ? fallback : null;
}

const love = resolveLove();
if (!love) {
    console.log('preview worker parity: SKIPPED (LOVE not found; set LOVE_PATH)');
    process.exit(0);
}

// The cold reference goes through the same staging boundary the endpoints used
// before this change, so it is the behaviour being preserved, not a new one.
function coldPreview(args) {
    // Same staging boundary the endpoints used before this change, so the
    // reference is the behaviour being preserved rather than a new one.
    const stageDir = projectPlay.stageProject({
        installRoot: projectRoot.INSTALL_ROOT,
        projectRoot: projectRoot.PROJECT_ROOT,
    });
    try {
        const run = spawnSync(love, [stageDir, ...args], {
            encoding: 'utf8', timeout: 180000, maxBuffer: 256 * 1024 * 1024, windowsHide: true,
        });
        return parseEnvelope(run.stdout);
    } finally {
        try { projectPlay.removeStage(stageDir); } catch (e) { /* cleanup is best effort */ }
    }
}

function parseEnvelope(stdout) {
    const text = String(stdout || '');
    const begin = text.indexOf('PREVIEW BEGIN');
    const end = text.indexOf('PREVIEW END');
    if (begin === -1 || end === -1 || end < begin) {
        throw new Error('cold preview produced no output');
    }
    return JSON.parse(text.slice(begin + 'PREVIEW BEGIN'.length, end).trim());
}

function firstSceneId() {
    try {
        const dir = path.join(projectRoot.PROJECT_ROOT, 'data', 'scenes');
        const names = fs.readdirSync(dir).filter(n => /\.json$/i.test(n) && n !== 'index.json').sort();
        if (names.length) return names[0].replace(/\.json$/i, '');
    } catch (e) { /* fall through */ }
    return null;
}

const cases = [
    { command: 'preview-font', payload: { name: '', size: '8' }, cold: ['preview-font', '', '8'] },
    { command: 'preview-font', payload: { name: '', size: '12' }, cold: ['preview-font', '', '12'] },
];

const sceneId = firstSceneId();
if (sceneId) {
    cases.push({ command: 'preview-scene', payload: { sceneId }, cold: ['preview-scene', sceneId] });
}

(async () => {
    const worker = createRuntimePreviewWorker({
        installRoot: projectRoot.INSTALL_ROOT,
        projectRoot: projectRoot.PROJECT_ROOT,
        previewExe: love,
        timeoutMs: 180000,
        startupTimeoutMs: 120000,
        maxOutputBytes: 256 * 1024 * 1024,
    });

    let checked = 0;
    try {
        for (const testCase of cases) {
            const cold = coldPreview(testCase.cold);
            const warmFirst = await worker.run(testCase.command, testCase.payload);
            const warmSecond = await worker.run(testCase.command, testCase.payload);

            const label = `${testCase.command} ${JSON.stringify(testCase.payload)}`;
            assert.deepStrictEqual(warmFirst, cold, `warm run differs from cold for ${label}`);
            assert.deepStrictEqual(warmSecond, warmFirst,
                `second warm run differs from the first for ${label}; the worker is carrying state between requests`);
            checked++;
        }
    } finally {
        await worker.shutdown();
    }

    assert.ok(checked > 0, 'the parity gate must compare at least one command');
    console.log(`preview worker parity: OK (${checked} commands identical cold and warm)`);
})().catch(error => { console.error(error && error.message ? error.message : error); process.exit(1); });
