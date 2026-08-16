'use strict';

const path = require('path');
const chokidar = require('chokidar');
const { classifyProjectPath } = require('./project-resource-invalidation');

const DEFAULT_SETTLE_MS = 120;
const DEFAULT_SELF_WRITE_MS = 1500;

function createProjectWatcher(options = {}) {
    const projectRoot = path.resolve(options.projectRoot || '');
    if (!options.projectRoot) throw new Error('Project watcher requires projectRoot');
    const watchFactory = options.watchFactory || chokidar.watch;
    const classify = options.classify || classifyProjectPath;
    const onResources = typeof options.onResources === 'function' ? options.onResources : () => {};
    const onAssets = typeof options.onAssets === 'function' ? options.onAssets : () => {};
    const onError = typeof options.onError === 'function' ? options.onError : error => {
        console.error('Thestra Project watcher error:', error && error.message ? error.message : error);
    };
    const settleMs = options.settleMs === undefined ? DEFAULT_SETTLE_MS : options.settleMs;
    const selfWriteMs = options.selfWriteMs === undefined ? DEFAULT_SELF_WRITE_MS : options.selfWriteMs;
    const now = options.now || Date.now;
    const schedule = options.schedule || setTimeout;
    const cancelSchedule = options.cancelSchedule || clearTimeout;

    const pendingResources = new Set();
    const pendingAssets = new Set();
    // Resource -> { expiresAt, count }. A successful Studio save earns one
    // suppression token for the watcher echo caused by that same disk write.
    // It is deliberately NOT a blanket time window: a distinct external write
    // shortly afterwards must still be observable.
    const selfWrites = new Map();
    let flushTimer = null;
    let closed = false;
    let readySettled = false;
    let resolveReady;
    const ready = new Promise(resolve => { resolveReady = resolve; });

    function settleReady(value) {
        if (readySettled) return;
        readySettled = true;
        resolveReady(value);
    }

    function pruneSelfWrites() {
        const time = now();
        for (const [resource, entry] of selfWrites.entries()) {
            if (!entry || entry.expiresAt <= time || entry.count <= 0) selfWrites.delete(resource);
        }
    }

    function suppressResources(resources) {
        const expiresAt = now() + selfWriteMs;
        for (const resource of resources || []) {
            if (typeof resource !== 'string' || !resource) continue;
            const current = selfWrites.get(resource);
            selfWrites.set(resource, {
                expiresAt,
                count: (current && current.expiresAt > now() ? current.count : 0) + 1,
            });
        }
    }

    function consumeSuppression(resource) {
        const entry = selfWrites.get(resource);
        if (!entry || entry.expiresAt <= now() || entry.count <= 0) {
            selfWrites.delete(resource);
            return false;
        }
        entry.count -= 1;
        if (entry.count <= 0) selfWrites.delete(resource);
        else selfWrites.set(resource, entry);
        return true;
    }

    function flush() {
        flushTimer = null;
        if (closed) return;
        pruneSelfWrites();

        const resources = Array.from(pendingResources)
            .sort()
            .filter(resource => !consumeSuppression(resource));
        const assets = Array.from(pendingAssets).sort();
        pendingResources.clear();
        pendingAssets.clear();

        if (resources.length) onResources(resources);
        if (assets.length) onAssets(assets);
    }

    function queueFlush() {
        if (flushTimer !== null) cancelSchedule(flushTimer);
        flushTimer = schedule(flush, settleMs);
    }

    function observe(filePath) {
        if (closed) return;
        let invalidation;
        try {
            invalidation = classify(projectRoot, filePath);
        } catch (error) {
            onError(error);
            return;
        }
        if (!invalidation) return;
        if (invalidation.kind === 'resource') pendingResources.add(invalidation.resource);
        else if (invalidation.kind === 'asset') pendingAssets.add(invalidation.assetPath);
        else return;
        queueFlush();
    }

    // Only data/ and assets/ can produce semantic invalidations. Watching the
    // entire Project would waste handles on tmp/dist/.git/generated build trees
    // and make unrelated repository cleanup look like authoring activity.
    const watchRoots = [path.join(projectRoot, 'data'), path.join(projectRoot, 'assets')];
    let watcher;
    try {
        watcher = watchFactory(watchRoots, {
            ignoreInitial: true,
            atomic: true,
            awaitWriteFinish: {
                stabilityThreshold: settleMs,
                pollInterval: Math.max(20, Math.min(50, settleMs || 50)),
            },
        });
        watcher.on('add', observe);
        watcher.on('change', observe);
        watcher.on('unlink', observe);
        watcher.on('error', error => {
            onError(error);
            settleReady(false);
        });
        if (typeof watcher.once === 'function') watcher.once('ready', () => settleReady(true));
        else settleReady(true);
    } catch (error) {
        onError(error);
        watcher = null;
        settleReady(false);
    }

    async function close() {
        if (closed) return;
        closed = true;
        settleReady(false);
        if (flushTimer !== null) {
            cancelSchedule(flushTimer);
            flushTimer = null;
        }
        pendingResources.clear();
        pendingAssets.clear();
        selfWrites.clear();
        if (watcher && typeof watcher.close === 'function') await watcher.close();
    }

    return Object.freeze({
        close,
        flush,
        observe,
        ready,
        suppressResources,
        watchRoots: Object.freeze(watchRoots.slice()),
    });
}

module.exports = {
    DEFAULT_SELF_WRITE_MS,
    DEFAULT_SETTLE_MS,
    createProjectWatcher,
};
