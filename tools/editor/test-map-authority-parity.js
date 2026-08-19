'use strict';

// #739 positive parity control for sharing one persistent runtime Map authority.
//
// The failure we are fixing is not "inspection is semantically wrong"; it is
// that the cold one-shot inspection process can cross its 60s bridge budget in
// G6. Moving inspection into a warm process trades process isolation for
// continuity, so this test makes that trade explicit: compare the old cold
// authority with warm request 1, warm request 2, and requests separated by the
// other route served by the same process. Any state leakage or missing runtime
// initialization must change the payload and fail this gate.

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const bridge = require('./runtime-bridge-server');
const { createRuntimeMapAuthorityWorker } = require('./runtime-map-authority-worker');

function elapsedMs(start) {
    return Number(process.hrtime.bigint() - start) / 1e6;
}

async function timed(fn) {
    const start = process.hrtime.bigint();
    const value = await fn();
    return { value, ms: elapsedMs(start) };
}

async function main() {
    const previewExe = process.env.LOVEC || process.env.LOVE_PATH;
    if (!previewExe || !fs.existsSync(previewExe)) {
        throw new Error('test-map-authority-parity requires LOVEC or LOVE_PATH pointing at LÖVE');
    }

    const repoRoot = path.resolve(__dirname, '..', '..');
    const projectRoot = require('../semantic-roots').DEFAULT_PROJECT_ROOT;
    const authoredStorage = require('./authored-storage');
    const maps = authoredStorage.loadResource(path.join(projectRoot, 'data'), 'maps').value || [];
    const authoredMap = maps.find(map => Number(map.id) === 2)
        || maps.find(map => Array.isArray(map.layout) && map.layout.length > 0);
    assert.ok(authoredMap, 'default Project supplies an authored Map fixture');

    const request = {
        map: JSON.parse(JSON.stringify(authoredMap)),
        seed: 424242,
        renderableEncoding: 'instances',
    };
    const coldOptions = {
        installRoot: repoRoot,
        projectRoot,
        previewExe,
    };

    const coldInspection = await timed(() => bridge.compileInspection(request, coldOptions));
    const coldRenderable = await timed(() => bridge.compileRenderable(request, coldOptions));

    const authority = createRuntimeMapAuthorityWorker({
        installRoot: repoRoot,
        projectRoot,
        previewExe,
        parseRenderableOutput: bridge.parseRenderableOutput,
        parseInspectionOutput: bridge.parseInspectionOutput,
        inspectionMaxBytes: bridge.INSPECTION_MAX_BUFFER,
        timeoutMs: bridge.BRIDGE_TIMEOUT_MS,
        maxOutputBytes: bridge.RENDERABLE_MAX_BUFFER,
    });

    try {
        const warmInspectionA = await timed(() => authority.compileInspection(request));
        const firstState = authority.state();
        const pid = firstState && firstState.generation && firstState.generation.pid;
        assert.ok(pid, 'persistent Map authority reports a live generation PID');

        const warmInspectionB = await timed(() => authority.compileInspection(request));
        const warmRenderableA = await timed(() => authority.compile(request));
        const afterRenderableState = authority.state();
        const warmInspectionAfterRenderable = await timed(() => authority.compileInspection(request));
        const warmRenderableAfterInspection = await timed(() => authority.compile(request));
        const finalState = authority.state();

        assert.deepStrictEqual(warmInspectionA.value, coldInspection.value,
            'first warm inspection matches the cold runtime authority exactly');
        assert.deepStrictEqual(warmInspectionB.value, coldInspection.value,
            'second warm inspection cannot leak state from the first');
        assert.deepStrictEqual(warmInspectionAfterRenderable.value, coldInspection.value,
            'renderable work in the same process cannot contaminate inspection');
        assert.deepStrictEqual(warmRenderableA.value, coldRenderable.value,
            'warm compact renderable remains equal to its cold runtime authority');
        assert.deepStrictEqual(warmRenderableAfterInspection.value, coldRenderable.value,
            'inspection work cannot contaminate a later renderable');

        assert.equal(afterRenderableState.generation.pid, pid,
            'inspection and renderable share one persistent generation');
        assert.equal(finalState.generation.pid, pid,
            'all warm parity controls remain on the same generation');

        console.log('MAP AUTHORITY PARITY OK');
        console.log(JSON.stringify({
            mapId: request.map.id,
            pid,
            coldInspectionMs: Number(coldInspection.ms.toFixed(3)),
            coldRenderableMs: Number(coldRenderable.ms.toFixed(3)),
            warmInspectionFirstMs: Number(warmInspectionA.ms.toFixed(3)),
            warmInspectionSecondMs: Number(warmInspectionB.ms.toFixed(3)),
            warmRenderableMs: Number(warmRenderableA.ms.toFixed(3)),
            warmInspectionAfterRenderableMs: Number(warmInspectionAfterRenderable.ms.toFixed(3)),
            warmRenderableAfterInspectionMs: Number(warmRenderableAfterInspection.ms.toFixed(3)),
        }));
    } finally {
        await authority.shutdown();
    }
}

main().catch(error => {
    console.error(error && error.stack ? error.stack : error);
    process.exitCode = 1;
});
