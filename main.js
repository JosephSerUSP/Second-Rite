const { app, BrowserWindow, Menu, ipcMain, dialog } = require('electron');
const path = require('path');
const fs = require('fs');
const {
    PRODUCT_NAME,
    WINDOWS_APP_USER_MODEL_ID,
    buildWindowsRelaunchCommand,
} = require('./tools/editor/studio-identity');
const {
    StudioWindowManager,
    createJsonWindowStateStore,
} = require('./tools/editor/studio-window-manager');

const APP_ICON_DIR = path.join(__dirname, 'tools/editor/Assets/icons/thestra-studio');
const APP_ICON_PATH = process.platform === 'win32'
    ? path.join(APP_ICON_DIR, 'icon.ico')
    : path.join(APP_ICON_DIR, 'icon-256.png');
const STUDIO_ROOT = process.env.THESTRA_STUDIO_ROOT || app.getAppPath();
const PROJECT_ENV = 'SECOND_RITE_PROJECT';

// #479: Electron relaunch passes --project so the next Studio process selects
// its Project BEFORE project-root.js/server.js are required. Do not import the
// Project lifecycle module above this point: it imports project-root.js, whose
// PROJECT_ROOT is intentionally resolved once at require time.
function projectArg(argv) {
    for (let i = 0; i < argv.length; i++) {
        const arg = argv[i];
        if (arg === '--project') {
            if (i + 1 >= argv.length) throw new Error('--project requires a path');
            return argv[i + 1];
        }
        if (typeof arg === 'string' && arg.startsWith('--project=')) {
            const value = arg.slice('--project='.length);
            if (!value) throw new Error('--project requires a path');
            return value;
        }
    }
    return null;
}

const requestedProject = projectArg(process.argv);
if (requestedProject) {
    const root = path.resolve(requestedProject);
    const dataDir = path.join(root, 'data');
    if (!fs.existsSync(root) || !fs.statSync(root).isDirectory()
            || !fs.existsSync(dataDir) || !fs.statSync(dataDir).isDirectory()) {
        throw new Error(`--project is not a Thestra Project (missing data/): ${root}`);
    }
    process.env[PROJECT_ENV] = root;
}

// Hosted Windows verification needs to prove that both the branded host and the
// raw Electron fallback actually load this checkout, not merely that an EXE can
// start. This opt-in marker exits before servers/windows are created and is never
// used by an ordinary Studio launch.
if (process.env.THESTRA_STUDIO_SMOKE_MARKER) {
    fs.writeFileSync(process.env.THESTRA_STUDIO_SMOKE_MARKER, JSON.stringify({
        appPath: STUDIO_ROOT,
        execPath: process.execPath,
        cwd: process.cwd(),
        project: process.env[PROJECT_ENV] || null,
    }), 'utf8');
    process.exit(0);
}

if (process.platform === 'win32') {
    app.setAppUserModelId(WINDOWS_APP_USER_MODEL_ID);
}

// Project-root selection is final now; modules below may safely resolve their
// one-process Project authority.
const projectRoot = require('./tools/editor/project-root');
const projectLifecycle = require('./tools/editor/project-lifecycle');
const { installProjectIpc } = require('./tools/editor/project-electron');

// 1. Boot embedded HTTP server from tools/editor/server.js
const PORT = process.env.PORT || 8080;
const server = require('./tools/editor/server.js');
// 2. Keep LÖVE invocation on a deliberately separate host boundary.
const runtimeBridge = require('./tools/editor/runtime-bridge-server.js').startRuntimeBridgeServer();

installProjectIpc({
    ipcMain,
    dialog,
    app,
    studioRoot: STUDIO_ROOT,
    currentProjectRoot: projectRoot.PROJECT_ROOT,
});

const windowStateStore = createJsonWindowStateStore({
    fs,
    userDataDir: app.getPath('userData'),
});
const windowManager = new StudioWindowManager({
    createWindow: options => new BrowserWindow(options),
    stateStore: windowStateStore,
});

windowManager.register('main', {
    defaultState: { width: 1440, height: 900, isMaximized: false },
    buildOptions: state => ({
        x: state.x,
        y: state.y,
        width: state.width || 1440,
        height: state.height || 900,
        title: PRODUCT_NAME,
        icon: APP_ICON_PATH,
        frame: true,
        show: false,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            sandbox: false,
            preload: path.join(__dirname, 'tools/editor/project-preload.js'),
        }
    }),
    configure: mainWindow => {
        if (process.platform === 'win32') {
            mainWindow.setAppDetails({
                appId: WINDOWS_APP_USER_MODEL_ID,
                appIconPath: APP_ICON_PATH,
                appIconIndex: 0,
                relaunchCommand: buildWindowsRelaunchCommand(process.execPath, STUDIO_ROOT),
                relaunchDisplayName: PRODUCT_NAME,
            });
        }

        mainWindow.loadURL(`http://127.0.0.1:${PORT}`);
        Menu.setApplicationMenu(null);

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
    },
});

function createWindow() {
    return windowManager.open('main');
}

app.whenReady().then(() => {
    if (process.platform === 'win32') {
        app.setAppUserModelId(WINDOWS_APP_USER_MODEL_ID);
    } else if (process.platform === 'darwin' && app.dock) {
        app.dock.setIcon(path.join(APP_ICON_DIR, 'icon-256.png'));
    }
    // Fail before showing UI if a caller managed to bypass the early shape
    // check with a malformed Project.
    projectLifecycle.projectInfo(projectRoot.PROJECT_ROOT);
    createWindow();
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
});

app.on('will-quit', () => {
    if (server && typeof server.close === 'function') server.close();
    if (runtimeBridge && typeof runtimeBridge.close === 'function') runtimeBridge.close();
});

module.exports = { projectArg };
