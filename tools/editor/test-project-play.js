'use strict';

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const test = require('node:test');
const { execStaged, stageProject, removeStage } = require('./project-play');

function write(filePath, contents = '') {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, contents, 'utf8');
}

function makeRuntime(root) {
    write(path.join(root, 'main.lua'), '-- install runtime');
    write(path.join(root, 'engine', 'runtime.lua'), '-- engine marker');
    write(path.join(root, 'presentation', 'draw.lua'), '-- presentation marker');
    write(path.join(root, 'data', 'authored_storage.lua'), '-- authored storage runtime');
    write(path.join(root, 'data', 'authored_storage_manifest.json'), '{}');
    write(path.join(root, 'data', 'json.lua'), '-- json runtime');
    write(path.join(root, 'data', 'loader.lua'), '-- loader runtime');
    write(path.join(root, 'tools', 'export', 'release-conf.lua'), '-- release config');
}

function makeExternalProject(root, id = 'external-project') {
    write(path.join(root, 'data', 'system.json'), JSON.stringify({ id }));
    write(path.join(root, 'assets', 'sprites', 'hero.txt'), `asset:${id}`);
    write(path.join(root, 'campaign.json'), JSON.stringify({ active: 'local-only-pointer' }));
}

function makeManifest(root) {
    const manifest = {
        version: 1,
        rootFiles: ['main.lua'],
        runtimeDirectories: ['engine', 'presentation'],
        projectDirectories: ['assets'],
        dataRuntimeFiles: ['authored_storage.lua', 'authored_storage_manifest.json', 'json.lua', 'loader.lua'],
        campaignExtensions: ['.json'],
        releaseConfig: 'tools/export/release-conf.lua',
    };
    const manifestPath = path.join(root, 'runtime-manifest.json');
    write(manifestPath, JSON.stringify(manifest));
    return manifestPath;
}

test('external-project staging combines install runtime with project assets and authored data', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'sr-project-play-'));
    const runtime = path.join(root, 'install');
    const project = path.join(root, 'project');
    makeRuntime(runtime);
    makeExternalProject(project);
    const manifestPath = makeManifest(root);
    let stageDir;
    try {
        stageDir = stageProject({ installRoot: runtime, projectRoot: project, manifestPath });
        assert.notEqual(stageDir, runtime);
        assert.notEqual(stageDir, project);
        assert.equal(fs.readFileSync(path.join(stageDir, 'main.lua'), 'utf8'), '-- install runtime');
        assert.equal(fs.readFileSync(path.join(stageDir, 'engine', 'runtime.lua'), 'utf8'), '-- engine marker');
        assert.equal(fs.readFileSync(path.join(stageDir, 'assets', 'sprites', 'hero.txt'), 'utf8'), 'asset:external-project');
        assert.equal(JSON.parse(fs.readFileSync(path.join(stageDir, 'data', 'system.json'), 'utf8')).id, 'external-project');
        assert.ok(!fs.existsSync(path.join(stageDir, 'campaign.json')), 'local campaign pointer must not enter the runnable stage');
    } finally {
        removeStage(stageDir);
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('the launched child actually observes the staged external project, not the install checkout', async () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'sr-project-play-'));
    const runtime = path.join(root, 'install');
    const project = path.join(root, 'project');
    makeRuntime(runtime);
    makeExternalProject(project, 'played-external-project');
    const manifestPath = makeManifest(root);
    const probe = path.join(root, 'probe.js');
    write(probe, "const fs=require('fs'); const path=require('path'); const s=JSON.parse(fs.readFileSync(path.join(process.cwd(),'data','system.json'),'utf8')); process.stdout.write(s.id);");

    try {
        const result = await new Promise((resolve, reject) => {
            execStaged({
                executable: process.execPath,
                projectArg: probe,
                installRoot: runtime,
                projectRoot: project,
                manifestPath,
                timeout: 5000,
            }, (error, stdout, stderr) => {
                if (error) return reject(new Error(`${error.message}\n${stderr || ''}`));
                resolve(String(stdout));
            });
        });
        assert.equal(result, 'played-external-project');
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('missing external authored data fails loud instead of falling back to install data', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'sr-project-play-'));
    const runtime = path.join(root, 'install');
    const project = path.join(root, 'project');
    makeRuntime(runtime);
    fs.mkdirSync(project, { recursive: true });
    const manifestPath = makeManifest(root);
    try {
        assert.throws(
            () => stageProject({ installRoot: runtime, projectRoot: project, manifestPath }),
            /Campaign source is missing/,
        );
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});
