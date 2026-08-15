'use strict';

const assert = require('node:assert/strict');
const childProcess = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const { ensureWindowsDevHost } = require('./windows-dev-host');

const REPO_ROOT = path.resolve(__dirname, '..', '..');

function terminateProcessTree(child) {
    if (!child || !child.pid || child.exitCode !== null) return;
    childProcess.spawnSync('taskkill.exe', ['/PID', String(child.pid), '/T', '/F'], {
        windowsHide: true,
        stdio: 'ignore',
        timeout: 5000,
    });
}

function startNativeSurfaceSmoke(hostPath, marker, timeoutMs = 30000) {
    return new Promise((resolve, reject) => {
        const child = childProcess.spawn(hostPath, [REPO_ROOT], {
            cwd: REPO_ROOT,
            windowsHide: true,
            stdio: ['ignore', 'pipe', 'pipe'],
            env: {
                ...process.env,
                THESTRA_STUDIO_SURFACE_SMOKE_MARKER: marker,
                ELECTRON_DISABLE_GPU: '1',
            },
        });

        let stdout = '';
        let stderr = '';
        let settled = false;
        let pollTimer = null;
        let timeoutTimer = null;

        if (child.stdout) {
            child.stdout.setEncoding('utf8');
            child.stdout.on('data', chunk => { stdout += chunk; });
        }
        if (child.stderr) {
            child.stderr.setEncoding('utf8');
            child.stderr.on('data', chunk => { stderr += chunk; });
        }

        function diagnostics(prefix) {
            return [
                prefix,
                `child pid: ${child.pid || '(none)'}`,
                `exit code: ${child.exitCode}`,
                'stdout:',
                stdout || '(empty)',
                'stderr:',
                stderr || '(empty)',
            ].join('\n');
        }

        function cleanupTimers() {
            if (pollTimer) clearInterval(pollTimer);
            if (timeoutTimer) clearTimeout(timeoutTimer);
        }

        function finishSuccess(smoke) {
            if (settled) return;
            settled = true;
            cleanupTimers();
            terminateProcessTree(child);
            resolve({ smoke, stdout, stderr });
        }

        function finishFailure(message) {
            if (settled) return;
            settled = true;
            cleanupTimers();
            terminateProcessTree(child);
            reject(new Error(diagnostics(message)));
        }

        function readMarker() {
            if (!fs.existsSync(marker)) return null;
            try {
                return JSON.parse(fs.readFileSync(marker, 'utf8'));
            } catch (_) {
                return null;
            }
        }

        pollTimer = setInterval(() => {
            const smoke = readMarker();
            if (smoke) finishSuccess(smoke);
        }, 50);

        timeoutTimer = setTimeout(() => {
            finishFailure(`native surface smoke did not produce a proof marker within ${timeoutMs}ms`);
        }, timeoutMs);

        child.once('error', error => {
            finishFailure(`native surface smoke process failed to start: ${error.message}`);
        });

        child.once('exit', (code, signal) => {
            const smoke = readMarker();
            if (smoke) {
                finishSuccess(smoke);
                return;
            }
            finishFailure(`native surface smoke exited before producing a proof marker (code=${code}, signal=${signal || 'none'})`);
        });
    });
}

test('real Electron host loads main, Database, Engine, and Tileset as separate BrowserWindows', {
    skip: process.platform !== 'win32',
    timeout: 120000,
}, async () => {
    const host = await ensureWindowsDevHost();
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-surface-smoke-'));
    const marker = path.join(dir, 'surfaces.json');
    try {
        const { smoke } = await startNativeSurfaceSmoke(host.hostPath, marker);
        assert.equal(fs.realpathSync(smoke.appPath), fs.realpathSync(REPO_ROOT));
        assert.equal(smoke.windows.length, 4,
            'Studio should own exactly main + Database + Engine + Tileset windows in this smoke');

        const urls = smoke.windows.map(window => window.url).sort();
        assert.ok(urls.some(url => /^http:\/\/127\.0\.0\.1:\d+\/?$/.test(url)),
            `main Studio URL missing from ${JSON.stringify(urls)}`);
        assert.ok(urls.some(url => /[?&]surface=database(?:&|$)/.test(url)),
            `Database surface URL missing from ${JSON.stringify(urls)}`);
        assert.ok(urls.some(url => /[?&]surface=engine(?:&|$)/.test(url)),
            `Engine surface URL missing from ${JSON.stringify(urls)}`);
        assert.ok(urls.some(url => /[?&]surface=tileset(?:&|$)/.test(url)),
            `Tileset surface URL missing from ${JSON.stringify(urls)}`);

        assert.ok(Array.isArray(smoke.readySurfaces) && smoke.readySurfaces.includes('database'),
            `Database renderer never completed the native surface-ready handshake: ${JSON.stringify(smoke.readySurfaces)}`);
        assert.ok(smoke.readySurfaces.includes('engine'),
            `Engine renderer never completed the native surface-ready handshake: ${JSON.stringify(smoke.readySurfaces)}`);
        assert.ok(smoke.readySurfaces.includes('tileset'),
            `Tileset renderer never completed the native surface-ready handshake: ${JSON.stringify(smoke.readySurfaces)}`);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});
