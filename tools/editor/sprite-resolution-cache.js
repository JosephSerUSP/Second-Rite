'use strict';

const fs = require('fs');
const path = require('path');

const LOOKUP_DIRS = [
    'assets/smallBattlers',
    'assets/sprites',
    'assets/system',
];

function statToken(fsImpl, filePath) {
    try {
        const stat = fsImpl.statSync(filePath);
        return [
            stat.size,
            Number(stat.mtimeMs || 0),
            Number(stat.ctimeMs || 0),
            stat.ino || 0,
        ].join(':');
    } catch (e) {
        return 'missing';
    }
}

function directoryInventoryToken(fsImpl, projectRoot) {
    return LOOKUP_DIRS.map(relativeDir => {
        const absoluteDir = path.join(projectRoot, ...relativeDir.split('/'));
        let names = [];
        try {
            names = fsImpl.readdirSync(absoluteDir)
                .filter(name => /\.png$/i.test(name))
                .sort((a, b) => a.localeCompare(b));
        } catch (e) {
            names = [];
        }
        // The runtime's fallback index is filename-driven and directory order is
        // meaningful. Listing the names here does not reimplement that resolver;
        // it only gives cached runtime answers a cheap invalidation generation.
        return relativeDir + ':' + names.join('\0');
    }).join('\n');
}

function requestKey(spec) {
    if (spec && Object.prototype.hasOwnProperty.call(spec, 'key')) {
        return 'key:' + String(spec.key);
    }
    if (spec && Object.prototype.hasOwnProperty.call(spec, 'path')) {
        return 'path:' + String(spec.path).replace(/\\/g, '/');
    }
    throw new Error('sprite metadata cache requires key or path');
}

class SpriteResolutionCache {
    constructor(options) {
        options = options || {};
        this.projectRoot = options.projectRoot;
        if (!this.projectRoot) throw new Error('projectRoot is required');
        this.fs = options.fs || fs;
        this.entries = new Map();
        this.inFlight = new Map();
        this.runtimeAuthorityPath = options.runtimeAuthorityPath
            || path.join(path.resolve(__dirname, '../..'), 'presentation', 'sprite_sheet.lua');
    }

    inventoryGeneration() {
        return directoryInventoryToken(this.fs, this.projectRoot)
            + '\nruntime:' + statToken(this.fs, this.runtimeAuthorityPath);
    }

    resolvedFileToken(payload) {
        if (!payload || !payload.path) return null;
        const normalized = String(payload.path).replace(/\\/g, '/');
        let absolute;
        try {
            absolute = path.resolve(this.projectRoot, ...normalized.split('/'));
            const relative = path.relative(this.projectRoot, absolute);
            if (relative.startsWith('..') || path.isAbsolute(relative)) return 'outside-project';
        } catch (e) {
            return 'invalid-path';
        }
        return statToken(this.fs, absolute);
    }

    generationFor(payload) {
        return {
            inventory: this.inventoryGeneration(),
            resolvedFile: this.resolvedFileToken(payload),
        };
    }

    generationMatches(entry, current) {
        return !!entry
            && entry.generation.inventory === current.inventory
            && entry.generation.resolvedFile === current.resolvedFile;
    }

    async resolve(spec, runtimeResolver) {
        if (typeof runtimeResolver !== 'function') {
            throw new Error('runtimeResolver must be a function');
        }
        const key = requestKey(spec);
        const cached = this.entries.get(key);
        if (cached) {
            const current = this.generationFor(cached.payload);
            if (this.generationMatches(cached, current)) return cached.payload;
            this.entries.delete(key);
        }

        const inventoryAtStart = this.inventoryGeneration();
        const pending = this.inFlight.get(key);
        if (pending && pending.inventory === inventoryAtStart) return pending.promise;

        let promise;
        promise = Promise.resolve()
            .then(() => runtimeResolver(spec))
            .then(payload => {
                // Runtime/transport errors must stay retryable. A normal
                // unresolved description (`resolved: false`) is cacheable.
                if (!payload || payload.error) return payload;
                const generation = this.generationFor(payload);
                // If the lookup inventory changed during the LÖVE call, this
                // answer is valid for the current caller but must not become a
                // reusable answer for the next selection.
                if (generation.inventory === inventoryAtStart) {
                    this.entries.set(key, { payload, generation });
                }
                return payload;
            })
            .finally(() => {
                const current = this.inFlight.get(key);
                if (current && current.promise === promise) this.inFlight.delete(key);
            });

        this.inFlight.set(key, { inventory: inventoryAtStart, promise });
        return promise;
    }

    clear() {
        this.entries.clear();
        this.inFlight.clear();
    }
}

module.exports = {
    LOOKUP_DIRS,
    SpriteResolutionCache,
    directoryInventoryToken,
    requestKey,
};
