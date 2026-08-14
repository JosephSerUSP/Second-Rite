'use strict';

// #479 / #392: one Project lifecycle boundary shared by Studio, generators,
// and agent/CLI workflows. A Project is the authored/runnable game root from
// #237/#299: data/ is required; assets/ is Project-owned when present.
//
// This module deliberately distinguishes an explicit Project FORK from a truly
// NEW/sparse Project. Current main still lacks the neutral inherited
// engine/Scene/Flow baseline owned by #390, so callers must never silently use
// Second Gate as a blank-project fallback.

const fs = require('fs');
const path = require('path');
const projectRoot = require('./project-root');

const PROJECT_DIRS = ['data', 'assets'];
const SPARSE_UNAVAILABLE = 'SPARSE_PROJECT_UNAVAILABLE';

function realOrResolved(value) {
    const resolved = path.resolve(value);
    try { return fs.realpathSync(resolved); } catch (_) { return resolved; }
}

function isInside(parent, candidate) {
    const base = path.resolve(parent);
    const target = path.resolve(candidate);
    return target === base || target.startsWith(base + path.sep);
}

function assertProjectRoot(value, label = 'Project') {
    if (typeof value !== 'string' || !value.trim()) {
        throw new Error(`${label} path must be a non-empty string`);
    }
    const root = path.resolve(value);
    if (!fs.existsSync(root) || !fs.statSync(root).isDirectory()) {
        throw new Error(`${label} path is not a directory: ${root}`);
    }
    if (!projectRoot.isProjectRoot(root)) {
        throw new Error(`${label} is not a Project: ${root} contains no data/ directory`);
    }
    return realOrResolved(root);
}

function assertNewTarget(value) {
    if (typeof value !== 'string' || !value.trim()) {
        throw new Error('Project target must be a non-empty path');
    }
    const target = path.resolve(value);
    if (fs.existsSync(target)) {
        throw new Error(`Project target already exists; refusing to overwrite it: ${target}`);
    }
    return target;
}

function assertSafeForkPlacement(sourceRoot, targetRoot) {
    if (realOrResolved(sourceRoot) === realOrResolved(targetRoot)) {
        throw new Error('Project fork source and target must be different directories');
    }

    // Fork copies only data/ and assets/. A target elsewhere under the same
    // monorepo is safe (projects/labs/foo is an important agent workflow), but
    // placing the target inside either copied tree can recursively copy into
    // itself while fs.cpSync is walking it.
    for (const ownedDir of PROJECT_DIRS) {
        const sourceDir = path.join(sourceRoot, ownedDir);
        if (fs.existsSync(sourceDir) && isInside(sourceDir, targetRoot)) {
            throw new Error(`Project target may not live inside source ${ownedDir}/: ${targetRoot}`);
        }
    }
}

function projectInfo(value, options = {}) {
    const root = assertProjectRoot(value);
    const installRoot = path.resolve(options.installRoot || projectRoot.INSTALL_ROOT);
    const dataPath = path.join(root, 'data');
    const assetsPath = path.join(root, 'assets');
    return {
        projectRoot: root,
        dataPath,
        assetsPath: fs.existsSync(assetsPath) && fs.statSync(assetsPath).isDirectory() ? assetsPath : null,
        installRoot,
        sameAsInstall: realOrResolved(root) === realOrResolved(installRoot),
    };
}

function sparseProjectAvailability() {
    return {
        available: false,
        code: SPARSE_UNAVAILABLE,
        reason: 'Neutral inherited engine/Scene/Flow authored defaults are not on current main yet; #390 owns that baseline. Fork Project is available now without pretending Second Gate is blank.',
    };
}

function createSparseProject() {
    const availability = sparseProjectAvailability();
    const error = new Error(availability.reason);
    error.code = availability.code;
    throw error;
}

function forkProject({ source, target, installRoot } = {}) {
    const sourceRoot = assertProjectRoot(source, 'Project fork source');
    const targetRoot = assertNewTarget(target);
    assertSafeForkPlacement(sourceRoot, targetRoot);

    // Build in a temporary sibling so an interrupted copy never leaves a path
    // that Studio could mistake for a completed Project. Explicit targets may
    // create their parent path (important for one-command agent workflows such
    // as projects/labs/foo), but the target itself is never overwritten.
    fs.mkdirSync(path.dirname(targetRoot), { recursive: true });
    const tempRoot = `${targetRoot}.thestra-partial-${process.pid}-${Date.now()}`;
    if (fs.existsSync(tempRoot)) fs.rmSync(tempRoot, { recursive: true, force: true });

    try {
        fs.mkdirSync(tempRoot);
        const sourceData = path.join(sourceRoot, 'data');
        fs.cpSync(sourceData, path.join(tempRoot, 'data'), {
            recursive: true,
            force: false,
            errorOnExist: true,
        });

        const sourceAssets = path.join(sourceRoot, 'assets');
        if (fs.existsSync(sourceAssets) && fs.statSync(sourceAssets).isDirectory()) {
            fs.cpSync(sourceAssets, path.join(tempRoot, 'assets'), {
                recursive: true,
                force: false,
                errorOnExist: true,
            });
        }

        if (!projectRoot.isProjectRoot(tempRoot)) {
            throw new Error('Fork materialization did not produce a valid Project data/ root');
        }
        fs.renameSync(tempRoot, targetRoot);
    } catch (error) {
        fs.rmSync(tempRoot, { recursive: true, force: true });
        throw error;
    }

    return Object.assign(projectInfo(targetRoot, { installRoot }), {
        mode: 'fork',
        sourceProjectRoot: sourceRoot,
    });
}

function createProject(options = {}) {
    const mode = options.mode || 'sparse';
    if (mode === 'fork') return forkProject(options);
    if (mode === 'sparse') return createSparseProject(options);
    throw new Error(`Unknown Project creation mode: ${mode}`);
}

module.exports = {
    PROJECT_DIRS,
    SPARSE_UNAVAILABLE,
    assertNewTarget,
    assertProjectRoot,
    assertSafeForkPlacement,
    createProject,
    createSparseProject,
    forkProject,
    isInside,
    projectInfo,
    sparseProjectAvailability,
};
