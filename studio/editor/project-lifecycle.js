'use strict';

// #479 / #392 / #699: one Project lifecycle boundary shared by Studio,
// generators, and agent/CLI workflows. A Project is the authored/runnable game
// root from #237/#299: data/ is required; assets/ is Project-owned when present.
// Installation/runtime/RTP/Studio roots are separate semantic inputs even while
// the current monorepo places them together.

const fs = require('fs');
const path = require('path');
const semanticRoots = require('../../tools/semantic-roots');
const template = require('./minimal-project-template');
const rtpBaseline = require('../../tools/export/rtp-baseline-resources');
const rtp = require('../../tools/export/rtp-resource-resolver');
const authoredDefaults = require('../../tools/export/authored-default-resolver');

const PROJECT_DIRS = ['data', 'assets'];
const SPARSE_REVISION = '1.0';
const DEFAULT_INSTALLATION = semanticRoots.resolveInstallationRoots();

// The lifecycle command surface is generic even though progression is the
// first single-file authored default we can safely Make Local end-to-end.
// Registries/fragmented resources need their own storage-aware materializers;
// add them here only when that ownership contract exists rather than copying
// files behind Studio's back.
const AUTHORED_DEFAULT_RESOLVERS = Object.freeze({
    progression({ projectRoot: root, systemValue, rtpRoot }) {
        return authoredDefaults.progression({ projectDir: root, systemValue, rtpRoot });
    },
});

function realOrResolved(value) {
    const resolved = path.resolve(value);
    try { return fs.realpathSync(resolved); } catch (_) { return resolved; }
}

function isInside(parent, candidate) {
    const base = path.resolve(parent);
    const target = path.resolve(candidate);
    return target === base || target.startsWith(base + path.sep);
}

function lifecycleInstallation(options = {}) {
    const input = {
        installRoot: options.installRoot || DEFAULT_INSTALLATION.installRoot,
        env: options.env || process.env,
    };
    if (options.runtimeRoot) input.runtimeRoot = options.runtimeRoot;
    if (options.rtpRoot) input.rtpRoot = options.rtpRoot;
    if (options.studioRoot) input.studioRoot = options.studioRoot;
    return semanticRoots.resolveInstallationRoots(input);
}

function assertProjectRoot(value, label = 'Project') {
    if (typeof value !== 'string' || !value.trim()) {
        throw new Error(`${label} path must be a non-empty string`);
    }
    const root = path.resolve(value);
    if (!fs.existsSync(root) || !fs.statSync(root).isDirectory()) {
        throw new Error(`${label} path is not a directory: ${root}`);
    }
    if (!semanticRoots.isProjectRoot(root)) {
        throw new Error(`${label} is not a Project: ${root} contains no data/ directory`);
    }
    return realOrResolved(root);
}

function assertNewTarget(value, options = {}) {
    if (typeof value !== 'string' || !value.trim()) {
        throw new Error('Project target must be a non-empty path');
    }
    const target = path.resolve(value);
    if (!fs.existsSync(target)) return target;

    if (options.allowExistingEmptyDirectory === true) {
        if (!fs.statSync(target).isDirectory()) {
            throw new Error(`Project target already exists and is not a directory: ${target}`);
        }
        if (fs.readdirSync(target).length === 0) return target;
        throw new Error(`Project target already exists and is not empty; refusing to overwrite it: ${target}`);
    }

    throw new Error(`Project target already exists; refusing to overwrite it: ${target}`);
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
    const installation = lifecycleInstallation(options);
    const dataPath = path.join(root, 'data');
    const assetsPath = path.join(root, 'assets');
    return {
        projectRoot: root,
        dataPath,
        assetsPath: fs.existsSync(assetsPath) && fs.statSync(assetsPath).isDirectory() ? assetsPath : null,
        installRoot: installation.installRoot,
        runtimeRoot: installation.runtimeRoot,
        rtpRoot: installation.rtpRoot,
        studioRoot: installation.studioRoot,
        sameAsInstall: realOrResolved(root) === realOrResolved(installation.installRoot),
    };
}

function authoredDefaultNames() {
    return Object.keys(AUTHORED_DEFAULT_RESOLVERS);
}

function resolveAuthoredDefault(options = {}) {
    const root = assertProjectRoot(options.project);
    const resolver = AUTHORED_DEFAULT_RESOLVERS[options.resource];
    if (!resolver) {
        const error = new Error(`Unsupported authored default '${options.resource}'. Supported: ${authoredDefaultNames().join(', ')}`);
        error.code = 'UNSUPPORTED_AUTHORED_DEFAULT';
        throw error;
    }
    const installation = lifecycleInstallation(options);
    const system = rtp.projectSystem(root);
    const resolved = resolver({
        projectRoot: root,
        systemValue: system.value,
        rtpRoot: installation.rtpRoot,
    });
    if (!resolved) {
        const error = new Error(`Project has no resolved authored default for '${options.resource}'`);
        error.code = 'AUTHORED_DEFAULT_UNRESOLVED';
        throw error;
    }
    return Object.assign({}, resolved, { projectRoot: root });
}

function authoredDefaultInfo(options = {}) {
    const resolved = resolveAuthoredDefault(options);
    return {
        projectRoot: resolved.projectRoot,
        resource: resolved.resource,
        logicalPath: resolved.logicalPath.replace(/\\/g, '/'),
        provider: resolved.provider.kind,
        providerId: resolved.provider.id,
        revision: resolved.provider.revision || null,
    };
}

function localAuthoredTarget(root, logicalPath) {
    const normalized = String(logicalPath || '').replace(/\\/g, '/');
    if (!normalized.startsWith('data/')) {
        throw new Error(`Authored default logical path must live under data/: ${normalized}`);
    }
    const target = path.resolve(root, ...normalized.split('/'));
    const dataRoot = path.resolve(root, 'data');
    if (!isInside(dataRoot, target) || target === dataRoot) {
        throw new Error(`Unsafe authored default logical path: ${normalized}`);
    }
    return target;
}

function makeAuthoredDefaultLocal(options = {}) {
    const resolved = resolveAuthoredDefault(options);
    if (resolved.provider.kind === 'project') {
        return Object.assign(authoredDefaultInfo(options), { madeLocal: false });
    }
    if (resolved.provider.kind !== 'rtp') {
        throw new Error(`Cannot Make Local authored default from provider '${resolved.provider.kind}'`);
    }

    const target = localAuthoredTarget(resolved.projectRoot, resolved.logicalPath);
    if (fs.existsSync(target)) {
        throw new Error(`Project-local authored default already exists: ${target}`);
    }
    fs.mkdirSync(path.dirname(target), { recursive: true });
    const partial = `${target}.thestra-partial-${process.pid}-${Date.now()}`;
    try {
        fs.writeFileSync(partial, JSON.stringify(resolved.value, null, 2) + '\n', 'utf8');
        fs.renameSync(partial, target);
    } catch (error) {
        fs.rmSync(partial, { force: true });
        throw error;
    }

    const local = resolveAuthoredDefault(options);
    if (local.provider.kind !== 'project' || realOrResolved(local.sourcePath) !== realOrResolved(target)) {
        fs.rmSync(target, { force: true });
        throw new Error(`Make Local did not resolve '${resolved.resource}' from the Project after materialization`);
    }
    return {
        projectRoot: local.projectRoot,
        resource: local.resource,
        logicalPath: local.logicalPath.replace(/\\/g, '/'),
        provider: local.provider.kind,
        providerId: local.provider.id,
        revision: null,
        madeLocal: true,
        inheritedFrom: resolved.provider.id,
        inheritedRevision: resolved.provider.revision || null,
    };
}

function sparseProjectAvailability(options = {}) {
    const installation = lifecycleInstallation(options);
    try {
        const manifest = rtpBaseline.readManifest({ revision: SPARSE_REVISION, rtpRoot: installation.rtpRoot });
        const authored = manifest && manifest.authored;
        const complete = authored
            && authored.engineRegistry
            && authored.progression
            && Object.keys(authored.sceneDefaults || {}).length > 0
            && Object.keys(authored.flowDefaults || {}).length > 0;
        if (!complete) {
            return {
                available: false,
                code: 'SPARSE_RTP_BASELINE_INCOMPLETE',
                revision: SPARSE_REVISION,
                reason: `Installed RTP revision ${SPARSE_REVISION} does not provide the authored engine/progression/Scene/Flow baseline required for New Project.`,
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

function createSparseProject(options = {}) {
    const targetRoot = assertNewTarget(options.target, { allowExistingEmptyDirectory: true });
    const targetExisted = fs.existsSync(targetRoot);
    const installation = lifecycleInstallation(options);
    const availability = sparseProjectAvailability(Object.assign({}, options, installation));
    if (!availability.available) {
        const error = new Error(availability.reason);
        error.code = availability.code;
        throw error;
    }

    fs.mkdirSync(path.dirname(targetRoot), { recursive: true });
    const tempRoot = `${targetRoot}.thestra-partial-${process.pid}-${Date.now()}`;
    try {
        fs.mkdirSync(tempRoot);
        writeTemplate(tempRoot, options.name || path.basename(targetRoot));
        if (!semanticRoots.isProjectRoot(tempRoot)) {
            throw new Error('Sparse materialization did not produce a valid Project data/ root');
        }
        if (targetExisted) {
            // Race-safe ownership handoff: only remove the folder the user chose
            // if it is still empty at the instant we are ready to publish the
            // fully materialized Project. rmdirSync fails rather than deleting
            // anything if another process placed content there meanwhile.
            fs.rmdirSync(targetRoot);
        }
        fs.renameSync(tempRoot, targetRoot);
    } catch (error) {
        fs.rmSync(tempRoot, { recursive: true, force: true });
        if (targetExisted && !fs.existsSync(targetRoot)) fs.mkdirSync(targetRoot);
        throw error;
    }

    return Object.assign(projectInfo(targetRoot, installation), {
        mode: 'sparse',
        rtpRevision: availability.revision,
    });
}

function forkProject(options = {}) {
    const sourceRoot = assertProjectRoot(options.source, 'Project fork source');
    const targetRoot = assertNewTarget(options.target);
    assertSafeForkPlacement(sourceRoot, targetRoot);
    const installation = lifecycleInstallation(options);

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

        if (!semanticRoots.isProjectRoot(tempRoot)) {
            throw new Error('Fork materialization did not produce a valid Project data/ root');
        }
        fs.renameSync(tempRoot, targetRoot);
    } catch (error) {
        fs.rmSync(tempRoot, { recursive: true, force: true });
        throw error;
    }

    return Object.assign(projectInfo(targetRoot, installation), {
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
    authoredDefaultInfo,
    authoredDefaultNames,
    createProject,
    createSparseProject,
    forkProject,
    isInside,
    lifecycleInstallation,
    makeAuthoredDefaultLocal,
    projectInfo,
    resolveAuthoredDefault,
    sparseProjectAvailability,
};
