'use strict';

// #487 baseline: what does one ordinary authoring gesture actually cost today?
//
// Measures the SHIPPED production path on main -- the persistent renderable
// worker the Map workspace already uses (RENDERABLE_CONSUMER_DIRECT ->
// renderableEncoding 'instances') -- rather than a branch-local experiment.
//
// Reports the generation-start cost (paid once per authority revision) and the
// per-request warm cost (paid on every gesture), because #487's target is the
// second number and only the second number.
//
//   node studio/editor/bench-authoring-latency.js --map 1 --runs 8

const path = require('node:path');
const { performance } = require('node:perf_hooks');
const { createRuntimeRenderableWorker } = require('./runtime-renderable-worker');
const projectRoot = require('./project-root');

function argument(name, fallback) {
    const index = process.argv.indexOf(name);
    return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
}

function quantiles(values) {
    const s = [...values].sort((a, b) => a - b);
    const at = q => s[Math.min(s.length - 1, Math.floor(q * s.length))];
    return { min: s[0], p50: at(0.5), p90: at(0.9), max: s[s.length - 1] };
}

function ms(v) { return `${v.toFixed(1)} ms`; }

async function main() {
    const mapId = Number(argument('--map', '1'));
    const runs = Number(argument('--runs', '8'));
    const loveExe = argument('--love', process.env.LOVE_PATH || 'C:/Program Files/LOVE/lovec.exe');

    // The bridge server parses the worker's framed stdout into a bundle. For a
    // latency baseline the payload shape is irrelevant, so keep the raw text
    // and measure bytes -- that is also what #736's transport ceiling cares
    // about.
    const parseOutput = text => ({ bytes: Buffer.byteLength(text, 'utf8') });

    const worker = createRuntimeRenderableWorker({
        installRoot: projectRoot.INSTALL_ROOT,
        projectRoot: projectRoot.PROJECT_ROOT,
        previewExe: loveExe,
        parseOutput,
        timeoutMs: 120000,
        maxOutputBytes: 512 * 1024 * 1024,
    });

    const request = { map: { id: mapId }, seed: 1735689600, renderableEncoding: 'instances' };

    console.log(`map ${mapId} | ${runs} warm runs | ${path.basename(loveExe)}`);

    const coldStart = performance.now();
    const first = await worker.compile(request);
    const cold = performance.now() - coldStart;
    console.log(`cold (generation start + first request): ${ms(cold)}`);
    console.log(`bundle: ${(first.bytes / 1048576).toFixed(2)} MiB`);

    const warm = [];
    for (let i = 0; i < runs; i++) {
        const t = performance.now();
        await worker.compile(request);
        warm.push(performance.now() - t);
    }
    const q = quantiles(warm);
    console.log(`warm per request: min ${ms(q.min)} | p50 ${ms(q.p50)} | p90 ${ms(q.p90)} | max ${ms(q.max)}`);

    // What the artist actually waits: the Studio debounce sits in front of every
    // one of these, so the felt latency is debounce + warm request + rebuild.
    console.log(`felt latency (180 ms debounce + p50 request): ${ms(180 + q.p50)}`);

    await worker.shutdown();
}

main().catch(error => { console.error(error); process.exit(1); });
