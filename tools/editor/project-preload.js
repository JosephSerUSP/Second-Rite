'use strict';

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('thestraProjects', Object.freeze({
    current: () => ipcRenderer.invoke('thestra-project-current'),
    chooseDirectory: options => ipcRenderer.invoke('thestra-project-choose-directory', options || {}),
    fork: payload => ipcRenderer.invoke('thestra-project-fork', payload || {}),
    create: payload => ipcRenderer.invoke('thestra-project-create', payload || {}),
    open: projectRoot => ipcRenderer.invoke('thestra-project-open', projectRoot),
}));

// Project UI is an Electron capability, not a browser/server root-selection
// protocol. Inject its ordinary renderer script only when this preload exists;
// browser-only Studio/golden hosting sees the exact old menu surface.
window.addEventListener('DOMContentLoaded', () => {
    const script = document.createElement('script');
    script.src = 'js/project-manager.js';
    script.defer = true;
    document.head.appendChild(script);
});
