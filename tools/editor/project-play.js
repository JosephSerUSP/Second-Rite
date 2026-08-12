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

// Launches any command with cwd pointed at the staged game. `projectArg` is
// `.` for LÖVE, but is injectable so the filesystem contract can be tested
// with Node itself on every CI platform. Cleanup happens only after the child
// exits, so an interactive Test Play keeps its stage for its whole lifetime.
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
    if (!Array.isArray(args)) throw new Error('execStaged args must be an array');
    const stageDir = stageProject({ installRoot, projectRoot, campaign, manifestPath });
    let child;
    try {
        child = childProcess.execFile(executable, [projectArg, ...args], {
            cwd: stageDir,
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
    return { child, stageDir };
}

module.exports = { execStaged, removeStage, stageProject };
