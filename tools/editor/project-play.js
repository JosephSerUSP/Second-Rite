'use strict';

// #247/#299/#667: LÖVE 11.5 cannot mount an arbitrary external Project
// directory, so Studio previews/Test Play run a short-lived player staging
// tree. The exporter owns both boundaries: installed runtime + opened Project
// resolution, followed by Candidate A+ semantic runtime-data compilation.
const childProcess = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const exporter = require('../export/export-game');

function stageProject({ installRoot, projectRoot, manifestPath }) {
    if (!installRoot || !projectRoot) throw new Error('stageProject requires installRoot and projectRoot');
    const stageDir = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-studio-play-'));
    try {
        exporter.stageRuntimeGame({
            runtimeDir: installRoot,
            projectDir: projectRoot,
            outputDir: stageDir,
            ...(manifestPath ? { manifestPath } : {}),
        });
        return stageDir;
    } catch (error) {
        fs.rmSync(stageDir, { recursive: true, force: true });
        throw error;
    }
}

function removeStage(stageDir) {
    if (!stageDir) return;
    try {
        fs.rmSync(stageDir, { recursive: true, force: true });
    } catch (error) {
        console.warn(`[project-play] could not remove staged project ${stageDir}: ${error.message}`);
    }
}

function sameRoot(left, right) {
    return fs.realpathSync(left) === fs.realpathSync(right);
}

// Launches any command against the Project Studio actually has open. External
// Projects use the compiled player boundary above. The ordinary checkout case
// deliberately remains direct for now: a full asset copy on every preview
// would regress authoring latency. #667's next slice will give same-root Test
// Play the same semantic compiler without paying that copy cost.
function execStaged({
    executable,
    installRoot,
    projectRoot,
    args = [],
    projectArg = '.',
    manifestPath,
    timeout,
    maxBuffer,
    windowsHide = true,
}, callback) {
    if (!executable) throw new Error('execStaged requires executable');
    if (!installRoot || !projectRoot) throw new Error('execStaged requires installRoot and projectRoot');
    if (!Array.isArray(args)) throw new Error('execStaged args must be an array');

    const direct = sameRoot(installRoot, projectRoot);
    const stageDir = direct ? null : stageProject({ installRoot, projectRoot, manifestPath });
    const cwd = stageDir || projectRoot;
    let child;
    try {
        child = childProcess.execFile(executable, [projectArg, ...args], {
            cwd,
            windowsHide,
            ...(timeout === undefined ? {} : { timeout }),
            ...(maxBuffer === undefined ? {} : { maxBuffer }),
        }, (error, stdout, stderr) => {
            removeStage(stageDir);
            if (callback) callback(error, stdout, stderr);
        });
    } catch (error) {
        removeStage(stageDir);
        throw error;
    }
    return { child, stageDir, direct };
}

module.exports = { execStaged, removeStage, sameRoot, stageProject };
