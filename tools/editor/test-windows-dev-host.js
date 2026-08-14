'use strict';

const assert = require('assert');
const childProcess = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const test = require('node:test');
const { checkCurrent: checkIconsCurrent } = require('./build-icons');
const {
    PRODUCT_NAME,
    WINDOWS_APP_USER_MODEL_ID,
    WINDOWS_HOST_DESCRIPTION,
    WINDOWS_HOST_FILENAME,
    buildWindowsRelaunchCommand,
} = require('./studio-identity');
const {
    checkWindowsDevHost,
    ensureWindowsDevHost,
    metadataForVersion,
    windowsVersion,
} = require('./windows-dev-host');

const REPO_ROOT = path.resolve(__dirname, '..', '..');

function spawnChecked(executable, args, options = {}) {
    const result = childProcess.spawnSync(executable, args, {
        cwd: REPO_ROOT,
        encoding: 'utf8',
        windowsHide: true,
        ...options,
    });
    if (result.error) throw result.error;
    assert.equal(
        result.status,
        0,
        `${executable} ${args.join(' ')} failed\nstdout:\n${result.stdout || ''}\nstderr:\n${result.stderr || ''}`,
    );
    return result;
}

function runStudioSmoke(executable, markerPath, args = [REPO_ROOT]) {
    fs.rmSync(markerPath, { force: true });
    spawnChecked(executable, args, {
        env: {
            ...process.env,
            THESTRA_STUDIO_SMOKE_MARKER: markerPath,
            ELECTRON_DISABLE_GPU: '1',
        },
        timeout: 30000,
    });
    assert.ok(fs.existsSync(markerPath), `Studio smoke marker was not written by ${executable}`);
    return JSON.parse(fs.readFileSync(markerPath, 'utf8'));
}

test('Windows product identity is singular and relaunch command retains the live checkout argument', () => {
    assert.equal(PRODUCT_NAME, 'Thestra Studio');
    assert.equal(WINDOWS_APP_USER_MODEL_ID, 'com.josephserusp.thestrastudio');
    assert.equal(WINDOWS_HOST_FILENAME, 'Thestra Studio.exe');
    assert.equal(WINDOWS_HOST_DESCRIPTION, 'Thestra Studio Development Host');
    assert.equal(
        buildWindowsRelaunchCommand('C:\\Program Files\\Electron\\Thestra Studio.exe', 'D:\\work trees\\Second Rite'),
        '"C:\\Program Files\\Electron\\Thestra Studio.exe" "D:\\work trees\\Second Rite"',
    );
    assert.throws(() => buildWindowsRelaunchCommand('C:\\bad"path.exe', 'D:\\repo'), /may not contain a quote/);
});

test('package versions become deterministic four-component PE versions', () => {
    assert.equal(windowsVersion('1.0.0'), '1.0.0.0');
    assert.equal(windowsVersion('43.2.0'), '43.2.0.0');
    assert.equal(windowsVersion('2.1.3-beta.1'), '2.1.3.0');
    assert.throws(() => windowsVersion('not-a-version'), /Cannot encode/);
    assert.equal(metadataForVersion('1.0.0').ProductName, PRODUCT_NAME);
});

test('hosted Windows builds, reuses and boots the branded live-checkout host', { skip: process.platform !== 'win32', timeout: 180000 }, async () => {
    checkIconsCurrent();
    const pkg = require(path.join(REPO_ROOT, 'package.json'));
    assert.equal(pkg.scripts['start:electron'], 'electron .', 'raw Electron fallback must remain explicit');

    const first = await ensureWindowsDevHost();
    assert.ok(fs.existsSync(first.hostPath), 'branded host was not generated');
    assert.equal(path.basename(first.hostPath), WINDOWS_HOST_FILENAME);
    assert.equal(path.dirname(first.hostPath), path.dirname(first.electronExe), 'host must live beside the resolved Electron runtime');
    assert.ok(fs.existsSync(path.join(first.bootstrapDir, 'package.json')), 'direct-launch bootstrap package was not generated');

    const hostStatBefore = fs.statSync(first.hostPath);
    const second = await ensureWindowsDevHost();
    const hostStatSecond = fs.statSync(second.hostPath);
    assert.equal(second.rebuilt, false, 'a current branded host must be reused');
    assert.equal(hostStatSecond.mtimeMs, hostStatBefore.mtimeMs, 'reuse must not rewrite the executable');

    // A normal Studio source edit is deliberately not a branded-host input.
    const mainPath = path.join(REPO_ROOT, 'main.js');
    const originalMain = fs.readFileSync(mainPath);
    try {
        fs.appendFileSync(mainPath, '\n// issue-258 source-change currentness probe\n');
        const afterSourceEdit = await ensureWindowsDevHost();
        assert.equal(afterSourceEdit.rebuilt, false, 'ordinary application source changes must not rebuild the host');
        assert.equal(fs.statSync(afterSourceEdit.hostPath).mtimeMs, hostStatBefore.mtimeMs);
    } finally {
        fs.writeFileSync(mainPath, originalMain);
    }

    const metadataScript = [
        '$v = (Get-Item -LiteralPath $env:THESTRA_HOST).VersionInfo',
        '@{ ProductName=$v.ProductName; FileDescription=$v.FileDescription; OriginalFilename=$v.OriginalFilename; FileVersion=$v.FileVersion; ProductVersion=$v.ProductVersion } | ConvertTo-Json -Compress',
    ].join('; ');
    const metadataResult = spawnChecked('powershell.exe', ['-NoProfile', '-Command', metadataScript], {
        env: { ...process.env, THESTRA_HOST: first.hostPath },
    });
    const metadata = JSON.parse(metadataResult.stdout.trim());
    assert.equal(metadata.ProductName, PRODUCT_NAME);
    assert.equal(metadata.FileDescription, WINDOWS_HOST_DESCRIPTION);
    assert.equal(metadata.OriginalFilename, WINDOWS_HOST_FILENAME);
    assert.ok(metadata.FileVersion.startsWith('1.0.0.0'));
    assert.ok(metadata.ProductVersion.startsWith('1.0.0.0'));

    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-host-test-'));
    try {
        const rawIcon = path.join(tempDir, 'electron.png');
        const brandedIcon = path.join(tempDir, 'thestra.png');
        const iconScript = [
            'Add-Type -AssemblyName System.Drawing',
            '$raw = [System.Drawing.Icon]::ExtractAssociatedIcon($env:ELECTRON_EXE)',
            '$brand = [System.Drawing.Icon]::ExtractAssociatedIcon($env:THESTRA_HOST)',
            '$raw.ToBitmap().Save($env:RAW_ICON, [System.Drawing.Imaging.ImageFormat]::Png)',
            '$brand.ToBitmap().Save($env:BRANDED_ICON, [System.Drawing.Imaging.ImageFormat]::Png)',
            '$raw.Dispose()',
            '$brand.Dispose()',
        ].join('; ');
        spawnChecked('powershell.exe', ['-NoProfile', '-Command', iconScript], {
            env: {
                ...process.env,
                ELECTRON_EXE: first.electronExe,
                THESTRA_HOST: first.hostPath,
                RAW_ICON: rawIcon,
                BRANDED_ICON: brandedIcon,
            },
        });
        assert.notDeepEqual(fs.readFileSync(brandedIcon), fs.readFileSync(rawIcon), 'branded PE icon must differ from generic Electron');

        const relativeHost = path.relative(REPO_ROOT, first.hostPath);
        assert.ok(!relativeHost.startsWith(`..${path.sep}`) && relativeHost !== '..', 'normal Electron host should resolve inside this checkout');
        spawnChecked('git', ['check-ignore', '-q', '--', relativeHost]);

        const brandedMarker = path.join(tempDir, 'branded-smoke.json');
        const brandedSmoke = runStudioSmoke(first.hostPath, brandedMarker);
        assert.equal(fs.realpathSync(brandedSmoke.appPath), fs.realpathSync(REPO_ROOT));
        assert.equal(path.resolve(brandedSmoke.execPath).toLowerCase(), path.resolve(first.hostPath).toLowerCase());

        const directMarker = path.join(tempDir, 'direct-smoke.json');
        const directSmoke = runStudioSmoke(first.hostPath, directMarker, []);
        assert.equal(fs.realpathSync(directSmoke.appPath), fs.realpathSync(REPO_ROOT));
        assert.equal(path.resolve(directSmoke.execPath).toLowerCase(), path.resolve(first.hostPath).toLowerCase());

        const rawMarker = path.join(tempDir, 'raw-smoke.json');
        const rawSmoke = runStudioSmoke(first.electronExe, rawMarker);
        assert.equal(fs.realpathSync(rawSmoke.appPath), fs.realpathSync(REPO_ROOT));
        assert.equal(path.resolve(rawSmoke.execPath).toLowerCase(), path.resolve(first.electronExe).toLowerCase());
    } finally {
        fs.rmSync(tempDir, { recursive: true, force: true });
    }

    const checked = checkWindowsDevHost();
    assert.equal(checked.hostPath, first.hostPath);
});
