'use strict';

const path = require('path');

function snapshotWindowState(win) {
    const bounds = win.getBounds();
    return {
        x: bounds.x,
        y: bounds.y,
        width: bounds.width,
        height: bounds.height,
        isMaximized: win.isMaximized(),
    };
}

function createJsonWindowStateStore(options) {
    const fs = options.fs;
    const userDataDir = options.userDataDir;
    const logger = options.logger || console;

    function statePath(surfaceId) {
        if (surfaceId === 'main') return path.join(userDataDir, 'window-state.json');
        const safeId = String(surfaceId).replace(/[^a-zA-Z0-9._-]/g, '_');
        return path.join(userDataDir, `window-state-${safeId}.json`);
    }

    return {
        load(surfaceId, defaults) {
            const fallback = { ...(defaults || {}) };
            const file = statePath(surfaceId);
            try {
                if (!fs.existsSync(file)) return fallback;
                const parsed = JSON.parse(fs.readFileSync(file, 'utf8'));
                if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return fallback;
                return { ...fallback, ...parsed };
            } catch (error) {
                logger.error(`Failed to load window state for ${surfaceId}:`, error);
                return fallback;
            }
        },

        save(surfaceId, state) {
            const file = statePath(surfaceId);
            try {
                fs.writeFileSync(file, JSON.stringify(state, null, 2));
            } catch (error) {
                logger.error(`Failed to save window state for ${surfaceId}:`, error);
            }
        },

        pathFor(surfaceId) {
            return statePath(surfaceId);
        },
    };
}

class StudioWindowManager {
    constructor(options) {
        if (!options || typeof options.createWindow !== 'function') {
            throw new Error('StudioWindowManager requires createWindow(options)');
        }
        if (!options.stateStore || typeof options.stateStore.load !== 'function'
                || typeof options.stateStore.save !== 'function') {
            throw new Error('StudioWindowManager requires a stateStore with load/save');
        }

        this.createWindow = options.createWindow;
        this.stateStore = options.stateStore;
        this.definitions = new Map();
        this.windows = new Map();
    }

    register(surfaceId, definition) {
        if (!surfaceId) throw new Error('surfaceId is required');
        if (!definition || typeof definition.buildOptions !== 'function') {
            throw new Error(`Surface ${surfaceId} requires buildOptions(state)`);
        }
        if (this.definitions.has(surfaceId)) {
            throw new Error(`Surface already registered: ${surfaceId}`);
        }
        this.definitions.set(surfaceId, definition);
    }

    get(surfaceId) {
        return this.windows.get(surfaceId) || null;
    }

    has(surfaceId) {
        const win = this.get(surfaceId);
        return !!win && !(typeof win.isDestroyed === 'function' && win.isDestroyed());
    }

    open(surfaceId) {
        const definition = this.definitions.get(surfaceId);
        if (!definition) throw new Error(`Unknown Studio surface: ${surfaceId}`);

        const existing = this.get(surfaceId);
        if (existing && !(typeof existing.isDestroyed === 'function' && existing.isDestroyed())) {
            if (typeof existing.isMinimized === 'function' && existing.isMinimized()
                    && typeof existing.restore === 'function') {
                existing.restore();
            }
            if (typeof existing.show === 'function') existing.show();
            if (typeof existing.focus === 'function') existing.focus();
            return existing;
        }

        const state = this.stateStore.load(surfaceId, definition.defaultState || {});
        const win = this.createWindow(definition.buildOptions(state));
        this.windows.set(surfaceId, win);

        if (state.isMaximized && typeof win.maximize === 'function') win.maximize();

        if (typeof win.once === 'function') {
            win.once('ready-to-show', () => {
                if (typeof win.show === 'function') win.show();
            });
        }

        if (typeof win.on === 'function') {
            win.on('close', () => {
                this.stateStore.save(surfaceId, snapshotWindowState(win));
            });
            win.on('closed', () => {
                if (this.windows.get(surfaceId) === win) this.windows.delete(surfaceId);
            });
        }

        if (typeof definition.configure === 'function') {
            definition.configure(win, state);
        }

        return win;
    }

    closeAll() {
        for (const win of this.windows.values()) {
            if (typeof win.isDestroyed === 'function' && win.isDestroyed()) continue;
            if (typeof win.close === 'function') win.close();
        }
    }
}

module.exports = {
    StudioWindowManager,
    createJsonWindowStateStore,
    snapshotWindowState,
};
