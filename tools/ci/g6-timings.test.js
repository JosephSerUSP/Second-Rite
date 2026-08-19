'use strict';
const assert = require('node:assert');
const { test } = require('node:test');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const REPORT = require('./report-timings');
const BATCH = path.join(__dirname, 'record-timings-batch.js');

test('batch recorder preserves nested G6 timing tags without running a command', () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'g6-timing-batch-'));
    try {
        const input = [{
            label: 'G6 capture frame', ms: 123, ok: true, exitCode: 0,
            tags: { kind: 'g6-frame', frame: 'x.png', screenshotRoundTripsMs: [11, 12] },
        }];
        const result = spawnSync(process.execPath, [BATCH], {
            input: JSON.stringify(input), encoding: 'utf8',
            env: { ...process.env, THESTRA_TIMINGS_DIR: dir, THESTRA_TIMINGS_RUN_ID: 'test-g6' },
        });
        assert.strictEqual(result.status, 0, result.stderr);
        const line = fs.readFileSync(path.join(dir, 'test-g6.jsonl'), 'utf8').trim();
        const record = JSON.parse(line);
        assert.deepStrictEqual(record.tags.screenshotRoundTripsMs, [11, 12]);
        assert.strictEqual(record.phase, 'cold');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('G6 report reconciles the leg and ranks slow frames first', () => {
    const records = [
        { runId: 'r', label: 'G6 capture frame', ms: 100, ok: true, tags: { kind: 'g6-frame', leg: 'base-b', frame: 'fast.png', readinessMs: 10, settlingMs: 20, screenshotMs: 30, otherMs: 40, stableScreenshotMs: 50, screenshotRoundTripsMs: [14,16], iterations: 1, binding: 'frame-match' } },
        { runId: 'r', label: 'G6 capture frame', ms: 200, ok: true, tags: { kind: 'g6-frame', leg: 'base-b', frame: 'slow.png', readinessMs: 20, settlingMs: 60, screenshotMs: 80, otherMs: 40, stableScreenshotMs: 110, screenshotRoundTripsMs: [39,41], iterations: 2, binding: 'pending-images' } },
        { runId: 'r', label: 'G6 capture leg', ms: 350, ok: true, tags: { kind: 'g6-leg', leg: 'base-b', targetSha: 'abcdef1234567890', setupReadinessMs: 10, setupOtherMs: 40 } },
    ];
    const output = REPORT.formatG6CaptureReport(records);
    assert.match(output, /Leg wall \*\*350 ms\*\* = readiness \*\*40 ms\*\* \+ settling \*\*80 ms\*\* \+ screenshot round trips \*\*110 ms\*\* \+ other\/setup \*\*120 ms\*\*/);
    assert.ok(output.indexOf('slow.png') < output.indexOf('fast.png'));
    assert.match(output, /pending-images/);
    assert.match(output, /stable_screenshot wall/);
});
