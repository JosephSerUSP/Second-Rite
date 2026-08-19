'use strict';

// #247/#299/#667/#701: external Projects run from a short-lived compiled player
// staging tree. Runtime, installation, RTP and Project roots are explicit; a
// direct/no-copy path exists only when the runtime root itself is the Project.
const childProcess = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const semanticRoots = require('../semantic-roots');
const exporter = require('../export/export-game');
const runtimeDataSnapshot = require('../export/runtime-data-snapshot');

function installationRoots({ installRoot, runtimeRoot, rtpRoot }) {
    return semanticRoots.resolveInstallationRoots({
        installRoot,
        runtimeRoot,
        rtpRoot,
        env: {},
    });
}

function stageProject({ installRoot, projectRoot, runtimeRoot, rtpRoot, manifestPath }) {
    if (!installRoot || !projectRoot) throw new Error('stageProject requires installRoot and projectRoot');
    const roots = installationRoots({ installRoot, runtimeRoot, rtpRoot });
    const stageDir = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-studio-play-'));
    try {
        exporter.stageRuntimeGame({
            installRoot: roots.installRoot,
            runtimeDir: roots.runtimeRoot,
            rtpRoot: roots.rtpRoot,
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

function snapshotSameRoot({ installRoot, runtimeRoot, projectRoot }) {
    const roots = installationRoots({ installRoot, runtimeRoot });
    return runtimeDataSnapshot.createRuntimeDataSnapshot({
        runtimeDir: roots.runtimeRoot,
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
// Same runtime/Project root: direct runtime/assets + ignored data-only snapshot.
function execStaged({
    executable,
    installRoot,
    runtimeRoot,
    rtpRoot,
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

    const roots = installationRoots({ installRoot, runtimeRoot, rtpRoot });
    const direct = sameRoot(roots.runtimeRoot, projectRoot);
    let stageDir = null;
    let snapshot = null;
    try {
        if (direct) {
            snapshot = snapshotSameRoot({
                installRoot: roots.installRoot,
                runtimeRoot: roots.runtimeRoot,
                projectRoot,
            });
        } else {
            stageDir = stageProject({
                installRoot: roots.installRoot,
                runtimeRoot: roots.runtimeRoot,
                rtpRoot: roots.rtpRoot,
                projectRoot,
                manifestPath,
            });
        }
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
    return {
        child,
        stageDir,
        direct,
        runtimeRoot: roots.runtimeRoot,
        runtimeDataSnapshot: snapshot,
    };
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
