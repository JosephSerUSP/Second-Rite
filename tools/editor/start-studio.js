'use strict';

const childProcess = require('child_process');
const path = require('path');
const { ensureWindowsDevHost } = require('./windows-dev-host');

const REPO_ROOT = path.resolve(__dirname, '..', '..');

async function main(argv = process.argv.slice(2)) {
    let executable;
    if (process.platform === 'win32') {
        executable = (await ensureWindowsDevHost()).hostPath;
    } else {
        executable = require('electron');
    }

    const child = childProcess.spawn(executable, [REPO_ROOT, ...argv], {
        cwd: REPO_ROOT,
        env: process.env,
        stdio: 'inherit',
        windowsHide: false,
    });
    child.on('error', error => {
        console.error(`Could not start Thestra Studio: ${error.message}`);
        process.exitCode = 1;
    });
    child.on('exit', (code, signal) => {
        if (signal) {
            console.error(`Thestra Studio exited after signal ${signal}`);
            process.exitCode = 1;
            return;
        }
        process.exitCode = code === null ? 1 : code;
    });
}

if (require.main === module) {
    main().catch(error => {
        console.error(error && error.stack ? error.stack : error);
        process.exitCode = 1;
    });
}

module.exports = { main };
