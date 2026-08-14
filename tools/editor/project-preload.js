'use strict';

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('thestraProjects', Object.freeze({
    current: () => ipcRenderer.invoke('thestra-project-current'),
    chooseDirectory: options => ipcRenderer.invoke('thestra-project-choose-directory', options || {}),
    fork: payload => ipcRenderer.invoke('thestra-project-fork', payload || {}),
    create: payload => ipcRenderer.invoke('thestra-project-create', payload || {}),
    open: projectRoot => ipcRenderer.invoke('thestra-project-open', projectRoot),
}));
