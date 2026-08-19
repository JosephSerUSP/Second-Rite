'use strict';

const path = require('path');
const lifecycle = require('./project-lifecycle');

function installProjectIpc({ ipcMain, dialog, app, studioRoot, currentProjectRoot }) {
    if (!ipcMain || !dialog || !app) throw new Error('Project Electron bridge requires ipcMain, dialog and app');
    const root = path.resolve(studioRoot);

    ipcMain.handle('thestra-project-current', async () => ({
        info: lifecycle.projectInfo(currentProjectRoot),
        sparse: lifecycle.sparseProjectAvailability(),
    }));

    ipcMain.handle('thestra-project-choose-directory', async (_event, options = {}) => {
        const result = await dialog.showOpenDialog({
            title: options.title || 'Choose Project Folder',
            defaultPath: options.defaultPath || undefined,
            properties: ['openDirectory', 'createDirectory'],
        });
        if (result.canceled || !result.filePaths || !result.filePaths[0]) return null;
        return path.resolve(result.filePaths[0]);
    });

    ipcMain.handle('thestra-project-fork', async (_event, payload = {}) => {
        return lifecycle.forkProject({
            source: payload.source || currentProjectRoot,
            target: payload.target,
        });
    });

    ipcMain.handle('thestra-project-create', async (_event, payload = {}) => {
        return lifecycle.createProject({
            mode: payload.mode || 'sparse',
            source: payload.source,
            target: payload.target,
        });
    });

    ipcMain.handle('thestra-project-open', async (_event, target) => {
        const info = lifecycle.projectInfo(target);
        // Full relaunch preserves the invariant that PROJECT_ROOT and all
        // resource/version state are resolved once at process boot. The target
        // is passed as an argument so the next process can set PROJECT_ENV
        // before requiring server.js.
        app.relaunch({
            execPath: process.execPath,
            args: [root, '--project', info.projectRoot],
        });
        setTimeout(() => app.quit(), 25);
        return { success: true, projectRoot: info.projectRoot };
    });
}

module.exports = { installProjectIpc };
