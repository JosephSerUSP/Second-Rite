'use strict';

const { contextBridge, ipcRenderer } = require('electron');

let stateListener = null;
contextBridge.exposeInMainWorld('thestraBootSplash', Object.freeze({
    getState: () => ipcRenderer.invoke('thestra-boot-splash-get-state'),
    reload: () => ipcRenderer.invoke('thestra-boot-splash-reload'),
    copyError: () => ipcRenderer.invoke('thestra-boot-splash-copy-error'),
    quit: () => ipcRenderer.invoke('thestra-boot-splash-quit'),
    onState: callback => {
        let receivedPush = false;
        if (stateListener) ipcRenderer.removeListener('thestra-boot-splash-state', stateListener);
        stateListener = (_event, payload) => {
            receivedPush = true;
            callback(payload || {});
        };
        ipcRenderer.on('thestra-boot-splash-state', stateListener);
        return ipcRenderer.invoke('thestra-boot-splash-get-state').then(state => {
            if (!receivedPush) callback(state || {});
        });
    },
}));
