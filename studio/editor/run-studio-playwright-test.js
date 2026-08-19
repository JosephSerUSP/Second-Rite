'use strict';

const childProcess = require('node:child_process');
const path = require('node:path');

const REPO_ROOT = path.resolve(__dirname, '..', '..');
const TEST_FILE = path.join('tools', 'editor', 'test-studio-playwright.js');
const WATCHDOG_MS = 100000;

function terminateProcessTree(child) {
    if (!child || !child.pid || child.exitCode !== null) return;
    if (process.platform === 'win32') {
        childProcess.spawnSync('taskkill.exe', ['/PID', String(child.pid), '/T', '/F'], {
            windowsHide: true,
            stdio: 'ignore',
            timeout: 10000,
        });
        return;
    }
    try { child.kill('SIGKILL'); } catch (_) {}
}

const child = childProcess.spawn(process.execPath, ['--test', TEST_FILE], {
    cwd: REPO_ROOT,
    env: process.env,
    stdio: 'inherit',
    windowsHide: true,
});

let finished = false;
const watchdog = setTimeout(() => {
    if (finished) return;
    console.error(`[studio-playwright] watchdog exceeded ${WATCHDOG_MS}ms; terminating the Node/Electron process tree`);
    terminateProcessTree(child);
}, WATCHDOG_MS);

child.once('error', error => {
    if (finished) return;
    finished = true;
    clearTimeout(watchdog);
    console.error('[studio-playwright] could not start behavioral test:', error);
    process.exitCode = 1;
});

child.once('exit', (code, signal) => {
    if (finished) return;
    finished = true;
    clearTimeout(watchdog);
    if (signal) {
        console.error(`[studio-playwright] behavioral test terminated by ${signal}`);
        process.exitCode = 1;
        return;
    }
    process.exitCode = code === null ? 1 : code;
});
