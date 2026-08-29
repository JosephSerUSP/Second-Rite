'use strict';

// #968 adapter parity gate.
//
// The rule the #965 audit set: `preview-*` stays, and it is the REFERENCE.
// LÖVE renders the corpus in runtime/presentation/parity_cases.json; the
// browser adapter renders the same corpus in headless Chrome; the LÖVE PNG is
// truth and any difference is a bug in the adapter. That ordering is what
// keeps the adapter an adapter: it can never be "right" in a way the game is
// not, so it can never quietly become a second presentation authority.
//
// Scope of the exact tier is deliberate. Text and the target reticle are not
// in the corpus: glyph rasterization differs between the hosts by construction
// (audit S4.4) and the reticle oscillates on wall-clock time. What remains is
// nine-slice blitting through the same rectangles, which has no excuse to
// differ by a single pixel.
//
//   node tools/presentation/parity/run-parity.js [--out <dir>] [--keep-stage]

const { execFileSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const contractBuilder = require('../contract');

const REPO = path.resolve(__dirname, '..', '..', '..');
const PROJECT = path.join(REPO, 'projects', 'hichaukitoden-game');
const RUNTIME = path.join(REPO, 'runtime');
const RTP = path.join(REPO, 'rtp');
const CASES = path.join(RUNTIME, 'presentation', 'parity_cases.json');
const ADAPTER = path.join(__dirname, '..', 'adapter', 'second-gate-ui.js');

function lovecBinary() {
    if (process.env.LOVEC) return process.env.LOVEC;
    const windowsDefault = 'C:/Program Files/LOVE/lovec.exe';
    if (process.platform === 'win32' && fs.existsSync(windowsDefault)) return windowsDefault;
    return 'lovec';
}

function envelope(text, begin = 'PREVIEW BEGIN', end = 'PREVIEW END') {
    const from = text.indexOf(begin);
    const to = text.indexOf(end);
    if (from === -1 || to === -1 || to < from) {
        throw new Error(`LÖVE produced no ${begin} envelope. Output was:\n${text}`);
    }
    return JSON.parse(text.slice(from + begin.length, to).trim());
}

function captureReference(stageDir) {
    const output = execFileSync(lovecBinary(), [stageDir, 'presentation-parity-fixture'],
        { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024, stdio: ['ignore', 'pipe', 'pipe'] });
    const payload = envelope(output);
    if (payload.error) throw new Error(`LÖVE parity fixture failed: ${payload.error}`);
    if (!payload.image) throw new Error('LÖVE parity fixture returned no image');
    return payload;
}

// Deliberate breakages, used by tools/presentation/parity/negative-control.js.
//
// A parity gate that has never been seen to fail is not evidence. Each of
// these is a mistake a real adapter author could make -- an off-by-one border,
// the wrong stretch divisor, a role that silently falls back, a minimum that
// lets a degenerate panel through -- and the gate must redden for every one of
// them. They are applied to the CONTRACT the page receives, so they exercise
// the same code path production does.
const MUTATIONS = {
    'border-off-by-one': contract => { contract.atlas.windowskin.border -= 1; },
    'background-inset': contract => { contract.atlas.windowskin.backgroundInset += 1; },
    'edge-span': contract => { contract.atlas.windowskin.parts.top.w = 8; },
    'panel-minimum': contract => { contract.metrics.panelMinWidth = 24; },
    'corner-origin': contract => { contract.atlas.windowskin.parts.br.x -= 8; },
    'rail-slice': contract => { contract.atlas.windowskin.parts.scrollRail.x += 1; },
    'arrow-alpha': contract => { contract.palettes.chrome.arrowInactiveAlpha = 1; },
};

function mutate(contract, name) {
    if (!name) return contract;
    const mutation = MUTATIONS[name];
    if (!mutation) throw new Error(`unknown mutation '${name}'; known: ${Object.keys(MUTATIONS).join(', ')}`);
    const copy = JSON.parse(JSON.stringify(contract));
    mutation(copy);
    return copy;
}

async function captureCandidate(reference, contract, outDir) {
    const { chromium } = require('playwright');
    const cases = JSON.parse(fs.readFileSync(CASES, 'utf8'));

    // Assets go in as data: URLs so the page needs no server and no network,
    // and so the bytes the adapter draws are provably the Project's bytes.
    const images = {};
    for (const asset of contract.assets) {
        if (asset.resource !== 'system-image' || !asset.available) continue;
        const file = path.join(PROJECT, asset.logicalPath);
        images[asset.role] = `data:image/png;base64,${fs.readFileSync(file).toString('base64')}`;
    }

    const browser = await chromium.launch();
    try {
        const page = await browser.newPage({ viewport: { width: cases.canvas.width, height: cases.canvas.height } });
        page.on('console', message => { if (message.type() === 'error') console.error(`[page] ${message.text()}`); });
        await page.addScriptTag({ path: ADAPTER });

        const dataUrl = await page.evaluate(async ({ contract, cases, sources }) => {
            const images = {};
            await Promise.all(Object.entries(sources).map(([role, src]) => new Promise((resolve, reject) => {
                const image = new Image();
                image.onload = () => { images[role] = image; resolve(); };
                image.onerror = () => reject(new Error(`failed to load ${role}`));
                image.src = src;
            })));

            const canvas = document.createElement('canvas');
            canvas.width = cases.canvas.width;
            canvas.height = cases.canvas.height;
            const ctx = canvas.getContext('2d', { willReadFrequently: true });
            ctx.imageSmoothingEnabled = false;
            ctx.fillStyle = '#000000';
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            const ui = window.SecondGateUI.create({ contract, images });
            for (const item of cases.cases) {
                if (item.kind === 'panel') {
                    ui.drawPanel(ctx, item.x, item.y, item.w, item.h, item.role);
                } else if (item.kind === 'opening') {
                    const r = ui.rescaleRect(item.x, item.y, item.w, item.h, item.progress);
                    ui.drawPanel(ctx, r.x, r.y, r.w, r.h, item.role);
                } else if (item.kind === 'scrollbar') {
                    ui.drawPanel(ctx, item.x, item.y, item.w, item.h, item.role);
                    ui.drawScrollbar(ctx, item.x, item.y, item.w, item.h,
                        item.totalRows, item.visibleRows, item.startOffset);
                } else {
                    throw new Error(`unknown parity case kind: ${item.kind}`);
                }
            }
            return canvas.toDataURL('image/png');
        }, { contract, cases, sources: images });

        const buffer = Buffer.from(dataUrl.split(',')[1], 'base64');
        fs.writeFileSync(path.join(outDir, 'candidate.png'), buffer);
        return buffer;
    } finally {
        await browser.close();
    }
}

// Decoding both PNGs back to raw pixels in the same place, with the same
// decoder, so the comparison cannot be fooled by two encoders disagreeing
// about how to spell an identical image.
async function decode(buffer, width, height) {
    const { chromium } = require('playwright');
    const browser = await chromium.launch();
    try {
        const page = await browser.newPage();
        const data = await page.evaluate(async ({ src, width, height }) => {
            const image = await new Promise((resolve, reject) => {
                const element = new Image();
                element.onload = () => resolve(element);
                element.onerror = () => reject(new Error('decode failed'));
                element.src = src;
            });
            const canvas = document.createElement('canvas');
            canvas.width = width; canvas.height = height;
            const ctx = canvas.getContext('2d', { willReadFrequently: true });
            ctx.imageSmoothingEnabled = false;
            ctx.drawImage(image, 0, 0);
            return Array.from(ctx.getImageData(0, 0, width, height).data);
        }, { src: `data:image/png;base64,${buffer.toString('base64')}`, width, height });
        return Uint8ClampedArray.from(data);
    } finally {
        await browser.close();
    }
}

// Where a difference between the two hosts is legitimate, and where it is not.
//
// Two operations genuinely differ between LOVE and a browser, and both are
// arithmetic, not logic:
//
//   * a STRETCHED edge tile, resampled by LOVE on the GPU and by the browser
//     in its own compositor. Measured at up to 10 levels on 25 pixels of this
//     corpus -- and no hand-rolled sampling loop got closer, see the numbers
//     recorded in the adapter.
//   * an ALPHA-BLENDED blit (the scrollbar arrows draw at 1.0 or 0.25), where
//     the two hosts round the blend differently. Measured at exactly 1 level.
//
// Everything else -- corners, the tiled interior, opaque 1:1 blits, and above
// all the PRESENCE of a shape at a rect -- is a straight copy and has no
// excuse to differ at all. That is the tier that catches adapter bugs: a wrong
// rectangle, a wrong role, a wrong minimum, a wrong opening geometry all move
// pixels far outside any blend band.
//
// The bands are computed from the CONTRACT and the case list, never from the
// adapter, so an adapter bug cannot widen its own tolerance.
const BLEND_TOLERANCE = 16;   // max per-channel delta inside a blended band
const BLEND_BUDGET = 0.05;    // max fraction of band pixels allowed to differ

function blendBands(cases, contract, rescale) {
    const windowskin = contract.atlas.windowskin;
    const border = windowskin.border;
    const spanH = windowskin.parts.top.w;
    const spanV = windowskin.parts.left.h;
    const rail = windowskin.parts.scrollRail;
    const bands = [];

    function panelBands(x, y, w, h) {
        const left = Math.floor(x + 0.5), top = Math.floor(y + 0.5);
        const right = Math.floor(x + w + 0.5), bottom = Math.floor(y + h + 0.5);
        const pw = right - left, ph = bottom - top;
        if (pw < contract.metrics.panelMinWidth || ph < contract.metrics.panelMinHeight) return;
        const edgeW = Math.max(0, pw - border * 2);
        const edgeH = Math.max(0, ph - border * 2);
        if (edgeW !== spanH && edgeW > 0) {
            bands.push({ x: left + border, y: top, w: edgeW, h: border });
            bands.push({ x: left + border, y: top + ph - border, w: edgeW, h: border });
        }
        if (edgeH !== spanV && edgeH > 0) {
            bands.push({ x: left, y: top + border, w: border, h: edgeH });
            bands.push({ x: left + pw - border, y: top + border, w: border, h: edgeH });
        }
    }

    for (const item of cases.cases) {
        if (item.kind === 'panel') {
            panelBands(item.x, item.y, item.w, item.h);
        } else if (item.kind === 'opening') {
            const r = rescale(item.x, item.y, item.w, item.h, item.progress);
            panelBands(r.x, r.y, r.w, r.h);
        } else if (item.kind === 'scrollbar') {
            panelBands(item.x, item.y, item.w, item.h);
            const railX = item.x + item.w - border;
            const railY = item.y + border;
            const railH = Math.max(border, item.h - border * 2);
            bands.push({ x: railX, y: railY, w: rail.w, h: railH });
            // The arrows are 1:1 copies, but drawn through an alpha, so they
            // are a blend band for the same reason a stretch is: the hosts
            // round the composite differently, by one level.
            const arrowX = railX - windowskin.arrowInset;
            const up = windowskin.parts.arrowUp;
            const down = windowskin.parts.arrowDown;
            bands.push({ x: arrowX, y: railY - border, w: up.w, h: up.h });
            bands.push({ x: arrowX, y: railY + railH, w: down.w, h: down.h });
        }
    }
    return bands;
}

function compare(reference, candidate, cases, contract, rescale) {
    const { width, height } = cases.canvas;
    const bands = blendBands(cases, contract, rescale);
    const inBand = new Uint8Array(width * height);
    let bandPixels = 0;
    for (const band of bands) {
        for (let y = band.y; y < band.y + band.h; y += 1) {
            for (let x = band.x; x < band.x + band.w; x += 1) {
                if (x < 0 || y < 0 || x >= width || y >= height) continue;
                if (!inBand[y * width + x]) { inBand[y * width + x] = 1; bandPixels += 1; }
            }
        }
    }

    const perCase = new Map(cases.cases.map(item => [item.name, 0]));
    const untolerated = [];
    let untoleratedCount = 0;
    let toleratedCount = 0;
    let worstTolerated = 0;
    let maxChannel = 0;

    function owner(x, y) {
        for (let index = cases.cases.length - 1; index >= 0; index -= 1) {
            const item = cases.cases[index];
            if (x >= item.x - 2 && x < item.x + item.w + 2 && y >= item.y - 2 && y < item.y + item.h + 2) return item.name;
        }
        return '(outside every case)';
    }

    for (let y = 0; y < height; y += 1) {
        for (let x = 0; x < width; x += 1) {
            const at = (y * width + x) * 4;
            let worst = 0;
            for (let channel = 0; channel < 4; channel += 1) {
                worst = Math.max(worst, Math.abs(reference[at + channel] - candidate[at + channel]));
            }
            if (worst === 0) continue;
            maxChannel = Math.max(maxChannel, worst);
            const name = owner(x, y);
            perCase.set(name, (perCase.get(name) || 0) + 1);
            if (inBand[y * width + x] && worst <= BLEND_TOLERANCE) {
                toleratedCount += 1;
                worstTolerated = Math.max(worstTolerated, worst);
                continue;
            }
            untoleratedCount += 1;
            if (untolerated.length < 20) {
                const where = inBand[y * width + x] ? 'blend band, OVER tolerance' : 'exact region';
                untolerated.push('(' + x + ',' + y + ') in ' + name + ' [' + where + ']: reference rgba('
                    + reference.slice(at, at + 4).join(',') + ') vs candidate rgba('
                    + candidate.slice(at, at + 4).join(',') + ') delta ' + worst);
            }
        }
    }
    return { untoleratedCount, untolerated, toleratedCount, worstTolerated, bandPixels, perCase, maxChannel, total: width * height };
}

async function main() {
    const args = process.argv.slice(2);
    const outIndex = args.indexOf('--out');
    const outDir = outIndex === -1
        ? fs.mkdtempSync(path.join(os.tmpdir(), 'sg-parity-'))
        : path.resolve(args[outIndex + 1]);
    fs.mkdirSync(outDir, { recursive: true });

    const stageDir = fs.mkdtempSync(path.join(os.tmpdir(), 'sg-parity-stage-'));
    let referencePayload;
    try {
        execFileSync(process.execPath, [path.join(REPO, 'tools', 'ci', 'stage-project-gates.js'), '--output', stageDir],
            { stdio: 'inherit' });
        referencePayload = captureReference(stageDir);
    } finally {
        if (!args.includes('--keep-stage')) fs.rmSync(stageDir, { recursive: true, force: true });
    }

    const referenceBuffer = Buffer.from(referencePayload.image, 'base64');
    fs.writeFileSync(path.join(outDir, 'reference.png'), referenceBuffer);

    const contract = contractBuilder.build({ projectDir: PROJECT, runtimeDir: RUNTIME, rtpRoot: RTP });
    const cases = JSON.parse(fs.readFileSync(CASES, 'utf8'));
    if (referencePayload.caseCount !== cases.cases.length) {
        throw new Error(`LÖVE drew ${referencePayload.caseCount} cases, the corpus declares ${cases.cases.length}`);
    }

    const mutationIndex = args.indexOf('--mutate');
    const mutation = mutationIndex === -1 ? null : args[mutationIndex + 1];
    if (mutation) console.log(`MUTATION ACTIVE: ${mutation} (the gate is expected to fail)`);
    const candidateBuffer = await captureCandidate(referencePayload, mutate(contract, mutation), outDir);
    const [reference, candidate] = await Promise.all([
        decode(referenceBuffer, cases.canvas.width, cases.canvas.height),
        decode(candidateBuffer, cases.canvas.width, cases.canvas.height),
    ]);

    const adapter = require(ADAPTER);
    const rescale = (x, y, w, h, p) => adapter.create({ contract, images: {} }).rescaleRect(x, y, w, h, p);
    const result = compare(reference, candidate, cases, contract, rescale);
    const budget = Math.floor(result.bandPixels * BLEND_BUDGET);

    console.log(`contract identity: ${contract.identity}`);
    console.log(`cases: ${cases.cases.length}`);
    console.log(`host-blend band pixels: ${result.bandPixels} / ${result.total}`);
    console.log(`tolerated inside bands: ${result.toleratedCount} / budget ${budget} (worst channel delta ${result.worstTolerated} / limit ${BLEND_TOLERANCE})`);
    console.log(`differences the gate does not tolerate: ${result.untoleratedCount}`);

    if (result.untoleratedCount === 0 && result.toleratedCount <= budget) {
        console.log('PRESENTATION ADAPTER PARITY OK');
        return;
    }
    if (result.toleratedCount > budget) {
        console.error(`\nhost-blend drift exceeded its budget: ${result.toleratedCount} > ${budget}`);
        console.error('Small per-pixel deltas are expected where a tile is stretched or blended, but');
        console.error('not across whole bands -- that pattern means a wrong stretch factor or a wrong');
        console.error('alpha, which is an adapter bug wearing a tolerable-looking magnitude.');
    }
    console.error('per case (every difference, tolerated ones included):');
    for (const [name, count] of [...result.perCase].sort((a, b) => b[1] - a[1])) {
        if (count > 0) console.error(`  ${name}: ${count}`);
    }
    if (result.untolerated.length) {
        console.error('differences the gate does NOT tolerate:');
        for (const sample of result.untolerated) console.error(`  ${sample}`);
    }
    console.error(`\nreference.png and candidate.png written to ${outDir}`);
    console.error('\nThe LÖVE render is the reference. A difference here is a bug in the');
    console.error('browser adapter, never a reason to change the game or a golden.');
    process.exitCode = 1;
}

if (require.main === module) {
    main().catch(error => {
        console.error(error.stack || String(error));
        process.exitCode = 1;
    });
}

module.exports = { MUTATIONS };
