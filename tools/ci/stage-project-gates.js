#!/usr/bin/env node
'use strict';

// #700: repository verification still owns tests/goldens, while the runnable
// game is now an ordinary Project. Build exactly one canonical runtime stage
// through the exporter, then add repository-only test fixtures for `unittest`.
// No production data/assets are copied by this helper outside stageRuntimeGame.
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');
const semanticRoots = require('../semantic-roots');
const exporter = require('../export/export-game');

function parseArgs(argv) {
    const options = {};
    for (let i = 0; i < argv.length; i += 1) {
        const arg = argv[i];
        if (arg === '--output') options.outputDir = path.resolve(argv[++i] || '');
        else if (arg === '--project') options.projectDir = path.resolve(argv[++i] || '');
        else if (arg === '--help') return null;
        else throw new Error(`Unknown argument: ${arg}`);
    }
    return options;
}

function stageProjectGates(options = {}) {
    const roots = semanticRoots.resolveSemanticRoots({
        projectRoot: options.projectDir || semanticRoots.DEFAULT_PROJECT_ROOT,
    });
    const outputDir = path.resolve(options.outputDir || path.join(os.tmpdir(), 'thestra-project-gates'));
    const staged = exporter.stageRuntimeGame({
        installRoot: roots.installRoot,
        runtimeDir: roots.runtimeRoot,
        rtpRoot: roots.rtpRoot,
        projectDir: roots.projectRoot,
        outputDir,
    });

    // `unittest` is a repository verification command, not a player capability.
    // Keep tests out of the runtime manifest/exported game while making the
    // temporary verification stage able to run the same registered Lua suite.
    const sourceTests = path.join(roots.installRoot, 'tests');
    const stageTests = path.join(staged.stageDir, 'tests');
    fs.cpSync(sourceTests, stageTests, { recursive: true, force: true });

    // The Effekseer shim is native code loaded outside LOVE's virtual
    // filesystem, so a staged tree that lacks it is not a runnable game: the
    // effects silently do not draw and only the two effect-bearing G5 frames
    // reveal it. It is gitignored build output rather than repository source,
    // so it is copied when present and simply absent on hosts that never built
    // it -- those hosts already run without effects.
    const shimNames = ['effekseer_shim.dll', 'effekseer_shim.provenance.json'];
    const stagedShims = [];
    for (const name of shimNames) {
        const source = path.join(roots.installRoot, name);
        if (!fs.existsSync(source)) continue;
        fs.cpSync(source, path.join(staged.stageDir, name), { force: true });
        stagedShims.push(name);
    }

    return {
        stageDir: staged.stageDir,
        projectDir: roots.projectRoot,
        runtimeDir: roots.runtimeRoot,
        rtpRoot: roots.rtpRoot,
        stagedShims,
    };
}

function notice(title, value) {
    const text = JSON.stringify(value)
        .replace(/%/g, '%25')
        .replace(/\r/g, '%0D')
        .replace(/\n/g, '%0A');
    process.stdout.write(`::notice title=${title}::${text}\n`);
}

function compactIssue760Evidence(captureDir) {
    const report = JSON.parse(fs.readFileSync(path.join(captureDir, 'issue-760-summary.json'), 'utf8'));
    const flat = JSON.parse(fs.readFileSync(path.join(captureDir, 'issue-760-flat-summary.json'), 'utf8'));

    notice('issue760-flat', flat.cases.flatMap(entry => entry.rows.map(row => ({
        b: entry.budget,
        s: row.surface,
        sc: row.sampleColumns,
        sr: row.sampleRows,
        d: row.denseTriangles,
        r: row.exposedReliefTriangles,
        seal: row.perimeterSealTriangles,
        final: row.finalTriangles,
        ms: row.coldCompileMs,
        min: row.minDisplacement,
        max: row.maxDisplacement,
    }))));

    notice('issue760-ceilings', report.summary.flatMap(entry => {
        const row = entry.surfaces && entry.surfaces.ceiling;
        if (!row) return [];
        return [{
            m: entry.map,
            b: entry.budget,
            sc: row.sampleColumns,
            sr: row.sampleRows,
            d: row.denseTriangles,
            r: row.exposedReliefTriangles,
            seal: row.perimeterSealTriangles,
            final: row.finalTriangles,
            ms: row.coldCompileMs,
            min: row.minDisplacement,
            max: row.maxDisplacement,
        }];
    }));

    notice('issue760-geometry-error', report.summary.flatMap(entry => {
        const grouped = new Map();
        for (const row of entry.geometryError || []) {
            const key = row.surface;
            const current = grouped.get(key) || {
                m: entry.map, b: entry.budget, s: row.surface,
                max: 0, mean: 0, rms: 0, p1: 0, p3: 0, p8: 0,
            };
            current.max = Math.max(current.max, Number(row.maxWorldError) || 0);
            current.mean = Math.max(current.mean, Number(row.meanAbsoluteWorldError) || 0);
            current.rms = Math.max(current.rms, Number(row.rmsWorldError) || 0);
            const projected = row.projectedMaxPixelError || {};
            current.p1 = Math.max(current.p1, Number(projected['1']) || 0);
            current.p3 = Math.max(current.p3, Number(projected['3']) || 0);
            current.p8 = Math.max(current.p8, Number(projected['8']) || 0);
            grouped.set(key, current);
        }
        return [...grouped.values()];
    }));

    notice('issue760-visual', report.visual.flatMap(entry => Object.entries(entry.views || {}).map(([view, row]) => ({
        m: entry.map,
        b: entry.budget,
        v: view,
        wall: row.actualWallStep,
        changed: row.changedPercent,
        c8: row.changedAtLeast8Percent,
        c16: row.changedAtLeast16Percent,
        mae: row.meanAbsoluteRgbDelta,
        max: row.maxChannelDelta,
    }))));
}

function runIssue760EvidenceIfRequested() {
    if (process.env.GITHUB_HEAD_REF !== 'exp/760-height-budget-projection') return;
    // This temporary evidence lane is intentionally piggy-backed ONLY on the
    // Windows `verify` job, which already installs the pinned LÖVE 11.5 + Mesa
    // software renderer used by the earlier #760 run. Other workflows may also
    // expose LOVEC, but must remain ordinary gates.
    if (process.env.GITHUB_WORKFLOW !== 'verify') return;
    const lovec = process.env.LOVEC;
    if (!lovec) return;
    const captureDir = path.join(os.tmpdir(), 'issue-760-current-main-captures');
    fs.mkdirSync(captureDir, { recursive: true });

    const sweep = spawnSync(process.execPath, [
        path.join(__dirname, '..', 'editor', 'bench-height-budget-sweep.js'),
        '--love', lovec,
        '--capture-dir', captureDir,
    ], { stdio: 'inherit', env: process.env });
    if (sweep.error) throw sweep.error;
    if (sweep.status !== 0) throw new Error(`#760 representative sweep failed (${sweep.status})`);

    const flat = spawnSync(process.execPath, [
        path.join(__dirname, '..', 'editor', 'bench-height-flat-field.js'),
        '--love', lovec,
        '--output', path.join(captureDir, 'issue-760-flat-summary.json'),
    ], { stdio: 'inherit', env: process.env });
    if (flat.error) throw flat.error;
    if (flat.status !== 0) throw new Error(`#760 exact-flat sweep failed (${flat.status})`);

    compactIssue760Evidence(captureDir);
}

function main() {
    const options = parseArgs(process.argv.slice(2));
    if (!options) {
        console.log('Usage: node tools/ci/stage-project-gates.js [--project dir] [--output dir]');
        return;
    }
    const result = stageProjectGates(options);
    process.stdout.write(`PROJECT GATE STAGE OK ${JSON.stringify(result)}\n`);
    runIssue760EvidenceIfRequested();
}

if (require.main === module) {
    try { main(); }
    catch (error) {
        console.error(error && error.stack ? error.stack : error);
        process.exitCode = 1;
    }
}

module.exports = { parseArgs, stageProjectGates };
