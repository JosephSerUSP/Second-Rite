const { app, BrowserWindow, Menu, ipcMain, dialog } = require('electron');
const path = require('path');
const fs = require('fs');
const semanticRoots = require('./tools/semantic-roots');
const {
    PRODUCT_NAME,
    WINDOWS_APP_USER_MODEL_ID,
    buildWindowsRelaunchCommand,
} = require('./tools/editor/studio-identity');
const {
    StudioWindowManager,
    createJsonWindowStateStore,
} = require('./tools/editor/studio-window-manager');
const { ALLOWED_SURFACES, installStudioIpc } = require('./tools/editor/studio-electron');
const { createStudioShutdownCoordinator } = require('./tools/editor/studio-shutdown');
const { createProjectWatcher } = require('./tools/editor/project-watcher');

const APP_ICON_DIR = path.join(__dirname, 'tools/editor/Assets/icons/thestra-studio');
const APP_ICON_PATH = process.platform === 'win32'
    ? path.join(APP_ICON_DIR, 'icon.ico')
    : path.join(APP_ICON_DIR, 'icon-256.png');
const BOOT_ROOTS = semanticRoots.resolveInstallationRoots({
    studioRoot: process.env[semanticRoots.STUDIO_ROOT_ENV] || app.getAppPath(),
});
const STUDIO_ROOT = BOOT_ROOTS.studioRoot;
const PROJECT_ENV = semanticRoots.PROJECT_ENV;
// Modules loaded after Project selection resolve the same Studio root instead
// of independently rediscovering app/install topology.
process.env[semanticRoots.STUDIO_ROOT_ENV] = STUDIO_ROOT;

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
    process.env[PROJECT_ENV] = semanticRoots.assertProjectRoot(requestedProject, '--project');
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
let projectWatcher = null;
const studioIpc = installStudioIpc({
    ipcMain,
    dialog,
    windowManager,
    onSurfaceReady: surfaceId => readySurfaces.add(surfaceId),
    // Studio's own save will also be visible to the filesystem watcher. Mark
    // the semantic resource briefly so the settled watcher event is coalesced
    // with this already-published commit rather than causing a duplicate reload.
    onResourceCommit: resources => {
        if (projectWatcher) projectWatcher.suppressResources(resources);
    },
});
projectWatcher = createProjectWatcher({
    projectRoot: projectRoot.PROJECT_ROOT,
    onResources: resources => studioIpc.broadcastResourceCommit('external', resources),
    onAssets: assets => studioIpc.broadcastAssetInvalidation(assets),
    onError: error => {
        console.error('Studio Project watcher unavailable:', error && error.message ? error.message : error);
    },
});
const shutdownCoordinator = createStudioShutdownCoordinator({
    windowManager,
    studioIpc,
    secondarySurfaces: ALLOWED_SURFACES,
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

// The real Electron smoke is our architectural proof for native EditorSurfaces.
// When it fails, capture renderer facts at the owning process boundary rather
// than inferring them from HTTP asset requests. This is entirely opt-in and is
// never installed for an ordinary Studio launch.
function installSurfaceSmokeDiagnostics(surfaceId, win) {
    if (!process.env.THESTRA_STUDIO_SURFACE_SMOKE_MARKER) return;
    const contents = win.webContents;
    const prefix = `[surface:${surfaceId}]`;

    contents.on('console-message', (_event, level, message, line, sourceId) => {
        console.log(`${prefix} console(${level}): ${message} @ ${sourceId || '(unknown)'}:${line || 0}`);
    });
    contents.on('did-fail-load', (_event, errorCode, errorDescription, validatedURL, isMainFrame) => {
        console.error(`${prefix} did-fail-load code=${errorCode} main=${!!isMainFrame} url=${validatedURL} ${errorDescription}`);
    });
    contents.on('render-process-gone', (_event, details) => {
        console.error(`${prefix} render-process-gone ${JSON.stringify(details)}`);
    });
    contents.on('dom-ready', () => {
        console.log(`${prefix} dom-ready url=${contents.getURL()}`);
        contents.executeJavaScript(`JSON.stringify({
            href: location.href,
            readyState: document.readyState,
            fetchDatabaseType: typeof fetchDatabase,
            bootState: window.thestraDatabaseBootState || null,
            bridgePresent: !!window.thestraStudio,
            databaseModalPresent: !!document.getElementById('db-modal'),
            engineModalPresent: !!document.getElementById('engine-modal'),
            tilesetModalPresent: !!document.getElementById('tileset-studio-modal'),
            scriptCount: document.scripts.length
        })`).then(snapshot => {
            console.log(`${prefix} renderer-snapshot ${snapshot}`);
        }).catch(error => {
            console.error(`${prefix} renderer-snapshot failed: ${error && error.stack ? error.stack : error}`);
        });
    });
    contents.on('did-finish-load', () => {
        console.log(`${prefix} did-finish-load url=${contents.getURL()}`);
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
    requestClose: (mainWindow, decide) => {
        shutdownCoordinator.requestMainClose(mainWindow, decide);
    },
    configure: mainWindow => {
        applyWindowsStudioIdentity(mainWindow);
        installSurfaceSmokeDiagnostics('main', mainWindow);
        mainWindow.loadURL(`http://127.0.0.1:${PORT}`);
        Menu.setApplicationMenu(null);
        installStudioWindowShortcuts(mainWindow);
    },
});

windowManager.register('database', {
    defaultState: { width: 1280, height: 800, isMaximized: false },
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
    requestClose: (databaseWindow, decide) => {
        studioIpc.requestClose('database', databaseWindow, decide);
    },
    configure: databaseWindow => {
        applyWindowsStudioIdentity(databaseWindow);
        installSurfaceSmokeDiagnostics('database', databaseWindow);
        databaseWindow.loadURL(`http://127.0.0.1:${PORT}/index.html?surface=database`);
        installStudioWindowShortcuts(databaseWindow);
    },
});

windowManager.register('engine', {
    defaultState: { width: 1200, height: 760, isMaximized: false },
    autoShow: false,
    buildOptions: state => ({
        x: state.x,
        y: state.y,
        width: state.width || 1200,
        height: state.height || 760,
        minWidth: 900,
        minHeight: 560,
        title: `Engine Editor - ${PRODUCT_NAME}`,
        icon: APP_ICON_PATH,
        frame: true,
        show: false,
        webPreferences: studioWebPreferences(),
    }),
    requestClose: (engineWindow, decide) => {
        studioIpc.requestClose('engine', engineWindow, decide);
    },
    configure: engineWindow => {
        applyWindowsStudioIdentity(engineWindow);
        installSurfaceSmokeDiagnostics('engine', engineWindow);
        engineWindow.loadURL(`http://127.0.0.1:${PORT}/index.html?surface=engine`);
        installStudioWindowShortcuts(engineWindow);
    },
});

windowManager.register('tileset', {
    defaultState: { width: 1320, height: 820, isMaximized: false },
    autoShow: false,
    buildOptions: state => ({
        x: state.x,
        y: state.y,
        width: state.width || 1320,
        height: state.height || 820,
        minWidth: 980,
        minHeight: 620,
        title: `Tileset Studio - ${PRODUCT_NAME}`,
        icon: APP_ICON_PATH,
        frame: true,
        show: false,
        webPreferences: studioWebPreferences(),
    }),
    requestClose: (tilesetWindow, decide) => {
        studioIpc.requestClose('tileset', tilesetWindow, decide);
    },
    configure: tilesetWindow => {
        applyWindowsStudioIdentity(tilesetWindow);
        installSurfaceSmokeDiagnostics('tileset', tilesetWindow);
        tilesetWindow.loadURL(`http://127.0.0.1:${PORT}/index.html?surface=tileset`);
        installStudioWindowShortcuts(tilesetWindow);
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
    windowManager.open('engine');
    windowManager.open('tileset');

    await Promise.all([
        waitForSurfaceReady('database'),
        waitForSurfaceReady('engine'),
        waitForSurfaceReady('tileset'),
    ]);

    fs.writeFileSync(markerPath, JSON.stringify({
        appPath: STUDIO_ROOT,
        readySurfaces: Array.from(readySurfaces),
        windows: BrowserWindow.getAllWindows().map(win => ({
            title: win.getTitle(),
            url: win.webContents.getURL(),
            visible: typeof win.isVisible === 'function' ? win.isVisible() : null,
        })),
    }, null, 2), 'utf8');

    BrowserWindow.getAllWindows().forEach(win => win.destroy());
    app.exit(0);
}

app.whenReady().then(() => {
    if (process.platform === 'win32') {
        app.setAppUserModelId(WINDOWS_APP_USER_MODEL_ID);
    } else if (process.platform === 'darwin' && app.dock) {
        app.dock.setIcon(path.join(APP_ICON_DIR, 'icon-256.png'));
    }
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
    if (projectWatcher) projectWatcher.close().catch(error => {
        console.error('Studio Project watcher close failed:', error && error.message ? error.message : error);
    });
    if (server && typeof server.close === 'function') server.close();
    if (runtimeBridge && typeof runtimeBridge.close === 'function') runtimeBridge.close();
});

module.exports = { projectArg };
