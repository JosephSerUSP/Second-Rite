'use strict';

function cleanText(value, fallback, limit = 2000) {
    const text = String(value == null ? '' : value).trim();
    return (text || fallback).slice(0, limit);
}

function isLive(window) {
    return !!window && !(typeof window.isDestroyed === 'function' && window.isDestroyed());
}

function createStudioBootSplash(options) {
    const { app, BrowserWindow, clipboard, ipcMain } = options;
    let splashWindow = null;
    let mainWindow = null;
    let ready = false;
    let state = {
        state: 'loading',
        studioName: options.productName || 'Studio',
        projectName: 'Selecting Project…',
        status: 'Opening Studio…',
        error: '',
    };

    function assertMainSender(event) {
        if (!mainWindow || !mainWindow.webContents || event.sender !== mainWindow.webContents) {
            throw new Error('Studio boot message came from a renderer that does not own the main window');
        }
    }

    function assertSplashSender(event) {
        if (!splashWindow || !splashWindow.webContents || event.sender !== splashWindow.webContents) {
            throw new Error('Studio splash action came from a renderer that does not own the splash window');
        }
    }

    function publishState() {
        if (isLive(splashWindow) && splashWindow.webContents) {
            splashWindow.webContents.send('thestra-boot-splash-state', { ...state });
        }
    }

    function setError(message) {
        if (ready) return;
        state = {
            ...state,
            state: 'error',
            status: 'Studio could not finish starting.',
            error: cleanText(message, 'Studio could not finish starting.', 12000),
        };
        publishState();
    }

    ipcMain.handle('thestra-boot-splash-get-state', event => {
        assertSplashSender(event);
        return { ...state };
    });
    ipcMain.handle('thestra-boot-splash-progress', (event, payload) => {
        assertMainSender(event);
        if (ready) return { state: 'ready' };
        const update = payload && typeof payload === 'object' ? payload : {};
        state = {
            state: 'loading',
            studioName: cleanText(update.studioName, options.productName || 'Studio', 120),
            projectName: cleanText(update.projectName, 'Project name unavailable', 240),
            status: cleanText(update.status, 'Preparing Studio…', 500),
            error: '',
        };
        publishState();
        return { state: state.state };
    });
    ipcMain.handle('thestra-boot-splash-failed', (event, message) => {
        assertMainSender(event);
        setError(message);
        return { state: state.state };
    });
    ipcMain.handle('thestra-boot-splash-ready', event => {
        assertMainSender(event);
        if (ready) return { ready: true };
        ready = true;
        state = { ...state, state: 'ready', status: 'Ready', error: '' };
        if (isLive(splashWindow)) splashWindow.close();
        splashWindow = null;
        if (isLive(mainWindow)) {
            mainWindow.show();
            mainWindow.focus();
        }
        return { ready: true };
    });
    ipcMain.handle('thestra-boot-splash-reload', event => {
        assertSplashSender(event);
        if (!isLive(mainWindow)) throw new Error('The Studio window is no longer available');
        ready = false;
        state = {
            ...state,
            state: 'loading',
            status: 'Reloading Studio…',
            error: '',
        };
        publishState();
        mainWindow.webContents.reload();
        return { reloading: true };
    });
    ipcMain.handle('thestra-boot-splash-copy-error', event => {
        assertSplashSender(event);
        if (!state.error) return { copied: false };
        clipboard.writeText(state.error);
        return { copied: true };
    });
    ipcMain.handle('thestra-boot-splash-quit', event => {
        assertSplashSender(event);
        app.quit();
        return { quitting: true };
    });

    function open() {
        if (isLive(splashWindow)) return splashWindow;
        ready = false;
        splashWindow = new BrowserWindow({
            width: 840,
            height: 502,
            useContentSize: true,
            center: true,
            show: false,
            frame: false,
            resizable: false,
            minimizable: false,
            maximizable: false,
            fullscreenable: false,
            backgroundColor: '#1a1422',
            title: options.productName || 'Studio',
            icon: options.icon,
            webPreferences: {
                nodeIntegration: false,
                contextIsolation: true,
                sandbox: false,
                preload: options.preloadPath,
            },
        });
        splashWindow.once('ready-to-show', () => {
            if (isLive(splashWindow) && !ready) splashWindow.show();
        });
        splashWindow.on('closed', () => {
            splashWindow = null;
            if (!ready) app.quit();
        });
        splashWindow.loadFile(options.htmlPath);
        publishState();
        return splashWindow;
    }

    function attachMain(window) {
        mainWindow = window;
        if (typeof window.hide === 'function') window.hide();
        const contents = window && window.webContents;
        if (!contents || typeof contents.on !== 'function') return;
        contents.on('did-fail-load', (event, errorCode, description, url, isMainFrame) => {
            if (!isMainFrame || errorCode === -3 || ready) return;
            setError(`Studio could not load ${url || 'its editor page'} (${errorCode}): ${description}`);
        });
        contents.on('render-process-gone', (_event, details) => {
            if (ready) return;
            const reason = details && details.reason ? details.reason : 'unknown reason';
            setError(`The Studio startup process stopped (${reason}). Reload Studio to try again.`);
        });
    }

    return Object.freeze({
        attachMain,
        getState: () => ({ ...state }),
        open,
    });
}

module.exports = { createStudioBootSplash };
