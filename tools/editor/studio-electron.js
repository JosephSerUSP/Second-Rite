'use strict';

const authoredStorage = require('./authored-storage');

const ALLOWED_SURFACES = Object.freeze(['database']);
const ALLOWED_RESOURCES = Object.freeze(authoredStorage.bulkEditableResources());

function installStudioIpc(options) {
    const ipcMain = options.ipcMain;
    const dialog = options.dialog;
    const windowManager = options.windowManager;
    const onSurfaceReady = typeof options.onSurfaceReady === 'function' ? options.onSurfaceReady : null;
    const allowed = new Set(options.allowedSurfaces || ALLOWED_SURFACES);
    const allowedResources = new Set(options.allowedResources || ALLOWED_RESOURCES);
    const pendingClose = new Map();

    function assertSurface(surfaceId) {
        if (!allowed.has(surfaceId)) throw new Error(`Unknown Studio surface: ${surfaceId}`);
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
    // becomes Project authority; sibling renderers re-read committed truth from
    // /data and decide whether their local working copy is clean enough to adopt
    // it. Do not echo to the sender: it already accepted the exact save result.
    ipcMain.handle('thestra-studio-resource-commit', (event, payload) => {
        const sourceSurface = senderSurfaceId(event);
        const resources = normalizeCommittedResources(payload);
        const deliveredTo = [];
        const targetSurfaceIds = ['main', ...allowed];

        for (const surfaceId of targetSurfaceIds) {
            if (surfaceId === sourceSurface) continue;
            const win = windowManager.get(surfaceId);
            const webContents = win && win.webContents;
            if (!webContents || (typeof webContents.isDestroyed === 'function' && webContents.isDestroyed())) continue;
            webContents.send('thestra-studio-resource-committed', {
                sourceSurface,
                resources,
            });
            deliveredTo.push(surfaceId);
        }

        return { sourceSurface, resources, deliveredTo };
    });

    // #521 safety gate: Project switching is a full-process relaunch today.
    // Do not let the main renderer relaunch out from under a secondary working
    // copy. The user closes each native surface through its own Save/Discard/
    // Cancel contract first, then retries the Project switch.
    ipcMain.handle('thestra-studio-project-switch-ready', event => {
        assertSenderOwnsSurface(event, 'main');
        const blockers = Array.from(allowed).filter(surfaceId => windowManager.has(surfaceId));
        return { ready: blockers.length === 0, blockers };
    });

    ipcMain.handle('thestra-studio-close-choice', async (event, surfaceId) => {
        assertSurface(surfaceId);
        const win = assertSenderOwnsSurface(event, surfaceId);
        const result = await dialog.showMessageBox(win, {
            type: 'warning',
            title: 'Unsaved Database Changes',
            message: 'Save changes before closing Database?',
            detail: 'Database has authored changes that have not been saved.',
            buttons: ['Save', 'Discard', 'Cancel'],
            defaultId: 0,
            cancelId: 2,
            noLink: true,
        });
        return ['save', 'discard', 'cancel'][result.response] || 'cancel';
    });

    ipcMain.on('thestra-studio-close-response', (event, payload) => {
        const surfaceId = payload && payload.surfaceId;
        if (!allowed.has(surfaceId)) return;
        const pending = pendingClose.get(event.sender.id);
        if (!pending || pending.surfaceId !== surfaceId) return;
        pendingClose.delete(event.sender.id);
        if (payload.allow) pending.approve();
    });

    function requestClose(surfaceId, win, approve) {
        assertSurface(surfaceId);
        const webContents = win && win.webContents;
        if (!webContents || (typeof webContents.isDestroyed === 'function' && webContents.isDestroyed())) {
            approve();
            return;
        }

        // A close decision may involve a native prompt and an async authored
        // save. Treat additional Alt+F4/title-bar close requests during that
        // decision as the same intent rather than replacing its approval
        // callback or sending a second renderer request.
        if (pendingClose.has(webContents.id)) return;

        pendingClose.set(webContents.id, { surfaceId, approve });
        webContents.send('thestra-studio-close-request', { surfaceId });
    }

    return Object.freeze({ requestClose });
}

module.exports = {
    ALLOWED_SURFACES,
    ALLOWED_RESOURCES,
    installStudioIpc,
};
