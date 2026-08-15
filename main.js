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
const { installStudioIpc } = require('./tools/editor/studio-electron');

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
const readySurfaces = new Set();
const studioIpc = installStudioIpc({
    ipcMain,
    dialog,
    windowManager,
    onSurfaceReady: surfaceId => readySurfaces.add(surfaceId),
});

function studioWebPreferences() {
    return {
        nodeIntegration: false,
        contextIsolation: true,
        sandbox: false,
        preload: path.join(__dirname, 'tools/editor/project-preload.js'),
    };
}

function applyWindowsStudioIdentity(win) {
    if (process.platform !== 'win32') return;
    win.setAppDetails({
        appId: WINDOWS_APP_USER_MODEL_ID,
        appIconPath: APP_ICON_PATH,
        appIconIndex: 0,
        relaunchCommand: buildWindowsRelaunchCommand(process.execPath, STUDIO_ROOT),
        relaunchDisplayName: PRODUCT_NAME,
    });
}

function installStudioWindowShortcuts(win) {
    win.webContents.on('before-input-event', (event, input) => {
        if (input.type !== 'keyDown') return;

        if (input.key === 'F12' || (input.control && input.shift && input.key.toLowerCase() === 'i')) {
            win.webContents.toggleDevTools();
            event.preventDefault();
        } else if (input.control && input.key.toLowerCase() === 'r') {
            win.webContents.reload();
            event.preventDefault();
        } else if (input.key === 'F11') {
            win.setFullScreen(!win.isFullScreen());
            event.preventDefault();
        }
    });
}

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
        webPreferences: studioWebPreferences(),
    }),
    configure: mainWindow => {
        applyWindowsStudioIdentity(mainWindow);
        mainWindow.loadURL(`http://127.0.0.1:${PORT}`);
        Menu.setApplicationMenu(null);
        installStudioWindowShortcuts(mainWindow);

        // A secondary EditorSurface belongs to this Studio application/session,
        // not to an OS parent-child z-order relationship. If the main workspace
        // actually goes away, ask the Database surface to close through its own
        // dirty-state protocol rather than orphaning it silently.
        mainWindow.on('closed', () => windowManager.close('database'));
    },
});

windowManager.register('database', {
    defaultState: { width: 1280, height: 800, isMaximized: false },
    // The renderer reveals this surface only after its host stylesheet is
    // mounted and the real Studio /data boot has completed, avoiding a frame
    // where the full Studio page or an uninitialized Database flashes first.
    autoShow: false,
    buildOptions: state => ({
        x: state.x,
        y: state.y,
        width: state.width || 1280,
        height: state.height || 800,
        minWidth: 900,
        minHeight: 560,
        title: `Database - ${PRODUCT_NAME}`,
        icon: APP_ICON_PATH,
        frame: true,
        show: false,
        webPreferences: studioWebPreferences(),
    }),
    requestClose: (databaseWindow, approve) => {
        studioIpc.requestClose('database', databaseWindow, approve);
    },
    configure: databaseWindow => {
        applyWindowsStudioIdentity(databaseWindow);
        databaseWindow.loadURL(`http://127.0.0.1:${PORT}/?surface=database`);
        installStudioWindowShortcuts(databaseWindow);
    },
});

function createWindow() {
    return windowManager.open('main');
}

function waitForSurfaceReady(surfaceId, timeoutMs = 15000) {
    if (readySurfaces.has(surfaceId)) return Promise.resolve();
    return new Promise((resolve, reject) => {
        const deadline = Date.now() + timeoutMs;
        const poll = () => {
            if (readySurfaces.has(surfaceId)) {
                resolve();
                return;
            }
            if (Date.now() >= deadline) {
                const win = windowManager.get(surfaceId);
                const url = win && win.webContents && typeof win.webContents.getURL === 'function'
                    ? win.webContents.getURL()
                    : '';
                reject(new Error([
                    `Studio surface did not signal semantic readiness: ${surfaceId}`,
                    `current URL: ${url || '(empty)'}`,
                ].join('\n')));
                return;
            }
            setTimeout(poll, 25);
        };
        poll();
    });
}

async function runSurfaceSmoke(markerPath) {
    readySurfaces.clear();
    createWindow();
    windowManager.open('database');

    // Database's surfaceReady signal is semantic: its existing DOM has mounted,
    // Electron host CSS has loaded, and the real /data boot attempt has reached
    // an initialized or terminal-offline editor state. That is a stronger proof
    // of usable Studio composition than waiting for the global page loading
    // indicator, which can remain active while preview assets stream.
    await waitForSurfaceReady('database');

    fs.writeFileSync(markerPath, JSON.stringify({
        appPath: STUDIO_ROOT,
        readySurfaces: Array.from(readySurfaces),
        windows: BrowserWindow.getAllWindows().map(win => ({
            title: win.getTitle(),
            url: win.webContents.getURL(),
            visible: typeof win.isVisible === 'function' ? win.isVisible() : null,
        })),
    }, null, 2), 'utf8');

    // This is a disposable verification process, not a user-initiated quit.
    // Once the positive marker is durable, destroy the fresh smoke windows and
    // exit immediately instead of waiting for embedded HTTP keep-alive handles
    // to drain through the production graceful-shutdown path.
    BrowserWindow.getAllWindows().forEach(win => win.destroy());
    app.exit(0);
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

    const surfaceSmokeMarker = process.env.THESTRA_STUDIO_SURFACE_SMOKE_MARKER;
    if (surfaceSmokeMarker) {
        runSurfaceSmoke(surfaceSmokeMarker).catch(error => {
            console.error('Studio surface smoke failed:', error);
            app.exit(1);
        });
        return;
    }

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
