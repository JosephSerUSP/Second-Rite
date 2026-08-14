'use strict';

// #479 / #392: one Project lifecycle boundary shared by Studio, generators,
// and agent/CLI workflows. A Project is the authored/runnable game root from
// #237/#299: data/ is required; assets/ is Project-owned when present.

const fs = require('fs');
const path = require('path');
const projectRoot = require('./project-root');
const template = require('./minimal-project-template');
const rtpBaseline = require('../export/rtp-baseline-resources');

const PROJECT_DIRS = ['data', 'assets'];
const SPARSE_REVISION = '1.0';

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

function sparseProjectAvailability(options = {}) {
    const installRoot = path.resolve(options.installRoot || projectRoot.INSTALL_ROOT);
    const rtpRoot = path.join(installRoot, 'rtp');
    try {
        const manifest = rtpBaseline.readManifest({ revision: SPARSE_REVISION, rtpRoot });
        const authored = manifest && manifest.authored;
        const complete = authored
            && authored.engineRegistry
            && Object.keys(authored.sceneDefaults || {}).length > 0
            && Object.keys(authored.flowDefaults || {}).length > 0;
        if (!complete) {
            return {
                available: false,
                code: 'SPARSE_RTP_BASELINE_INCOMPLETE',
                revision: SPARSE_REVISION,
                reason: `Installed RTP revision ${SPARSE_REVISION} does not provide the authored engine/Scene/Flow baseline required for New Project.`,
            };
        }
        return { available: true, revision: SPARSE_REVISION, reason: null };
    } catch (error) {
        return {
            available: false,
            code: 'SPARSE_RTP_BASELINE_UNAVAILABLE',
            revision: SPARSE_REVISION,
            reason: error.message,
        };
    }
}

function writeTemplate(tempRoot, projectName) {
    for (const [relative, value] of template.files(projectName)) {
        const target = path.join(tempRoot, ...relative.split('/'));
        fs.mkdirSync(path.dirname(target), { recursive: true });
        fs.writeFileSync(target, JSON.stringify(value, null, 2) + '\n', 'utf8');
    }
    fs.mkdirSync(path.join(tempRoot, 'assets'), { recursive: true });
}

function createSparseProject({ target, installRoot, name } = {}) {
    const targetRoot = assertNewTarget(target);
    const install = path.resolve(installRoot || projectRoot.INSTALL_ROOT);
    const availability = sparseProjectAvailability({ installRoot: install });
    if (!availability.available) {
        const error = new Error(availability.reason);
        error.code = availability.code;
        throw error;
    }

    fs.mkdirSync(path.dirname(targetRoot), { recursive: true });
    const tempRoot = `${targetRoot}.thestra-partial-${process.pid}-${Date.now()}`;
    try {
        fs.mkdirSync(tempRoot);
        writeTemplate(tempRoot, name || path.basename(targetRoot));
        if (!projectRoot.isProjectRoot(tempRoot)) {
            throw new Error('Sparse materialization did not produce a valid Project data/ root');
        }
        fs.renameSync(tempRoot, targetRoot);
    } catch (error) {
        fs.rmSync(tempRoot, { recursive: true, force: true });
        throw error;
    }

    return Object.assign(projectInfo(targetRoot, { installRoot: install }), {
        mode: 'sparse',
        rtpRevision: availability.revision,
    });
}

function forkProject({ source, target, installRoot } = {}) {
    const sourceRoot = assertProjectRoot(source, 'Project fork source');
    const targetRoot = assertNewTarget(target);
    assertSafeForkPlacement(sourceRoot, targetRoot);

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
    SPARSE_REVISION,
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
