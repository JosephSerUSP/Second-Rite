'use strict';

const path = require('path');
const { getSurfacePolicy } = require('./studio-surface-registry');

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
        this.closeWaiters = new Map();
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

    settleCloseWaiters(surfaceId, allowed) {
        const waiters = this.closeWaiters.get(surfaceId);
        if (!waiters || waiters.length === 0) return;
        this.closeWaiters.delete(surfaceId);
        for (const resolve of waiters) resolve(!!allowed);
    }

    buildNativeOptions(surfaceId, definition, state) {
        const options = { ...definition.buildOptions(state) };
        const policy = getSurfacePolicy(surfaceId);

        // #809: hosting and interaction ownership are separate policy axes.
        // An exclusive EditorSurface remains its own BrowserWindow/renderer,
        // but Electron owns the blocking relationship so the main Map workspace
        // cannot continue mutating behind a project-level editor. Browser/G6
        // hosts already express this policy through their DOM modal adapters.
        if (policy && policy.interactionPolicy === 'exclusive') {
            const mainWindow = this.get('main');
            if (mainWindow && !(typeof mainWindow.isDestroyed === 'function' && mainWindow.isDestroyed())) {
                options.parent = mainWindow;
                options.modal = true;
            }
        }

        return options;
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
            // autoShow:false surfaces are intentionally hidden until their
            // renderer says its host composition is ready. A repeated Open
            // during that bootstrap must not reveal the generic page early.
            const mayReveal = definition.autoShow !== false
                || (typeof existing.isVisible === 'function' && existing.isVisible());
            if (mayReveal && typeof existing.show === 'function') existing.show();
            if (mayReveal && typeof existing.focus === 'function') existing.focus();
            return existing;
        }

        const state = this.stateStore.load(surfaceId, definition.defaultState || {});
        const win = this.createWindow(this.buildNativeOptions(surfaceId, definition, state));
        this.windows.set(surfaceId, win);
        let approvedClose = false;

        if (state.isMaximized && typeof win.maximize === 'function') win.maximize();

        if (definition.autoShow !== false && typeof win.once === 'function') {
            win.once('ready-to-show', () => {
                if (typeof win.show === 'function') win.show();
            });
        }

        if (typeof win.on === 'function') {
            win.on('close', event => {
                if (typeof definition.requestClose === 'function' && !approvedClose) {
                    if (event && typeof event.preventDefault === 'function') event.preventDefault();
                    definition.requestClose(win, allow => {
                        if (!allow) {
                            this.settleCloseWaiters(surfaceId, false);
                            return;
                        }
                        if (typeof win.isDestroyed === 'function' && win.isDestroyed()) {
                            this.settleCloseWaiters(surfaceId, true);
                            return;
                        }
                        approvedClose = true;
                        if (typeof win.close === 'function') win.close();
                    });
                    return;
                }

                // Consume the approval: if another listener prevents this close,
                // a later native close request must ask the surface again.
                approvedClose = false;
                this.stateStore.save(surfaceId, snapshotWindowState(win));
            });
            win.on('closed', () => {
                if (this.windows.get(surfaceId) === win) this.windows.delete(surfaceId);
                this.settleCloseWaiters(surfaceId, true);
            });
        }

        if (typeof definition.configure === 'function') {
            definition.configure(win, state);
        }

        return win;
    }

    close(surfaceId) {
        const win = this.get(surfaceId);
        if (!win || (typeof win.isDestroyed === 'function' && win.isDestroyed())) return false;
        if (typeof win.close === 'function') win.close();
        return true;
    }

    closeAndWait(surfaceId) {
        const win = this.get(surfaceId);
        if (!win || (typeof win.isDestroyed === 'function' && win.isDestroyed())) {
            return Promise.resolve(true);
        }
        return new Promise(resolve => {
            const waiters = this.closeWaiters.get(surfaceId) || [];
            waiters.push(resolve);
            this.closeWaiters.set(surfaceId, waiters);
            this.close(surfaceId);
        });
    }

    closeAll() {
        for (const [surfaceId] of this.windows) this.close(surfaceId);
    }
}

module.exports = {
    StudioWindowManager,
    createJsonWindowStateStore,
    snapshotWindowState,
};
