// Safe, disposable Project roots for generator integration tests and preview.
// These are deliberately not Campaign roots: each fixture is an ordinary
// Project-shaped tree. Bootstrap delegates to the shared #479 Project lifecycle
// instead of owning a second copy policy.
'use strict';

const fs = require('fs');
const path = require('path');
const lifecycle = require('../editor/project-lifecycle');

const FIXTURE_PARENT = path.join('tmp', 'generated-projects');
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

function fixtureProjectsRoot(installRoot) {
    return path.join(assertInstallRoot(installRoot), FIXTURE_PARENT);
}

function fixtureProjectPath(installRoot, name) {
    const parent = fixtureProjectsRoot(installRoot);
    const target = path.join(parent, assertSafeName(name));
    if (path.dirname(target) !== parent) {
        throw new Error('fixture Project path escapes its fixed root');
    }
    return target;
}

function fixtureStatePath(installRoot, name) {
    return path.join(fixtureProjectPath(installRoot, name), STATE_FILE);
}

function statePathForProject(projectRoot) {
    return path.join(path.resolve(projectRoot), STATE_FILE);
}

function bootstrapFixtureProject({ installRoot, name, target } = {}) {
    const source = assertInstallRoot(installRoot);
    const projectTarget = target ? path.resolve(target) : fixtureProjectPath(source, name);
    fs.mkdirSync(path.dirname(projectTarget), { recursive: true });
    const result = lifecycle.forkProject({ source, target: projectTarget, installRoot: source });
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
    const source = assertInstallRoot(installRoot);
    const projectTarget = target ? path.resolve(target) : fixtureProjectPath(source, name);
    if (target) {
        throw new Error(`refusing to clean an explicit Project target automatically: ${projectTarget}`);
    }
    fs.rmSync(projectTarget, { recursive: true, force: true });
}

module.exports = {
    STATE_FILE,
    assertSafeName,
    fixtureProjectsRoot,
    fixtureProjectPath,
    fixtureStatePath,
    statePathForProject,
    bootstrapFixtureProject,
    cleanFixtureProject,
};
