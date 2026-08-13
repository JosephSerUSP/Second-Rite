const { app, BrowserWindow, Menu } = require('electron');
const path = require('path');
const fs = require('fs');

// Path to store window bounds/state across restarts
const WINDOW_STATE_PATH = path.join(app.getPath('userData'), 'window-state.json');
const APP_ICON_DIR = path.join(__dirname, 'tools/editor/Assets/icons/thestra-studio');
const APP_ICON_PATH = process.platform === 'win32'
    ? path.join(APP_ICON_DIR, 'icon.ico')
    : path.join(APP_ICON_DIR, 'icon-256.png');
const WINDOWS_APP_USER_MODEL_ID = 'com.josephserusp.thestrastudio';

function loadWindowState() {
    try {
        if (fs.existsSync(WINDOW_STATE_PATH)) {
            const data = fs.readFileSync(WINDOW_STATE_PATH, 'utf8');
            return JSON.parse(data);
        }
    } catch (e) {
        console.error('Failed to load window state:', e);
    }
    return { width: 1440, height: 900, isMaximized: false };
}

function saveWindowState(win) {
    if (!win) return;
    try {
        const isMaximized = win.isMaximized();
        const bounds = win.getBounds();
        const state = {
            x: bounds.x,
            y: bounds.y,
            width: bounds.width,
            height: bounds.height,
            isMaximized: isMaximized
        };
        fs.writeFileSync(WINDOW_STATE_PATH, JSON.stringify(state, null, 2));
    } catch (e) {
        console.error('Failed to save window state:', e);
    }
}

// 1. Boot embedded HTTP server from tools/editor/server.js
const PORT = process.env.PORT || 8080;
const server = require('./tools/editor/server.js');
// 2. Keep LÖVE invocation on a deliberately separate host boundary. The
// browser talks to this local service only for authoritative compiled
// renderables; ordinary authored-data/editor HTTP remains server.js's job.
const runtimeBridge = require('./tools/editor/runtime-bridge-server.js').startRuntimeBridgeServer();

let mainWindow = null;

function createWindow() {
    const state = loadWindowState();

    mainWindow = new BrowserWindow({
        x: state.x,
        y: state.y,
        width: state.width || 1440,
        height: state.height || 900,
        title: 'Second Rite Developer Studio',
        icon: APP_ICON_PATH,
        frame: true,
        show: false,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            sandbox: false
        }
    });

    // Windows can otherwise keep the development Electron executable's
    // taskbar identity even when the BrowserWindow has its own icon.
    if (process.platform === 'win32') {
        mainWindow.setAppDetails({
            appId: WINDOWS_APP_USER_MODEL_ID,
            appIconPath: APP_ICON_PATH,
            appIconIndex: 0
        });
    }

    if (state.isMaximized) {
        mainWindow.maximize();
    }

    mainWindow.once('ready-to-show', () => {
        mainWindow.show();
    });

    // Save bounds on close
    mainWindow.on('close', () => {
        saveWindowState(mainWindow);
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
    });

    // Load editor web app
    mainWindow.loadURL(`http://127.0.0.1:${PORT}`);

    // Disable native Electron menu bar to prevent duplicated toolbars (app has its own HTML menu bar)
    Menu.setApplicationMenu(null);

    // Register developer keyboard shortcuts (F12 DevTools, Ctrl+R Reload, F11 Fullscreen)
    mainWindow.webContents.on('before-input-event', (event, input) => {
        if (input.type !== 'keyDown') return;

        if (input.key === 'F12' || (input.control && input.shift && input.key.toLowerCase() === 'i')) {
            mainWindow.webContents.toggleDevTools();
            event.preventDefault();
        } else if (input.control && input.key.toLowerCase() === 'r') {
            mainWindow.webContents.reload();
            event.preventDefault();
        } else if (input.key === 'F11') {
            mainWindow.setFullScreen(!mainWindow.isFullScreen());
            event.preventDefault();
        }
    });
}

app.whenReady().then(() => {
    if (process.platform === 'win32') {
        // Give development runs a stable identity instead of inheriting
        // electron.exe's generic AppUserModelID/taskbar grouping.
        app.setAppUserModelId(WINDOWS_APP_USER_MODEL_ID);
    } else if (process.platform === 'darwin' && app.dock) {
        app.dock.setIcon(path.join(APP_ICON_DIR, 'icon-256.png'));
    }
    createWindow();
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createWindow();
    }
});

app.on('will-quit', () => {
    if (server && typeof server.close === 'function') {
        server.close();
    }
    if (runtimeBridge && typeof runtimeBridge.close === 'function') {
        runtimeBridge.close();
    }
});
