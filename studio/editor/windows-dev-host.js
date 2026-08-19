'use strict';

const childProcess = require('child_process');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { checkCurrent: checkIconsCurrent } = require('./build-icons');
const {
    COMPANY_NAME,
    PRODUCT_NAME,
    WINDOWS_HOST_DESCRIPTION,
    WINDOWS_HOST_FILENAME,
} = require('./studio-identity');

const REPO_ROOT = path.resolve(__dirname, '..', '..');
const STUDIO_ROOT = path.resolve(__dirname, '..');
const ICON_PATH = path.join(__dirname, 'Assets', 'icons', 'thestra-studio', 'icon.ico');
const HOST_STATE_SCHEMA = 2;
const HOST_BOOTSTRAP_SCHEMA = 1;
const RCEDIT_VERSION = '2.0.0';
const RCEDIT_URL = 'https://github.com/electron/rcedit/releases/download/v2.0.0/rcedit-x64.exe';
const RCEDIT_SHA256 = '3e7801db1a5edbec91b49a24a094aad776cb4515488ea5a4ca2289c400eade2a';
const RCEDIT_CACHE_PATH = path.join(REPO_ROOT, 'node_modules', '.cache', 'thestra-studio', `rcedit-v${RCEDIT_VERSION}-x64.exe`);

function sha256File(filename) {
    const hash = crypto.createHash('sha256');
    const fd = fs.openSync(filename, 'r');
    const buffer = Buffer.allocUnsafe(1024 * 1024);
    try {
        let bytesRead;
        do {
            bytesRead = fs.readSync(fd, buffer, 0, buffer.length, null);
            if (bytesRead > 0) hash.update(buffer.subarray(0, bytesRead));
        } while (bytesRead > 0);
    } finally {
        fs.closeSync(fd);
    }
    return hash.digest('hex');
}

function sha256Text(text) {
    return crypto.createHash('sha256').update(text, 'utf8').digest('hex');
}

function statIdentity(filename) {
    const stat = fs.statSync(filename);
    return { size: stat.size, mtimeMs: stat.mtimeMs };
}

function sameJson(left, right) {
    return JSON.stringify(left) === JSON.stringify(right);
}

function readJson(filename) {
    try {
        return JSON.parse(fs.readFileSync(filename, 'utf8'));
    } catch (error) {
        return null;
    }
}

function packageInfo() {
    const pkg = require(path.join(REPO_ROOT, 'package.json'));
    const electronPkg = require(path.join(REPO_ROOT, 'node_modules', 'electron', 'package.json'));
    return { packageVersion: pkg.version, electronVersion: electronPkg.version };
}

function windowsVersion(version) {
    const numeric = String(version).split('-')[0].split('.');
    if (numeric.length < 1 || numeric.length > 4 || numeric.some(part => !/^\d+$/.test(part))) {
        throw new Error(`Cannot encode package version as Windows version metadata: ${version}`);
    }
    while (numeric.length < 4) numeric.push('0');
    return numeric.join('.');
}

function metadataForVersion(packageVersion) {
    const version = windowsVersion(packageVersion);
    return {
        CompanyName: COMPANY_NAME,
        FileDescription: WINDOWS_HOST_DESCRIPTION,
        FileVersion: version,
        InternalName: PRODUCT_NAME,
        OriginalFilename: WINDOWS_HOST_FILENAME,
        ProductName: PRODUCT_NAME,
        ProductVersion: version,
    };
}

function resolveElectronExecutable() {
    // Electron 43's package owns binary installation. Requiring it resolves the
    // platform executable and lazily downloads dist when npm installed only the
    // JS shim. Do not duplicate that installation contract or assume dist exists.
    return require('electron');
}

function pathsForElectron(electronExe) {
    const hostPath = path.join(path.dirname(electronExe), WINDOWS_HOST_FILENAME);
    const bootstrapDir = path.join(path.dirname(electronExe), 'resources', 'app');
    return { hostPath, statePath: `${hostPath}.host.json`, bootstrapDir };
}

function bootstrapFiles() {
    return {
        'package.json': `${JSON.stringify({ name: 'thestra-studio-live-checkout-host', main: 'main.js', private: true }, null, 2)}\n`,
        'main.js': `'use strict';\n\nprocess.env.THESTRA_STUDIO_ROOT = ${JSON.stringify(STUDIO_ROOT)};\nrequire(${JSON.stringify(path.join(STUDIO_ROOT, 'main.js'))});\n`,
    };
}

function staticInputs({ electronVersion, iconSha256, packageVersion }) {
    return {
        schema: HOST_STATE_SCHEMA,
        electronVersion,
        iconSha256,
        rcedit: {
            version: RCEDIT_VERSION,
            sha256: RCEDIT_SHA256,
        },
        metadata: metadataForVersion(packageVersion),
        bootstrap: {
            schema: HOST_BOOTSTRAP_SCHEMA,
            files: Object.fromEntries(Object.entries(bootstrapFiles()).map(([name, source]) => [name, sha256Text(source)])),
        },
    };
}

function inspectCurrentHost({ electronExe, electronVersion, packageVersion, hostPath, statePath, bootstrapDir }) {
    if (!fs.existsSync(hostPath) || !fs.existsSync(statePath) || !fs.existsSync(bootstrapDir)) {
        return { current: false, reason: 'host, bootstrap, or state is missing' };
    }

    const state = readJson(statePath);
    if (!state) return { current: false, reason: 'host state is unreadable' };

    const expectedStatic = staticInputs({
        electronVersion,
        iconSha256: sha256File(ICON_PATH),
        packageVersion,
    });
    if (!sameJson(state.staticInputs, expectedStatic)) {
        return { current: false, reason: 'branded host inputs changed' };
    }
    for (const [name, expectedHash] of Object.entries(expectedStatic.bootstrap.files)) {
        const filename = path.join(bootstrapDir, name);
        if (!fs.existsSync(filename) || sha256File(filename) !== expectedHash) {
            return { current: false, reason: 'generated host bootstrap was modified' };
        }
    }

    const electronStat = statIdentity(electronExe);
    let electronMatches = sameJson(state.electronStat, electronStat);
    let electronSha256 = state.electronSha256;
    if (!electronMatches) {
        electronSha256 = sha256File(electronExe);
        electronMatches = electronSha256 === state.electronSha256;
    }
    if (!electronMatches) return { current: false, reason: 'Electron executable changed' };

    const hostStat = statIdentity(hostPath);
    let hostMatches = sameJson(state.hostStat, hostStat);
    let hostSha256 = state.hostSha256;
    if (!hostMatches) {
        hostSha256 = sha256File(hostPath);
        hostMatches = hostSha256 === state.hostSha256;
    }
    if (!hostMatches) return { current: false, reason: 'generated host was modified' };

    return {
        current: true,
        reason: 'current',
        state,
        refreshedState: (!sameJson(state.electronStat, electronStat) || !sameJson(state.hostStat, hostStat))
            ? { ...state, electronStat, hostStat, electronSha256, hostSha256 }
            : null,
    };
}

function runRcedit(rceditPath, args) {
    const result = childProcess.spawnSync(rceditPath, args, {
        encoding: 'utf8',
        windowsHide: true,
    });
    if (result.error) throw result.error;
    if (result.status !== 0) {
        throw new Error(`rcedit failed (exit ${result.status}): ${(result.stderr || result.stdout || '').trim()}`);
    }
    return String(result.stdout || '').trim();
}

function verifyPatchedMetadata(rceditPath, hostPath, metadata) {
    for (const key of ['ProductName', 'FileDescription', 'OriginalFilename', 'CompanyName', 'InternalName']) {
        const actual = runRcedit(rceditPath, [hostPath, '--get-version-string', key]);
        if (actual !== metadata[key]) {
            throw new Error(`rcedit verification failed for ${key}: expected "${metadata[key]}", got "${actual}"`);
        }
    }
    for (const key of ['FileVersion', 'ProductVersion']) {
        const actual = runRcedit(rceditPath, [hostPath, '--get-version-string', key]);
        if (!actual.startsWith(metadata[key])) {
            throw new Error(`rcedit verification failed for ${key}: expected "${metadata[key]}", got "${actual}"`);
        }
    }
}

function downloadFileWithWindowsPowerShell(url, destination) {
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    const tempPath = `${destination}.download-${process.pid}`;
    fs.rmSync(tempPath, { force: true });

    // The actual Electron-43 Windows probe for #258 verified GitHub release
    // downloads through Windows PowerShell. Use that native path instead of a
    // second Node/TLS stack, then authenticate the result by the pinned digest.
    const script = [
        "$ErrorActionPreference = 'Stop'",
        "$ProgressPreference = 'SilentlyContinue'",
        'for ($attempt = 1; $attempt -le 3; $attempt++) {',
        '  try {',
        '    Invoke-WebRequest -UseBasicParsing -Uri $env:THESTRA_DOWNLOAD_URL -OutFile $env:THESTRA_DOWNLOAD_DEST',
        '    exit 0',
        '  } catch {',
        '    if ($attempt -eq 3) { throw }',
        '    Start-Sleep -Seconds $attempt',
        '  }',
        '}',
    ].join('\n');
    const result = childProcess.spawnSync('powershell.exe', ['-NoProfile', '-NonInteractive', '-Command', script], {
        encoding: 'utf8',
        windowsHide: true,
        env: {
            ...process.env,
            THESTRA_DOWNLOAD_URL: url,
            THESTRA_DOWNLOAD_DEST: tempPath,
        },
    });
    try {
        if (result.error) throw result.error;
        if (result.status !== 0) {
            throw new Error(`PowerShell download failed (exit ${result.status}): ${(result.stderr || result.stdout || '').trim()}`);
        }
        if (!fs.existsSync(tempPath)) throw new Error(`PowerShell download produced no file: ${url}`);
        fs.rmSync(destination, { force: true });
        fs.renameSync(tempPath, destination);
    } catch (error) {
        fs.rmSync(tempPath, { force: true });
        throw error;
    }
}

function ensureRcedit() {
    if (process.arch !== 'x64') {
        throw new Error(`Thestra Studio's pinned Windows host patcher currently supports x64 only; got ${process.arch}`);
    }
    if (fs.existsSync(RCEDIT_CACHE_PATH)) {
        if (sha256File(RCEDIT_CACHE_PATH) === RCEDIT_SHA256) return RCEDIT_CACHE_PATH;
        fs.rmSync(RCEDIT_CACHE_PATH, { force: true });
    }
    downloadFileWithWindowsPowerShell(RCEDIT_URL, RCEDIT_CACHE_PATH);
    const actual = sha256File(RCEDIT_CACHE_PATH);
    if (actual !== RCEDIT_SHA256) {
        fs.rmSync(RCEDIT_CACHE_PATH, { force: true });
        throw new Error(`rcedit v${RCEDIT_VERSION} digest mismatch: expected ${RCEDIT_SHA256}, got ${actual}`);
    }
    return RCEDIT_CACHE_PATH;
}

function writeJsonAtomic(filename, value) {
    const tempPath = `${filename}.writing-${process.pid}`;
    fs.writeFileSync(tempPath, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
    fs.rmSync(filename, { force: true });
    fs.renameSync(tempPath, filename);
}

function writeBootstrap(bootstrapDir) {
    fs.mkdirSync(bootstrapDir, { recursive: true });
    for (const [name, source] of Object.entries(bootstrapFiles())) {
        fs.writeFileSync(path.join(bootstrapDir, name), source, 'utf8');
    }
}

async function ensureWindowsDevHost() {
    if (process.platform !== 'win32') {
        throw new Error('The branded Thestra Studio development host is Windows-only');
    }

    // #357 is the authority for platform container generation. Refuse a stale
    // tracked ICO instead of silently embedding artwork that is behind its PNGs.
    checkIconsCurrent();

    const electronExe = resolveElectronExecutable();
    if (!fs.existsSync(electronExe)) throw new Error(`Electron executable is missing: ${electronExe}`);
    const { packageVersion, electronVersion } = packageInfo();
    const { hostPath, statePath, bootstrapDir } = pathsForElectron(electronExe);
    const status = inspectCurrentHost({ electronExe, electronVersion, packageVersion, hostPath, statePath, bootstrapDir });
    if (status.current) {
        if (status.refreshedState) writeJsonAtomic(statePath, status.refreshedState);
        return { rebuilt: false, electronExe, hostPath, statePath, bootstrapDir, reason: status.reason };
    }

    const rceditPath = ensureRcedit();
    const metadata = metadataForVersion(packageVersion);
    const tempHostPath = `${hostPath}.building-${process.pid}`;
    fs.rmSync(tempHostPath, { force: true });
    try {
        fs.copyFileSync(electronExe, tempHostPath);
        runRcedit(rceditPath, [
            tempHostPath,
            '--set-icon', ICON_PATH,
            '--set-version-string', 'ProductName', metadata.ProductName,
            '--set-version-string', 'FileDescription', metadata.FileDescription,
            '--set-version-string', 'InternalName', metadata.InternalName,
            '--set-version-string', 'OriginalFilename', metadata.OriginalFilename,
            '--set-version-string', 'CompanyName', metadata.CompanyName,
            '--set-product-version', metadata.ProductVersion,
            '--set-file-version', metadata.FileVersion,
        ]);
        verifyPatchedMetadata(rceditPath, tempHostPath, metadata);
        writeBootstrap(bootstrapDir);

        try {
            fs.rmSync(hostPath, { force: true });
            fs.renameSync(tempHostPath, hostPath);
        } catch (error) {
            throw new Error(`Could not replace ${WINDOWS_HOST_FILENAME}. Close any running Thestra Studio window and retry. ${error.message}`);
        }

        const state = {
            staticInputs: staticInputs({
                electronVersion,
                iconSha256: sha256File(ICON_PATH),
                packageVersion,
            }),
            electronSha256: sha256File(electronExe),
            electronStat: statIdentity(electronExe),
            hostSha256: sha256File(hostPath),
            hostStat: statIdentity(hostPath),
        };
        writeJsonAtomic(statePath, state);
        return { rebuilt: true, electronExe, hostPath, statePath, bootstrapDir, reason: status.reason };
    } finally {
        fs.rmSync(tempHostPath, { force: true });
    }
}

function checkWindowsDevHost() {
    if (process.platform !== 'win32') return { skipped: true, reason: 'not Windows' };
    checkIconsCurrent();
    const electronExe = resolveElectronExecutable();
    const { packageVersion, electronVersion } = packageInfo();
    const { hostPath, statePath, bootstrapDir } = pathsForElectron(electronExe);
    const status = inspectCurrentHost({ electronExe, electronVersion, packageVersion, hostPath, statePath, bootstrapDir });
    if (!status.current) throw new Error(`Thestra Studio Windows development host is stale: ${status.reason}; run npm run studio:host`);
    return { skipped: false, electronExe, hostPath, statePath, bootstrapDir };
}

async function main(argv = process.argv.slice(2)) {
    if (argv.length !== 1 || !['--ensure', '--check'].includes(argv[0])) {
        throw new Error('usage: node studio/editor/windows-dev-host.js --ensure|--check');
    }
    if (process.platform !== 'win32') {
        console.log('Thestra Studio Windows development host: skipped (not Windows).');
        return;
    }
    if (argv[0] === '--check') {
        const result = checkWindowsDevHost();
        console.log(`Thestra Studio Windows development host is current: ${result.hostPath}`);
        return;
    }
    const result = await ensureWindowsDevHost();
    console.log(`${result.rebuilt ? 'Rebuilt' : 'Using current'} Thestra Studio Windows development host: ${result.hostPath}`);
}

if (require.main === module) {
    main().catch(error => {
        console.error(error && error.stack ? error.stack : error);
        process.exitCode = 1;
    });
}

module.exports = {
    HOST_STATE_SCHEMA,
    HOST_BOOTSTRAP_SCHEMA,
    ICON_PATH,
    RCEDIT_SHA256,
    RCEDIT_URL,
    RCEDIT_VERSION,
    checkWindowsDevHost,
    downloadFileWithWindowsPowerShell,
    ensureRcedit,
    ensureWindowsDevHost,
    inspectCurrentHost,
    metadataForVersion,
    pathsForElectron,
    resolveElectronExecutable,
    sha256File,
    sha256Text,
    staticInputs,
    bootstrapFiles,
    windowsVersion,
};
