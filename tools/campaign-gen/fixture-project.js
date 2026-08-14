// Safe, disposable Project roots for generator integration tests and preview.
// These are deliberately not Campaign roots: each fixture is an ordinary
// Project-shaped tree that owns its own authored data and assets.
'use strict';

const fs = require('fs');
const path = require('path');

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
    // Keep this check beside the name rule: future name-rule changes must not
    // turn cleanup or bootstrap into a path traversal primitive.
    if (path.dirname(target) !== parent) {
        throw new Error('fixture Project path escapes its fixed root');
    }
    return target;
}

function fixtureStatePath(installRoot, name) {
    return path.join(fixtureProjectPath(installRoot, name), STATE_FILE);
}

function requiredSource(installRoot, name) {
    const source = path.join(assertInstallRoot(installRoot), name);
    if (!fs.existsSync(source) || !fs.statSync(source).isDirectory()) {
        throw new Error(`fixture Project source directory is missing: ${name}`);
    }
    return source;
}

function bootstrapFixtureProject({ installRoot, name }) {
    const target = fixtureProjectPath(installRoot, name);
    if (fs.existsSync(target)) {
        throw new Error(`fixture Project already exists: ${name}`);
    }

    const dataSource = requiredSource(installRoot, 'data');
    const assetsSource = requiredSource(installRoot, 'assets');
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.mkdirSync(target);
    fs.cpSync(dataSource, path.join(target, 'data'), { recursive: true, force: false, errorOnExist: true });
    fs.cpSync(assetsSource, path.join(target, 'assets'), { recursive: true, force: false, errorOnExist: true });

    return {
        name,
        projectRoot: target,
        dataPath: path.join(target, 'data'),
        assetsPath: path.join(target, 'assets'),
        statePath: fixtureStatePath(installRoot, name),
    };
}

function cleanFixtureProject({ installRoot, name }) {
    const target = fixtureProjectPath(installRoot, name);
    // target is always a direct child of fixtureProjectsRoot(). rmSync on a
    // symlink removes the link itself, rather than following it.
    fs.rmSync(target, { recursive: true, force: true });
}

module.exports = {
    STATE_FILE,
    assertSafeName,
    fixtureProjectsRoot,
    fixtureProjectPath,
    fixtureStatePath,
    bootstrapFixtureProject,
    cleanFixtureProject,
};
