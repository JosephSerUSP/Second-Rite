'use strict';

// #247: LÖVE 11.5 cannot mount an arbitrary external project directory, so
// Studio previews/Test Play run a short-lived exporter staging tree instead.
// The exporter remains the one authority for what constitutes a runnable game.
const childProcess = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const exporter = require('../export/export-game');

function stageProject({ installRoot, projectRoot, campaign = '', manifestPath }) {
    if (!installRoot || !projectRoot) throw new Error('stageProject requires installRoot and projectRoot');
    const stageDir = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-studio-play-'));
    try {
        exporter.stageGame({
            runtimeDir: installRoot,
            projectDir: projectRoot,
            outputDir: stageDir,
            campaign: campaign || '',
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

// Launches any command against the project Studio actually has open. The
// ordinary checkout case deliberately remains direct: when project and install
// are the same tree, staging would only add a full asset copy to every preview
// while changing nothing about what LÖVE can see. External projects use #221's
// staging boundary. `projectArg` is `.` for LÖVE, but injectable so CI can use
// Node itself to prove which cwd was played.
function execStaged({
    executable,
    installRoot,
    projectRoot,
    campaign = '',
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
    const stageDir = direct ? null : stageProject({ installRoot, projectRoot, campaign, manifestPath });
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
