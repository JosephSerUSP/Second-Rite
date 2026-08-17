'use strict';

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const test = require('node:test');
const roots = require('./semantic-roots');

function makeProject(root) {
    fs.mkdirSync(path.join(root, 'data'), { recursive: true });
    fs.writeFileSync(path.join(root, 'data', 'system.json'), '{}', 'utf8');
    return root;
}

test('current checkout defaults remain ergonomic while semantic roots stay explicit', () => {
    const resolved = roots.resolveSemanticRoots({ env: {} });
    assert.equal(resolved.installRoot, roots.DEFAULT_INSTALL_ROOT);
    assert.equal(resolved.runtimeRoot, resolved.installRoot);
    assert.equal(resolved.studioRoot, resolved.installRoot);
    assert.equal(resolved.projectRoot, resolved.installRoot);
    assert.equal(resolved.rtpRoot, path.join(resolved.runtimeRoot, 'rtp'));
    assert.equal(resolved.projectDataRoot, path.join(resolved.projectRoot, 'data'));
    assert.equal(resolved.projectAssetsRoot, path.join(resolved.projectRoot, 'assets'));
});

test('runtime, RTP, Studio, and Project roots are independent semantic inputs', () => {
    const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-roots-'));
    try {
        const installRoot = path.join(temp, 'install');
        const runtimeRoot = path.join(temp, 'runtime');
        const rtpRoot = path.join(temp, 'defaults');
        const studioRoot = path.join(temp, 'studio');
        const projectRoot = makeProject(path.join(temp, 'project'));
        for (const dir of [installRoot, runtimeRoot, rtpRoot, studioRoot]) fs.mkdirSync(dir, { recursive: true });

        const resolved = roots.resolveSemanticRoots({
            installRoot,
            env: {
                [roots.RUNTIME_ROOT_ENV]: runtimeRoot,
                [roots.RTP_ROOT_ENV]: rtpRoot,
                [roots.STUDIO_ROOT_ENV]: studioRoot,
                [roots.PROJECT_ENV]: projectRoot,
            },
        });

        assert.equal(resolved.installRoot, path.resolve(installRoot));
        assert.equal(resolved.runtimeRoot, path.resolve(runtimeRoot));
        assert.equal(resolved.rtpRoot, path.resolve(rtpRoot));
        assert.equal(resolved.studioRoot, path.resolve(studioRoot));
        assert.equal(resolved.projectRoot, path.resolve(projectRoot));
        assert.notEqual(resolved.runtimeRoot, resolved.projectRoot);
        assert.notEqual(resolved.rtpRoot, resolved.projectRoot);
        assert.notEqual(resolved.studioRoot, resolved.projectRoot);
    } finally {
        fs.rmSync(temp, { recursive: true, force: true });
    }
});

test('explicit options override process-shaped environment without changing root meaning', () => {
    const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-roots-'));
    try {
        const installRoot = makeProject(path.join(temp, 'install-project'));
        const projectRoot = makeProject(path.join(temp, 'explicit-project'));
        const wrongProject = makeProject(path.join(temp, 'env-project'));
        const explicitRuntime = path.join(temp, 'explicit-runtime');
        const wrongRuntime = path.join(temp, 'env-runtime');
        const resolved = roots.resolveSemanticRoots({
            installRoot,
            projectRoot,
            runtimeRoot: explicitRuntime,
            env: {
                [roots.PROJECT_ENV]: wrongProject,
                [roots.RUNTIME_ROOT_ENV]: wrongRuntime,
            },
        });
        assert.equal(resolved.projectRoot, path.resolve(projectRoot));
        assert.equal(resolved.runtimeRoot, path.resolve(explicitRuntime));
    } finally {
        fs.rmSync(temp, { recursive: true, force: true });
    }
});

test('invalid explicit Project roots fail at the shared authority', () => {
    const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'thestra-roots-'));
    try {
        const installRoot = makeProject(path.join(temp, 'install'));
        const empty = path.join(temp, 'empty');
        fs.mkdirSync(empty);
        assert.throws(
            () => roots.resolveSemanticRoots({ installRoot, projectRoot: empty, env: {} }),
            /is not a project/,
        );
        assert.throws(
            () => roots.resolveSemanticRoots({ installRoot, projectRoot: path.join(temp, 'missing'), env: {} }),
            /does not exist/,
        );
    } finally {
        fs.rmSync(temp, { recursive: true, force: true });
    }
});

test('resolveWithin rejects topology escapes instead of rewriting them', () => {
    const root = path.join(os.tmpdir(), 'thestra-root-boundary');
    assert.equal(roots.resolveWithin(root, 'assets', 'sprites'), path.join(root, 'assets', 'sprites'));
    assert.throws(() => roots.resolveWithin(root, '..', 'outside'), /refusing a path outside/);
});
