'use strict';

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('thestraProjects', Object.freeze({
    current: () => ipcRenderer.invoke('thestra-project-current'),
    chooseDirectory: options => ipcRenderer.invoke('thestra-project-choose-directory', options || {}),
    fork: payload => ipcRenderer.invoke('thestra-project-fork', payload || {}),
    create: payload => ipcRenderer.invoke('thestra-project-create', payload || {}),
    open: projectRoot => ipcRenderer.invoke('thestra-project-open', projectRoot),
}));

let closeRequestListener = null;
let resourceCommitListener = null;
let assetInvalidationListener = null;
contextBridge.exposeInMainWorld('thestraStudio', Object.freeze({
    openSurface: surfaceId => ipcRenderer.invoke('thestra-studio-open-surface', surfaceId),
    closeSurface: surfaceId => ipcRenderer.invoke('thestra-studio-close-surface', surfaceId),
    surfaceReady: surfaceId => ipcRenderer.invoke('thestra-studio-surface-ready', surfaceId),
    projectSwitchReady: () => ipcRenderer.invoke('thestra-studio-project-switch-ready'),
    chooseCloseAction: surfaceId => ipcRenderer.invoke('thestra-studio-close-choice', surfaceId),
    announceResourceCommit: (resources, versions) => ipcRenderer.invoke('thestra-studio-resource-commit', {
        resources: Array.isArray(resources) ? resources.slice() : resources,
        versions: versions && typeof versions === 'object' && !Array.isArray(versions)
            ? Object.assign({}, versions)
            : undefined,
    }),
    onResourceCommit: callback => {
        if (resourceCommitListener) {
            ipcRenderer.removeListener('thestra-studio-resource-committed', resourceCommitListener);
        }
        resourceCommitListener = (_event, payload) => callback(payload || {});
        ipcRenderer.on('thestra-studio-resource-committed', resourceCommitListener);
    },
    onAssetInvalidation: callback => {
        if (assetInvalidationListener) {
            ipcRenderer.removeListener('thestra-studio-assets-invalidated', assetInvalidationListener);
        }
        assetInvalidationListener = (_event, payload) => callback(payload || {});
        ipcRenderer.on('thestra-studio-assets-invalidated', assetInvalidationListener);
    },
    onCloseRequest: callback => {
        if (closeRequestListener) ipcRenderer.removeListener('thestra-studio-close-request', closeRequestListener);
        closeRequestListener = (_event, payload) => callback(payload || {});
        ipcRenderer.on('thestra-studio-close-request', closeRequestListener);
    },
    resolveCloseRequest: (surfaceId, allow) => {
        ipcRenderer.send('thestra-studio-close-response', { surfaceId, allow: !!allow });
    },
}));

// Project/native-surface UI are Electron capabilities, not browser/server
// protocols. Inject their ordinary renderer adapters only when this preload
// exists; browser-only Studio/G6 hosting keeps the existing DOM-modal path.
window.addEventListener('DOMContentLoaded', () => {
    const projectScript = document.createElement('script');
    projectScript.src = 'js/project-manager.js';
    document.head.appendChild(projectScript);

    // Resource synchronization is likewise Electron-only. It layers onto the
    // already-loaded net.js transaction functions and exchanges only invalidation
    // metadata through IPC; committed values still come from the editor server.
    const syncScript = document.createElement('script');
    syncScript.src = 'js/studio-resource-sync.js';
    document.head.appendChild(syncScript);

    const surfaceStyles = document.createElement('link');
    surfaceStyles.id = 'thestra-surface-host-styles';
    surfaceStyles.rel = 'stylesheet';
    surfaceStyles.href = 'surface-host.css';

    // The native adapter is allowed to tell Electron that the surface is ready
    // only after its host stylesheet has positively loaded. Attach the listener
    // before appending the link so a fast cache/disk hit cannot outrun it.
    const injectSurfaceScript = () => {
        const surfaceScript = document.createElement('script');
        surfaceScript.src = 'js/studio-surface-host.js';
        document.head.appendChild(surfaceScript);
    };
    surfaceStyles.addEventListener('load', injectSurfaceScript, { once: true });
    surfaceStyles.addEventListener('error', () => {
        console.error('Thestra Studio surface host stylesheet failed to load');
    }, { once: true });
    document.head.appendChild(surfaceStyles);
});
