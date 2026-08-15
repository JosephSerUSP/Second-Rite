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
contextBridge.exposeInMainWorld('thestraStudio', Object.freeze({
    openSurface: surfaceId => ipcRenderer.invoke('thestra-studio-open-surface', surfaceId),
    closeSurface: surfaceId => ipcRenderer.invoke('thestra-studio-close-surface', surfaceId),
    surfaceReady: surfaceId => ipcRenderer.invoke('thestra-studio-surface-ready', surfaceId),
    projectSwitchReady: () => ipcRenderer.invoke('thestra-studio-project-switch-ready'),
    chooseCloseAction: surfaceId => ipcRenderer.invoke('thestra-studio-close-choice', surfaceId),
    announceResourceCommit: resources => ipcRenderer.invoke('thestra-studio-resource-commit', {
        resources: Array.isArray(resources) ? resources.slice() : resources,
    }),
    onResourceCommit: callback => {
        if (resourceCommitListener) {
            ipcRenderer.removeListener('thestra-studio-resource-committed', resourceCommitListener);
        }
        resourceCommitListener = (_event, payload) => callback(payload || {});
        ipcRenderer.on('thestra-studio-resource-committed', resourceCommitListener);
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
