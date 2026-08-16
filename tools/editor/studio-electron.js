'use strict';

const authoredStorage = require('./authored-storage');
const {
    SECONDARY_NATIVE_SURFACE_IDS,
    requireSurfacePolicy,
} = require('./studio-surface-registry');

const ALLOWED_SURFACES = SECONDARY_NATIVE_SURFACE_IDS;
// Bulk-editable resources refresh from /data. Record-managed resources have
// dedicated read/write APIs but still need bounded same-session invalidation.
// Keep this list explicit so IPC never turns into an arbitrary resource bus.
const RECORD_MANAGED_RESOURCES = Object.freeze(['tilesets']);
const ALLOWED_RESOURCES = Object.freeze(Array.from(new Set([
    ...authoredStorage.bulkEditableResources(),
    ...RECORD_MANAGED_RESOURCES,
])));

function installStudioIpc(options) {
    const ipcMain = options.ipcMain;
    const dialog = options.dialog;
    const windowManager = options.windowManager;
    const onSurfaceReady = typeof options.onSurfaceReady === 'function' ? options.onSurfaceReady : null;
    const onResourceCommit = typeof options.onResourceCommit === 'function' ? options.onResourceCommit : null;
    const allowed = new Set(options.allowedSurfaces || ALLOWED_SURFACES);
    const closeable = new Set(['main', ...allowed]);
    const allowedResources = new Set(options.allowedResources || ALLOWED_RESOURCES);
    const pendingClose = new Map();

    function assertSurface(surfaceId) {
        if (!allowed.has(surfaceId)) throw new Error(`Unknown Studio surface: ${surfaceId}`);
        return surfaceId;
    }

    function assertCloseableSurface(surfaceId) {
        if (!closeable.has(surfaceId)) throw new Error(`Unknown closeable Studio surface: ${surfaceId}`);
        return surfaceId;
    }

    function assertSenderOwnsSurface(event, surfaceId) {
        const win = windowManager.get(surfaceId);
        if (!win || !win.webContents || win.webContents !== event.sender) {
            throw new Error(`Renderer does not own Studio surface: ${surfaceId}`);
        }
        return win;
    }

    function senderSurfaceId(event) {
        const surfaceIds = ['main', ...allowed];
        for (const surfaceId of surfaceIds) {
            const win = windowManager.get(surfaceId);
            if (win && win.webContents === event.sender) return surfaceId;
        }
        throw new Error('Renderer does not own a Studio surface');
    }

    function normalizeCommittedResources(payload) {
        const requested = payload && payload.resources;
        if (!Array.isArray(requested) || requested.length === 0 || requested.length > allowedResources.size) {
            throw new Error('Committed resource notification requires a bounded resource list');
        }
        const unique = [];
        const seen = new Set();
        for (const name of requested) {
            if (typeof name !== 'string' || !allowedResources.has(name)) {
                throw new Error(`Unknown authored resource: ${String(name)}`);
            }
            if (!seen.has(name)) {
                seen.add(name);
                unique.push(name);
            }
        }
        return unique;
    }

    function normalizeCommittedVersions(payload, resources) {
        const requested = payload && payload.versions;
        if (requested === undefined || requested === null) return {};
        if (typeof requested !== 'object' || Array.isArray(requested)) {
            throw new Error('Committed resource versions must be a resource-to-version object');
        }
        const committed = new Set(resources);
        const versions = {};
        for (const [name, version] of Object.entries(requested)) {
            if (!committed.has(name)) {
                throw new Error(`Committed version supplied for uncommitted resource: ${name}`);
            }
            if (typeof version !== 'string' || !version) {
                throw new Error(`Committed version for '${name}' must be a non-empty string`);
            }
            versions[name] = version;
        }
        return versions;
    }

    function liveWebContents(surfaceId) {
        const win = windowManager.get(surfaceId);
        const webContents = win && win.webContents;
        if (!webContents || (typeof webContents.isDestroyed === 'function' && webContents.isDestroyed())) return null;
        return webContents;
    }

    function broadcastResourceCommit(sourceSurface, requestedResources) {
        const resources = normalizeCommittedResources({ resources: requestedResources });
        const deliveredTo = [];
        const targetSurfaceIds = ['main', ...allowed];
        for (const surfaceId of targetSurfaceIds) {
            if (surfaceId === sourceSurface) continue;
            const webContents = liveWebContents(surfaceId);
            if (!webContents) continue;
            webContents.send('thestra-studio-resource-committed', { sourceSurface, resources });
            deliveredTo.push(surfaceId);
        }
        return { sourceSurface, resources, deliveredTo };
    }

    function broadcastAssetInvalidation(assetPaths) {
        const assets = Array.from(new Set((assetPaths || [])
            .filter(assetPath => typeof assetPath === 'string' && assetPath.length > 0)))
            .sort();
        if (assets.length === 0) return { assets: [], deliveredTo: [] };
        const deliveredTo = [];
        for (const surfaceId of ['main', ...allowed]) {
            const webContents = liveWebContents(surfaceId);
            if (!webContents) continue;
            webContents.send('thestra-studio-assets-invalidated', { sourceSurface: 'external', assets });
            deliveredTo.push(surfaceId);
        }
        return { assets, deliveredTo };
    }

    ipcMain.handle('thestra-studio-open-surface', (_event, surfaceId) => {
        assertSurface(surfaceId);
        windowManager.open(surfaceId);
        return { surfaceId };
    });

    ipcMain.handle('thestra-studio-close-surface', (_event, surfaceId) => {
        assertSurface(surfaceId);
        return { surfaceId, requested: windowManager.close(surfaceId) };
    });

    ipcMain.handle('thestra-studio-surface-ready', (event, surfaceId) => {
        assertSurface(surfaceId);
        const win = assertSenderOwnsSurface(event, surfaceId);
        if (typeof win.show === 'function') win.show();
        if (typeof win.focus === 'function') win.focus();
        if (onSurfaceReady) onSurfaceReady(surfaceId, win);
        return { surfaceId, shown: true };
    });

    // A renderer announces only WHICH authored resources the existing server
    // successfully committed. Electron never carries resource values and never
    // becomes Project authority. Exact committed version tokens may accompany
    // that identity only so the filesystem watcher can prove a later event is
    // the echo of this transaction rather than a real external edit. Sibling
    // renderers still receive resource identity only and re-read authority.
    ipcMain.handle('thestra-studio-resource-commit', (event, payload) => {
        const sourceSurface = senderSurfaceId(event);
        const resources = normalizeCommittedResources(payload);
        const versions = normalizeCommittedVersions(payload, resources);
        if (onResourceCommit) onResourceCommit(resources, sourceSurface, versions);
        return broadcastResourceCommit(sourceSurface, resources);
    });

    ipcMain.handle('thestra-studio-project-switch-ready', event => {
        assertSenderOwnsSurface(event, 'main');
        const blockers = Array.from(allowed).filter(surfaceId => windowManager.has(surfaceId));
        return { ready: blockers.length === 0, blockers };
    });

    ipcMain.handle('thestra-studio-close-choice', async (event, surfaceId) => {
        assertCloseableSurface(surfaceId);
        const win = assertSenderOwnsSurface(event, surfaceId);
        const isMain = surfaceId === 'main';
        const displayName = isMain ? 'Thestra Studio' : requireSurfacePolicy(surfaceId).displayName;
        const result = await dialog.showMessageBox(win, {
            type: 'warning',
            title: isMain ? 'Unsaved Project Changes' : `Unsaved ${displayName} Changes`,
            message: isMain
                ? 'Save Project changes before closing Thestra Studio?'
                : `Save changes before closing ${displayName}?`,
            detail: isMain
                ? 'The main Studio workspace has authored changes that have not been saved.'
                : `${displayName} has authored changes that have not been saved.`,
            buttons: ['Save', 'Discard', 'Cancel'],
            defaultId: 0,
            cancelId: 2,
            noLink: true,
        });
        return ['save', 'discard', 'cancel'][result.response] || 'cancel';
    });

    ipcMain.on('thestra-studio-close-response', (event, payload) => {
        const surfaceId = payload && payload.surfaceId;
        if (!closeable.has(surfaceId)) return;
        const pending = pendingClose.get(event.sender.id);
        if (!pending || pending.surfaceId !== surfaceId) return;
        pendingClose.delete(event.sender.id);
        pending.decide(!!payload.allow);
    });

    function requestClose(surfaceId, win, decide) {
        assertCloseableSurface(surfaceId);
        const webContents = win && win.webContents;
        if (!webContents || (typeof webContents.isDestroyed === 'function' && webContents.isDestroyed())) {
            decide(true);
            return;
        }
        if (pendingClose.has(webContents.id)) return;
        pendingClose.set(webContents.id, { surfaceId, decide });
        webContents.send('thestra-studio-close-request', { surfaceId });
    }

    return Object.freeze({
        broadcastAssetInvalidation,
        broadcastResourceCommit,
        requestClose,
    });
}

module.exports = {
    ALLOWED_SURFACES,
    ALLOWED_RESOURCES,
    RECORD_MANAGED_RESOURCES,
    installStudioIpc,
};
