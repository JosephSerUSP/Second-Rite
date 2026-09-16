'use strict';

const path = require('path');

function isFiniteNumber(val) {
    return typeof val === 'number' && Number.isFinite(val);
}

function isUsableBounds(bounds) {
    if (!bounds || typeof bounds !== 'object') return false;
    if (!isFiniteNumber(bounds.width) || bounds.width < 200) return false;
    if (!isFiniteNumber(bounds.height) || bounds.height < 100) return false;
    if (isFiniteNumber(bounds.x) && bounds.x <= -10000) return false;
    if (isFiniteNumber(bounds.y) && bounds.y <= -10000) return false;
    return true;
}

function boundsIntersectDisplay(bounds, display) {
    const area = display.workArea || display.bounds;
    if (!area) return false;
    const minOverlapX = Math.min(100, bounds.width);
    const minOverlapY = Math.min(50, bounds.height);
    const overlapX = Math.max(0, Math.min(bounds.x + bounds.width, area.x + area.width) - Math.max(bounds.x, area.x));
    const overlapY = Math.max(0, Math.min(bounds.y + bounds.height, area.y + area.height) - Math.max(bounds.y, area.y));
    return overlapX >= minOverlapX && overlapY >= minOverlapY;
}

function sanitizeWindowState(state, defaults = {}, displays = null) {
    const fallback = { ...(defaults || {}) };
    const raw = (state && typeof state === 'object' && !Array.isArray(state)) ? state : {};

    let width = isFiniteNumber(raw.width) && raw.width >= 200 ? Math.round(raw.width) : fallback.width;
    let height = isFiniteNumber(raw.height) && raw.height >= 100 ? Math.round(raw.height) : fallback.height;
    if (!isFiniteNumber(width) || width < 200) width = 1440;
    if (!isFiniteNumber(height) || height < 100) height = 900;

    let x = isFiniteNumber(raw.x) ? Math.round(raw.x) : undefined;
    let y = isFiniteNumber(raw.y) ? Math.round(raw.y) : undefined;

    // Check for Win32 minimized dummy coordinates (-32000) or corrupt offscreen coordinates
    if (x !== undefined && (x <= -10000 || y <= -10000)) {
        x = undefined;
        y = undefined;
    }

    // If coordinates exist and display topology is known, ensure window intersects at least one display
    if (x !== undefined && y !== undefined && Array.isArray(displays) && displays.length > 0) {
        const candidate = { x, y, width, height };
        const visible = displays.some(display => boundsIntersectDisplay(candidate, display));
        if (!visible) {
            x = undefined;
            y = undefined;
        }
    }

    const result = {
        width,
        height,
        isMaximized: Boolean(raw.isMaximized),
    };
    if (x !== undefined && y !== undefined) {
        result.x = x;
        result.y = y;
    }
    return result;
}

function snapshotWindowState(win, previousState = {}) {
    if (!win) return { ...(previousState || {}) };

    const isMinimized = typeof win.isMinimized === 'function' && win.isMinimized();
    const isMaximized = typeof win.isMaximized === 'function' && win.isMaximized();

    let bounds = null;
    if ((isMinimized || isMaximized) && typeof win.getNormalBounds === 'function') {
        try {
            const normal = win.getNormalBounds();
            if (isUsableBounds(normal)) {
                bounds = normal;
            }
        } catch (_) {
            bounds = null;
        }
    }

    if (!bounds && typeof win.getBounds === 'function') {
        try {
            bounds = win.getBounds();
        } catch (_) {
            bounds = null;
        }
    }

    if (isMinimized || !isUsableBounds(bounds)) {
        if (isUsableBounds(bounds)) {
            const res = {
                width: bounds.width,
                height: bounds.height,
                isMaximized: isMaximized || (previousState && Boolean(previousState.isMaximized)),
            };
            if (isFiniteNumber(bounds.x) && isFiniteNumber(bounds.y)) {
                res.x = bounds.x;
                res.y = bounds.y;
            }
            return res;
        }

        const fallback = { ...(previousState || {}) };
        const res = {
            width: isFiniteNumber(fallback.width) && fallback.width >= 200 ? fallback.width : 1440,
            height: isFiniteNumber(fallback.height) && fallback.height >= 100 ? fallback.height : 900,
            isMaximized: isMaximized || Boolean(fallback.isMaximized),
        };
        if (isFiniteNumber(fallback.x) && isFiniteNumber(fallback.y) && fallback.x > -10000 && fallback.y > -10000) {
            res.x = fallback.x;
            res.y = fallback.y;
        }
        return res;
    }

    const res = {
        width: bounds.width,
        height: bounds.height,
        isMaximized,
    };
    if (isFiniteNumber(bounds.x) && isFiniteNumber(bounds.y)) {
        res.x = bounds.x;
        res.y = bounds.y;
    }
    return res;
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
                return sanitizeWindowState(parsed, fallback);
            } catch (error) {
                logger.error(`Failed to load window state for ${surfaceId}:`, error);
                return fallback;
            }
        },

        save(surfaceId, state) {
            const file = statePath(surfaceId);
            try {
                const cleanState = sanitizeWindowState(state);
                fs.writeFileSync(file, JSON.stringify(cleanState, null, 2));
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
        this.getDisplays = typeof options.getDisplays === 'function' ? options.getDisplays : null;
        this.definitions = new Map();
        this.windows = new Map();
        this.surfaceStates = new Map();
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

        const rawState = this.stateStore.load(surfaceId, definition.defaultState || {});
        const displays = typeof this.getDisplays === 'function' ? this.getDisplays() : null;
        const state = sanitizeWindowState(rawState, definition.defaultState || {}, displays);
        this.surfaceStates.set(surfaceId, { ...state });

        const win = this.createWindow(definition.buildOptions(state));
        this.windows.set(surfaceId, win);
        let approvedClose = false;

        if (state.isMaximized && typeof win.maximize === 'function') win.maximize();

        if (definition.autoShow !== false && typeof win.once === 'function') {
            // Electron normally emits ready-to-show, but a renderer that is
            // slow to paint (or is recovering after a forced process close)
            // can leave the BrowserWindow alive and permanently hidden. A
            // completed document load is sufficient for the ordinary Studio
            // surface and gives the user a recoverable window instead of a
            // "live but dead" process. The guard keeps the two events from
            // revealing/focusing the same surface twice.
            let revealed = false;
            const reveal = () => {
                if (revealed) return;
                revealed = true;
                if (typeof win.show === 'function') win.show();
            };
            win.once('ready-to-show', reveal);
            win.once('did-finish-load', reveal);
        }

        if (typeof win.on === 'function') {
            const updateTrackedBounds = () => {
                if (typeof win.isMinimized === 'function' && win.isMinimized()) return;
                const prev = this.surfaceStates.get(surfaceId) || definition.defaultState || {};
                const snap = snapshotWindowState(win, prev);
                if (isUsableBounds(snap)) {
                    this.surfaceStates.set(surfaceId, snap);
                }
            };
            win.on('resize', updateTrackedBounds);
            win.on('move', updateTrackedBounds);

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
                const prev = this.surfaceStates.get(surfaceId) || definition.defaultState || {};
                const nextState = snapshotWindowState(win, prev);
                this.surfaceStates.set(surfaceId, nextState);
                this.stateStore.save(surfaceId, nextState);
            });
            win.on('closed', () => {
                if (this.windows.get(surfaceId) === win) this.windows.delete(surfaceId);
                this.surfaceStates.delete(surfaceId);
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
    sanitizeWindowState,
    isUsableBounds,
};
