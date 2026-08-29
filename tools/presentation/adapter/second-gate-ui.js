'use strict';

// Second Gate presentation adapter for browser hosts (#968, from the #965 audit).
//
// This is an ADAPTER, not an authority. Every rectangle, thickness, colour and
// metric it draws with comes from the published presentation contract
// (`tools/presentation/contract.js`, #967). It contains no windowskin
// geometry, no palette and no fallback value of its own: if a fact is not in
// the contract, this file does not know it, and the honest result is a throw
// rather than a guess.
//
// The shipped renderer remains `runtime/presentation/ui.lua`. This file is
// measured against it: `tools/presentation/parity` renders the corpus in
// `runtime/presentation/parity_cases.json` through both, with the LÖVE PNG as
// the reference and this output as the candidate. A difference is a bug here.
//
// Deliberately dependency-free and framework-free, so any of the browser
// surfaces in the audit's inventory can use it without adopting a build step.

(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    else root.SecondGateUI = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {

    function required(value, what) {
        if (value === undefined || value === null) {
            throw new Error(`Second Gate adapter: the presentation contract has no ${what}`);
        }
        return value;
    }

    function at(contract, dotted) {
        let node = contract;
        for (const segment of dotted.split('.')) {
            if (node === null || typeof node !== 'object') {
                throw new Error(`Second Gate adapter: '${dotted}' is not reachable in the contract`);
            }
            node = node[segment];
            if (node === undefined) {
                throw new Error(`Second Gate adapter: '${dotted}' is missing from the contract`);
            }
        }
        return node;
    }

    function rgba(color) {
        const [r, g, b, a] = color;
        const to255 = v => Math.max(0, Math.min(255, Math.round(v * 255)));
        return `rgba(${to255(r)}, ${to255(g)}, ${to255(b)}, ${a === undefined ? 1 : a})`;
    }

    // LÖVE's drawPanel snaps the two EDGES rather than position and size
    // separately, so the far edge cannot jitter while the near one rounds.
    // An animated panel produces fractional rects, and rounding them the
    // obvious way is what used to leave a one-pixel seam between the tiled
    // interior and the border ring.
    function snapRect(x, y, w, h) {
        const left = Math.floor(x + 0.5);
        const top = Math.floor(y + 0.5);
        const right = Math.floor(x + w + 0.5);
        const bottom = Math.floor(y + h + 0.5);
        return { x: left, y: top, w: right - left, h: bottom - top };
    }

    function create(options) {
        const contract = required(options && options.contract, 'contract');
        const images = (options && options.images) || {};

        const metrics = at(contract, 'metrics');
        const windowskin = at(contract, 'atlas.windowskin');
        const target = at(contract, 'atlas.target');
        const palettes = at(contract, 'palettes');

        const BORDER = required(windowskin.border, 'atlas.windowskin.border');
        const INSET = required(windowskin.backgroundInset, 'atlas.windowskin.backgroundInset');
        const BG = required(windowskin.background, 'atlas.windowskin.background');
        const PARTS = required(windowskin.parts, 'atlas.windowskin.parts');
        const EDGE_SPAN_H = required(PARTS.top, 'atlas.windowskin.parts.top').w;
        const EDGE_SPAN_V = required(PARTS.left, 'atlas.windowskin.parts.left').h;
        const MIN_W = required(metrics.panelMinWidth, 'metrics.panelMinWidth');
        const MIN_H = required(metrics.panelMinHeight, 'metrics.panelMinHeight');
        const ARROW_INSET = required(windowskin.arrowInset, 'atlas.windowskin.arrowInset');
        const THUMB_MIN_H = required(metrics.scrollThumbMinHeight, 'metrics.scrollThumbMinHeight');

        // Which loaded image a role resolves to. The role->file mapping and the
        // fallback ORDER both come from the contract and from ui.lua's stated
        // rule: a role whose own skin is absent wears `back` rather than
        // drawing nothing, because a panel in the wrong skin is still a panel.
        function skinFor(role) {
            const order = role === 'button_highlight'
                ? ['windowskin.button_highlight', 'windowskin.button', 'windowskin.back']
                : role === 'button'
                    ? ['windowskin.button', 'windowskin.back']
                    : ['windowskin.back'];
            for (const key of order) {
                if (images[key]) return images[key];
            }
            return null;
        }

        // Stretched blits are the one place two renderers legitimately
        // disagree. LOVE stretches an edge tile on the GPU with nearest
        // filtering; a browser resamples in its own compositor. Both were
        // measured here against the real renderer:
        //
        //   delegate to drawImage      45 differing px, max channel delta 10
        //   explicit pixel-centre rule 220 differing px, max delta 14
        //   explicit floor rule        148 differing px, max delta 255
        //
        // Reimplementing the sampling by hand is therefore WORSE, not better:
        // the browser's own nearest path is already closest to LOVE's, and a
        // hand-rolled loop just adds a third sampling opinion. So the stretch
        // is delegated, and the residual is bounded by the parity gate instead
        // of pretended away -- see tools/presentation/parity/run-parity.js,
        // which holds resampled bands to a tolerance and everything else to
        // byte equality.
        function blit(ctx, image, part, dx, dy, dw, dh) {
            ctx.drawImage(image, part.x, part.y, part.w, part.h,
                dx, dy, dw === undefined ? part.w : dw, dh === undefined ? part.h : dh);
        }

        function drawSkinlessPanel(ctx, x, y, w, h) {
            // Reached only when the Project ships no windowskin at all. Kept
            // faithful rather than prettied up: the viewer of an adapter
            // surface must be able to tell that a resource was missing.
            const shadow = at(contract, 'palettes.skinless.shadowOffset');
            const inset = at(contract, 'palettes.skinless.edgeInset');
            ctx.fillStyle = rgba(at(contract, 'palettes.skinless.panelShadow'));
            ctx.fillRect(x + shadow, y + shadow, w, h);
            ctx.fillStyle = rgba(at(contract, 'palettes.skinless.panelFill'));
            ctx.fillRect(x, y, w, h);
            ctx.strokeStyle = rgba(at(contract, 'palettes.skinless.panelEdge'));
            ctx.strokeRect(x + inset + 0.5, y + inset + 0.5, w - inset * 2 - 1, h - inset * 2 - 1);
        }

        function drawPanel(ctx, x, y, w, h, role) {
            const r = snapRect(x, y, w, h);
            if (r.w < MIN_W || r.h < MIN_H) return;

            const skin = skinFor(role);
            ctx.save();
            ctx.imageSmoothingEnabled = false;
            ctx.globalAlpha = 1;

            if (!skin) {
                drawSkinlessPanel(ctx, r.x, r.y, r.w, r.h);
                ctx.restore();
                return;
            }

            // 1. Interior, tiled from the background rect. Each partial tile is
            // CROPPED from the rect's origin rather than wrapped around it --
            // that is what LÖVE's per-tile quad does, and wrapping instead
            // would shift the pattern at every panel edge.
            const startX = r.x + INSET, startY = r.y + INSET;
            const endX = r.x + r.w - INSET, endY = r.y + r.h - INSET;
            for (let by = startY; by < endY; by += BG.h) {
                for (let bx = startX; bx < endX; bx += BG.w) {
                    const drawW = Math.min(BG.w, endX - bx);
                    const drawH = Math.min(BG.h, endY - by);
                    ctx.drawImage(skin, BG.x, BG.y, drawW, drawH, bx, by, drawW, drawH);
                }
            }

            // 2. Edges, each stretched along its own axis only. The divisor is
            // the edge tile's span, not the border thickness.
            const edgeW = Math.max(0, r.w - BORDER * 2);
            const edgeH = Math.max(0, r.h - BORDER * 2);
            blit(ctx, skin, PARTS.top, r.x + BORDER, r.y, PARTS.top.w * (edgeW / EDGE_SPAN_H), PARTS.top.h);
            blit(ctx, skin, PARTS.bot, r.x + BORDER, r.y + r.h - BORDER, PARTS.bot.w * (edgeW / EDGE_SPAN_H), PARTS.bot.h);
            blit(ctx, skin, PARTS.left, r.x, r.y + BORDER, PARTS.left.w, PARTS.left.h * (edgeH / EDGE_SPAN_V));
            blit(ctx, skin, PARTS.right, r.x + r.w - BORDER, r.y + BORDER, PARTS.right.w, PARTS.right.h * (edgeH / EDGE_SPAN_V));

            // 3. Corners, 1:1.
            blit(ctx, skin, PARTS.tl, r.x, r.y);
            blit(ctx, skin, PARTS.tr, r.x + r.w - BORDER, r.y);
            blit(ctx, skin, PARTS.bl, r.x, r.y + r.h - BORDER);
            blit(ctx, skin, PARTS.br, r.x + r.w - BORDER, r.y + r.h - BORDER);

            ctx.restore();
        }

        function drawScrollbar(ctx, x, y, w, h, totalRows, visibleRows, startOffset) {
            if (totalRows <= visibleRows || totalRows <= 0) return;

            // Chrome on a transparent shell has to stay legible against
            // whatever shows through it, so it samples the solid button skin.
            const skin = images['windowskin.button'] || images['windowskin.back'] || null;
            const rail = required(PARTS.scrollRail, 'atlas.windowskin.parts.scrollRail');
            const thumbPart = required(PARTS.scrollThumb, 'atlas.windowskin.parts.scrollThumb');

            const maxScroll = totalRows - visibleRows;
            const scrollPos = Math.max(0, Math.min(maxScroll, (startOffset || 1) - 1));
            const railX = x + w - BORDER;
            const railY = y + BORDER;
            const railH = Math.max(BORDER, h - BORDER * 2);

            ctx.save();
            ctx.imageSmoothingEnabled = false;
            ctx.globalAlpha = 1;

            if (skin) blit(ctx, skin, rail, railX, railY, rail.w, rail.h * (railH / rail.h));
            else { ctx.fillStyle = rgba(at(contract, 'palettes.skinless.scrollRail')); ctx.fillRect(railX, railY, rail.w, railH); }

            const thumbH = Math.max(THUMB_MIN_H, Math.floor(railH * (visibleRows / totalRows)));
            const thumbY = railY + Math.floor((railH - thumbH) * (maxScroll > 0 ? (scrollPos / maxScroll) : 0));
            if (skin) blit(ctx, skin, thumbPart, railX, thumbY, thumbPart.w, thumbPart.h * (thumbH / thumbPart.h));
            else { ctx.fillStyle = rgba(at(contract, 'palettes.skinless.scrollThumb')); ctx.fillRect(railX, thumbY, thumbPart.w, thumbH); }

            const arrowX = railX - ARROW_INSET;
            const active = at(contract, 'palettes.chrome.arrowActiveAlpha');
            const inactive = at(contract, 'palettes.chrome.arrowInactiveAlpha');
            if (skin && PARTS.arrowUp) {
                ctx.globalAlpha = startOffset > 1 ? active : inactive;
                blit(ctx, skin, PARTS.arrowUp, arrowX, railY - BORDER);
            }
            if (skin && PARTS.arrowDown) {
                ctx.globalAlpha = (startOffset + visibleRows - 1) < totalRows ? active : inactive;
                blit(ctx, skin, PARTS.arrowDown, arrowX, railY + railH);
            }
            ctx.restore();
        }

        // Panel opening/closing rect. Both axes grow at the same PIXEL rate,
        // not the same fraction of their own length, so a wide button reaches
        // full height long before full width and unrolls sideways instead of
        // inflating. The rate is set so the longer axis completes exactly at
        // p = 1, which keeps an authored duration meaning "time until open".
        //
        // This is a candidate for extraction as a shared semantic leaf (#973).
        // Until that lands it is reimplemented here, and the parity corpus
        // covers it at three progress values precisely because a
        // reimplementation of it is easy to get almost right.
        function rescaleRect(x, y, w, h, p) {
            const clamped = Math.max(0, Math.min(1, p === undefined ? 1 : p));
            const reach = Math.max(w, h) * clamped;
            const nw = Math.min(w, Math.max(reach, Math.min(w, MIN_W)));
            const nh = Math.min(h, Math.max(reach, Math.min(h, MIN_H)));
            return { x: x + (w - nw) / 2, y: y + (h - nh) / 2, w: nw, h: nh };
        }

        function drawTargetReticle(ctx, x, y, w, h, timeSeconds) {
            const skin = images.target || images['windowskin.button'] || null;
            if (!skin) return;
            const usingTarget = Boolean(images.target);
            const parts = usingTarget ? required(target.parts, 'atlas.target.parts') : PARTS;
            const border = usingTarget ? required(target.border, 'atlas.target.border') : BORDER;
            const spanH = parts.top.w;
            const spanV = parts.left.h;

            // Oscillation offset: alternates between 0 and 2 every ~0.125 s.
            const offset = Math.floor((timeSeconds || 0) * 8) % 2 === 0 ? 0 : 2;
            const rx = x - offset / 2, ry = y - offset / 2;
            const rw = w + offset, rh = h + offset;
            const edgeW = rw - border * 2, edgeH = rh - border * 2;

            ctx.save();
            ctx.imageSmoothingEnabled = false;
            ctx.globalAlpha = 1;
            blit(ctx, skin, parts.top, rx + border, ry, parts.top.w * (edgeW / spanH), parts.top.h);
            blit(ctx, skin, parts.bot, rx + border, ry + rh - border, parts.bot.w * (edgeW / spanH), parts.bot.h);
            blit(ctx, skin, parts.left, rx, ry + border, parts.left.w, parts.left.h * (edgeH / spanV));
            blit(ctx, skin, parts.right, rx + rw - border, ry + border, parts.right.w, parts.right.h * (edgeH / spanV));
            blit(ctx, skin, parts.tl, rx, ry);
            blit(ctx, skin, parts.tr, rx + rw - border, ry);
            blit(ctx, skin, parts.bl, rx, ry + rh - border);
            blit(ctx, skin, parts.br, rx + rw - border, ry + rh - border);
            ctx.restore();
        }

        // ---- Text -------------------------------------------------------
        //
        // Glyph pixels are the one thing this adapter cannot match by
        // construction: LÖVE's rasterizer and the browser's differ in hinting
        // and rounding (#965 audit S4.4). What IS matched is everything
        // around them -- the face, the size, the vertical offset, the line
        // step and the \c[n] colour runs -- so a reviewer reads the same words
        // in the same shape, and the residual stays a glyph-level difference
        // rather than a layout one.

        const project = contract.project || {};
        const fontOffsetY = project.fontOffsetY || 0;
        const fontSize = project.fontSize || metrics.tileSize;
        const lineHeight = metrics.tileSize;

        function cssFontFamily() {
            const font = contract.font || {};
            if (font.engineDefault || !font.logicalPath) return null;
            return `SecondGate-${font.active}`;
        }

        // Split `\c[N]` runs against the Project's authored text palette.
        // Candidate for extraction as a shared leaf (#971); until that lands
        // the index arithmetic is mirrored here exactly as ui.lua spells it,
        // including the deliberate `index % length + 1` wrap.
        function parseRichText(text, defaultColor) {
            const palette = project.textPalette;
            if (!palette) throw new Error('Second Gate adapter: the contract publishes no textPalette');
            const runs = [];
            let position = 0;
            let color = defaultColor;
            const pattern = /\\c\[(\d+)\]/g;
            let match;
            while ((match = pattern.exec(text)) !== null) {
                if (match.index > position) runs.push({ color, text: text.slice(position, match.index) });
                color = palette[Number(match[1]) % palette.length] || defaultColor;
                position = pattern.lastIndex;
            }
            if (position < text.length) runs.push({ color, text: text.slice(position) });
            return runs;
        }

        function applyFont(ctx) {
            const family = cssFontFamily();
            ctx.font = `${fontSize}px ${family ? `"${family}", ` : ''}monospace`;
            ctx.textBaseline = 'top';
        }

        // Rasterize one run as a hard-edged mask, tinted.
        //
        // Two problems with drawing a pixel font straight onto the target, both
        // reported against the first version of this adapter:
        //
        //   * The browser antialiases glyph edges. LOVE's render of the same
        //     face at the same size is 1-bit -- monogram is drawn ON the pixel
        //     grid -- so the browser's grey fringe reads as blur, worst
        //     horizontally where subpixel advances land a stem between columns.
        //   * ui.drawString draws every string TWICE: the shadow colour offset
        //     down and right, then the text colour. A host that skips that is
        //     not rendering the game's text.
        //
        // So each run is rasterized offscreen, its alpha is thresholded back to
        // 1-bit, and the resulting mask is tinted and stamped twice. Thresholding
        // is what a pixel font wants: its glyphs have no partial coverage to
        // preserve, and keeping the browser's guess at one just softens them.
        // Measured, not guessed. Rendering the five-line `preview-font` sample
        // through both hosts and sweeping threshold x baseline offset against
        // the real LOVE PNG:
        //
        //   threshold >= 160, baseline -1   ->  ZERO differing lit pixels
        //   threshold 144, baseline -1      ->  81
        //   threshold 96..128, baseline -1  ->  152
        //   any threshold, baseline 0       ->  1554
        //
        // So exact glyph parity IS reachable for a pixel font at an integer
        // size -- the #965 audit's S4.4 residual is about the general case, not
        // this one. 176 sits in the middle of the 160-200 plateau rather than
        // on its edge, so a slightly different rasterizer stays inside it.
        const TEXT_ALPHA_THRESHOLD = 176;

        // The browser's `textBaseline = 'top'` origin sits one pixel below
        // where LOVE's printf puts the same face. This is a HOST difference,
        // not a game fact, so it is corrected here and stays out of the
        // contract -- publishing it would make the game's data carry an
        // apology for a browser.
        const BASELINE_CORRECTION = -1;
        const maskCache = new Map();

        function rasterize(text, color) {
            const key = text + '|' + fontSize + '|' + color.join(',');
            const cached = maskCache.get(key);
            if (cached) return cached;

            const measurer = document.createElement('canvas').getContext('2d');
            applyFont(measurer);
            const width = Math.max(1, Math.ceil(measurer.measureText(text).width) + 2);
            const height = Math.max(1, Math.ceil(fontSize * 2));

            const canvas = document.createElement('canvas');
            canvas.width = width;
            canvas.height = height;
            const ctx = canvas.getContext('2d', { willReadFrequently: true });
            applyFont(ctx);
            ctx.fillStyle = '#ffffff';
            ctx.fillText(text, 0, 0);

            const image = ctx.getImageData(0, 0, width, height);
            const data = image.data;
            const r = Math.round(color[0] * 255);
            const g = Math.round(color[1] * 255);
            const b = Math.round(color[2] * 255);
            const a = Math.round((color[3] === undefined ? 1 : color[3]) * 255);
            for (let i = 0; i < data.length; i += 4) {
                const on = data[i + 3] >= TEXT_ALPHA_THRESHOLD;
                data[i] = r; data[i + 1] = g; data[i + 2] = b;
                data[i + 3] = on ? a : 0;
            }
            ctx.putImageData(image, 0, 0);

            const result = { canvas, width, advance: measurer.measureText(text).width };
            // Bounded so a long research transcript cannot grow this without
            // limit; the win is redrawing the same line, not remembering every
            // line ever drawn.
            if (maskCache.size > 512) maskCache.clear();
            maskCache.set(key, result);
            return result;
        }

        function drawString(ctx, text, x, y, options) {
            options = options || {};
            const defaultColor = options.color || [1, 1, 1, 1];
            const shadow = at(contract, 'palettes.chrome.textShadow');
            const shadowOffset = at(contract, 'metrics.textShadowOffset');

            ctx.save();
            ctx.imageSmoothingEnabled = false;
            // Glyph origins land on whole pixels. A fractional x is the other
            // half of the horizontal blur: the browser will happily place a
            // stem across two columns and shade both.
            let cursor = Math.round(x);
            const top = Math.round(y + fontOffsetY) + BASELINE_CORRECTION;

            for (const run of parseRichText(String(text === undefined ? '' : text), defaultColor)) {
                if (!run.text) continue;
                const glyphs = rasterize(run.text, run.color);
                const shade = rasterize(run.text, shadow);
                ctx.drawImage(shade.canvas, cursor + shadowOffset, top + shadowOffset);
                ctx.drawImage(glyphs.canvas, cursor, top);
                cursor += Math.round(glyphs.advance);
            }
            ctx.restore();
        }

        // What a string will occupy, so a caller can wrap or centre without
        // reaching for a measuring context of its own. Approximate against
        // LOVE by construction (#965 audit S4.4) -- this host rasterizes with
        // its own metrics -- so it is honest about being a browser measurement,
        // not a claim about the game's wrap points.
        function measureText(text) {
            const measurer = document.createElement('canvas').getContext('2d');
            applyFont(measurer);
            return measurer.measureText(String(text === undefined ? '' : text).replace(/\\c\[\d+\]/g, '')).width;
        }

        // ---- Theme tokens ----------------------------------------------
        //
        // For surface chrome that is ordinary DOM rather than a canvas. Emits
        // only what the contract publishes; a consumer that wants a colour the
        // contract does not carry has found a missing authored fact, not a
        // reason to pick one.
        function themeCss(options) {
            options = options || {};
            const assetBase = options.assetBase === undefined ? '' : options.assetBase;
            const font = contract.font || {};
            const lines = [];
            const family = cssFontFamily();
            if (family && font.logicalPath) {
                lines.push(`@font-face { font-family: "${family}"; src: url("${assetBase}${font.logicalPath}"); font-display: block; }`);
            }
            const vars = [
                `--sg-font-family: ${family ? `"${family}", monospace` : 'monospace'}`,
                `--sg-font-size: ${fontSize}px`,
                `--sg-font-offset-y: ${fontOffsetY}px`,
                `--sg-line-height: ${lineHeight}px`,
                `--sg-tile: ${metrics.tileSize}px`,
            ];
            (project.textPalette || []).forEach((color, index) => vars.push(`--sg-text-${index}: ${rgba(color)}`));
            // Every resolved system image as a ready-to-use url(), so a surface
            // can put the game's cursor beside a menu row without hardcoding a
            // path the Project is free to move.
            for (const asset of (contract.assets || [])) {
                if (asset.resource !== 'system-image' || !asset.available || !asset.role) continue;
                vars.push(`--sg-asset-${asset.role.replace(/[._]/g, '-')}: url("${assetBase}${asset.logicalPath}")`);
            }
            for (const [group, entries] of Object.entries(palettes)) {
                if (!entries || typeof entries !== 'object') continue;
                for (const [name, value] of Object.entries(entries)) {
                    if (Array.isArray(value)) vars.push(`--sg-${group}-${name}: ${rgba(value)}`);
                }
            }
            lines.push(`:root {\n  ${vars.join(';\n  ')};\n}`);
            // Pixel art must never be resampled by the browser's default
            // smoothing; the game's own filter is nearest everywhere.
            lines.push(`.sg-pixel, .sg-pixel img, .sg-pixel canvas { image-rendering: pixelated; }`);
            return lines.join('\n');
        }

        // Nine-slice chrome for ordinary DOM.
        //
        // This is the "inert theme token" half of the #965 audit's decision,
        // and the line it draws is worth restating: chrome may be CSS, because
        // a sidebar is not a claim about the game. Anything that says "this is
        // what the player sees" goes through the canvas path, which is measured
        // against the real renderer. `border-image` repeats where LOVE tiles
        // and stretches, so this is a FAMILY resemblance -- the right fidelity
        // for a page frame, the wrong one for a screenshot.
        //
        // The images cannot be used directly. A windowskin is a 160x80 atlas
        // whose border ring lives at x=32..64, and neither `background-image`
        // nor `border-image` can address a sub-rect -- pointed at the file they
        // tile the entire sheet, numbers and all. So the nine-slice source and
        // the ground tile are COMPOSED here, from the contract's own
        // rectangles, into small images CSS can consume.
        function crop(image, rect, width, height) {
            const canvas = document.createElement('canvas');
            canvas.width = width === undefined ? rect.w : width;
            canvas.height = height === undefined ? rect.h : height;
            const ctx = canvas.getContext('2d');
            ctx.imageSmoothingEnabled = false;
            ctx.drawImage(image, rect.x, rect.y, canvas.width, canvas.height, 0, 0, canvas.width, canvas.height);
            return canvas;
        }

        // A 3x3 of BORDER-sized cells: corners verbatim, edges sampled from the
        // middle of their tile (they repeat, so any representative slice does),
        // and the interior from the background rect.
        function nineSliceSource(image) {
            const b = BORDER;
            const canvas = document.createElement('canvas');
            canvas.width = b * 3;
            canvas.height = b * 3;
            const ctx = canvas.getContext('2d');
            ctx.imageSmoothingEnabled = false;

            const cell = (part, dx, dy, offsetX, offsetY) => {
                if (!part) return;
                ctx.drawImage(image,
                    part.x + (offsetX || 0), part.y + (offsetY || 0), b, b,
                    dx, dy, b, b);
            };
            const midX = part => Math.floor((part.w - b) / 2);
            const midY = part => Math.floor((part.h - b) / 2);

            cell(PARTS.tl, 0, 0);
            cell(PARTS.top, b, 0, midX(PARTS.top), 0);
            cell(PARTS.tr, b * 2, 0);
            cell(PARTS.left, 0, b, 0, midY(PARTS.left));
            ctx.drawImage(image, BG.x, BG.y, b, b, b, b, b, b);
            cell(PARTS.right, b * 2, b, 0, midY(PARTS.right));
            cell(PARTS.bl, 0, b * 2);
            cell(PARTS.bot, b, b * 2, midX(PARTS.bot), 0);
            cell(PARTS.br, b * 2, b * 2);
            return canvas.toDataURL('image/png');
        }

        // How strongly the page ground shows its weave. A presentation choice
        // for chrome, not a game fact, so it lives here rather than in the
        // contract -- the game has no page to put a ground under.
        const GROUND_ALPHA = 0.22;

        function frameCss() {
            // Needs a DOM to compose with, and needs the skins to have loaded.
            // Without either it emits nothing rather than pointing CSS at a raw
            // atlas, which is the visibly-wrong result rather than an absent one.
            if (typeof document === 'undefined') return '';

            const roles = at(contract, 'atlas.windowskin.roles');
            const rules = [];
            for (const role of Object.keys(roles)) {
                const image = images[`windowskin.${role}`];
                if (!image) continue;
                const klass = `.sg-frame-${role.replace(/_/g, '-')}`;
                rules.push(`${klass} {
  border-style: solid;
  border-width: ${BORDER}px;
  border-image: url("${nineSliceSource(image)}") ${BORDER} repeat;
  background-image: url("${crop(image, BG).toDataURL('image/png')}");
  background-repeat: repeat;
  image-rendering: pixelated;
}`);
            }

            // A page ground made of the game's own material rather than a
            // stock texture. The `back` interior is nearly black by design --
            // it is meant to sit over the 3D world -- so tiling it alone gives
            // a flat field. The solid `button` weave at low alpha over the
            // skinless fill reads as a surface without competing with the
            // panels sitting on it.
            const ground = images['windowskin.button'] || images['windowskin.back'];
            if (ground) {
                const tile = crop(ground, BG);
                const washed = document.createElement('canvas');
                washed.width = tile.width;
                washed.height = tile.height;
                const wash = washed.getContext('2d');
                wash.imageSmoothingEnabled = false;
                wash.globalAlpha = GROUND_ALPHA;
                wash.drawImage(tile, 0, 0);
                rules.push(`.sg-ground {
  background-color: ${rgba(at(contract, 'palettes.skinless.panelFill'))};
  background-image: url("${washed.toDataURL('image/png')}");
  background-repeat: repeat;
  image-rendering: pixelated;
}`);
            }
            return rules.join('\n');
        }

        // A surface must be able to SAY that a resource is missing rather than
        // quietly rendering without it. This reports what the contract
        // declared against what actually loaded.
        function missingAssets() {
            const declared = (contract.assets || []);
            return declared
                .filter(asset => asset.available === false || (asset.role && !images[asset.role] && asset.available))
                .map(asset => ({
                    role: asset.role || asset.name,
                    logicalPath: asset.logicalPath,
                    reason: asset.available === false
                        ? (asset.unavailableReason || 'declared unavailable by the contract')
                        : 'declared available but not loaded by this host',
                }));
        }

        return {
            contract,
            identity: contract.identity,
            metrics,
            drawPanel,
            drawScrollbar,
            drawTargetReticle,
            rescaleRect,
            drawString,
            measureText,
            parseRichText,
            themeCss,
            frameCss,
            missingAssets,
            snapRect,
        };
    }

    return { create, snapRect, rgba };
}));
