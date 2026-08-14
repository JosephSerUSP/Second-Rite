'use strict';

const childProcess = require('child_process');
const path = require('path');
const { ensureWindowsDevHost } = require('./windows-dev-host');
const lifecycle = require('./project-lifecycle');
const { PROJECT_ENV } = require('./project-root');

const REPO_ROOT = path.resolve(__dirname, '..', '..');

function parseLaunchArgs(argv) {
    const passthrough = [];
    let project = null;
    for (let i = 0; i < argv.length; i++) {
        const arg = argv[i];
        if (arg === '--project') {
            if (i + 1 >= argv.length) throw new Error('--project requires a path');
            project = argv[++i];
            continue;
        }
        if (arg.startsWith('--project=')) {
            project = arg.slice('--project='.length);
            if (!project) throw new Error('--project requires a path');
            continue;
        }
        passthrough.push(arg);
    }
    return { project, passthrough };
}

async function main(argv = process.argv.slice(2)) {
    const launch = parseLaunchArgs(argv);
    const env = Object.assign({}, process.env);
    if (launch.project) {
        const info = lifecycle.projectInfo(path.resolve(launch.project));
        env[PROJECT_ENV] = info.projectRoot;
    }

    let executable;
    if (process.platform === 'win32') {
        executable = (await ensureWindowsDevHost()).hostPath;
    } else {
        executable = require('electron');
    }

    const child = childProcess.spawn(executable, [REPO_ROOT, ...launch.passthrough], {
        cwd: REPO_ROOT,
        env,
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

module.exports = { main, parseLaunchArgs };
