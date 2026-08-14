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
    // Poison pills from the retired ontology: neither a pointer nor an
    // alternate root may influence what this Project stages or plays.
    write(path.join(root, 'campaign.json'), JSON.stringify({ active: 'stale-alt' }));
    write(path.join(root, 'campaigns', 'stale-alt', 'system.json'), JSON.stringify({ id: 'wrong-campaign' }));
}

function makeManifest(root) {
    const manifest = {
        version: 1,
        rootFiles: ['main.lua'],
        runtimeDirectories: ['engine', 'presentation'],
        projectDirectories: ['assets'],
        dataRuntimeFiles: ['authored_storage.lua', 'authored_storage_manifest.json', 'json.lua', 'loader.lua'],
        authoredDataExtensions: ['.json'],
        releaseConfig: 'tools/export/release-conf.lua',
    };
    const manifestPath = path.join(root, 'runtime-manifest.json');
    write(manifestPath, JSON.stringify(manifest));
    return manifestPath;
}

test('external Project staging combines install runtime with exactly Project assets/data', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'sr-project-play-'));
    const runtime = path.join(root, 'install');
    const project = path.join(root, 'project');
    makeRuntime(runtime);
    makeExternalProject(project);

    write(path.join(runtime, 'data', 'system.json'), JSON.stringify({ id: 'checkout-project' }));
    write(path.join(runtime, 'assets', 'sprites', 'hero.txt'), 'asset:checkout-project');
    write(path.join(project, 'main.lua'), '-- project main must not run');
    write(path.join(project, 'engine', 'runtime.lua'), '-- project engine must not run');

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
        assert.ok(!fs.existsSync(path.join(stageDir, 'campaign.json')), 'stale pointer must never enter the runnable stage');
        assert.ok(!fs.existsSync(path.join(stageDir, 'campaigns')), 'stale alternate roots must never enter the runnable stage');
    } finally {
        removeStage(stageDir);
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('the launched child observes external Project data, never checkout or stale campaign data', async () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'sr-project-play-'));
    const runtime = path.join(root, 'install');
    const project = path.join(root, 'project');
    makeRuntime(runtime);
    makeExternalProject(project, 'played-external-project');
    write(path.join(runtime, 'data', 'system.json'), JSON.stringify({ id: 'checkout-project' }));
    write(path.join(runtime, 'assets', 'sprites', 'hero.txt'), 'asset:checkout-project');
    const manifestPath = makeManifest(root);
    const probe = path.join(root, 'probe.js');
    write(probe, "const fs=require('fs'); const path=require('path'); const s=JSON.parse(fs.readFileSync(path.join(process.cwd(),'data','system.json'),'utf8')); process.stdout.write(s.id);");
    let launch;

    try {
        const result = await new Promise((resolve, reject) => {
            launch = execStaged({
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

        assert.equal(result, 'played-external-project', 'checkout/stale campaign data must not masquerade as the opened Project');
        assert.equal(launch.direct, false);
        assert.ok(launch.stageDir && !fs.existsSync(launch.stageDir), 'temporary stage must be gone before the launch callback completes');
        assert.equal(JSON.parse(fs.readFileSync(path.join(runtime, 'data', 'system.json'), 'utf8')).id, 'checkout-project');
        assert.equal(JSON.parse(fs.readFileSync(path.join(project, 'data', 'system.json'), 'utf8')).id, 'played-external-project');
        assert.ok(fs.existsSync(path.join(project, 'campaign.json')), 'staging cleanup must not mutate source residue');
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('the ordinary in-checkout Project stays on the direct no-copy path', async () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'sr-project-play-direct-'));
    makeRuntime(root);
    makeExternalProject(root, 'direct-project');
    const probe = path.join(root, 'probe.js');
    write(probe, "const fs=require('fs'); const path=require('path'); const s=JSON.parse(fs.readFileSync(path.join(process.cwd(),'data','system.json'),'utf8')); process.stdout.write(s.id);");
    let launch;
    try {
        const stdout = await new Promise((resolve, reject) => {
            launch = execStaged({
                executable: process.execPath,
                projectArg: probe,
                installRoot: root,
                projectRoot: root,
                timeout: 5000,
            }, (error, output, stderr) => {
                if (error) return reject(new Error(`${error.message}\n${stderr || ''}`));
                resolve(String(output));
            });
        });
        assert.equal(stdout, 'direct-project');
        assert.equal(launch.direct, true);
        assert.equal(launch.stageDir, null, 'same-root launches must not create a staging copy');
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('missing external Project authored data fails loud instead of falling back to install data', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'sr-project-play-'));
    const runtime = path.join(root, 'install');
    const project = path.join(root, 'project');
    makeRuntime(runtime);
    write(path.join(runtime, 'data', 'system.json'), JSON.stringify({ id: 'checkout-project' }));
    fs.mkdirSync(project, { recursive: true });
    const manifestPath = makeManifest(root);
    try {
        assert.throws(
            () => stageProject({ installRoot: runtime, projectRoot: project, manifestPath }),
            /Project authored data is missing/,
        );
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('execStaged respects windowsHide: false for interactive Test Play launches', async () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'sr-project-play-hide-'));
    makeRuntime(root);
    makeExternalProject(root, 'visible-project');
    const probe = path.join(root, 'probe.js');
    write(probe, "const fs=require('fs'); const path=require('path'); const s=JSON.parse(fs.readFileSync(path.join(process.cwd(),'data','system.json'),'utf8')); process.stdout.write(s.id);");
    let launch;
    try {
        const stdout = await new Promise((resolve, reject) => {
            launch = execStaged({
                executable: process.execPath,
                projectArg: probe,
                installRoot: root,
                projectRoot: root,
                windowsHide: false,
                timeout: 5000,
            }, (error, output, stderr) => {
                if (error) return reject(new Error(`${error.message}\n${stderr || ''}`));
                resolve(String(output));
            });
        });
        assert.equal(stdout, 'visible-project');
        assert.ok(launch.child && launch.child.pid > 0);
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

