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

        function drawString(ctx, text, x, y, options) {
            options = options || {};
            const defaultColor = options.color || [1, 1, 1, 1];
            ctx.save();
            applyFont(ctx);
            let cursor = x;
            const baseline = y + fontOffsetY;
            for (const run of parseRichText(String(text === undefined ? '' : text), defaultColor)) {
                ctx.fillStyle = rgba(run.color);
                ctx.fillText(run.text, cursor, baseline);
                cursor += ctx.measureText(run.text).width;
            }
            ctx.restore();
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
            parseRichText,
            themeCss,
            missingAssets,
            snapRect,
        };
    }

    return { create, snapRect, rgba };
}));
