'use strict';

// #247/#299/#667: external Projects run from a short-lived compiled player
// staging tree. Same-root development keeps engine/assets direct for iteration
// speed, but now points the subprocess at a data-only resolved/compiled snapshot
// so both paths consume the same semantic Project data boundary.
const childProcess = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const exporter = require('../export/export-game');
const runtimeDataSnapshot = require('../export/runtime-data-snapshot');

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

function snapshotSameRoot({ installRoot, projectRoot }) {
    return runtimeDataSnapshot.createRuntimeDataSnapshot({
        runtimeDir: installRoot,
        projectDir: projectRoot,
    });
}

function cleanupLaunch(stageDir, snapshot) {
    removeStage(stageDir);
    runtimeDataSnapshot.removeRuntimeDataSnapshot(snapshot);
}

function launchEnvironment(extra, snapshot) {
    const env = Object.assign({}, process.env, extra || {});
    // This process boundary is host-owned. A stale shell variable must never
    // redirect an external compiled stage, and callers cannot override the
    // exact snapshot selected for a same-root launch.
    delete env[runtimeDataSnapshot.RUNTIME_DATA_ENV];
    if (snapshot) Object.assign(env, snapshot.env);
    return env;
}

// Launches any command against the Project Studio actually has open.
//
// External Project: full compiled player stage (runtime + assets + data).
// Same-root Project: direct runtime/assets + ignored data-only compiled snapshot.
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
    env,
}, callback) {
    if (!executable) throw new Error('execStaged requires executable');
    if (!installRoot || !projectRoot) throw new Error('execStaged requires installRoot and projectRoot');
    if (!Array.isArray(args)) throw new Error('execStaged args must be an array');

    const direct = sameRoot(installRoot, projectRoot);
    let stageDir = null;
    let snapshot = null;
    try {
        if (direct) snapshot = snapshotSameRoot({ installRoot, projectRoot });
        else stageDir = stageProject({ installRoot, projectRoot, manifestPath });
    } catch (error) {
        cleanupLaunch(stageDir, snapshot);
        throw error;
    }

    const cwd = stageDir || projectRoot;
    const childEnv = launchEnvironment(env, snapshot);
    let child;
    try {
        child = childProcess.execFile(executable, [projectArg, ...args], {
            cwd,
            env: childEnv,
            windowsHide,
            ...(timeout === undefined ? {} : { timeout }),
            ...(maxBuffer === undefined ? {} : { maxBuffer }),
        }, (error, stdout, stderr) => {
            cleanupLaunch(stageDir, snapshot);
            if (callback) callback(error, stdout, stderr);
        });
    } catch (error) {
        cleanupLaunch(stageDir, snapshot);
        throw error;
    }
    return { child, stageDir, direct, runtimeDataSnapshot: snapshot };
}

module.exports = {
    cleanupLaunch,
    execStaged,
    launchEnvironment,
    removeStage,
    sameRoot,
    snapshotSameRoot,
    stageProject,
};
