'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const worker = require('./runtime-renderable-worker');

function write(filePath, value) {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, value);
}

function fixture() {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'second-rite-authority-cache-'));
    const installRoot = path.join(root, 'install');
    const projectRoot = path.join(root, 'project');
    const manifestPath = path.join(installRoot, 'tools', 'export', 'runtime-manifest.json');

    write(path.join(installRoot, 'main.lua'), '-- main\n');
    write(path.join(installRoot, 'engine', 'runtime.lua'), '-- runtime A\n');
    write(path.join(installRoot, 'presentation', 'runtime.lua'), '-- presentation\n');
    write(path.join(installRoot, 'tools', 'export', 'release-conf.lua'), '-- release\n');
    write(path.join(installRoot, 'tools', 'export', 'runtime-semantic-resources.lua'), '-- provider\n');
    write(path.join(installRoot, 'tools', 'export', 'runtime-engine-server.lua'), '-- server\n');
    write(path.join(installRoot, 'rtp', 'revision-a', 'height.bin'), 'AAAA');
    write(path.join(projectRoot, 'data', 'system.json'), '{}\n');
    write(path.join(projectRoot, 'assets', 'tilesets', 'height.bin'), '0000');
    write(path.join(projectRoot, 'project.json'), '{}\n');
    write(manifestPath, JSON.stringify({
        version: 1,
        rootFiles: ['main.lua'],
        runtimeDirectories: ['engine', 'presentation'],
        projectDirectories: ['assets'],
        authoredDataExtensions: ['.json'],
        releaseConfig: 'tools/export/release-conf.lua',
    }));

    return { root, installRoot, projectRoot, manifestPath };
}

function revision(f, digestCache) {
    return worker.runtimeAuthorityRevision({
        installRoot: f.installRoot,
        projectRoot: f.projectRoot,
        manifestPath: f.manifestPath,
        digestCache,
    });
}

test('content-digest cache cannot hide same-size edits with restored mtime', () => {
    const f = fixture();
    try {
        const digestCache = new Map();
        const runtimePath = path.join(f.installRoot, 'engine', 'runtime.lua');

        // Establish the baseline using a timestamp that round-trips through the
        // host filesystem. Windows can expose a fractional-ms creation write
        // time that utimes subsequently rounds, which would accidentally make
        // mtime itself invalidate the cache instead of exercising ctime/file
        // identity. Normalize first, then cache that exact representable state.
        const createdStat = fs.statSync(runtimePath);
        const normalizedMtime = new Date(Math.floor(createdStat.mtimeMs));
        fs.utimesSync(runtimePath, createdStat.atime, normalizedMtime);
        const originalStat = fs.statSync(runtimePath);

        const first = revision(f, digestCache);
        assert.equal(revision(f, digestCache), first, 'unchanged source reuses cached content digests');

        fs.writeFileSync(runtimePath, '-- runtime B\n');
        fs.utimesSync(runtimePath, originalStat.atime, originalStat.mtime);
        const secondStat = fs.statSync(runtimePath);
        assert.equal(secondStat.size, originalStat.size, 'adversarial edit preserves file size');
        assert.equal(secondStat.mtimeMs, originalStat.mtimeMs, 'adversarial edit restores exact representable mtime');
        assert.notEqual(secondStat.ctimeMs, originalStat.ctimeMs,
            'ordinary same-size rewrite still advances filesystem change identity');
        const second = revision(f, digestCache);
        assert.notEqual(second, first,
            'cached content authority must invalidate despite equal size and restored mtime');

        fs.writeFileSync(runtimePath, '-- runtime C\n');
        fs.utimesSync(runtimePath, originalStat.atime, originalStat.mtime);
        const thirdStat = fs.statSync(runtimePath);
        assert.equal(thirdStat.mtimeMs, originalStat.mtimeMs,
            'rapid second edit also restores the same mtime');
        const third = revision(f, digestCache);
        assert.notEqual(third, second, 'rapid second same-size edit also invalidates the cached digest');
    } finally {
        fs.rmSync(f.root, { recursive: true, force: true });
    }
});
