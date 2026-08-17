'use strict';

const childProcess = require('child_process');
const path = require('path');
const projectPlay = require('../editor/project-play');

const REPO = path.resolve(__dirname, '..', '..');
const LOVEC = 'C:\\Program Files\\LOVE\\lovec.exe';
const CANDIDATES = ['candidate-a', 'candidate-b', 'candidate-c'];

function validateProject(candidateName) {
    const projectRoot = path.join(REPO, 'projects', 'experiments', 'gauntlet-unidentified-gear', candidateName);
    console.log(`\n========================================`);
    console.log(`Validating ${candidateName}...`);
    console.log(`========================================`);
    const stageDir = projectPlay.stageProject({ installRoot: REPO, projectRoot });
    try {
        const result = childProcess.spawnSync(LOVEC, [stageDir, 'validate'], {
            encoding: 'utf8',
            timeout: 30000
        });
        const out = (result.stdout || '') + (result.stderr || '');
        console.log(out);
        if (result.status !== 0 || !out.includes('VALIDATE OK')) {
            throw new Error(`Validation failed for ${candidateName} (exit ${result.status})`);
        }
        console.log(`>>> ${candidateName}: VALIDATE OK`);
        return true;
    } finally {
        projectPlay.removeStage(stageDir);
    }
}

function main() {
    let allPassed = true;
    for (const name of CANDIDATES) {
        try {
            validateProject(name);
        } catch (err) {
            console.error(`ERROR: ${err.message}`);
            allPassed = false;
        }
    }
    if (!allPassed) {
        process.exit(1);
    }
    console.log(`\nAll gauntlet candidates passed validation!`);
}

if (require.main === module) {
    main();
}

module.exports = { validateProject };
