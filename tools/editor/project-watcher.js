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
    const selfWrites = new Map();
    let flushTimer = null;
    let closed = false;

    function pruneSelfWrites() {
        const time = now();
        for (const [resource, expiresAt] of selfWrites.entries()) {
            if (expiresAt <= time) selfWrites.delete(resource);
        }
    }

    function suppressResources(resources) {
        const expiresAt = now() + selfWriteMs;
        for (const resource of resources || []) {
            if (typeof resource === 'string' && resource) selfWrites.set(resource, expiresAt);
        }
    }

    function flush() {
        flushTimer = null;
        if (closed) return;
        pruneSelfWrites();

        const resources = Array.from(pendingResources)
            .filter(resource => !selfWrites.has(resource))
            .sort();
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
        watcher.on('error', onError);
    } catch (error) {
        onError(error);
        watcher = null;
    }

    async function close() {
        if (closed) return;
        closed = true;
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
        suppressResources,
        watchRoots: Object.freeze(watchRoots.slice()),
    });
}

module.exports = {
    DEFAULT_SELF_WRITE_MS,
    DEFAULT_SETTLE_MS,
    createProjectWatcher,
};
