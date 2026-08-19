'use strict';

// #760 exact constant-field evidence. This is intentionally separate from the
// representative map sweep so its zero-displacement rows cannot be mistaken for
// authored material statistics. A disposable staged Project receives the #760
// bridge only for this probe; production renderable execution remains untouched.
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const authoredStorage = require('./authored-storage');
const projectPlay = require('./project-play');

const BUDGETS = [64, 96, 128, 192, 256, 384];
const MAP_ID = 2;
const SEED = 1735689600;
const MAX_BUFFER = 32 * 1024 * 1024;

function argument(name, fallback) {
    const index = process.argv.indexOf(name);
    return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
}
function round(value) { return Number(Number(value || 0).toFixed(3)); }

const installRoot = path.resolve(argument('--install-root', path.join(__dirname, '..', '..')));
const projectRoot = path.resolve(argument('--project-root', path.join(installRoot, 'projects', 'hichaukitoden-game')));
const loveExe = path.resolve(argument('--love', process.env.LOVE_PATH || 'C:\\Program Files\\LOVE\\love.exe'));
const lovec = /love\.exe$/i.test(loveExe) ? loveExe.replace(/love\.exe$/i, 'lovec.exe') : loveExe;
const outputArg = argument('--output', '');
const outputPath = outputArg ? path.resolve(outputArg) : null;
if (!fs.existsSync(lovec)) throw new Error(`LÖVE console executable not found: ${lovec}`);

const authoredMaps = authoredStorage.loadOrderedCollection(path.join(projectRoot, 'data'), 'maps').entries;
const map = authoredMaps.find(candidate => String(candidate.id) === String(MAP_ID));
if (!map) throw new Error(`Map ${MAP_ID} not found in opened Project.`);
const mapSnapshot = JSON.parse(JSON.stringify(map));

function installIssue760Bridge(runtimeRoot) {
    const source = path.join(installRoot, 'presentation', 'issue760_renderable_bridge.lua');
    const target = path.join(runtimeRoot, 'presentation', 'editor_renderable_bridge.lua');
    if (!fs.existsSync(source)) throw new Error(`#760 experiment bridge not found: ${source}`);
    if (!fs.existsSync(target)) throw new Error(`#760 staged renderable bridge not found: ${target}`);
    fs.copyFileSync(source, target);
}

function parseEnvelope(stdout) {
    const match = String(stdout).match(/RENDERABLE BEGIN\s*([\s\S]*?)\s*RENDERABLE END/);
    if (!match) throw new Error('LÖVE returned no complete renderable envelope');
    return JSON.parse(match[1]);
}

function runCase(runtimeRoot, budget) {
    const requestDir = path.join(runtimeRoot, 'tmp', 'issue-760-flat-benchmark');
    fs.mkdirSync(requestDir, { recursive: true });
    const nonce = crypto.randomBytes(5).toString('hex');
    const requestPath = path.join(requestDir, `flat-b${budget}-${nonce}.json`);
    fs.writeFileSync(requestPath, JSON.stringify({ map: mapSnapshot, seed: SEED }));
    const runId = `${process.pid}-${Date.now()}-flat-${budget}-${nonce}`;
    const env = projectPlay.launchEnvironment({
        SECOND_RITE_RENDERABLE_REQUEST: path.relative(runtimeRoot, requestPath).split(path.sep).join('/'),
        SECOND_RITE_RENDERABLE_ENCODING: 'instances',
        SECOND_RITE_ISSUE760_BUDGET: String(budget),
        SECOND_RITE_ISSUE760_RUN_ID: runId,
        SECOND_RITE_ISSUE760_CAPTURE: '0',
        SECOND_RITE_ISSUE760_FLAT: '1',
        SDL_AUDIODRIVER: 'dummy',
    });
    const child = spawnSync(lovec, ['.', 'preview-map', String(MAP_ID)], {
        cwd: runtimeRoot,
        env,
        encoding: 'utf8',
        windowsHide: true,
        maxBuffer: MAX_BUFFER,
        timeout: 180000,
    });
    try { fs.unlinkSync(requestPath); } catch (error) { /* cleanup only */ }
    if (child.error) throw child.error;
    if (child.status !== 0) {
        throw new Error(`Flat field budget ${budget} failed: ${child.stderr || child.stdout}`);
    }
    const payload = parseEnvelope(child.stdout);
    if (payload.error) throw new Error(`Flat field budget ${budget}: ${payload.error}`);
    const rows = (payload.issue760 && payload.issue760.surfaces || [])
        .filter(row => String(row.identity || '').startsWith('issue760-flat:'))
        .map(row => ({
            surface: row.surface,
            sampleColumns: row.sampleColumns,
            sampleRows: row.sampleRows,
            denseTriangles: row.denseTriangles,
            exposedReliefCeiling: row.exposedReliefCeiling,
            exposedReliefTriangles: row.exposedReliefTriangles,
            perimeterSealTriangles: row.perimeterSealTriangles,
            finalTriangles: row.finalTriangles,
            coldCompileMs: round(row.coldCompileMs),
            loadCallMs: round(row.loadCallMs),
            minDisplacement: Number(Number(row.minDisplacement).toFixed(9)),
            maxDisplacement: Number(Number(row.maxDisplacement).toFixed(9)),
        }));
    if (rows.length !== 3) {
        throw new Error(`Flat field budget ${budget}: expected wall/floor/ceiling rows, got ${rows.length}`);
    }
    console.log(`ISSUE760 FLAT ${JSON.stringify({ budget, rows })}`);
    return { budget, rows };
}

let stageDir = null;
try {
    stageDir = projectPlay.stageProject({ installRoot, projectRoot });
    installIssue760Bridge(stageDir);
    const cases = BUDGETS.map(budget => runCase(stageDir, budget));
    const report = { budgets: BUDGETS, exactConstantField: 128 / 255, offset: 0, cases };
    if (outputPath) {
        fs.mkdirSync(path.dirname(outputPath), { recursive: true });
        fs.writeFileSync(outputPath, `${JSON.stringify(report, null, 2)}\n`);
    }
    console.log('ISSUE760 FLAT SUMMARY');
    console.log(JSON.stringify(report, null, 2));
} finally {
    projectPlay.cleanupLaunch(stageDir, null);
}