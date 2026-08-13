'use strict';

// #237: the two roots Thestra Studio works from, and the only place either is
// resolved.
//
//   install root   Studio/runtime ownership: tools/, engine/presentation code,
//                  native/runtime support, dist/screenshots, and main.lua.
//   project root   the opened authored game: data/ plus Project-owned assets.
//
// A Project is the one authored/runnable game boundary. There is no nested
// alternate active-content root inside a Project. Routes, stories and chapters
// belong to ordinary authored data; alternate games are separate Projects.
//
// The roots remain separate because #237/#358 deliberately allow Studio to run
// installed runtime code with an arbitrary external Project's authored data.

const fs = require('fs');
const path = require('path');

const INSTALL_ROOT = path.resolve(__dirname, '..', '..');
const PROJECT_ENV = 'SECOND_RITE_PROJECT';

// Keep the minimum Project contract deliberately thin: authored data is what
// makes a directory a Project. Requiring manifests/version files here would
// invent a larger Project format before the architecture needs one.
function isProjectRoot(dir) {
    try {
        return fs.statSync(path.join(dir, 'data')).isDirectory();
    } catch (e) {
        return false;
    }
}

// Resolved once at require time. A bad SECOND_RITE_PROJECT fails here, at
// boot, naming the path and the reason rather than degrading into an editor
// that silently reads checkout data.
function resolveProjectRoot(configured = process.env[PROJECT_ENV]) {
    if (!configured) return INSTALL_ROOT;
    const root = path.resolve(configured);
    if (!fs.existsSync(root)) {
        throw new Error(`${PROJECT_ENV} points at a path that does not exist: ${root}`);
    }
    if (!isProjectRoot(root)) {
        throw new Error(`${PROJECT_ENV} is not a project: ${root} contains no data/ directory`);
    }
    return root;
}

const PROJECT_ROOT = resolveProjectRoot();

// Joins under a root and REFUSES anything that leaves it, rather than
// mangling the path into something that happens to stay inside. Reject both
// native and Windows-style absolute segments so the invariant is testable on
// every host platform rather than depending on the runner's path flavor.
function resolveWithin(root, ...segments) {
    const base = path.resolve(root);
    for (const segment of segments) {
        if (path.isAbsolute(segment) || path.win32.isAbsolute(segment)) {
            throw new Error(`refusing a path outside ${base}: ${path.join(...segments)}`);
        }
    }
    const target = path.resolve(base, ...segments);
    if (target !== base && !target.startsWith(base + path.sep)) {
        throw new Error(`refusing a path outside ${base}: ${path.join(...segments)}`);
    }
    return target;
}

const inProject = (...segments) => resolveWithin(PROJECT_ROOT, ...segments);
const inInstall = (...segments) => resolveWithin(INSTALL_ROOT, ...segments);

module.exports = {
    INSTALL_ROOT,
    PROJECT_ROOT,
    PROJECT_ENV,
    inProject,
    inInstall,
    isProjectRoot,
    resolveProjectRoot,
    resolveWithin,
};
