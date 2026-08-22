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
    write(path.join(root, 'engine', 'data', 'authored_storage.lua'), '-- authored storage runtime');
    write(path.join(root, 'engine', 'data', 'authored_storage_manifest.json'), '{}');
    write(path.join(root, 'engine', 'data', 'semantic_resources.lua'), '-- source semantic provider');
    write(path.join(root, 'engine', 'data', 'json.lua'), '-- json runtime');
    write(path.join(root, 'engine', 'data', 'loader.lua'), '-- loader runtime');
    write(path.join(root, 'release-conf.lua'), '-- release config');
}

function makeExternalProject(root, id = 'external-project') {
    write(path.join(root, 'data', 'system.json'), JSON.stringify({ id }));
    for (const stem of ['units', 'maps', 'scenes', 'tilesets']) {
        write(path.join(root, 'data', stem, 'index.json'), JSON.stringify({ files: [] }));
    }
    for (const module of ['battle', 'exploration', 'progression', 'quest']) {
        write(path.join(root, 'data', 'flows', `${module}.json`), '{}');
    }
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
        authoredDataExtensions: ['.json'],
        releaseConfig: 'release-conf.lua',
    };
    const manifestPath = path.join(root, 'runtime-manifest.json');
    write(manifestPath, JSON.stringify(manifest));
    return manifestPath;
}

test('external Project staging combines install runtime with compiled Project semantics', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'sr-project-play-'));
    const install = path.join(root, 'install');
    const runtime = path.join(install, 'runtime');
    const project = path.join(root, 'project');
    makeRuntime(runtime);
    makeExternalProject(project);

    write(path.join(install, 'data', 'system.json'), JSON.stringify({ id: 'checkout-project' }));
    write(path.join(install, 'assets', 'sprites', 'hero.txt'), 'asset:checkout-project');
    write(path.join(project, 'main.lua'), '-- project main must not run');
    write(path.join(project, 'engine', 'runtime.lua'), '-- project engine must not run');

    const manifestPath = makeManifest(root);
    let stageDir;
    try {
        stageDir = stageProject({ installRoot: install, runtimeRoot: runtime, projectRoot: project, manifestPath });
        assert.notEqual(stageDir, runtime);
        assert.notEqual(stageDir, project);
        assert.equal(fs.readFileSync(path.join(stageDir, 'main.lua'), 'utf8'), '-- install runtime');
        assert.equal(fs.readFileSync(path.join(stageDir, 'engine', 'runtime.lua'), 'utf8'), '-- engine marker');
        assert.equal(fs.readFileSync(path.join(stageDir, 'assets', 'sprites', 'hero.txt'), 'utf8'), 'asset:external-project');
        assert.equal(JSON.parse(fs.readFileSync(path.join(stageDir, 'data', 'system.json'), 'utf8')).id, 'external-project');

        for (const stem of ['units', 'maps', 'flows', 'scenes', 'tilesets']) {
            assert.ok(fs.existsSync(path.join(stageDir, 'data', `${stem}.json`)), `${stem} semantic monolith must exist`);
            assert.ok(!fs.existsSync(path.join(stageDir, 'data', stem)), `${stem} source directory must be absent`);
        }
        assert.deepEqual(JSON.parse(fs.readFileSync(path.join(stageDir, 'data', 'units.json'), 'utf8')), []);
        assert.deepEqual(JSON.parse(fs.readFileSync(path.join(stageDir, 'data', 'maps.json'), 'utf8')), []);
        assert.deepEqual(JSON.parse(fs.readFileSync(path.join(stageDir, 'data', 'scenes.json'), 'utf8')), []);
        assert.deepEqual(JSON.parse(fs.readFileSync(path.join(stageDir, 'data', 'tilesets.json'), 'utf8')), {});
        assert.deepEqual(Object.keys(JSON.parse(fs.readFileSync(path.join(stageDir, 'data', 'flows.json'), 'utf8'))).sort(),
            ['battle', 'exploration', 'progression', 'quest']);
        assert.ok(fs.existsSync(path.join(stageDir, 'data', 'runtime_data_manifest.json')), 'compiled provenance must exist');
        assert.ok(!fs.existsSync(path.join(stageDir, 'engine', 'data', 'authored_storage.lua')), 'player must not ship source parser');
        assert.ok(!fs.existsSync(path.join(stageDir, 'engine', 'data', 'authored_storage_manifest.json')), 'player must not ship source manifest');
        const provider = fs.readFileSync(path.join(stageDir, 'engine', 'data', 'semantic_resources.lua'), 'utf8');
        assert.match(provider, /Candidate A\+ runtime provider/);
        assert.doesNotMatch(provider, /authored_storage/);

        assert.ok(!fs.existsSync(path.join(stageDir, 'campaign.json')), 'stale pointer must never enter the runnable stage');
        assert.ok(!fs.existsSync(path.join(stageDir, 'campaigns')), 'stale alternate roots must never enter the runnable stage');
    } finally {
        removeStage(stageDir);
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('the launched child observes external Project data, never checkout or stale campaign data', async () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'sr-project-play-'));
    const install = path.join(root, 'install');
    const runtime = path.join(install, 'runtime');
    const project = path.join(root, 'project');
    makeRuntime(runtime);
    makeExternalProject(project, 'played-external-project');
    write(path.join(install, 'data', 'system.json'), JSON.stringify({ id: 'checkout-project' }));
    write(path.join(install, 'assets', 'sprites', 'hero.txt'), 'asset:checkout-project');
    const manifestPath = makeManifest(root);
    const probe = path.join(root, 'probe.js');
    write(probe, "const fs=require('fs'); const path=require('path'); const s=JSON.parse(fs.readFileSync(path.join(process.cwd(),'data','system.json'),'utf8')); process.stdout.write(s.id);");
    let launch;

    try {
        const result = await new Promise((resolve, reject) => {
            launch = execStaged({
                executable: process.execPath,
                projectArg: probe,
                installRoot: install,
                runtimeRoot: runtime,
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
        assert.equal(launch.runtimeRoot, path.resolve(runtime));
        assert.equal(launch.runtimeDataSnapshot, null);
        assert.ok(launch.stageDir && !fs.existsSync(launch.stageDir), 'temporary stage must be gone before the launch callback completes');
        assert.equal(JSON.parse(fs.readFileSync(path.join(install, 'data', 'system.json'), 'utf8')).id, 'checkout-project');
        assert.equal(JSON.parse(fs.readFileSync(path.join(project, 'data', 'system.json'), 'utf8')).id, 'played-external-project');
        assert.ok(fs.existsSync(path.join(project, 'campaign.json')), 'staging cleanup must not mutate source residue');
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('same-root Test Play keeps runtime/assets direct but reads a compiled data snapshot', async () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'sr-project-play-direct-'));
    makeRuntime(root);
    makeExternalProject(root, 'direct-project');
    const probe = path.join(root, 'probe.js');
    write(probe, `
const fs=require('fs');
const path=require('path');
const relative=process.env.THESTRA_RUNTIME_DATA_ROOT;
if (!relative) throw new Error('missing THESTRA_RUNTIME_DATA_ROOT');
const dataRoot=path.join(process.cwd(), ...relative.split('/'));
const system=JSON.parse(fs.readFileSync(path.join(dataRoot,'system.json'),'utf8'));
const manifest=JSON.parse(fs.readFileSync(path.join(dataRoot,'runtime_data_manifest.json'),'utf8'));
const value={
  id: system.id,
  relative,
  compiler: manifest.compiler && manifest.compiler.id,
  unitsMonolith: fs.existsSync(path.join(dataRoot,'units.json')),
  unitsSourceDir: fs.existsSync(path.join(dataRoot,'units')),
  cwd: process.cwd(),
};
process.stdout.write(JSON.stringify(value));
`);
    let launch;
    try {
        const value = await new Promise((resolve, reject) => {
            launch = execStaged({
                executable: process.execPath,
                projectArg: probe,
                installRoot: root,
                runtimeRoot: root,
                projectRoot: root,
                timeout: 5000,
            }, (error, output, stderr) => {
                if (error) return reject(new Error(`${error.message}\n${stderr || ''}`));
                resolve(JSON.parse(String(output)));
            });
        });
        assert.equal(value.id, 'direct-project');
        assert.equal(value.compiler, 'thestra-runtime-data');
        assert.equal(value.unitsMonolith, true);
        assert.equal(value.unitsSourceDir, false);
        assert.equal(path.resolve(value.cwd), fs.realpathSync(root), 'same-root runtime/assets must stay direct');
        assert.match(value.relative, /^tmp\/editor-runtime-data\/snapshot-[^/]+\/data$/);
        assert.equal(launch.direct, true);
        assert.equal(launch.runtimeRoot, path.resolve(root));
        assert.equal(launch.stageDir, null, 'same-root launches must not create a runtime/assets staging copy');
        assert.ok(launch.runtimeDataSnapshot, 'same-root launch must create a data-only snapshot');
        assert.ok(!fs.existsSync(launch.runtimeDataSnapshot.snapshotRoot),
            'data-only snapshot must be removed before launch callback completes');
        assert.ok(fs.existsSync(path.join(root, 'data', 'units', 'index.json')),
            'compiled snapshot must not mutate source fragment storage');
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('missing external Project authored data fails loud instead of falling back to install data', () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'sr-project-play-'));
    const install = path.join(root, 'install');
    const runtime = path.join(install, 'runtime');
    const project = path.join(root, 'project');
    makeRuntime(runtime);
    write(path.join(install, 'data', 'system.json'), JSON.stringify({ id: 'checkout-project' }));
    fs.mkdirSync(project, { recursive: true });
    const manifestPath = makeManifest(root);
    try {
        assert.throws(
            () => stageProject({ installRoot: install, runtimeRoot: runtime, projectRoot: project, manifestPath }),
            /is not a project|Project authored data is missing/,
        );
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});

test('execStaged respects windowsHide: false while cleaning same-root data snapshots', async () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'sr-project-play-hide-'));
    makeRuntime(root);
    makeExternalProject(root, 'visible-project');
    const probe = path.join(root, 'probe.js');
    write(probe, "process.stdout.write(process.env.THESTRA_RUNTIME_DATA_ROOT ? 'visible-project' : 'missing-snapshot');");
    let launch;
    try {
        const stdout = await new Promise((resolve, reject) => {
            launch = execStaged({
                executable: process.execPath,
                projectArg: probe,
                installRoot: root,
                runtimeRoot: root,
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
        assert.ok(launch.runtimeDataSnapshot && !fs.existsSync(launch.runtimeDataSnapshot.snapshotRoot));
    } finally {
        fs.rmSync(root, { recursive: true, force: true });
    }
});
