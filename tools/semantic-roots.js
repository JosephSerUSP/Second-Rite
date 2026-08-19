'use strict';

// #699/#700/#701: one neutral authority for what repository/install, runtime,
// RTP, Studio, and Project roots *mean*. They are distinct semantic inputs; the
// current developer-facing Second Gate Project is an explicit policy path under
// projects/, and the reusable Thestra runtime is physically owned by runtime/.
const fs = require('fs');
const path = require('path');

const DEFAULT_INSTALL_ROOT = path.resolve(__dirname, '..');
const DEFAULT_RUNTIME_ROOT = path.join(DEFAULT_INSTALL_ROOT, 'runtime');
const DEFAULT_RTP_ROOT = path.join(DEFAULT_INSTALL_ROOT, 'rtp');
const DEFAULT_PROJECT_ROOT = path.join(DEFAULT_INSTALL_ROOT, 'projects', 'hichaukitoden-game');
const PROJECT_ENV = 'SECOND_RITE_PROJECT';
const RUNTIME_ROOT_ENV = 'THESTRA_RUNTIME_ROOT';
const RTP_ROOT_ENV = 'THESTRA_RTP_ROOT';
const STUDIO_ROOT_ENV = 'THESTRA_STUDIO_ROOT';

function isProjectRoot(dir) {
    if (!dir) return false;
    try {
        return fs.statSync(path.join(path.resolve(dir), 'data')).isDirectory();
    } catch (error) {
        return false;
    }
}

function assertProjectRoot(value, label = 'Project') {
    if (typeof value !== 'string' || !value.trim()) {
        throw new Error(`${label} path must be a non-empty string`);
    }
    const root = path.resolve(value);
    if (!fs.existsSync(root)) {
        throw new Error(`${label} points at a path that does not exist: ${root}`);
    }
    if (!isProjectRoot(root)) {
        throw new Error(`${label} is not a project: ${root} contains no data/ directory`);
    }
    return root;
}

function assertRuntimeRoot(value, label = 'runtime root') {
    if (typeof value !== 'string' || !value.trim()) {
        throw new Error(`${label} path must be a non-empty string`);
    }
    const root = path.resolve(value);
    if (!fs.existsSync(path.join(root, 'main.lua'))
            || !fs.existsSync(path.join(root, 'engine'))
            || !fs.existsSync(path.join(root, 'presentation'))) {
        throw new Error(`${label} is not a Thestra runtime root: ${root}`);
    }
    return root;
}

function resolveProjectRoot(configured, { defaultProjectRoot = DEFAULT_PROJECT_ROOT } = {}) {
    if (!configured) return assertProjectRoot(path.resolve(defaultProjectRoot), 'default Project root');
    return assertProjectRoot(configured, PROJECT_ENV);
}

function resolveWithin(root, ...segments) {
    const base = path.resolve(root);
    const target = path.resolve(base, ...segments);
    if (target !== base && !target.startsWith(base + path.sep)) {
        throw new Error(`refusing a path outside ${base}: ${path.join(...segments)}`);
    }
    return target;
}

function resolveInstallationRoots(options = {}) {
    const env = options.env || process.env;
    const installRoot = path.resolve(options.installRoot || DEFAULT_INSTALL_ROOT);
    const defaultRuntimeRoot = path.join(installRoot, 'runtime');
    const defaultRtpRoot = path.join(installRoot, 'rtp');
    const runtimeRoot = path.resolve(options.runtimeRoot || env[RUNTIME_ROOT_ENV] || defaultRuntimeRoot);
    const rtpRoot = path.resolve(options.rtpRoot || env[RTP_ROOT_ENV] || defaultRtpRoot);
    const studioRoot = path.resolve(options.studioRoot || env[STUDIO_ROOT_ENV] || installRoot);
    return Object.freeze({ installRoot, runtimeRoot, rtpRoot, studioRoot });
}

function resolveSemanticRoots(options = {}) {
    const env = options.env || process.env;
    const installation = resolveInstallationRoots(options);
    const configuredProject = options.projectRoot === undefined ? env[PROJECT_ENV] : options.projectRoot;
    const projectRoot = resolveProjectRoot(configuredProject, {
        defaultProjectRoot: options.defaultProjectRoot || DEFAULT_PROJECT_ROOT,
    });

    return Object.freeze({
        ...installation,
        projectRoot,
        projectDataRoot: path.join(projectRoot, 'data'),
        projectAssetsRoot: path.join(projectRoot, 'assets'),
    });
}

module.exports = {
    DEFAULT_INSTALL_ROOT,
    DEFAULT_PROJECT_ROOT,
    DEFAULT_RTP_ROOT,
    DEFAULT_RUNTIME_ROOT,
    PROJECT_ENV,
    RTP_ROOT_ENV,
    RUNTIME_ROOT_ENV,
    STUDIO_ROOT_ENV,
    assertProjectRoot,
    assertRuntimeRoot,
    isProjectRoot,
    resolveInstallationRoots,
    resolveProjectRoot,
    resolveSemanticRoots,
    resolveWithin,
};
