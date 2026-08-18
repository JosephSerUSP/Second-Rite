'use strict';

// #760 geometry-side evidence. Every child runs the ordinary editor renderable
// bridge and therefore the real tileset resolver / viewport / geometry compiler.
// The Lua probe varies ONLY the exposed-relief QEM ceiling.
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const authoredStorage = require('./authored-storage');
const projectPlay = require('./project-play');

const BUDGETS = [64, 96, 128, 192, 256, 384];
const MAPS = [
    { id: 2, label: 'dungeon_default' },
    { id: 15, label: 'stillnight_bellroot_vigil' },
    { id: 14, label: 'dungeon_hand_authored_height_compare' },
    { id: 12, label: 'dungeon_ffxii_depth_explore' },
];
const SEED = 1735689600;
const MAX_BUFFER = 32 * 1024 * 1024;

function argument(name, fallback) {
    const index = process.argv.indexOf(name);
    return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
}
function round(value) { return Number(Number(value || 0).toFixed(3)); }
function median(values) {
    if (!values.length) return 0;
    const sorted = [...values].sort((a, b) => a - b);
    const middle = Math.floor(sorted.length / 2);
    return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}
function uniq(values) { return [...new Set(values)].sort((a, b) => Number(a) - Number(b)); }

const installRoot = path.resolve(argument('--install-root', path.join(__dirname, '..', '..')));
const projectRoot = path.resolve(argument('--project-root', path.join(installRoot, 'projects', 'hichaukitoden-game')));
const loveExe = path.resolve(argument('--love', process.env.LOVE_PATH || 'C:\\Program Files\\LOVE\\love.exe'));
const lovec = /love\.exe$/i.test(loveExe) ? loveExe.replace(/love\.exe$/i, 'lovec.exe') : loveExe;
if (!fs.existsSync(lovec)) throw new Error(`LÖVE console executable not found: ${lovec}`);

const authoredMaps = authoredStorage.loadOrderedCollection(path.join(projectRoot, 'data'), 'maps').entries;
function mapSnapshot(id) {
    const map = authoredMaps.find(candidate => String(candidate.id) === String(id));
    if (!map) throw new Error(`Map ${id} not found in opened Project.`);
    return JSON.parse(JSON.stringify(map));
}

function parseEnvelope(stdout) {
    const match = String(stdout).match(/RENDERABLE BEGIN\s*([\s\S]*?)\s*RENDERABLE END/);
    if (!match) throw new Error('LÖVE returned no complete renderable envelope');
    return JSON.parse(match[1]);
}

function runCase(runtimeRoot, mapInfo, budget) {
    const map = mapSnapshot(mapInfo.id);
    const requestDir = path.join(runtimeRoot, 'tmp', 'issue-760-benchmark');
    fs.mkdirSync(requestDir, { recursive: true });
    const nonce = crypto.randomBytes(5).toString('hex');
    const requestPath = path.join(requestDir, `map-${mapInfo.id}-b${budget}-${nonce}.json`);
    fs.writeFileSync(requestPath, JSON.stringify({ map, seed: SEED }));
    const runId = `${process.pid}-${Date.now()}-${mapInfo.id}-${budget}-${nonce}`;
    const env = projectPlay.launchEnvironment({
        SECOND_RITE_RENDERABLE_REQUEST: path.relative(runtimeRoot, requestPath).split(path.sep).join('/'),
        SECOND_RITE_RENDERABLE_ENCODING: 'instances',
        SECOND_RITE_ISSUE760_BUDGET: String(budget),
        SECOND_RITE_ISSUE760_RUN_ID: runId,
        SDL_AUDIODRIVER: 'dummy',
    });
    const child = spawnSync(lovec, ['.', 'preview-map', String(mapInfo.id)], {
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
        throw new Error(`Map ${mapInfo.id} budget ${budget} failed: ${child.stderr || child.stdout}`);
    }
    const payload = parseEnvelope(child.stdout);
    if (payload.error) throw new Error(`Map ${mapInfo.id} budget ${budget}: ${payload.error}`);
    if (!payload.issue760 || !Array.isArray(payload.issue760.surfaces)) {
        throw new Error(`Map ${mapInfo.id} budget ${budget}: no #760 probe evidence`);
    }
    const surfaces = payload.issue760.surfaces.map(row => ({
        ...row,
        coldCompileMs: round(row.coldCompileMs),
        loadCallMs: round(row.loadCallMs),
        minDisplacement: Number(Number(row.minDisplacement).toFixed(6)),
        maxDisplacement: Number(Number(row.maxDisplacement).toFixed(6)),
    }));
    const result = {
        map: mapInfo.id,
        label: mapInfo.label,
        budget,
        surfaces,
        profile: payload.issue760.profile || null,
    };
    console.log(`ISSUE760 CASE ${JSON.stringify(result)}`);
    return result;
}

function summarizeSurface(rows) {
    const compiles = rows.map(row => Number(row.coldCompileMs));
    return {
        coldCompileCount: rows.length,
        identities: rows.map(row => row.identity),
        ids: [...new Set(rows.map(row => row.id))],
        sampleColumns: uniq(rows.map(row => row.sampleColumns)),
        sampleRows: uniq(rows.map(row => row.sampleRows)),
        denseTriangles: uniq(rows.map(row => row.denseTriangles)),
        exposedReliefTriangles: uniq(rows.map(row => row.exposedReliefTriangles)),
        perimeterSealTriangles: uniq(rows.map(row => row.perimeterSealTriangles)),
        finalTriangles: uniq(rows.map(row => row.finalTriangles)),
        coldCompileMs: {
            min: round(Math.min(...compiles)),
            median: round(median(compiles)),
            max: round(Math.max(...compiles)),
            total: round(compiles.reduce((sum, value) => sum + value, 0)),
        },
        minDisplacement: Number(Math.min(...rows.map(row => row.minDisplacement)).toFixed(6)),
        maxDisplacement: Number(Math.max(...rows.map(row => row.maxDisplacement)).toFixed(6)),
    };
}

function summarizeCase(result) {
    const bySurface = {};
    for (const row of result.surfaces) {
        if (!bySurface[row.surface]) bySurface[row.surface] = [];
        bySurface[row.surface].push(row);
    }
    const surfaces = {};
    for (const [surface, rows] of Object.entries(bySurface)) surfaces[surface] = summarizeSurface(rows);
    return { map: result.map, label: result.label, budget: result.budget, surfaces };
}

let stageDir = null;
try {
    stageDir = projectPlay.stageProject({ installRoot, projectRoot });
    const cases = [];
    for (const mapInfo of MAPS) {
        for (const budget of BUDGETS) {
            cases.push(runCase(stageDir, mapInfo, budget));
        }
    }
    const summary = cases.map(summarizeCase);
    console.log('ISSUE760 SUMMARY');
    console.log(JSON.stringify({ budgets: BUDGETS, maps: MAPS, summary, rawCases: cases }, null, 2));
} finally {
    projectPlay.cleanupLaunch(stageDir, null);
}
