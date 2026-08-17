// Safe, disposable Project roots for generator integration tests and preview.
// These are deliberately not Campaign roots: each fixture is an ordinary
// Project-shaped tree. Bootstrap delegates to the shared #479 Project lifecycle
// instead of owning a second copy policy.
'use strict';

const fs = require('fs');
const path = require('path');
const semanticRoots = require('../semantic-roots');
const lifecycle = require('../editor/project-lifecycle');

const FIXTURE_PARENT = path.join('tmp', 'generated-projects');
const PROJECTS_ROOT_ENV = 'THESTRA_GENERATED_PROJECTS_ROOT';
const PROJECT_TARGET_ENV = 'THESTRA_GENERATED_PROJECT_TARGET';
const STATE_FILE = 'fixture-state.json';
const SAFE_NAME = /^[a-z0-9][a-z0-9_-]{0,63}$/;

function assertInstallRoot(installRoot) {
    if (typeof installRoot !== 'string' || installRoot.length === 0) {
        throw new Error('fixture Project installRoot must be a non-empty path');
    }
    const resolved = path.resolve(installRoot);
    if (!path.isAbsolute(resolved) || !fs.statSync(resolved).isDirectory()) {
        throw new Error(`fixture Project installRoot is not a directory: ${installRoot}`);
    }
    return resolved;
}

function assertSafeName(name) {
    if (typeof name !== 'string' || !SAFE_NAME.test(name)) {
        throw new Error('fixture Project name must contain only lowercase letters, digits, _ or -');
    }
    return name;
}

function fixtureProjectsRoot(installRoot, configured = process.env[PROJECTS_ROOT_ENV]) {
    const install = assertInstallRoot(installRoot);
    if (!configured) return path.join(install, FIXTURE_PARENT);
    return path.resolve(configured);
}

function explicitProjectTarget(configured = process.env[PROJECT_TARGET_ENV]) {
    if (!configured) return null;
    return path.resolve(configured);
}

function fixtureProjectPath(installRoot, name) {
    const explicit = explicitProjectTarget();
    if (explicit) {
        // The explicit destination belongs to the lifecycle wrapper; the legacy
        // generator's --name is only a run/state identifier in this mode.
        return explicit;
    }
    const parent = fixtureProjectsRoot(installRoot);
    const target = path.join(parent, assertSafeName(name));
    if (path.dirname(target) !== parent) {
        throw new Error('fixture Project path escapes its configured root');
    }
    return target;
}

function fixtureStatePath(installRoot, name) {
    return path.join(fixtureProjectPath(installRoot, name), STATE_FILE);
}

function statePathForProject(projectRoot) {
    return path.join(path.resolve(projectRoot), STATE_FILE);
}

function sourceProjectForInstall(installRoot, configuredSource) {
    if (configuredSource) return lifecycle.assertProjectRoot(configuredSource, 'Generator source Project');
    // Legacy/synthetic fixtures may deliberately make their install root a
    // Project. The real repository no longer does: #700 moved Second Gate under
    // projects/, so the compatibility generator explicitly forks that default
    // Project while continuing to use the repository as installed Thestra.
    if (semanticRoots.isProjectRoot(installRoot)) return lifecycle.assertProjectRoot(installRoot, 'Generator source Project');
    return lifecycle.assertProjectRoot(semanticRoots.DEFAULT_PROJECT_ROOT, 'Generator source Project');
}

function bootstrapFixtureProject({ installRoot, sourceProject, name, target } = {}) {
    const install = assertInstallRoot(installRoot);
    const source = sourceProjectForInstall(install, sourceProject);
    const projectTarget = target ? path.resolve(target) : fixtureProjectPath(install, name);
    fs.mkdirSync(path.dirname(projectTarget), { recursive: true });
    const result = lifecycle.forkProject({
        source,
        target: projectTarget,
        installRoot: install,
        runtimeRoot: install,
    });
    return {
        name: name || path.basename(projectTarget),
        projectRoot: result.projectRoot,
        dataPath: result.dataPath,
        assetsPath: result.assetsPath,
        statePath: statePathForProject(result.projectRoot),
        bootstrapMode: result.mode,
        sourceProjectRoot: result.sourceProjectRoot,
    };
}

function cleanFixtureProject({ installRoot, name, target } = {}) {
    const install = assertInstallRoot(installRoot);
    const configuredTarget = explicitProjectTarget();
    const projectTarget = target ? path.resolve(target) : fixtureProjectPath(install, name);
    if (target || configuredTarget) {
        throw new Error(`refusing to clean an explicit Project target automatically: ${projectTarget}`);
    }
    fs.rmSync(projectTarget, { recursive: true, force: true });
}

module.exports = {
    FIXTURE_PARENT,
    PROJECTS_ROOT_ENV,
    PROJECT_TARGET_ENV,
    STATE_FILE,
    assertSafeName,
    explicitProjectTarget,
    fixtureProjectsRoot,
    fixtureProjectPath,
    fixtureStatePath,
    statePathForProject,
    sourceProjectForInstall,
    bootstrapFixtureProject,
    cleanFixtureProject,
};
