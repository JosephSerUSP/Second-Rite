'use strict';

// #760 geometry + exact-game projection evidence. Every child runs the ordinary
// editor renderable bridge and therefore the real tileset resolver / viewport /
// geometry compiler. The Lua probe varies ONLY the exposed-relief QEM ceiling.
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
function sha256(buffer) { return crypto.createHash('sha256').update(buffer).digest('hex'); }

const installRoot = path.resolve(argument('--install-root', path.join(__dirname, '..', '..')));
const projectRoot = path.resolve(argument('--project-root', path.join(installRoot, 'projects', 'hichaukitoden-game')));
const loveExe = path.resolve(argument('--love', process.env.LOVE_PATH || 'C:\\Program Files\\LOVE\\love.exe'));
const lovec = /love\.exe$/i.test(loveExe) ? loveExe.replace(/love\.exe$/i, 'lovec.exe') : loveExe;
const captureArg = argument('--capture-dir', '');
const captureDir = captureArg ? path.resolve(captureArg) : null;
if (!fs.existsSync(lovec)) throw new Error(`LÖVE console executable not found: ${lovec}`);
if (captureDir) fs.mkdirSync(captureDir, { recursive: true });

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

function safeCaptureName(mapInfo, budget, frame) {
    return `map-${String(mapInfo.id).padStart(2, '0')}-${mapInfo.label}-b${budget}-${frame.label}-wall${frame.actualWallStep}.png`;
}

function consumeCaptures(mapInfo, budget, payload) {
    if (!captureDir) return [];
    const frames = payload.issue760 && payload.issue760.captures;
    if (!Array.isArray(frames) || frames.length !== 3) {
        throw new Error(`Map ${mapInfo.id} budget ${budget}: expected near/mid/far #760 captures`);
    }
    return frames.map(frame => {
        const png = Buffer.from(frame.png, 'base64');
        const rgba = Buffer.from(frame.rgba, 'base64');
        const expectedBytes = Number(frame.width) * Number(frame.height) * 4;
        if (rgba.length !== expectedBytes) {
            throw new Error(`Map ${mapInfo.id} budget ${budget} ${frame.label}: RGBA ${rgba.length} != ${expectedBytes}`);
        }
        const filename = safeCaptureName(mapInfo, budget, frame);
        fs.writeFileSync(path.join(captureDir, filename), png);
        return {
            label: frame.label,
            targetWallStep: frame.targetWallStep,
            actualWallStep: frame.actualWallStep,
            playerX: frame.playerX,
            playerY: frame.playerY,
            playerDir: frame.playerDir,
            width: frame.width,
            height: frame.height,
            pngFile: filename,
            pngSha256: sha256(png),
            _rgba: rgba,
        };
    });
}

function publicCapture(frame) {
    const { _rgba, ...rest } = frame;
    return rest;
}

function pixelDiff(candidate, baseline) {
    if (!candidate || !baseline || candidate.length !== baseline.length || candidate.length % 4 !== 0) {
        throw new Error('Cannot compare #760 frames with incompatible RGBA buffers');
    }
    const pixels = candidate.length / 4;
    let changedPixels = 0;
    let maxChannelDelta = 0;
    let absoluteChannelDelta = 0;
    let changedAtLeast8 = 0;
    let changedAtLeast16 = 0;
    for (let offset = 0; offset < candidate.length; offset += 4) {
        let pixelMax = 0;
        for (let channel = 0; channel < 3; channel++) {
            const delta = Math.abs(candidate[offset + channel] - baseline[offset + channel]);
            absoluteChannelDelta += delta;
            if (delta > pixelMax) pixelMax = delta;
            if (delta > maxChannelDelta) maxChannelDelta = delta;
        }
        if (pixelMax > 0) changedPixels++;
        if (pixelMax >= 8) changedAtLeast8++;
        if (pixelMax >= 16) changedAtLeast16++;
    }
    return {
        changedPixels,
        changedPercent: round(changedPixels * 100 / pixels),
        changedAtLeast8,
        changedAtLeast8Percent: round(changedAtLeast8 * 100 / pixels),
        changedAtLeast16,
        changedAtLeast16Percent: round(changedAtLeast16 * 100 / pixels),
        meanAbsoluteRgbDelta: round(absoluteChannelDelta / (pixels * 3)),
        maxChannelDelta,
        note: 'Differences are measured after the production 1px vertex snap, fog, lighting, affine UVs and exact 256x240 game projection.',
    };
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
        SECOND_RITE_ISSUE760_CAPTURE: captureDir ? '1' : '0',
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
    const geometryError = Array.isArray(payload.issue760.geometryError)
        ? payload.issue760.geometryError : [];
    const captures = consumeCaptures(mapInfo, budget, payload);
    const result = {
        map: mapInfo.id,
        label: mapInfo.label,
        budget,
        surfaces,
        geometryError,
        profile: payload.issue760.profile || null,
        captures,
    };
    console.log(`ISSUE760 CASE ${JSON.stringify({ ...result, captures: captures.map(publicCapture) })}`);
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

function visualDiffs(cases) {
    const out = [];
    for (const mapInfo of MAPS) {
        const mapCases = cases.filter(result => result.map === mapInfo.id);
        const baseline = mapCases.find(result => result.budget === 384);
        if (!baseline || !baseline.captures.length) continue;
        for (const result of mapCases) {
            const views = {};
            for (const frame of result.captures) {
                const control = baseline.captures.find(candidate => candidate.label === frame.label);
                if (!control) throw new Error(`Map ${mapInfo.id}: missing 384 ${frame.label} control`);
                views[frame.label] = {
                    candidatePose: `${frame.playerX},${frame.playerY},${frame.playerDir}`,
                    actualWallStep: frame.actualWallStep,
                    ...pixelDiff(frame._rgba, control._rgba),
                };
            }
            out.push({ map: mapInfo.id, label: mapInfo.label, budget: result.budget, views });
        }
    }
    return out;
}

function summarizeCase(result) {
    const bySurface = {};
    for (const row of result.surfaces) {
        if (!bySurface[row.surface]) bySurface[row.surface] = [];
        bySurface[row.surface].push(row);
    }
    const surfaces = {};
    for (const [surface, rows] of Object.entries(bySurface)) surfaces[surface] = summarizeSurface(rows);
    return {
        map: result.map,
        label: result.label,
        budget: result.budget,
        surfaces,
        geometryError: result.geometryError,
        captures: result.captures.map(publicCapture),
    };
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
    const visual = visualDiffs(cases);
    const report = {
        budgets: BUDGETS,
        maps: MAPS,
        summary,
        visual,
        rawCases: cases.map(result => ({ ...result, captures: result.captures.map(publicCapture) })),
    };
    if (captureDir) fs.writeFileSync(path.join(captureDir, 'issue-760-summary.json'), `${JSON.stringify(report, null, 2)}\n`);
    console.log('ISSUE760 SUMMARY');
    console.log(JSON.stringify(report, null, 2));
} finally {
    projectPlay.cleanupLaunch(stageDir, null);
}
