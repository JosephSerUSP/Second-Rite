'use strict';

// #237/#699: Thestra Studio works from explicit semantic roots. The current
// monorepo still happens to place runtime, Studio, RTP, and the default Project
// under one checkout, but that topology is not the ownership contract.
//
// A Project is the one authored/runnable game boundary. There is no nested
// alternate active-content root inside a Project. Routes, stories and chapters
// belong to ordinary authored data; alternate games are separate Projects.

const semanticRoots = require('../../tools/semantic-roots');

// Resolve once at process boot. Project selection is finalized before modules
// that import this boundary are loaded; a bad configured Project therefore
// fails loud here instead of degrading into checkout data.
const ROOTS = semanticRoots.resolveSemanticRoots();
const INSTALL_ROOT = ROOTS.installRoot;
const RUNTIME_ROOT = ROOTS.runtimeRoot;
const RTP_ROOT = ROOTS.rtpRoot;
const STUDIO_ROOT = ROOTS.studioRoot;
const PROJECT_ROOT = ROOTS.projectRoot;
const PROJECT_ENV = semanticRoots.PROJECT_ENV;

function resolveProjectRoot(configured = process.env[PROJECT_ENV]) {
    return semanticRoots.resolveProjectRoot(configured, { installRoot: INSTALL_ROOT });
}

const inProject = (...segments) => semanticRoots.resolveWithin(PROJECT_ROOT, ...segments);
const inInstall = (...segments) => semanticRoots.resolveWithin(INSTALL_ROOT, ...segments);
const inRuntime = (...segments) => semanticRoots.resolveWithin(RUNTIME_ROOT, ...segments);
const inRtp = (...segments) => semanticRoots.resolveWithin(RTP_ROOT, ...segments);
const inStudio = (...segments) => semanticRoots.resolveWithin(STUDIO_ROOT, ...segments);

module.exports = {
    INSTALL_ROOT,
    PROJECT_ROOT,
    PROJECT_ENV,
    ROOTS,
    RTP_ROOT,
    RUNTIME_ROOT,
    STUDIO_ROOT,
    inInstall,
    inProject,
    inRtp,
    inRuntime,
    inStudio,
    isProjectRoot: semanticRoots.isProjectRoot,
    resolveProjectRoot,
    resolveSemanticRoots: semanticRoots.resolveSemanticRoots,
    resolveWithin: semanticRoots.resolveWithin,
};
