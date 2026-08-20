'use strict';

// #825: the cross-process lock around the Thestra Studio host rebuild.
//
// The property under test is mutual exclusion between PROCESSES, so these tests
// spawn real ones. The critical test is the negative control: the same harness
// run with the lock disabled must FAIL. Without that, "the locked run did not
// interleave" is equally consistent with a harness too coarse to observe
// interleaving at all -- and this race is intermittent, so a passing suite is
// not evidence on its own.
const assert = require('node:assert/strict');
const { test } = require('node:test');
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const HOST = path.join(__dirname, 'windows-dev-host.js');

function tempDir() {
    return fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-host-lock-'));
}

// Each child enters the critical section, dwells, then leaves, appending a
// marker at each edge. Serialized runs read ENTER/LEAVE, ENTER/LEAVE. An
// overlap reads ENTER, ENTER.
const CHILD = `
const fs = require('fs');
const { withHostLock } = require(process.argv[2]);
const hostPath = process.argv[3];
const log = process.argv[4];
const useLock = process.argv[5] === 'lock';
const dwellMs = Number(process.argv[6]);
const mark = (what) => fs.appendFileSync(log, what + ' ' + process.pid + String.fromCharCode(10));

async function critical() {
    mark('ENTER');
    await new Promise((r) => setTimeout(r, dwellMs));
    mark('LEAVE');
}

(async () => {
    if (useLock) await withHostLock(hostPath, critical, { waitMs: 30000 });
    else await critical();
})().catch((error) => { console.error(error.message); process.exit(1); });
`;

function runPair({ dir, mode, dwellMs = 300 }) {
    const childPath = path.join(dir, 'child.js');
    fs.writeFileSync(childPath, CHILD, 'utf8');
    const hostPath = path.join(dir, 'host.exe');
    const log = path.join(dir, 'log.txt');
    fs.writeFileSync(log, '', 'utf8');

    const spawnOne = () => new Promise((resolve) => {
        const child = spawn(process.execPath,
            [childPath, HOST, hostPath, log, mode, String(dwellMs)],
            { stdio: 'inherit' });
        child.on('close', (code) => resolve(code));
    });
    return Promise.all([spawnOne(), spawnOne()]).then((codes) => ({
        codes,
        events: fs.readFileSync(log, 'utf8').trim().split(/\r?\n/).filter(Boolean),
    }));
}

function overlapped(events) {
    let inside = 0;
    for (const line of events) {
        if (line.startsWith('ENTER')) inside += 1;
        else inside -= 1;
        if (inside > 1) return true;
    }
    return false;
}

test('two processes holding the lock never overlap', async () => {
    const dir = tempDir();
    try {
        const { codes, events } = await runPair({ dir, mode: 'lock' });
        assert.deepStrictEqual(codes, [0, 0]);
        assert.strictEqual(events.length, 4, `expected 4 edges, got: ${events.join(' | ')}`);
        assert.strictEqual(overlapped(events), false, `sections overlapped: ${events.join(' | ')}`);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('NEGATIVE CONTROL: the same harness overlaps when the lock is removed', async () => {
    const dir = tempDir();
    try {
        const { events } = await runPair({ dir, mode: 'nolock' });
        // If this ever stops overlapping, the test above has stopped proving
        // anything and the dwell needs to grow -- do not delete this assertion.
        assert.strictEqual(overlapped(events), true,
            `harness cannot observe interleaving, so the locked case proves nothing: ${events.join(' | ')}`);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('a lock whose holder is gone is broken rather than waited on', async () => {
    const { lockIsStale, withHostLock, lockPathFor } = require('./windows-dev-host');
    const dir = tempDir();
    try {
        const hostPath = path.join(dir, 'host.exe');
        const lockPath = lockPathFor(hostPath);
        // pid 2^22 is above every Windows/Linux pid range in practice.
        fs.writeFileSync(lockPath, JSON.stringify({ pid: 4194304, at: new Date().toISOString() }), 'utf8');
        assert.strictEqual(lockIsStale(lockPath), true);
        let ran = false;
        await withHostLock(hostPath, async () => { ran = true; }, { waitMs: 2000 });
        assert.strictEqual(ran, true, 'a dead holder must not block the next run');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('a live holder is respected until it ages out', () => {
    const { lockIsStale, lockPathFor } = require('./windows-dev-host');
    const dir = tempDir();
    try {
        const lockPath = lockPathFor(path.join(dir, 'host.exe'));
        fs.writeFileSync(lockPath, JSON.stringify({ pid: process.pid, at: new Date().toISOString() }), 'utf8');
        assert.strictEqual(lockIsStale(lockPath), false, 'this process is alive; its lock is not stale');
        // Same live holder, but older than any rebuild takes.
        assert.strictEqual(lockIsStale(lockPath, Date.now() + 10 * 60 * 1000), true);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('an unreadable lock file is judged by age, not assumed dead', () => {
    const { lockIsStale, lockPathFor } = require('./windows-dev-host');
    const dir = tempDir();
    try {
        const lockPath = lockPathFor(path.join(dir, 'host.exe'));
        fs.writeFileSync(lockPath, '{half-writ', 'utf8');
        assert.strictEqual(lockIsStale(lockPath), false, 'a torn write is not evidence the holder died');
        assert.strictEqual(lockIsStale(lockPath, Date.now() + 10 * 60 * 1000), true);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('a missing lock file is not stale', () => {
    const { lockIsStale, lockPathFor } = require('./windows-dev-host');
    assert.strictEqual(lockIsStale(lockPathFor(path.join(tempDir(), 'gone.exe'))), false);
});
