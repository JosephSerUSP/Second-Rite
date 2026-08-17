'use strict';

const fs = require('fs');
const path = require('path');
const childProcess = require('child_process');
const projectPlay = require('../editor/project-play');

function resolveLoveExecutable() {
    if (process.env.LOVEC) return process.env.LOVEC;
    if (process.env.LOVE_PATH) return process.env.LOVE_PATH;
    return process.platform === 'win32' ? 'C:\\Program Files\\LOVE\\lovec.exe' : 'lovec';
}

function runLove(stageDir, args, timeoutMs = 30000) {
    const lovec = resolveLoveExecutable();
    const result = childProcess.spawnSync(lovec, ['.', ...args], {
        cwd: stageDir,
        timeout: timeoutMs,
        encoding: 'utf8',
        env: Object.assign({}, process.env, { THESTRA_CI_FAIL_ON_ERROR: '1' }),
    });
    return result;
}

function main() {
    const targetProject = process.argv[2] || 'projects/labs/pale-crossing';
    const projectRoot = path.resolve(targetProject);
    const installRoot = process.cwd();

    console.log(`Staging ${projectRoot}...`);
    const stageDir = projectPlay.stageProject({ installRoot, projectRoot });
    console.log(`Staged at ${stageDir}`);

    try {
        console.log(`Running validate on ${stageDir}...`);
        const valRes = runLove(stageDir, ['validate'], 30000);
        console.log(valRes.stdout || '');
        if (valRes.stderr) console.error(valRes.stderr);
        if (valRes.status !== 0 || !(valRes.stdout || '').includes('VALIDATE OK')) {
            console.error(`Validation FAILED for ${targetProject} (exit ${valRes.status})`);
            process.exit(1);
        }
        console.log(`VALIDATE OK for ${targetProject}`);
    } finally {
        projectPlay.removeStage(stageDir);
    }
}

if (require.main === module) {
    main();
}
