// ============================================================================
// #547 EXPERIMENT C — MAP-CONTEXTUAL TILESET AUTHORING
// ----------------------------------------------------------------------------
// DISPOSABLE INTERACTION PROTOTYPE. Deliberately not production code and
// deliberately NOT a recommendation to merge.
//
// Hypothesis: the most trustworthy specimen of a Tileset is the real Map using
// it. So the author clicks a visible wall/floor/door/fixture in the Map, the
// prototype names the semantic owner that produced it, and the owner is edited
// in place while the Map stays on screen.
//
// OFF BY DEFAULT. Enable with `?exp=tileset-map-context` (which persists the
// flag) or localStorage `thestraExpTilesetMapContext = '1'`. Nothing below runs
// otherwise, so committed editor canon renders exactly as it does on main.
//
// CROSS-SURFACE RULE, honoured:
//   * no authored object is ever sent between windows;
//   * selection travels as runtime provenance FACTS (cell + role + variantId);
//   * the authored record is re-read from the Project authority (/api/tilesets);
//   * a commit is announced as resource identity and siblings re-read;
//   * provisional editor marking is an additive overlay that is visually and
//     textually distinct from authoritative runtime output.
// ============================================================================
(function () {
    'use strict';

    const FLAG = 'thestraExpTilesetMapContext';

    function enabled() {
        try {
            const params = new URLSearchParams(window.location.search);
            if (params.get('exp') === 'tileset-map-context') {
                localStorage.setItem(FLAG, '1');
                return true;
            }
            if (params.get('exp') === 'off') {
                localStorage.removeItem(FLAG);
                return false;
            }
            return localStorage.getItem(FLAG) === '1';
        } catch (error) {
            return false;
        }
    }

    if (!enabled()) return;

    const Model = window.ThestraTilesetMapContext;
    const workspaceContext = window.ThestraMapWorkspaceContext;
    const toolbarMount = window.ThestraMapWorkspaceToolbar;
    if (!Model || !workspaceContext || !toolbarMount) {
        console.warn('#547 Map-context experiment needs the Map workspace membrane; not installing.');
        return;
    }

    // --- state ---------------------------------------------------------------
    let record = null;             // working copy of the authored tileset record
    let baselineJson = null;       // loaded revision, for dirty/discard
    let recordId = null;
    let textures = [];
    let selection = null;          // { provenance, roleKey, variantId }
    let census = {};               // realized variant occupancy from the bundle
    let pickMode = null;           // { variantId, roleKey } while source-picking
    let provisionalSince = null;   // ms timestamp of the last provisional edit
    let lastCorrectionMs = null;
    let correctionFailure = null;
    let provisionalMarked = 0;
    let sourceImage = null;
    let sourceImagePath = null;
    let paletteOpen = false;
    const metrics = { contextChanges: 0, rawCoordinateUses: 0, rawJsonUses: 0 };

    function deepClone(value) { return value == null ? value : JSON.parse(JSON.stringify(value)); }

    function toast(message, kind) {
        if (typeof showToast === 'function') showToast(message, kind);
        else console.log(`[#547] ${message}`);
    }

    // --- chrome --------------------------------------------------------------
    const panel = document.createElement('aside');
    panel.id = 'exp547-map-context';
    panel.setAttribute('aria-label', 'Environment palette (experiment)');
    panel.style.cssText = [
        'position:absolute', 'top:34px', 'right:6px', 'width:328px',
        'max-height:calc(100% - 46px)', 'z-index:25', 'display:none',
        'flex-direction:column', 'overflow:hidden',
        'background:var(--win-gray)', 'border:2px solid',
        'border-color:var(--win-white) var(--win-shadow) var(--win-shadow) var(--win-white)',
        'font-size:10px', 'box-sizing:border-box',
    ].join(';');

    const titleBar = document.createElement('div');
    titleBar.style.cssText = 'flex:0 0 auto;display:flex;align-items:center;gap:4px;padding:3px 4px;background:var(--win-navy,#000080);color:#fff;font-weight:bold;';
    const titleText = document.createElement('span');
    titleText.textContent = 'Environment · exp #547';
    titleText.style.cssText = 'flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;';
    const paletteToggle = document.createElement('button');
    paletteToggle.type = 'button';
    paletteToggle.className = 'win98-btn';
    paletteToggle.style.cssText = 'font-size:9px;padding:0 4px;';
    paletteToggle.textContent = 'Palette';
    paletteToggle.title = 'Show the whole visual vocabulary of this place';
    const closeButton = document.createElement('button');
    closeButton.type = 'button';
    closeButton.className = 'win98-btn';
    closeButton.style.cssText = 'font-size:9px;padding:0 4px;';
    closeButton.textContent = '×';
    titleBar.append(titleText, paletteToggle, closeButton);

    const body = document.createElement('div');
    body.style.cssText = 'flex:1;min-height:0;overflow:auto;padding:6px;box-sizing:border-box;';

    const footer = document.createElement('div');
    footer.style.cssText = 'flex:0 0 auto;display:flex;gap:4px;align-items:center;padding:4px;border-top:1px solid var(--win-shadow);';

    panel.append(titleBar, body, footer);

    function attach() {
        const canvas = document.getElementById('map-canvas');
        const area = canvas && canvas.parentElement;
        if (!area) return false;
        area.appendChild(panel);
        return true;
    }

    // --- widgets -------------------------------------------------------------
    function group(label) {
        const box = document.createElement('fieldset');
        box.style.cssText = 'margin:0 0 6px;padding:4px 5px 5px;border:1px solid var(--win-shadow);';
        const legend = document.createElement('legend');
        legend.textContent = label;
        legend.style.cssText = 'font-weight:bold;padding:0 3px;';
        box.appendChild(legend);
        return box;
    }

    function fact(label, value, title) {
        const row = document.createElement('div');
        row.style.cssText = 'display:grid;grid-template-columns:82px minmax(0,1fr);gap:5px;margin:2px 0;';
        const key = document.createElement('span');
        key.style.color = 'var(--win-dark-shadow)';
        key.textContent = label;
        const val = document.createElement('span');
        val.style.cssText = 'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;';
        val.textContent = value == null || value === '' ? '—' : String(value);
        val.title = title || String(value == null ? '' : value);
        row.append(key, val);
        return row;
    }

    function note(text) {
        const el = document.createElement('p');
        el.style.cssText = 'margin:3px 0;color:var(--win-dark-shadow);line-height:1.35;';
        el.textContent = text;
        return el;
    }

    function button(label, handler, title) {
        const el = document.createElement('button');
        el.type = 'button';
        el.className = 'win98-btn';
        el.style.cssText = 'font-size:10px;padding:2px 6px;';
        el.textContent = label;
        if (title) el.title = title;
        el.addEventListener('click', handler);
        return el;
    }

    function buttonRow(buttons) {
        const row = document.createElement('div');
        row.style.cssText = 'display:flex;gap:3px;flex-wrap:wrap;margin:4px 0 2px;';
        buttons.forEach(el => row.appendChild(el));
        return row;
    }

    // --- source image (visual picking, no coordinates typed) ------------------
    function ensureSourceImage(path, onReady) {
        if (!path) return;
        if (sourceImagePath === path && sourceImage) { onReady && onReady(); return; }
        const image = new Image();
        image.onload = () => {
            sourceImage = image;
            sourceImagePath = path;
            onReady && onReady();
        };
        image.onerror = () => {
            sourceImage = null;
            sourceImagePath = path;
            onReady && onReady();
        };
        image.src = `/${path}?t=${Date.now()}`;
    }

    function tileSize() {
        return {
            w: (record && Number(record.tileWidth)) || 64,
            h: (record && Number(record.tileHeight)) || 64,
        };
    }

    // A card is the visual identity of a variant: the actual pixels the runtime
    // will sample, cropped out of the source image. No coordinates on screen.
    function variantCard(variant, roleKey, size) {
        const wrap = document.createElement('div');
        wrap.style.cssText = `width:${size}px;height:${size}px;flex:0 0 ${size}px;border:1px solid var(--win-shadow);background:#2b2b2b;position:relative;overflow:hidden;`;
        const canvas = document.createElement('canvas');
        canvas.width = size;
        canvas.height = size;
        canvas.style.cssText = 'width:100%;height:100%;display:block;image-rendering:pixelated;';
        wrap.appendChild(canvas);
        const cells = Model.visualCells(variant, roleKey);
        const model = variant && (variant.model || variant.geometry);
        if (!sourceImage || cells.length === 0) {
            const label = document.createElement('span');
            label.style.cssText = 'position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#ccc;font-size:9px;text-align:center;';
            label.textContent = model ? 'model' : 'no visual';
            wrap.appendChild(label);
            return wrap;
        }
        const tile = tileSize();
        const ctx = canvas.getContext('2d');
        ctx.imageSmoothingEnabled = false;
        const main = cells[0];
        ctx.drawImage(sourceImage, main.col * tile.w, main.row * tile.h, tile.w, tile.h, 0, 0, size, size);
        if (model) {
            ctx.fillStyle = 'rgba(0,0,0,0.6)';
            ctx.fillRect(0, size - 12, size, 12);
            ctx.fillStyle = '#ffd45a';
            ctx.font = '9px sans-serif';
            ctx.fillText('+ model', 3, size - 3);
        }
        return wrap;
    }

    // --- provisional / authoritative boundary --------------------------------
    function markProvisional(matchSpec, color) {
        const viewport = workspaceContext.viewport();
        if (!viewport || typeof viewport.setProvisionalOverlay !== 'function') return 0;
        return viewport.setProvisionalOverlay(matchSpec ? { match: matchSpec, color, opacity: 0.4 } : null);
    }

    function highlightVariantOccupancy(variantId) {
        if (!variantId) return markProvisional(null);
        return markProvisional(source =>
            !!source && (source.variantId === variantId || source.featureId === variantId), 0x38d6ff);
    }

    function flagAwaitingCorrection(variantId) {
        provisionalSince = performance.now();
        // How many visible surfaces this edit currently owns. Zero is the
        // common case for a brand-new variant, and claiming "magenta marks the
        // surfaces" when nothing is marked would be a lie.
        provisionalMarked = markProvisional(source =>
            !!source && (source.variantId === variantId || source.featureId === variantId), 0xff4fd8);
    }

    // --- authored record access (Project authority, never IPC) ----------------
    async function loadRecordForCurrentMap(force) {
        const context = workspaceContext.runtimeContext();
        const wanted = (context.bundleTileset && context.bundleTileset.resolvedId)
            || context.mapTilesetId
            || 'dungeon_default';
        if (!force && recordId === wanted && record) return record;
        if (record && Model.recordIsDirty(record, baselineJson) && recordId !== wanted) {
            // Switching Maps must not silently drop authored work.
            const keep = !window.confirm(
                `The Environment palette '${recordId}' has unsaved changes.\n\nOK = discard them and follow the Map.\nCancel = keep editing '${recordId}'.`);
            if (keep) return record;
        }
        const response = await fetch('/api/tilesets');
        if (!response.ok) throw new Error('Could not read the Project tileset registry');
        const snapshot = await response.json();
        textures = Array.isArray(snapshot.textures) ? snapshot.textures : [];
        const found = (snapshot.tilesets || []).find(entry => entry && entry.id === wanted) || null;
        if (!found) {
            record = null;
            baselineJson = null;
            recordId = wanted;
            return null;
        }
        record = deepClone(found);
        record.base = record.base || {};
        record.base.walls = record.base.walls || [];
        record.base.floors = record.base.floors || [];
        record.base.ceilings = record.base.ceilings || [];
        record.base.wallTops = record.base.wallTops || [];
        record.doors = record.doors || [];
        record.features = record.features || [];
        baselineJson = JSON.stringify(record);
        recordId = wanted;
        ensureSourceImage(record.texture, render);
        return record;
    }

    function selectedVariant() {
        if (!selection || !record) return null;
        return Model.findVariant(record, selection.roleKey, selection.variantId);
    }

    function touched(variantId) {
        flagAwaitingCorrection(variantId || (selection && selection.variantId));
        render();
    }

    // --- save / discard ------------------------------------------------------
    async function save() {
        if (!record) return false;
        const payload = Model.savePayload(record);
        const response = await fetch('/api/tilesets/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const result = await response.json().catch(() => ({}));
        if (!response.ok || !result.success) {
            toast(result.stale
                ? 'Save refused: this Tileset changed on disk after it was read here. Reload the palette first.'
                : `Save failed: ${result.message || response.status}`, 'error');
            render();
            return false;
        }
        if (result.version) record._storageVersion = result.version;
        baselineJson = JSON.stringify(record);

        // Committed-resource identity announcement. Siblings re-read the
        // Project; no authored value crosses a window boundary.
        const bridge = window.thestraStudio;
        if (bridge && typeof bridge.announceResourceCommit === 'function') {
            try { await bridge.announceResourceCommit(['tilesets']); } catch (error) {
                console.error('#547 commit announcement failed:', error);
            }
        }

        // Authoritative correction is requested, then awaited asynchronously.
        provisionalSince = performance.now();
        render();
        workspaceContext.requestAuthoritativeRefresh().catch(console.error);
        toast(`Environment '${recordId}' saved. Waiting for runtime correction…`);
        return true;
    }

    function discard() {
        if (baselineJson == null) return;
        record = JSON.parse(baselineJson);
        markProvisional(null);
        provisionalSince = null;
        ensureSourceImage(record.texture, render);
        render();
    }

    // --- source picking ------------------------------------------------------
    function renderSourcePicker(container) {
        const variant = pickMode && Model.findVariant(record, pickMode.roleKey, pickMode.variantId);
        const box = group(`Pick the look for “${pickMode.variantId}”`);
        if (!sourceImage) {
            box.appendChild(note(`The source image ${record.texture || '(none)'} could not be read, so visual picking is unavailable.`));
            box.appendChild(buttonRow([button('Cancel', () => { pickMode = null; render(); })]));
            container.appendChild(box);
            return;
        }
        box.appendChild(note(Model.ROLES[pickMode.roleKey].visualKind === 'wall-triptych'
            ? 'Click the main face. The join halves are taken from the region to its right, the way this Tileset already stores them.'
            : 'Click the region to use.'));

        const tile = tileSize();
        const scale = Math.max(1, Math.min(3, Math.floor(300 / Math.max(1, sourceImage.width))) || 1);
        const canvas = document.createElement('canvas');
        canvas.width = sourceImage.width * scale;
        canvas.height = sourceImage.height * scale;
        canvas.style.cssText = 'display:block;max-width:100%;image-rendering:pixelated;cursor:crosshair;border:1px solid var(--win-shadow);';
        const ctx = canvas.getContext('2d');
        ctx.imageSmoothingEnabled = false;
        ctx.drawImage(sourceImage, 0, 0, canvas.width, canvas.height);
        const columns = Math.floor(sourceImage.width / tile.w);
        const rows = Math.floor(sourceImage.height / tile.h);
        ctx.strokeStyle = 'rgba(255,255,255,0.35)';
        for (let c = 0; c <= columns; c++) {
            ctx.beginPath(); ctx.moveTo(c * tile.w * scale, 0); ctx.lineTo(c * tile.w * scale, canvas.height); ctx.stroke();
        }
        for (let r = 0; r <= rows; r++) {
            ctx.beginPath(); ctx.moveTo(0, r * tile.h * scale); ctx.lineTo(canvas.width, r * tile.h * scale); ctx.stroke();
        }
        canvas.addEventListener('click', event => {
            const rect = canvas.getBoundingClientRect();
            const col = Math.floor(((event.clientX - rect.left) / rect.width) * columns);
            const rowIndex = Math.floor(((event.clientY - rect.top) / rect.height) * rows);
            const outcome = Model.assignVisual(variant, pickMode.roleKey,
                { row: rowIndex, col, columns });
            if (!outcome.ok) {
                toast(outcome.reason === 'wall-needs-join-column'
                    ? 'A wall also needs the region to its right for join halves. Pick a region that is not in the last column.'
                    : 'That is not a usable region.', 'error');
                return;
            }
            const assigned = pickMode.variantId;
            pickMode = null;
            touched(assigned);
        });
        box.appendChild(canvas);
        box.appendChild(buttonRow([button('Cancel', () => { pickMode = null; render(); })]));
        container.appendChild(box);
    }

    // --- palette board (the "show me this place's vocabulary" view) ----------
    function renderPalette(container) {
        const box = group(`Vocabulary of ${record && (record.name || record.id) || 'this place'}`);
        box.appendChild(note('Every visual this environment can use, grouped by the job it does. Authored weight, its share of the pool, and how many cells of the open Map actually resolved to it.'));
        for (const roleKey of ['wall', 'wall_top', 'floor', 'ceiling', 'door', 'wall_feature', 'floor_feature']) {
            const pool = Model.poolFor(record, roleKey);
            const heading = document.createElement('div');
            heading.style.cssText = 'margin:5px 0 2px;font-weight:bold;text-transform:uppercase;letter-spacing:0.04em;';
            heading.textContent = `${Model.ROLES[roleKey].label} · ${pool.length}`;
            box.appendChild(heading);
            if (pool.length === 0) {
                box.appendChild(note('Nothing authored for this job yet.'));
                continue;
            }
            const shares = Model.poolShares(pool);
            const strip = document.createElement('div');
            strip.style.cssText = 'display:flex;gap:4px;flex-wrap:wrap;';
            pool.forEach((variant, index) => {
                const cell = document.createElement('div');
                cell.style.cssText = 'width:56px;cursor:pointer;';
                cell.title = `${variant.id} — click to edit`;
                cell.appendChild(variantCard(variant, roleKey, 54));
                const caption = document.createElement('div');
                const realized = Model.realizedShare(census, roleKey, variant.id);
                const share = shares[index];
                caption.style.cssText = 'font-size:9px;line-height:1.2;word-break:break-all;';
                caption.textContent = Model.ROLES[roleKey].weighted
                    ? `${variant.id}\nw${share.weight} · ${Math.round(share.share * 100)}%${realized ? ` · ${realized.cells} here` : ''}`
                    : `${variant.id}\n${Model.chancePercent(variant)}% chance${realized ? ` · ${realized.cells} here` : ''}`;
                caption.style.whiteSpace = 'pre-line';
                cell.appendChild(caption);
                cell.addEventListener('click', () => {
                    selection = { provenance: null, roleKey, variantId: variant.id };
                    metrics.contextChanges += 1;
                    paletteOpen = false;
                    highlightVariantOccupancy(variant.id);
                    render();
                });
                strip.appendChild(cell);
            });
            box.appendChild(strip);
        }
        container.appendChild(box);
    }

    // --- selected-owner editor ----------------------------------------------
    function renderWeightedPool(container, roleKey) {
        const pool = Model.poolFor(record, roleKey);
        const shares = Model.poolShares(pool);
        const box = group(`${Model.ROLES[roleKey].label} pool · ${pool.length} variant${pool.length === 1 ? '' : 's'}`);
        pool.forEach((variant, index) => {
            const row = document.createElement('div');
            const active = selection && variant.id === selection.variantId;
            row.style.cssText = `display:flex;gap:5px;align-items:center;padding:3px;margin:2px 0;border:1px solid ${active ? '#316ac5' : 'var(--win-shadow)'};${active ? 'background:#dce6f7;' : ''}`;
            const card = variantCard(variant, roleKey, 40);
            card.style.cursor = 'pointer';
            card.addEventListener('click', () => {
                selection = { provenance: selection && selection.provenance, roleKey, variantId: variant.id };
                highlightVariantOccupancy(variant.id);
                render();
            });
            const info = document.createElement('div');
            info.style.cssText = 'flex:1;min-width:0;';
            const name = document.createElement('div');
            name.style.cssText = 'font-weight:bold;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;';
            name.textContent = variant.id;
            info.appendChild(name);

            const realized = Model.realizedShare(census, roleKey, variant.id);
            const shareLine = document.createElement('div');
            shareLine.style.cssText = 'color:var(--win-dark-shadow);';
            shareLine.textContent = `authored ${Math.round(shares[index].share * 100)}% of the pool`
                + (realized ? ` · runtime chose it in ${realized.cells} of ${realized.total} cells here` : ' · not in the open Map');
            info.appendChild(shareLine);

            const weight = document.createElement('input');
            weight.type = 'range';
            weight.min = '1'; weight.max = '200'; weight.step = '1';
            weight.value = String(Number(variant.weight === undefined ? 100 : variant.weight));
            weight.style.cssText = 'width:100%;';
            weight.dataset.exp = 'weight';
            weight.dataset.variant = variant.id;
            weight.title = `Authored weight ${variant.weight === undefined ? 100 : variant.weight}`;
            weight.addEventListener('input', () => {
                variant.weight = Number(weight.value);
                shareLine.textContent = `authored ${Math.round(Model.poolShares(Model.poolFor(record, roleKey))[index].share * 100)}% of the pool`
                    + (realized ? ` · runtime chose it in ${realized.cells} of ${realized.total} cells here` : ' · not in the open Map');
                weight.title = `Authored weight ${variant.weight}`;
                markDirtyChrome();
            });
            weight.addEventListener('change', () => touched(variant.id));
            info.appendChild(weight);
            row.append(card, info);
            box.appendChild(row);
        });

        box.appendChild(buttonRow([
            button('Replace this look…', () => {
                if (!selection || !selectedVariant()) return toast('Select a variant first.');
                pickMode = { roleKey, variantId: selection.variantId };
                metrics.contextChanges += 1;
                render();
            }, 'Point at a source region instead of typing coordinates'),
            button('+ Variant', () => {
                const backing = Model.backingArray(record, roleKey);
                const id = Model.suggestVariantId(record, roleKey, `${recordId}_${roleKey}`);
                const variant = Model.newVariant(roleKey, id);
                backing.push(variant);
                selection = { provenance: selection && selection.provenance, roleKey, variantId: id };
                pickMode = { roleKey, variantId: id };
                metrics.contextChanges += 1;
                render();
            }, 'Add another weighted variant to this pool'),
            button('Remove', () => {
                const variant = selectedVariant();
                if (!variant) return;
                const backing = Model.backingArray(record, roleKey);
                const index = backing.indexOf(variant);
                if (index >= 0) backing.splice(index, 1);
                selection = { provenance: selection && selection.provenance, roleKey, variantId: null };
                touched(null);
            }),
        ]));
        container.appendChild(box);
    }

    function renderFeatureEditor(container, roleKey) {
        const variant = selectedVariant();
        const box = group(`${Model.ROLES[roleKey].label} behaviour`);
        if (!variant) {
            box.appendChild(note('No fixture selected.'));
            container.appendChild(box);
            return;
        }

        const chanceWrap = document.createElement('label');
        chanceWrap.style.cssText = 'display:flex;align-items:center;gap:5px;margin:3px 0;';
        const chanceLabel = document.createElement('span');
        chanceLabel.style.cssText = 'width:82px;';
        chanceLabel.textContent = 'Chance';
        const chance = document.createElement('input');
        chance.type = 'range'; chance.min = '0'; chance.max = '100'; chance.step = '1';
        chance.dataset.exp = 'chance';
        chance.value = String(Model.chancePercent(variant));
        chance.style.flex = '1';
        const chanceValue = document.createElement('span');
        chanceValue.style.cssText = 'width:34px;text-align:right;';
        chanceValue.textContent = `${Model.chancePercent(variant)}%`;
        chance.addEventListener('input', () => {
            const outcome = Model.setChancePercent(variant, chance.value);
            if (outcome.ok) chanceValue.textContent = `${chance.value}%`;
            markDirtyChrome();
        });
        chance.addEventListener('change', () => touched(variant.id));
        chanceWrap.append(chanceLabel, chance, chanceValue);
        box.appendChild(chanceWrap);
        box.appendChild(note('Chance is the deterministic per-cell roll the runtime already uses; it is not a random seed you have to manage.'));

        const presetWrap = document.createElement('label');
        presetWrap.style.cssText = 'display:flex;align-items:center;gap:5px;margin:3px 0;';
        const presetLabel = document.createElement('span');
        presetLabel.style.cssText = 'width:82px;';
        presetLabel.textContent = 'Where';
        const preset = document.createElement('select');
        preset.dataset.exp = 'placement';
        preset.className = 'win98-input';
        preset.style.flex = '1';
        for (const entry of Model.PLACEMENT_PRESETS) {
            const option = document.createElement('option');
            option.value = entry.key;
            option.textContent = entry.label;
            preset.appendChild(option);
        }
        const current = variant.prefab ? 'custom' : Model.placementPresetOf(variant.where);
        if (current === 'custom') {
            const option = document.createElement('option');
            option.value = 'custom';
            option.textContent = variant.prefab ? `Prefab rule: ${variant.prefab}` : 'Exact rule (see Advanced)';
            preset.appendChild(option);
        }
        preset.value = current;
        preset.addEventListener('change', () => {
            if (preset.value === 'custom') return;
            Model.applyPlacementPreset(variant, preset.value);
            touched(variant.id);
        });
        presetWrap.append(presetLabel, preset);
        box.appendChild(presetWrap);

        const warmButton = button('Warm emission', () => { Model.setEmission(variant, 'warm'); touched(variant.id); });
        warmButton.dataset.exp = 'emission-warm';
        const emissionRow = buttonRow([
            warmButton,
            button('Cool emission', () => { Model.setEmission(variant, 'cool'); touched(variant.id); }),
            button('No emission', () => { Model.setEmission(variant, 'none'); touched(variant.id); }),
        ]);
        box.appendChild(emissionRow);

        if (variant.emitsLight) {
            const color = document.createElement('input');
            color.type = 'color';
            const rgb = variant.emitsLight.color || [1, 1, 1];
            color.value = '#' + rgb.map(v => Math.round(Math.max(0, Math.min(1, Number(v))) * 255).toString(16).padStart(2, '0')).join('');
            color.addEventListener('input', () => {
                const hex = color.value.replace('#', '');
                variant.emitsLight.color = [0, 2, 4].map(offset => parseInt(hex.slice(offset, offset + 2), 16) / 255);
                markDirtyChrome();
            });
            color.addEventListener('change', () => touched(variant.id));
            const colorRow = document.createElement('label');
            colorRow.style.cssText = 'display:flex;align-items:center;gap:5px;margin:3px 0;';
            const colorLabel = document.createElement('span');
            colorLabel.style.cssText = 'width:82px;';
            colorLabel.textContent = 'Light colour';
            colorRow.append(colorLabel, color);
            box.appendChild(colorRow);

            for (const [key, label, min, max, step] of [['radius', 'Radius', 0.5, 12, 0.5], ['falloff', 'Falloff', 0.5, 6, 0.5]]) {
                const row = document.createElement('label');
                row.style.cssText = 'display:flex;align-items:center;gap:5px;margin:3px 0;';
                const text = document.createElement('span');
                text.style.cssText = 'width:82px;';
                text.textContent = label;
                const input = document.createElement('input');
                input.type = 'range';
                input.min = String(min); input.max = String(max); input.step = String(step);
                input.value = String(Number(variant.emitsLight[key]));
                input.dataset.exp = `light-${key}`;
                input.style.flex = '1';
                const readout = document.createElement('span');
                readout.style.cssText = 'width:26px;text-align:right;';
                readout.textContent = String(Number(variant.emitsLight[key]));
                input.addEventListener('input', () => {
                    variant.emitsLight[key] = Number(input.value);
                    readout.textContent = input.value;
                    markDirtyChrome();
                });
                input.addEventListener('change', () => touched(variant.id));
                row.append(text, input, readout);
                box.appendChild(row);
            }
            box.appendChild(note('Emitted light is generated per placed fixture by the runtime. Its effect on the Map appears with the authoritative correction, not before.'));
        }

        const blocks = document.createElement('label');
        blocks.style.cssText = 'display:flex;align-items:center;gap:5px;margin:4px 0;';
        const blocksInput = document.createElement('input');
        blocksInput.type = 'checkbox';
        blocksInput.checked = !!variant.blocksMovement;
        blocksInput.addEventListener('change', () => {
            if (blocksInput.checked) variant.blocksMovement = true; else delete variant.blocksMovement;
            touched(variant.id);
        });
        const blocksText = document.createElement('span');
        blocksText.textContent = 'Blocks movement (runtime refuses placements that would cut the map)';
        blocks.append(blocksInput, blocksText);
        box.appendChild(blocks);

        container.appendChild(box);
    }

    function renderAdvanced(container) {
        const variant = selectedVariant();
        if (!variant) return;
        const box = group('Advanced — exact authored record');
        box.appendChild(note('The persisted representation, including the exact placement predicate. Editing here is the escape hatch, not the normal path.'));
        const area = document.createElement('textarea');
        area.className = 'win98-input';
        area.rows = 10;
        area.spellcheck = false;
        area.style.cssText = 'width:100%;font-family:Consolas,monospace;font-size:10px;';
        area.dataset.exp = 'advanced';
        area.value = JSON.stringify(variant, null, 2);
        area.addEventListener('focus', () => { metrics.rawJsonUses += 1; });
        box.appendChild(area);
        box.appendChild(buttonRow([
            button('Apply exact record', () => {
                let parsed;
                try {
                    parsed = JSON.parse(area.value);
                } catch (error) {
                    toast(`That is not valid JSON: ${error.message}`, 'error');
                    return;
                }
                if (!parsed || typeof parsed !== 'object' || !parsed.id) {
                    toast('An authored variant needs at least an id.', 'error');
                    return;
                }
                const backing = Model.backingArray(record, selection.roleKey);
                const index = backing.indexOf(variant);
                if (index < 0) return;
                backing[index] = parsed;
                selection = { provenance: selection.provenance, roleKey: selection.roleKey, variantId: parsed.id };
                touched(parsed.id);
            }),
        ]));
        container.appendChild(box);
    }

    function renderStructure(container) {
        const variant = selectedVariant();
        if (!selection || selection.roleKey !== 'wall' || !variant) return;
        const box = group('Structure');
        const hasJoins = !!(variant.leftEdge && variant.rightEdge);
        box.appendChild(fact('Main face', variant.middle ? 'assigned' : 'not assigned'));
        box.appendChild(fact('Join halves', hasJoins ? 'left + right, taken from the neighbouring region' : 'none'));
        const provenance = selection.provenance;
        if (provenance) {
            box.appendChild(fact('This face', [
                provenance.leftJoin ? 'left join active' : null,
                provenance.rightJoin ? 'right join active' : null,
            ].filter(Boolean).join(', ') || 'flat run, no joins here'));
        }
        if (record.heightMap) {
            box.appendChild(fact('Relief', `height map, wall scale ${(record.heightMapScale && record.heightMapScale.wall) ?? '—'}`));
            box.appendChild(note('Relief comes from this environment\'s height map and its per-surface scale. The prototype reports it; it does not author height maps.'));
        } else {
            box.appendChild(fact('Relief', 'flat — no height map on this environment'));
        }
        container.appendChild(box);
    }

    function renderSelection(container) {
        const provenance = selection && selection.provenance;
        const box = group('Selected in the Map');
        if (!provenance && !(selection && selection.variantId)) {
            box.appendChild(note('Click a wall, floor, ceiling, doorway or fixture in the 3D Map. The surface will name the semantic owner that produced it.'));
            const context = workspaceContext.runtimeContext();
            if (!context.hasBundle) {
                box.appendChild(note('No authoritative runtime geometry is loaded yet, so surfaces cannot be traced. The Map workspace status shows the compile state.'));
            }
            container.appendChild(box);
            return;
        }
        if (provenance) {
            box.appendChild(fact('Surface', Model.describeSurface(provenance)));
            box.appendChild(fact('Cell', `${provenance.x}, ${provenance.y}`));
        }
        const roleKey = selection.roleKey;
        box.appendChild(fact('Owner job', roleKey ? Model.ROLES[roleKey].label : 'unknown'));
        box.appendChild(fact('Owner variant', selection.variantId || 'not identified'));
        if (provenance && !selection.variantId) {
            box.appendChild(note('The runtime resolved this surface without an authored variant id — it fell back to a legacy row/column path in this Tileset. That is a real finding, not a prototype limitation.'));
        }
        container.appendChild(box);
    }

    function markDirtyChrome() {
        const dirty = Model.recordIsDirty(record, baselineJson);
        titleText.textContent = `Environment · ${recordId || '—'}${dirty ? ' *' : ''} · exp #547`;
        for (const child of footer.children) {
            if (child.dataset && child.dataset.role === 'save') child.disabled = !dirty;
            if (child.dataset && child.dataset.role === 'discard') child.disabled = !dirty;
        }
    }

    function renderFooter() {
        footer.replaceChildren();
        const saveButton = button('Save', () => { save().catch(error => toast(error.message, 'error')); });
        saveButton.dataset.role = 'save';
        const discardButton = button('Discard', discard);
        discardButton.dataset.role = 'discard';
        const state = document.createElement('span');
        state.style.cssText = 'flex:1;color:var(--win-dark-shadow);line-height:1.25;';
        if (correctionFailure) {
            state.style.color = '#800000';
            state.textContent = `RUNTIME CORRECTION FAILED — the Map is showing STALE geometry (${correctionFailure}). The authored record may still be saved.`;
        } else if (provisionalSince != null) {
            state.style.color = 'var(--win-dark-shadow)';
            state.textContent = provisionalMarked > 0
                ? `PROVISIONAL — magenta marks the ${provisionalMarked} visible surface(s) this edit owns. Runtime has not corrected them yet.`
                : 'PROVISIONAL — this edit owns no surface in the open Map yet. Only the runtime can place it; save to find out where it lands.';
        } else if (lastCorrectionMs != null) {
            state.style.color = 'var(--win-dark-shadow)';
            state.textContent = `Authoritative runtime geometry applied (${Math.round(lastCorrectionMs)} ms).`;
        } else {
            state.style.color = 'var(--win-dark-shadow)';
            state.textContent = 'Reading the Project authority.';
        }
        footer.append(saveButton, discardButton, state);
        markDirtyChrome();
    }

    function render() {
        if (!record) {
            body.replaceChildren();
            const box = group('No environment palette');
            box.appendChild(note(recordId
                ? `The open Map asks for Tileset '${recordId}', which is not in this Project's registry.`
                : 'No Map is open.'));
            body.appendChild(box);
            renderFooter();
            return;
        }
        body.replaceChildren();

        const header = group('Environment');
        header.appendChild(fact('Palette', record.name || record.id));
        header.appendChild(fact('Id', record.id));
        const context = workspaceContext.runtimeContext();
        header.appendChild(fact('Map', context.mapTitle || context.mapId));
        header.appendChild(fact('Source image', record.texture || 'none'));
        if (context.bundleTileset && context.bundleTileset.hasMapOverride) {
            header.appendChild(note('This Map carries a tileset override, so what you see is the palette plus Map-local changes. Editing here changes the shared palette.'));
        }
        body.appendChild(header);

        if (paletteOpen) {
            renderPalette(body);
            renderFooter();
            return;
        }
        if (pickMode) {
            renderSourcePicker(body);
            renderFooter();
            return;
        }

        renderSelection(body);
        if (selection && selection.roleKey) {
            const role = Model.ROLES[selection.roleKey];
            if (role.weighted) renderWeightedPool(body, selection.roleKey);
            else renderFeatureEditor(body, selection.roleKey);
            renderStructure(body);
            renderAdvanced(body);
        }
        renderFooter();
    }

    // --- wiring --------------------------------------------------------------
    function refreshCensus() {
        census = Model.realizedCensus(workspaceContext.runtimeProvenance());
    }

    workspaceContext.onRuntimeSelection(({ selection: semantic, provenance }) => {
        if (!provenance) {
            // A click that hit no runtime surface is not a tileset selection.
            // Say so instead of leaving a stale owner on screen.
            if (semantic && semantic.kind === 'cell') {
                selection = { provenance: null, roleKey: null, variantId: null };
                markProvisional(null);
                render();
            }
            return;
        }
        const role = Model.roleFromProvenance(provenance);
        selection = {
            provenance,
            roleKey: role ? role.key : null,
            variantId: Model.ownerVariantId(provenance),
        };
        metrics.contextChanges += 1;
        provisionalSince = null;
        highlightVariantOccupancy(selection.variantId);
        render();
    });

    window.addEventListener('thestra-map-bundle-installed', event => {
        const ok = !(event && event.detail && event.detail.ok === false);
        if (!ok) {
            // The authoritative path refused. Saying nothing here, or clearing
            // the provisional marking, would present stale runtime geometry as
            // if it had been corrected.
            correctionFailure = (event.detail && event.detail.message) || 'the runtime did not return geometry';
            render();
            return;
        }
        correctionFailure = null;
        if (provisionalSince != null) {
            lastCorrectionMs = performance.now() - provisionalSince;
            provisionalSince = null;
            markProvisional(null);
        }
        refreshCensus();
        loadRecordForCurrentMap(false).then(render).catch(error => {
            console.error('#547 palette read failed:', error);
        });
    });

    // Another surface committed the tilesets resource. Re-read the Project
    // rather than accepting any transported value.
    window.addEventListener('thestra-tilesets-refreshed', () => {
        loadRecordForCurrentMap(true).then(() => {
            toast('Environment palette reloaded after an external commit.');
            render();
        }).catch(error => console.error('#547 palette refresh failed:', error));
    });

    paletteToggle.addEventListener('click', () => {
        paletteOpen = !paletteOpen;
        if (paletteOpen) markProvisional(null);
        metrics.contextChanges += 1;
        render();
    });
    closeButton.addEventListener('click', () => {
        panel.style.display = 'none';
        markProvisional(null);
    });

    const openButton = document.createElement('button');
    openButton.type = 'button';
    openButton.className = 'win98-btn';
    openButton.style.cssText = 'font-size:10px;padding:2px 6px;';
    openButton.textContent = 'Environment';
    openButton.title = '#547 experiment — edit this Map\'s tileset in Map context';
    openButton.addEventListener('click', () => {
        panel.style.display = panel.style.display === 'none' ? 'flex' : 'none';
        if (panel.style.display === 'flex') {
            refreshCensus();
            loadRecordForCurrentMap(false).then(render).catch(error => toast(error.message, 'error'));
        } else {
            markProvisional(null);
        }
    });

    window.exp547MapContextMetrics = function () {
        return {
            contextChanges: metrics.contextChanges,
            rawCoordinateUses: metrics.rawCoordinateUses,
            rawJsonUses: metrics.rawJsonUses,
            lastCorrectionMs,
            correctionFailure,
            recordId,
            dirty: Model.recordIsDirty(record, baselineJson),
            census,
        };
    };

    function install() {
        if (!attach()) {
            window.requestAnimationFrame(install);
            return;
        }
        toolbarMount.mount('exp547-tileset-map-context', [openButton]);
        panel.style.display = 'flex';
        refreshCensus();
        loadRecordForCurrentMap(false).then(render).catch(error => {
            console.warn('#547 initial palette read failed:', error.message);
            render();
        });
    }

    install();
}());
