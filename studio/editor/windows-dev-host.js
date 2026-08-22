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
    const pkg = require(path.join(STUDIO_ROOT, 'package.json'));
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

// #825: two test files call ensureWindowsDevHost(), and the rebuild is not
// safe to run twice at once -- the rm+rename onto the shared hostPath is not
// atomic, and the state file is written from hashes taken after that rename,
// so concurrent callers could leave statePath describing the other process's
// artifact. This is an advisory cross-process lock around every WRITE.
//
// A lock that can wedge is worse than the race it prevents: rarely wrong
// becomes permanently stuck. So a held lock is broken when its holder is gone
// or when it is far older than any rebuild takes, and waiting is bounded.
const LOCK_STALE_MS = 5 * 60 * 1000;
const LOCK_WAIT_MS = 2 * 60 * 1000;
const LOCK_POLL_MS = 50;

function lockPathFor(hostPath) {
    return `${hostPath}.lock`;
}

function holderIsAlive(pid) {
    if (!Number.isInteger(pid) || pid <= 0) return false;
    try {
        process.kill(pid, 0);
        return true;
    } catch (error) {
        // EPERM means it exists but belongs to someone else.
        return error.code === 'EPERM';
    }
}

function lockIsStale(lockPath, now = Date.now()) {
    let stat;
    try {
        stat = fs.statSync(lockPath);
    } catch (error) {
        if (error.code === 'ENOENT') return false;
        throw error;
    }
    if (now - stat.mtimeMs > LOCK_STALE_MS) return true;
    const holder = readJson(lockPath);
    // An unreadable or half-written lock file is not evidence of a live
    // holder, but it is also not evidence of a dead one -- only age decides.
    if (!holder || typeof holder.pid !== 'number') return false;
    return !holderIsAlive(holder.pid);
}

async function withHostLock(hostPath, fn, options = {}) {
    const lockPath = options.lockPath || lockPathFor(hostPath);
    const waitMs = options.waitMs === undefined ? LOCK_WAIT_MS : options.waitMs;
    const deadline = Date.now() + waitMs;
    let held = false;
    while (!held) {
        try {
            // wx is the whole mechanism: exclusive create, fails if it exists.
            const fd = fs.openSync(lockPath, 'wx');
            try {
                fs.writeSync(fd, `${JSON.stringify({ pid: process.pid, at: new Date().toISOString() })}
`);
            } finally {
                fs.closeSync(fd);
            }
            held = true;
            break;
        } catch (error) {
            if (error.code !== 'EEXIST') throw error;
        }
        if (lockIsStale(lockPath)) {
            fs.rmSync(lockPath, { force: true });
            continue;
        }
        if (Date.now() > deadline) {
            const holder = readJson(lockPath) || {};
            throw new Error(`Timed out after ${Math.round(waitMs / 1000)}s waiting for the Thestra Studio host lock at ${lockPath}`
                + `${holder.pid ? ` (held by pid ${holder.pid} since ${holder.at})` : ''}.`
                + ' Close any running Thestra Studio window, or delete that file if nothing is building.');
        }
        await new Promise((resolve) => { setTimeout(resolve, LOCK_POLL_MS); });
    }
    try {
        return await fn();
    } finally {
        fs.rmSync(lockPath, { force: true });
    }
}

function writeBootstrap(bootstrapDir) {
    fs.mkdirSync(bootstrapDir, { recursive: true });
    for (const [name, source] of Object.entries(bootstrapFiles())) {
        fs.writeFileSync(path.join(bootstrapDir, name), source, 'utf8');
    }
}

// NOT SAFE TO CALL CONCURRENTLY FROM TWO PROCESSES, and two test files do
// call it: test-windows-dev-host.js and test-studio-native-surface-smoke.js.
// They are kept in separate `node --test` invocations in `test:studio-host`
// for exactly this reason -- `node --test` runs test FILES in parallel, so
// putting them in one group would overlap them.
//
// #825 fixed ONE of three conflicts: the rebuild now holds withHostLock(), so
// two concurrent rebuilds can no longer leave statePath describing the other
// process's artifact. That was a wrong-answer race and it is gone.
//
// The other two are NOT fixed, and they are why the two test files still may
// not overlap:
//
//   * rebuild vs. execution. test-studio-native-surface-smoke.js SPAWNS
//     hostPath and runs it for up to 30s. Windows holds a running image open,
//     so a concurrent rebuild's rm+rename over that exact file fails -- the
//     "Could not replace" error below is precisely this. The lock cannot help:
//     the smoke test does not hold it while the host runs, and should not.
//   * shared source mutation. test-windows-dev-host.js appends to
//     studio/editor/main.js to prove a source edit does not force a rebuild,
//     restoring it in a finally. The smoke test spawns the host over
//     STUDIO_ROOT and could load the mutated copy.
//
// So the ~6s the separation costs (#811) is not yet recoverable. Serializing
// is load-bearing, not leftover chaining.
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
    const inspect = () => inspectCurrentHost({ electronExe, electronVersion, packageVersion, hostPath, statePath, bootstrapDir });

    // The common case -- already current, nothing to write -- stays lock-free.
    // Everything that WRITES hostPath or statePath goes through the lock.
    const status = inspect();
    if (status.current && !status.refreshedState) {
        return { rebuilt: false, electronExe, hostPath, statePath, bootstrapDir, reason: status.reason };
    }

    return withHostLock(hostPath, async () => {
        // Re-inspect under the lock. If another process rebuilt while we
        // waited, observe its result instead of racing it -- without this the
        // lock would only serialize duplicate rebuilds, not prevent them.
        const settled = inspect();
        if (settled.current) {
            if (settled.refreshedState) writeJsonAtomic(statePath, settled.refreshedState);
            return { rebuilt: false, electronExe, hostPath, statePath, bootstrapDir, reason: settled.reason };
        }
        return rebuildWindowsDevHost({ electronExe, electronVersion, packageVersion, hostPath, statePath, bootstrapDir, reason: settled.reason });
    });
}

// The rebuild proper. Only ever called while the host lock is held.
function rebuildWindowsDevHost({ electronExe, electronVersion, packageVersion, hostPath, statePath, bootstrapDir, reason }) {
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
        return { rebuilt: true, electronExe, hostPath, statePath, bootstrapDir, reason };
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
    lockIsStale,
    lockPathFor,
    withHostLock,
    metadataForVersion,
    pathsForElectron,
    resolveElectronExecutable,
    sha256File,
    sha256Text,
    staticInputs,
    bootstrapFiles,
    windowsVersion,
};
