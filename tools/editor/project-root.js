'use strict';

// #237: the two roots the Developer Studio works from, and the only place
// either is resolved.
//
//   install root   the editor and engine: tools/, the native shim, the dist/
//                  and screenshots/ output roots, and the directory holding
//                  main.lua that LOVE must run from.
//   project root   the opened project: data/, campaigns/, assets/, and the
//                  local campaign.json pointer.
//
// They are separate because collapsing them is what tied the editor to being
// located inside the Second Rite checkout. The project root is configurable;
// the install root is a property of where this file lives and never moves.

const fs = require('fs');
const path = require('path');

const INSTALL_ROOT = path.resolve(__dirname, '..', '..');
const PROJECT_ENV = 'SECOND_RITE_PROJECT';

// The minimum a directory must hold to be opened as a project. Deliberately
// thin: authored content is what the editor edits, and demanding more (a
// manifest, a version file) would invent a project format before there is a
// second project to shape it. Alternate campaign roots count, because a
// generated campaign is a legitimate thing to open.
function isProjectRoot(dir) {
    // Each candidate is tested on its own: a missing data/ makes statSync
    // throw, and sharing one try would let that swallow the campaigns/ check
    // before it ever ran.
    const isDir = (name) => {
        try {
            return fs.statSync(path.join(dir, name)).isDirectory();
        } catch (e) {
            return false;
        }
    };
    return isDir('data') || isDir('campaigns');
}

// Resolved once at require time. A bad SECOND_RITE_PROJECT fails here, at
// boot, naming the path and the reason -- rather than serving an editor whose
// every tab is empty and letting the author discover it one blank panel at a
// time.
function resolveProjectRoot(configured = process.env[PROJECT_ENV]) {
    if (!configured) return INSTALL_ROOT;
    const root = path.resolve(configured);
    if (!fs.existsSync(root)) {
        throw new Error(`${PROJECT_ENV} points at a path that does not exist: ${root}`);
    }
    if (!isProjectRoot(root)) {
        throw new Error(`${PROJECT_ENV} is not a project: ${root} contains no data/ or campaigns/ directory`);
    }
    return root;
}

const PROJECT_ROOT = resolveProjectRoot();

// Joins under a root and REFUSES anything that leaves it, rather than
// mangling the path into something that happens to stay inside. A silently
// rewritten path is indistinguishable from a working one at the call site,
// so a traversal attempt and a typo both end up serving the wrong file.
function resolveWithin(root, ...segments) {
    const base = path.resolve(root);
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
