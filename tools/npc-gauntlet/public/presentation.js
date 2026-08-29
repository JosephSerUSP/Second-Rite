'use strict';

// #969: show a gauntlet transcript the way the game shows it.
//
// The lab's question is whether a proposed line sounds like the character.
// Answering it against `system-ui` on a white card, next to no one, is judging
// the wrong artifact -- so a line is drawn in a real Second Gate message
// window, in the Project's font, beside whatever sprite the Project itself
// authors for that speaker.
//
// Everything visual comes from the #967 contract through the #968 adapter.
// This file owns no rectangle, no colour and no font: it decides layout inside
// the window and nothing else. The raw JSON stays one click away, because the
// transcript is evidence and its provenance must not be dressed up.

const SecondGatePresentation = (function () {
    const ASSET_BASE = '/project-asset/';
    let state = null;

    function loadImage(src) {
        return new Promise(resolve => {
            const image = new Image();
            image.onload = () => resolve(image);
            image.onerror = () => resolve(null);   // absence is reported, not thrown
            image.src = src;
        });
    }

    async function boot() {
        if (state) return state;
        const response = await fetch('/api/presentation');
        const body = await response.json();
        if (!response.ok || body.success === false) {
            throw new Error(body.message || `presentation contract unavailable (HTTP ${response.status})`);
        }

        const images = {};
        await Promise.all((body.contract.assets || [])
            .filter(asset => asset.resource === 'system-image' && asset.available)
            .map(async asset => {
                const image = await loadImage(ASSET_BASE + asset.logicalPath);
                if (image) images[asset.role] = image;
            }));

        const ui = window.SecondGateUI.create({ contract: body.contract, images });
        const style = document.createElement('style');
        style.textContent = ui.themeCss({ assetBase: ASSET_BASE });
        document.head.appendChild(style);

        state = { ui, contract: body.contract, speakers: body.speakers, images, sprites: new Map() };
        return state;
    }

    async function spriteFor(speaker) {
        if (!state) return null;
        const entry = state.speakers[speaker];
        if (!entry || !entry.sprite || !entry.available) return null;
        if (!state.sprites.has(entry.sprite)) {
            state.sprites.set(entry.sprite, await loadImage(ASSET_BASE + entry.sprite));
        }
        return state.sprites.get(entry.sprite) || null;
    }

    // A sprite sheet is a strip of frames; the standing front-facing frame is
    // the first cell. Frame geometry is `sprite-timing`/`sprite-resolution`
    // territory and this lab does not need the animation, so it takes the
    // leftmost square cell and says so rather than pretending to know more.
    function firstFrame(image) {
        if (!image) return null;
        const size = Math.min(image.width, image.height);
        return { sx: 0, sy: 0, sw: size, sh: size };
    }

    function escapeHtml(value) {
        return String(value).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    }

    // Wrap to a pixel limit using THIS host's measurement. The words and their
    // order are exact; the break points are approximate by construction,
    // because LOVE rasterizes with its own metrics (#965 audit S4.4). Inline
    // \c[n] codes are stripped before measuring, exactly as ui.wrapText does --
    // measuring the raw string overestimates every word carrying one.
    function wrap(ctx, text, limit) {
        const words = String(text || '').split(/\s+/).filter(Boolean);
        const rows = [];
        let line = '';
        for (const word of words) {
            const candidate = line ? line + ' ' + word : word;
            if (line && ctx.measureText(candidate.replace(/\\c\[\d+\]/g, '')).width > limit) {
                rows.push(line);
                line = word;
            } else {
                line = candidate;
            }
        }
        if (line) rows.push(line);
        return rows;
    }

    // One dialogue frame: a message window the width of the game screen, with
    // the speaker standing beside their line.
    //
    // The row step is the authored FONT size, not the tile: the tile grid
    // positions windows, but a 16px face stepped by an 8px tile writes each
    // line through the one above it.
    function drawLine(canvas, speaker, text, sprite) {
        const { ui, contract } = state;
        const tile = contract.metrics.tileSize;
        const step = contract.project.fontSize || tile;
        const width = contract.metrics.screenWidthTiles * tile;
        const scale = Number(canvas.dataset.scale || 2);
        const face = contract.font.engineDefault
            ? 'monospace'
            : '"SecondGate-' + contract.font.active + '", monospace';

        const portraitW = sprite ? tile * 6 : 0;
        const textX = portraitW + tile;
        const limit = width - textX - tile;

        // Measure before sizing: the window has to be tall enough for the line
        // it was given, and for a sprite that is taller than the text.
        const measurer = document.createElement('canvas').getContext('2d');
        measurer.font = step + 'px ' + face;
        const rows = wrap(measurer, text, limit);
        const textHeight = tile * 3 + rows.length * step + tile;
        const height = Math.max(tile * 9, sprite ? portraitW + tile : 0, textHeight);

        canvas.width = width;
        canvas.height = height;
        canvas.style.width = (width * scale) + 'px';
        canvas.style.height = (height * scale) + 'px';

        const ctx = canvas.getContext('2d');
        ctx.imageSmoothingEnabled = false;
        ctx.clearRect(0, 0, width, height);

        ui.drawPanel(ctx, 0, 0, width, height);

        if (sprite) {
            const frame = firstFrame(sprite);
            ctx.drawImage(sprite, frame.sx, frame.sy, frame.sw, frame.sh,
                tile, tile, portraitW - tile, portraitW - tile);
        }

        ui.drawString(ctx, speaker, textX, tile, { color: contract.palettes.chrome.panelTitle });
        rows.forEach(function (row, index) {
            ui.drawString(ctx, row, textX, tile * 3 + index * step);
        });
    }

    // Turn a transcript into dialogue frames. Anything without a speaker and
    // text stays raw: the lab must not invent a speaker to make a line
    // presentable.
    function linesOf(transcript) {
        if (!Array.isArray(transcript)) return [];
        return transcript
            .map(turn => ({
                speaker: turn && (turn.speaker || turn.actor || turn.name),
                text: turn && (turn.text || turn.line || turn.content),
            }))
            .filter(turn => typeof turn.speaker === 'string' && turn.speaker && typeof turn.text === 'string' && turn.text);
    }

    async function renderTranscript(container, transcript) {
        await boot();
        const lines = linesOf(transcript);
        if (!lines.length) return false;

        container.innerHTML = '';
        container.classList.add('sg-pixel', 'sg-transcript');
        for (const line of lines) {
            const entry = state.speakers[line.speaker];
            const wrapper = document.createElement('div');
            wrapper.className = 'sg-line';

            const canvas = document.createElement('canvas');
            wrapper.appendChild(canvas);

            if (entry && entry.ambiguous) {
                // The Project authors this speaker more than one way. Say so and
                // let the researcher choose; picking silently would mean judging
                // a line against a face the game might not use.
                const note = document.createElement('div');
                note.className = 'sg-note';
                note.innerHTML = `<strong>${escapeHtml(line.speaker)}</strong> is authored with `
                    + `${entry.ambiguous.length} different sprites — choose one: `
                    + `<select>${['(none)'].concat(entry.ambiguous).map(p => `<option>${escapeHtml(p)}</option>`).join('')}</select>`;
                note.querySelector('select').onchange = async event => {
                    const chosen = event.target.value;
                    if (chosen === '(none)') { drawLine(canvas, line.speaker, line.text, null); return; }
                    if (!state.sprites.has(chosen)) state.sprites.set(chosen, await loadImage(ASSET_BASE + chosen));
                    drawLine(canvas, line.speaker, line.text, state.sprites.get(chosen));
                };
                wrapper.appendChild(note);
            } else if (!entry) {
                const note = document.createElement('div');
                note.className = 'sg-note';
                note.textContent = `${line.speaker} has no authored map event, so the Project declares no sprite for them.`;
                wrapper.appendChild(note);
            }

            container.appendChild(wrapper);
            drawLine(canvas, line.speaker, line.text, await spriteFor(line.speaker));
        }
        return true;
    }

    function missingReport() {
        return state ? state.ui.missingAssets() : [];
    }

    return { boot, renderTranscript, linesOf, missingReport, drawLine };
}());

if (typeof module === 'object' && module.exports) module.exports = SecondGatePresentation;
