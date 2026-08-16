'use strict';

const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');
const fs = require('fs');
const os = require('os');
const path = require('path');
const test = require('node:test');
const { createProjectWatcher } = require('./project-watcher');

function tempProject() {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-project-watcher-'));
    fs.mkdirSync(path.join(root, 'data', 'units'), { recursive: true });
    fs.mkdirSync(path.join(root, 'assets', 'sprites'), { recursive: true });
    return root;
}

function fakeWatcherFactory(holder) {
    return (roots, options) => {
        const watcher = new EventEmitter();
        watcher.close = async () => {};
        holder.roots = roots;
        holder.options = options;
        holder.watcher = watcher;
        queueMicrotask(() => watcher.emit('ready'));
        return watcher;
    };
}

function deterministicScheduler() {
    let pending = null;
    return {
        schedule(callback) { pending = callback; return callback; },
        cancel() { pending = null; },
        run() { const callback = pending; pending = null; if (callback) callback(); },
    };
}

test('watcher coalesces Project data and asset invalidations', async () => {
    const root = tempProject();
    const holder = {};
    const scheduler = deterministicScheduler();
    const resourceBatches = [];
    const assetBatches = [];
    try {
        const service = createProjectWatcher({
            projectRoot: root,
            watchFactory: fakeWatcherFactory(holder),
            onResources: resources => resourceBatches.push(resources),
            onAssets: assets => assetBatches.push(assets),
            schedule: scheduler.schedule,
            cancelSchedule: scheduler.cancel,
        });
        assert.equal(await service.ready, true);
        assert.deepEqual(holder.roots, [path.join(root, 'data'), path.join(root, 'assets')]);
        assert.equal(holder.options.ignoreInitial, true);
        assert.equal(holder.options.atomic, true);
        assert.ok(holder.options.awaitWriteFinish);

        holder.watcher.emit('change', path.join(root, 'data', 'system.json'));
        holder.watcher.emit('change', path.join(root, 'data', 'units', 'pixie.json'));
        holder.watcher.emit('change', path.join(root, 'data', 'units', 'another.json'));
        holder.watcher.emit('change', path.join(root, 'assets', 'sprites', 'pixie.png'));
        holder.watcher.emit('change', path.join(root, 'tmp', 'generated.json'));
        scheduler.run();

        assert.deepEqual(resourceBatches, [['system', 'units']]);
        assert.deepEqual(assetBatches, [['sprites/pixie.png']]);
        await service.close();
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('self-write suppression removes duplicate delivery and expires', async () => {
    const root = tempProject();
    const holder = {};
    const scheduler = deterministicScheduler();
    const resourceBatches = [];
    let time = 1000;
    try {
        const service = createProjectWatcher({
            projectRoot: root,
            watchFactory: fakeWatcherFactory(holder),
            onResources: resources => resourceBatches.push(resources),
            schedule: scheduler.schedule,
            cancelSchedule: scheduler.cancel,
            now: () => time,
            selfWriteMs: 500,
        });
        await service.ready;
        holder.watcher.emit('change', path.join(root, 'data', 'system.json'));
        service.suppressResources(['system']);
        scheduler.run();
        assert.deepEqual(resourceBatches, []);

        time += 501;
        holder.watcher.emit('change', path.join(root, 'data', 'system.json'));
        scheduler.run();
        assert.deepEqual(resourceBatches, [['system']]);
        await service.close();
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('watch backend failure is diagnostic rather than fatal', async () => {
    const root = tempProject();
    const errors = [];
    try {
        const service = createProjectWatcher({
            projectRoot: root,
            watchFactory: () => { throw new Error('watch backend unavailable'); },
            onError: error => errors.push(error.message),
        });
        assert.equal(await service.ready, false);
        assert.deepEqual(errors, ['watch backend unavailable']);
        await service.close();
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});
