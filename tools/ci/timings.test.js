'use strict';

// #811 step 1. The properties worth guarding are not "does it measure a number"
// -- it is a subtraction of two clock reads -- but the two rules that make the
// instrumentation safe to put in front of every gate:
//
//   * the wrapper is TRANSPARENT (exit code and stdio survive it), and
//   * recording NEVER fails the wrapped command.
//
// Each of those has a negative control here, because a wrapper that passes only
// the exit-0 case is a wrapper nobody has actually tested.
const assert = require('node:assert');
const { test } = require('node:test');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const TIME_STEP = path.join(__dirname, 'time-step.js');

function withTempDir(fn) {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-timings-'));
    try {
        return fn(dir);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
}

function runWrapper(dir, args, extraEnv = {}) {
    return spawnSync(process.execPath, [TIME_STEP, ...args], {
        encoding: 'utf8',
        env: {
            ...process.env,
            THESTRA_TIMINGS_DIR: dir,
            THESTRA_TIMINGS_RUN_ID: 'test-run',
            THESTRA_TIMINGS: extraEnv.THESTRA_TIMINGS ?? '',
        },
    });
}

function recordsIn(dir) {
    const timings = requireFresh(dir);
    return timings.loadRun('test-run');
}

function requireFresh(dir) {
    process.env.THESTRA_TIMINGS_DIR = dir;
    delete require.cache[require.resolve('./timings')];
    return require('./timings');
}

test('the wrapper passes a success exit code through', () => {
    withTempDir((dir) => {
        const result = runWrapper(dir, ['--label', 'ok', '--', process.execPath, '-e', 'process.exit(0)']);
        assert.strictEqual(result.status, 0);
        const records = recordsIn(dir);
        assert.strictEqual(records.length, 1);
        assert.strictEqual(records[0].label, 'ok');
        assert.strictEqual(records[0].ok, true);
        assert.strictEqual(records[0].phase, 'cold');
    });
});

test('negative control: a failing command still fails through the wrapper', () => {
    withTempDir((dir) => {
        const result = runWrapper(dir, ['--label', 'boom', '--', process.execPath, '-e', 'process.exit(3)']);
        // The whole point: instrumentation must not swallow a red gate.
        assert.strictEqual(result.status, 3);
        const records = recordsIn(dir);
        assert.strictEqual(records[0].ok, false);
        assert.strictEqual(records[0].exitCode, 3);
    });
});

test('negative control: an unrecordable timings dir does not fail the command', () => {
    withTempDir((dir) => {
        // A file where the directory should be makes every write path fail.
        const blocked = path.join(dir, 'blocked');
        fs.writeFileSync(blocked, 'not a directory', 'utf8');
        const result = spawnSync(process.execPath, [TIME_STEP, '--label', 'x', '--', process.execPath, '-e', 'process.exit(0)'], {
            encoding: 'utf8',
            env: { ...process.env, THESTRA_TIMINGS_DIR: blocked, THESTRA_TIMINGS_RUN_ID: 'test-run' },
        });
        assert.strictEqual(result.status, 0, 'a failed timing write must not turn a green step red');
    });
});

test('child stdout survives the wrapper', () => {
    withTempDir((dir) => {
        const result = runWrapper(dir, ['--label', 'chatty', '--', process.execPath, '-e', 'console.log("gate output")']);
        assert.match(result.stdout, /gate output/);
    });
});

test('THESTRA_TIMINGS=0 runs the command and records nothing', () => {
    withTempDir((dir) => {
        const result = runWrapper(dir, ['--label', 'off', '--', process.execPath, '-e', 'process.exit(0)'], { THESTRA_TIMINGS: '0' });
        assert.strictEqual(result.status, 0);
        assert.strictEqual(recordsIn(dir).length, 0);
    });
});

test('the first run of a label is cold and later runs are warm', () => {
    withTempDir((dir) => {
        runWrapper(dir, ['--label', 'repeat', '--', process.execPath, '-e', '0']);
        runWrapper(dir, ['--label', 'repeat', '--', process.execPath, '-e', '0']);
        runWrapper(dir, ['--label', 'other', '--', process.execPath, '-e', '0']);
        const records = recordsIn(dir);
        assert.deepStrictEqual(
            records.map((entry) => `${entry.label}:${entry.phase}`),
            ['repeat:cold', 'repeat:warm', 'other:cold'],
        );
    });
});

test('a truncated final line does not poison a report', () => {
    withTempDir((dir) => {
        const timings = requireFresh(dir);
        timings.record({ label: 'good', ms: 5, ok: true, exitCode: 0, runId: 'test-run' });
        fs.appendFileSync(timings.timingsFile('test-run'), '{"label":"trunca', 'utf8');
        const records = timings.loadRun('test-run');
        assert.strictEqual(records.length, 1);
        assert.strictEqual(records[0].label, 'good');
    });
});

test('the summary separates cold from the warm mean and ranks by total', () => {
    const rows = require('./timings').summarize([
        { label: 'slow', phase: 'cold', ms: 1000, ok: true },
        { label: 'slow', phase: 'warm', ms: 200, ok: true },
        { label: 'slow', phase: 'warm', ms: 400, ok: true },
        { label: 'quick', phase: 'cold', ms: 50, ok: false },
    ]);
    assert.strictEqual(rows[0].label, 'slow');
    assert.strictEqual(rows[0].coldMs, 1000);
    assert.strictEqual(rows[0].warmMeanMs, 300);
    assert.strictEqual(rows[0].totalMs, 1600);
    assert.strictEqual(rows[1].failures, 1);
});

test('--record stores a timing for a command the caller already ran', () => {
    withTempDir((dir) => {
        const result = runWrapper(dir, ['--record', '--label', 'G2 battle', '--ms', '41230', '--exit', '0']);
        assert.strictEqual(result.status, 0);
        const records = recordsIn(dir);
        assert.strictEqual(records.length, 1);
        assert.strictEqual(records[0].ms, 41230);
        assert.strictEqual(records[0].ok, true);
    });
});

test('--record carries a non-zero exit through as a failure', () => {
    withTempDir((dir) => {
        runWrapper(dir, ['--record', '--label', 'G2 battle', '--ms', '900', '--exit', '1']);
        const records = recordsIn(dir);
        assert.strictEqual(records[0].ok, false);
        assert.strictEqual(records[0].exitCode, 1);
    });
});

test('negative control: --record runs no child process at all', () => {
    withTempDir((dir) => {
        // The whole reason --record exists is that re-spawning changed the
        // environment a PowerShell gate ran in. If --record ever spawned the
        // trailing command, it would reintroduce exactly that hazard.
        const canary = path.join(dir, 'canary.txt');
        const result = runWrapper(dir, [
            '--record', '--label', 'nospawn', '--ms', '10', '--',
            process.execPath, '-e', `require('fs').writeFileSync(${JSON.stringify(canary)}, 'ran')`,
        ]);
        assert.strictEqual(result.status, 0);
        assert.strictEqual(fs.existsSync(canary), false, '--record must never execute the command');
        // ...but it should still note what the caller says it measured.
        assert.match(recordsIn(dir)[0].command, /-e/);
    });
});

test('--record without --ms is a usage error, not a silent no-op', () => {
    withTempDir((dir) => {
        const result = runWrapper(dir, ['--record', '--label', 'oops']);
        assert.strictEqual(result.status, 2);
        assert.strictEqual(recordsIn(dir).length, 0);
    });
});
