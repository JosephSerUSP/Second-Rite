// ============================================================================
// EXPERIMENTAL TILESET LIVE SPECIMEN — issue #547
// Branch-only interaction prototype. The assembled environment is primary;
// atlases/models are contextual source browsers. Runtime geometry/materials are
// always supplied by the existing LÖVE renderable bridge.
// ============================================================================
(function () {
    'use strict';

    const RUNTIME_URL = 'http://127.0.0.1:8082';
    const SPECIMEN_ID = '__tileset_live_specimen__';
    const ROLE_ORDER = ['wall', 'floor', 'ceiling', 'door', 'wall_feature', 'floor_feature', 'wall_top'];
    const ROLE_LABEL = {
        wall: 'Wall', floor: 'Floor', ceiling: 'Ceiling', door: 'Opening / Door',
        wall_feature: 'Wall Feature', floor_feature: 'Floor Feature', wall_top: 'Wall Top'
    };
    const RUNTIME_ROLE = {
        floor: 'floor', ceiling: 'ceiling', opening: 'door', 'floor-feature': 'floor_feature',
        'wall-top': 'wall_top', 'north-wall': 'wall', 'south-wall': 'wall',
        'east-wall': 'wall', 'west-wall': 'wall', wall: 'wall'
    };

    let mounted = false;
    let viewport = null;
    let currentTilesetId = 'dungeon_default';
    let tilesets = [];
    let textures = [];
    let models = [];
    let working = null;
    let baselineJson = null;
    let selectedRole = 'wall';
    let selectedVariant = null;
    let selectedSemantic = null;
    let renderableBundle = null;
    let seed = 547001;
    let refreshTimer = null;
    let refreshSerial = 0;
    let atlasImage = null;
    let sourceBrowserMode = 'image';

    function clone(value) { return value == null ? value : JSON.parse(JSON.stringify(value)); }
    function el(id) { return document.getElementById(id); }
    function escapeHtml(value) {
        return String(value == null ? '' : value)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
    }
    function toast(message, kind) {
        if (typeof window.showToast === 'function') window.showToast(message, kind);
        else console[kind === 'error' ? 'error' : 'log'](message);
    }
    function dirty() { return !!working && baselineJson != null && JSON.stringify(working) !== baselineJson; }
    function normalize(record) {
        const value = clone(record || {});
        value.id = value.id || currentTilesetId;
        value.name = value.name || value.id;
        value.base = value.base || {};
        for (const name of ['walls', 'floors', 'ceilings', 'wallTops']) value.base[name] = value.base[name] || [];
        value.doors = value.doors || [];
        value.features = value.features || [];
        value.fixturePrefabs = value.fixturePrefabs || [];
        value.tileWidth = value.tileWidth || 64;
        value.tileHeight = value.tileHeight || 64;
        return value;
    }
    function currentRecord() { return tilesets.find(item => String(item.id) === String(currentTilesetId)); }
    function pool(role) {
        if (!working) return [];
        if (role === 'wall') return working.base.walls;
        if (role === 'floor') return working.base.floors;
        if (role === 'ceiling') return working.base.ceilings;
        if (role === 'wall_top') return working.base.wallTops;
        if (role === 'door') return working.doors;
        return working.features.filter(item => item.role === role);
    }
    function backingPool(role) {
        if (role === 'wall') return working.base.walls;
        if (role === 'floor') return working.base.floors;
        if (role === 'ceiling') return working.base.ceilings;
        if (role === 'wall_top') return working.base.wallTops;
        if (role === 'door') return working.doors;
        return working.features;
    }
    function weightedRole(role) { return ['wall', 'floor', 'ceiling', 'wall_top', 'door'].includes(role); }
    function featureRole(role) { return role === 'wall_feature' || role === 'floor_feature'; }
    function modelRole(role) { return role === 'door' || featureRole(role); }
    function atlasFor(variant) { return variant && (variant.middle || variant.atlas) || [0, 0]; }
    function nextVariantId(role) {
        const stem = role === 'door' ? 'door' : role;
        let index = pool(role).length + 1;
        let id = `${stem}_${index}`;
        const all = new Set(backingPool(role).map(item => item.id));
        while (all.has(id)) id = `${stem}_${++index}`;
        return id;
    }

    function specimenMap() {
        // Fixed authored vocabulary sample. Nothing here changes Map schema; it
        // is only an unsaved preview snapshot fed to the same runtime bridge as
        // the ordinary Studio map viewport.
        return {
            id: SPECIMEN_ID,
            title: 'Tileset live specimen',
            tileset: currentTilesetId,
            generation: 'Fixed',
            category: 'developer',
            safe: true,
            ceilingStyle: 'solid',
            layout: [
                '###########',
                '#....#....#',
                '#....#....#',
                '#....o....#',
                '#.........#',
                '#..##.....#',
                '#..#......#',
                '#.........#',
                '###########'
            ],
            spawn: { x: 2, y: 4, dir: 'N' },
            events: [], treasures: [], encounters: [], recruits: []
        };
    }

    function injectStyles() {
        if (el('ts-live-specimen-style')) return;
        const style = document.createElement('style');
        style.id = 'ts-live-specimen-style';
        style.textContent = `
            #tileset-studio-modal .db-modal-window{width:min(1500px,96vw)!important;height:min(900px,94vh)!important;max-width:none!important;}
            .tsls-body{display:grid;grid-template-columns:210px minmax(500px,1fr) 360px;gap:7px;flex:1;min-height:0;padding:7px;background:#c0c0c0;}
            .tsls-pane{min-height:0;background:#efefef;border:2px solid;border-color:#808080 #fff #fff #808080;overflow:auto;}
            .tsls-left{padding:7px;display:flex;flex-direction:column;gap:7px;}
            .tsls-center{position:relative;background:#24282d;overflow:hidden;}
            .tsls-right{padding:7px;display:flex;flex-direction:column;gap:7px;}
            .tsls-section{border:1px solid #aaa;background:#f7f7f7;padding:6px;}
            .tsls-title{font-weight:700;font-size:11px;margin:0 0 5px;}
            .tsls-muted{font-size:10px;color:#555;line-height:1.35;}
            .tsls-role{display:flex;justify-content:space-between;align-items:center;width:100%;text-align:left;margin:2px 0;padding:5px 6px;}
            .tsls-role.active,.tsls-variant.active{background:#316ac5!important;color:#fff!important;}
            .tsls-role .count{font-size:9px;opacity:.8;}
            .tsls-variant{display:flex;align-items:center;gap:6px;padding:5px;border:1px solid transparent;cursor:default;background:#fff;margin-bottom:3px;}
            .tsls-variant:hover{border-color:#888;}
            .tsls-thumb{width:40px;height:40px;flex:0 0 40px;border:1px solid #777;background:#333;image-rendering:pixelated;object-fit:none;}
            .tsls-fields{display:grid;grid-template-columns:105px minmax(0,1fr);gap:5px;align-items:center;font-size:10px;}
            .tsls-fields input,.tsls-fields select,.tsls-fields textarea{font-size:10px;min-width:0;box-sizing:border-box;width:100%;}
            .tsls-fields textarea{height:76px;font-family:monospace;resize:vertical;}
            #tsls-viewport{position:absolute;inset:0;}
            #tsls-status{position:absolute;left:8px;top:8px;z-index:4;background:rgba(20,22,25,.87);color:#fff;border:1px solid #777;padding:5px 7px;font:11px monospace;pointer-events:none;max-width:70%;}
            #tsls-selection-badge{position:absolute;left:8px;bottom:8px;z-index:4;background:rgba(20,22,25,.87);color:#ffd45a;border:1px solid #777;padding:5px 7px;font:11px monospace;pointer-events:none;}
            .tsls-source-tabs{display:flex;gap:3px;margin-bottom:5px;}
            .tsls-source-tabs button.active{font-weight:700;background:#fff;}
            #tsls-atlas-wrap{max-height:235px;overflow:auto;background:#222;border:1px inset #999;padding:4px;}
            #tsls-atlas{image-rendering:pixelated;display:block;cursor:crosshair;}
            #tsls-models{max-height:235px;overflow:auto;background:#fff;border:1px inset #999;}
            .tsls-model{padding:4px 5px;border-bottom:1px solid #ddd;font:10px monospace;cursor:default;word-break:break-all;}
            .tsls-model:hover{background:#dbe8ff;}
            .tsls-footer{display:flex;gap:6px;justify-content:flex-end;padding:7px;border-top:1px solid #888;background:#c0c0c0;}
            .tsls-seed{display:flex;gap:4px;align-items:center;font-size:10px;}
            .tsls-seed input{width:90px;font:10px monospace;}
            @media(max-width:1000px){.tsls-body{grid-template-columns:175px minmax(420px,1fr) 310px;}.tsls-fields{grid-template-columns:90px 1fr;}}
        `;
        document.head.appendChild(style);
    }

    function mount() {
        if (mounted) return;
        injectStyles();
        const modal = el('tileset-studio-modal');
        const win = modal && modal.querySelector('.db-modal-window');
        if (!win) throw new Error('Tileset Studio modal shell not found.');
        win.innerHTML = `
            <div class="title-bar">
                <div class="title-bar-text">Tileset Studio — Live Specimen [EXPERIMENT]</div>
                <div class="title-bar-controls"><button id="tsls-close-x" class="win-btn-small outset-bevel">×</button></div>
            </div>
            <div class="tsls-body">
                <div class="tsls-pane tsls-left">
                    <div class="tsls-section">
                        <div class="tsls-title">Environmental vocabulary</div>
                        <select id="tsls-tileset" class="win98-input" style="width:100%"></select>
                        <input id="tsls-name" class="win98-input" style="width:100%;margin-top:4px" placeholder="Tileset name">
                    </div>
                    <div class="tsls-section" style="flex:1;overflow:auto">
                        <div class="tsls-title">Surfaces & structural roles</div>
                        <div class="tsls-muted" style="margin-bottom:5px">Click the assembled specimen first. This list is the vocabulary fallback, not the main canvas.</div>
                        <div id="tsls-roles"></div>
                    </div>
                    <div class="tsls-section">
                        <div class="tsls-title">Deterministic specimen</div>
                        <div class="tsls-seed"><button id="tsls-prev" class="win98-btn">◀</button><input id="tsls-seed" type="number" class="win98-input"><button id="tsls-next" class="win98-btn">▶</button></div>
                        <button id="tsls-cycle" class="win98-btn" style="width:100%;margin-top:4px">Cycle resolved variants</button>
                        <div class="tsls-muted" style="margin-top:4px">Same working copy + same seed → same runtime resolution.</div>
                    </div>
                </div>
                <div class="tsls-pane tsls-center">
                    <div id="tsls-viewport"></div>
                    <div id="tsls-status">Preparing runtime specimen…</div>
                    <div id="tsls-selection-badge">Click a visible surface</div>
                </div>
                <div class="tsls-pane tsls-right">
                    <div class="tsls-section">
                        <div class="tsls-title">Semantic owner</div>
                        <div id="tsls-owner" style="font-weight:700;font-size:13px">Wall</div>
                        <div id="tsls-owner-detail" class="tsls-muted">Choose a visible specimen surface.</div>
                    </div>
                    <div class="tsls-section" style="max-height:180px;overflow:auto">
                        <div style="display:flex;align-items:center;gap:4px"><div class="tsls-title" style="flex:1;margin:0">Variants</div><button id="tsls-add" class="win98-btn">+ Add</button><button id="tsls-delete" class="win98-btn">Delete</button></div>
                        <div id="tsls-variants" style="margin-top:5px"></div>
                    </div>
                    <div class="tsls-section" style="overflow:auto;flex:1">
                        <div class="tsls-title">Contextual Inspector</div>
                        <div id="tsls-inspector"></div>
                    </div>
                    <div class="tsls-section">
                        <div class="tsls-title">Source browser</div>
                        <div class="tsls-source-tabs"><button id="tsls-tab-image" class="win98-btn active">Image / atlas</button><button id="tsls-tab-model" class="win98-btn">Model</button></div>
                        <div id="tsls-source"></div>
                    </div>
                </div>
            </div>
            <div class="tsls-footer">
                <span id="tsls-dirty" style="margin-right:auto;font-size:10px;align-self:center">No unsaved changes</span>
                <button id="tsls-discard" class="win98-btn">Discard</button>
                <button id="tsls-save" class="win98-btn win98-btn-success">Save Tileset</button>
                <button id="tsls-close" class="win98-btn">Close</button>
            </div>`;

        el('tsls-close-x').onclick = () => window.closeTilesetStudioModal();
        el('tsls-close').onclick = () => window.closeTilesetStudioModal();
        el('tsls-save').onclick = () => save();
        el('tsls-discard').onclick = () => discard();
        el('tsls-tileset').onchange = event => switchTileset(event.target.value);
        el('tsls-name').oninput = event => mutate(() => { working.name = event.target.value || working.id; }, false);
        el('tsls-seed').onchange = event => { seed = Math.trunc(Number(event.target.value) || 547001); event.target.value = seed; refreshRuntime(); };
        el('tsls-prev').onclick = () => { seed -= 1; el('tsls-seed').value = seed; refreshRuntime(); };
        el('tsls-next').onclick = () => { seed += 1; el('tsls-seed').value = seed; refreshRuntime(); };
        el('tsls-cycle').onclick = () => { seed += 1; el('tsls-seed').value = seed; refreshRuntime(); };
        el('tsls-add').onclick = addVariant;
        el('tsls-delete').onclick = deleteVariant;
        el('tsls-tab-image').onclick = () => { sourceBrowserMode = 'image'; renderSourceBrowser(); };
        el('tsls-tab-model').onclick = () => { sourceBrowserMode = 'model'; renderSourceBrowser(); };
        mounted = true;
    }

    async function ensureViewport() {
        if (viewport) return;
        await import('/js/thestra-editor-scene.js');
        const module = await import('/js/three-editor-viewport.js');
        viewport = module.createThreeEditorViewport(el('tsls-viewport'), {
            getInteractionMode: () => 'map',
            onSelection: semantic => selectSemantic(semantic)
        });
        viewport.setMode('perspective');
    }

    async function loadInventories() {
        const [tilesetResponse, modelResponse] = await Promise.all([
            fetch('/api/tilesets'),
            fetch('/api/models?root=models').catch(() => null)
        ]);
        if (!tilesetResponse.ok) throw new Error(`Tilesets HTTP ${tilesetResponse.status}`);
        const data = await tilesetResponse.json();
        tilesets = data.tilesets || [];
        textures = data.textures || [];
        if (modelResponse && modelResponse.ok) {
            const value = await modelResponse.json();
            models = value.files || value.models || [];
        }
        renderTilesetSelect();
    }

    function renderTilesetSelect() {
        const select = el('tsls-tileset');
        if (!select) return;
        select.innerHTML = tilesets.map(item => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name || item.id)}</option>`).join('');
        if (tilesets.some(item => String(item.id) === String(currentTilesetId))) select.value = currentTilesetId;
        else if (tilesets.length) currentTilesetId = select.value = tilesets[0].id;
    }

    function applyRecord(record, captureBaseline) {
        working = normalize(record);
        currentTilesetId = working.id;
        if (captureBaseline) baselineJson = JSON.stringify(working);
        selectedSemantic = null;
        selectedRole = 'wall';
        selectedVariant = pool(selectedRole)[0] || null;
        el('tsls-name').value = working.name || working.id;
        el('tsls-seed').value = seed;
        renderAll();
        loadAtlas();
        updateSceneModel();
        refreshRuntime();
    }

    async function switchTileset(id) {
        if (String(id) === String(currentTilesetId)) return true;
        if (!(await resolveDirtyTransition('Discard unsaved Tileset changes before switching?'))) {
            el('tsls-tileset').value = currentTilesetId;
            return false;
        }
        const record = tilesets.find(item => String(item.id) === String(id));
        if (!record) return false;
        applyRecord(record, true);
        el('tsls-tileset').value = currentTilesetId;
        return true;
    }

    function renderAll() {
        renderRoles();
        renderOwner();
        renderVariants();
        renderInspector();
        renderSourceBrowser();
        renderDirty();
    }

    function renderRoles() {
        el('tsls-roles').innerHTML = ROLE_ORDER.map(role => {
            const count = pool(role).length;
            return `<button class="win98-btn tsls-role ${role === selectedRole ? 'active' : ''}" data-role="${role}"><span>${escapeHtml(ROLE_LABEL[role])}</span><span class="count">${count}</span></button>`;
        }).join('');
        el('tsls-roles').querySelectorAll('[data-role]').forEach(button => {
            button.onclick = () => selectRole(button.dataset.role, null, false);
        });
    }

    function selectRole(role, preferredId, fromSpecimen) {
        selectedRole = role;
        const candidates = pool(role);
        selectedVariant = preferredId ? candidates.find(item => item.id === preferredId) : null;
        if (!selectedVariant) selectedVariant = candidates[0] || null;
        if (!fromSpecimen) selectedSemantic = null;
        renderAll();
    }

    function sourceCandidatesAt(semantic) {
        if (!renderableBundle || !semantic || !semantic.cell) return [];
        return (renderableBundle.surfaces || []).filter(surface => {
            const source = surface && surface.source;
            return source && source.kind === 'cell'
                && Number(source.x) === Number(semantic.cell.x)
                && Number(source.y) === Number(semantic.cell.y);
        });
    }

    function selectSemantic(semantic) {
        selectedSemantic = semantic;
        const runtimeRole = semantic && RUNTIME_ROLE[semantic.role];
        const sources = sourceCandidatesAt(semantic);
        let chosen = null;
        if (runtimeRole) chosen = sources.find(surface => RUNTIME_ROLE[surface.source.surface] === runtimeRole);
        if (!chosen && sources.length) chosen = sources[0];
        const source = chosen && chosen.source;
        const role = (source && RUNTIME_ROLE[source.surface]) || runtimeRole || (semantic.role === 'opening' ? 'door' : null);
        if (role) {
            const preferred = source && source.featureId;
            selectRole(role, preferred, true);
        } else {
            renderOwner();
        }
        renderSelectionBadge();
    }

    function renderSelectionBadge() {
        const badge = el('tsls-selection-badge');
        if (!badge) return;
        if (!selectedSemantic || !selectedSemantic.cell) {
            badge.textContent = 'Click a visible surface';
            return;
        }
        badge.textContent = `${ROLE_LABEL[selectedRole]} · cell ${selectedSemantic.cell.x},${selectedSemantic.cell.y}`;
    }

    function renderOwner() {
        const owner = el('tsls-owner');
        const detail = el('tsls-owner-detail');
        if (!owner || !detail) return;
        owner.textContent = ROLE_LABEL[selectedRole];
        if (!selectedSemantic || !selectedSemantic.cell) {
            detail.textContent = 'Vocabulary selection. Click the assembled specimen to bind this Inspector to a visible runtime surface.';
            renderSelectionBadge();
            return;
        }
        const sources = sourceCandidatesAt(selectedSemantic);
        const roles = [...new Set(sources.map(surface => surface.source && surface.source.surface).filter(Boolean))];
        detail.textContent = `Runtime cell ${selectedSemantic.cell.x},${selectedSemantic.cell.y}. Resolved components here: ${roles.length ? roles.join(', ') : selectedSemantic.role || 'unknown'}.`;
        renderSelectionBadge();
    }

    function thumbStyle(variant) {
        const a = atlasFor(variant);
        const size = 40;
        if (!working || !working.texture) return '';
        const tw = working.tileWidth || 64, th = working.tileHeight || 64;
        const scaleX = size / tw, scaleY = size / th;
        return `background-image:url('/${working.texture}');background-size:auto;background-position:-${a[1] * tw * scaleX}px -${a[0] * th * scaleY}px;`;
    }

    function renderVariants() {
        const list = el('tsls-variants');
        const variants = pool(selectedRole);
        if (!variants.length) {
            list.innerHTML = '<div class="tsls-muted">Nothing assigned. Add a variant, then choose its source in context.</div>';
            return;
        }
        list.innerHTML = variants.map((variant, index) => {
            const active = variant === selectedVariant;
            const weight = weightedRole(selectedRole) ? `weight ${variant.weight == null ? 1 : variant.weight}` : `prob ${Math.round((variant.injectProbability == null ? .12 : variant.injectProbability) * 100)}%`;
            const source = variant.model ? 'OBJ' : (variant.geometry ? 'Geometry' : 'Image');
            return `<div class="tsls-variant ${active ? 'active' : ''}" data-index="${index}"><div class="tsls-thumb" style="${thumbStyle(variant)}"></div><div style="min-width:0;flex:1"><div style="font:11px monospace;overflow:hidden;text-overflow:ellipsis">${escapeHtml(variant.id || '(unnamed)')}</div><div style="font-size:9px;opacity:.8">${source} · ${weight}</div></div></div>`;
        }).join('');
        list.querySelectorAll('[data-index]').forEach(row => {
            row.onclick = () => { selectedVariant = variants[Number(row.dataset.index)]; renderAll(); };
        });
    }

    function addVariant() {
        if (!working) return;
        let variant;
        if (selectedRole === 'wall') variant = { id: nextVariantId('wall'), role: 'base_wall', middle: [0, 0], leftEdge: [0, 1, 0], rightEdge: [0, 1, 32], weight: 100 };
        else if (selectedRole === 'floor') variant = { id: nextVariantId('floor'), role: 'base_floor', atlas: [0, 0], weight: 100, heightOffset: 0 };
        else if (selectedRole === 'ceiling') variant = { id: nextVariantId('ceiling'), role: 'base_ceiling', atlas: [0, 0], weight: 100 };
        else if (selectedRole === 'wall_top') variant = { id: nextVariantId('wall_top'), role: 'base_wall_top', atlas: [0, 0], weight: 100 };
        else if (selectedRole === 'door') variant = { id: nextVariantId('door'), role: 'door', atlas: [0, 0], weight: 100 };
        else variant = { id: nextVariantId(selectedRole), role: selectedRole, atlas: [0, 0], injectProbability: .12 };
        backingPool(selectedRole).push(variant);
        selectedVariant = variant;
        mutate(() => {}, true);
    }

    function deleteVariant() {
        if (!selectedVariant) return;
        const backing = backingPool(selectedRole);
        const index = backing.indexOf(selectedVariant);
        if (index >= 0) backing.splice(index, 1);
        selectedVariant = pool(selectedRole)[0] || null;
        mutate(() => {}, true);
    }

    function inspectorInput(label, key, value, type, extra) {
        return `<label>${escapeHtml(label)}</label><input class="win98-input" data-field="${key}" type="${type || 'text'}" value="${escapeHtml(value == null ? '' : value)}" ${extra || ''}>`;
    }

    function renderInspector() {
        const host = el('tsls-inspector');
        if (!selectedVariant) {
            host.innerHTML = '<div class="tsls-muted">Add or select a variant.</div>';
            return;
        }
        const v = selectedVariant;
        let html = '<div class="tsls-fields">';
        html += inspectorInput('Variant ID', 'id', v.id || '');
        if (weightedRole(selectedRole)) html += inspectorInput('Weight', 'weight', v.weight == null ? 1 : v.weight, 'number', 'min="1" step="1"');
        if (selectedRole === 'floor') html += inspectorInput('Height offset', 'heightOffset', v.heightOffset || 0, 'number', 'step="0.01"');
        if (featureRole(selectedRole)) {
            html += inspectorInput('Probability %', 'injectProbability', Math.round((v.injectProbability == null ? .12 : v.injectProbability) * 100), 'number', 'min="0" max="100" step="1"');
            html += '<label>Placement preset</label><select class="win98-input" data-field="prefab"><option value="">Custom exact rule</option>'
                + (working.fixturePrefabs || []).map(p => `<option value="${escapeHtml(p.id)}" ${v.prefab === p.id ? 'selected' : ''}>${escapeHtml(p.name || p.id)}</option>`).join('') + '</select>';
            html += `<label>Exact predicate</label><textarea class="win98-input" data-field="whereJson" ${v.prefab ? 'disabled' : ''}>${escapeHtml(v.where ? JSON.stringify(v.where, null, 2) : '')}</textarea>`;
            html += '<label>Emits light</label><input data-field="emitsLight" type="checkbox" ' + (v.emitsLight ? 'checked' : '') + ' style="justify-self:start">';
            if (v.emitsLight) {
                html += inspectorInput('Light color', 'lightColor', rgbToHex(v.emitsLight.color), 'color');
                html += inspectorInput('Light radius', 'lightRadius', v.emitsLight.radius == null ? 4 : v.emitsLight.radius, 'number', 'step="0.1"');
                html += inspectorInput('Light falloff', 'lightFalloff', v.emitsLight.falloff == null ? 2 : v.emitsLight.falloff, 'number', 'step="0.1"');
            }
            if (selectedRole === 'floor_feature') {
                html += '<label>Blocks movement</label><input data-field="blocksMovement" type="checkbox" ' + (v.blocksMovement ? 'checked' : '') + ' style="justify-self:start">';
            }
        }
        if (modelRole(selectedRole)) html += inspectorInput('Model source', 'model', v.model || '', 'text', 'placeholder="assets/models/…obj"');
        html += '</div>';
        html += `<div class="tsls-muted" style="margin-top:6px">Authored source: ${v.model ? escapeHtml(v.model) : (v.geometry ? escapeHtml(v.geometry) : `atlas ${escapeHtml(JSON.stringify(atlasFor(v)))}`)}. Changes refresh the real assembled runtime specimen.</div>`;
        host.innerHTML = html;
        host.querySelectorAll('[data-field]').forEach(control => {
            const eventName = control.tagName === 'TEXTAREA' || control.type === 'text' ? 'change' : 'change';
            control.addEventListener(eventName, () => applyField(control.dataset.field, control));
        });
    }

    function applyField(field, control) {
        const v = selectedVariant;
        if (!v) return;
        try {
            if (field === 'id') v.id = control.value.trim() || v.id;
            else if (field === 'weight') v.weight = Math.max(1, Math.trunc(Number(control.value) || 1));
            else if (field === 'heightOffset') v.heightOffset = Number(control.value) || 0;
            else if (field === 'injectProbability') v.injectProbability = Math.max(0, Math.min(100, Number(control.value) || 0)) / 100;
            else if (field === 'prefab') {
                if (control.value) { v.prefab = control.value; delete v.where; }
                else delete v.prefab;
            } else if (field === 'whereJson') {
                const text = control.value.trim();
                if (!text) delete v.where;
                else v.where = JSON.parse(text);
            } else if (field === 'emitsLight') {
                if (control.checked) v.emitsLight = v.emitsLight || { color: [1, .58, .22], radius: 4, falloff: 2 };
                else delete v.emitsLight;
            } else if (field === 'lightColor') { if (v.emitsLight) v.emitsLight.color = hexToRgb(control.value); }
            else if (field === 'lightRadius') { if (v.emitsLight) v.emitsLight.radius = Number(control.value) || 4; }
            else if (field === 'lightFalloff') { if (v.emitsLight) v.emitsLight.falloff = Number(control.value) || 2; }
            else if (field === 'blocksMovement') { if (control.checked) v.blocksMovement = true; else delete v.blocksMovement; }
            else if (field === 'model') { if (control.value.trim()) v.model = control.value.trim(); else delete v.model; }
        } catch (error) {
            toast('Exact predicate is not valid JSON: ' + error.message, 'error');
            return;
        }
        mutate(() => {}, true);
    }

    function rgbToHex(value) {
        return '#' + (value || [1, .58, .22]).slice(0, 3).map(n => Math.round(Math.max(0, Math.min(1, Number(n) || 0)) * 255).toString(16).padStart(2, '0')).join('');
    }
    function hexToRgb(hex) {
        const m = /^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(hex || '');
        return m ? [parseInt(m[1], 16) / 255, parseInt(m[2], 16) / 255, parseInt(m[3], 16) / 255] : [1, .58, .22];
    }

    function mutate(fn, runtimeRefresh) {
        fn();
        renderAll();
        if (runtimeRefresh !== false) scheduleRuntimeRefresh();
    }

    function renderDirty() {
        const status = el('tsls-dirty');
        if (status) status.textContent = dirty() ? '● Unsaved Tileset working copy' : 'No unsaved changes';
    }

    function loadAtlas() {
        atlasImage = null;
        if (!working || !working.texture) { renderSourceBrowser(); return; }
        const image = new Image();
        image.onload = () => { atlasImage = image; renderSourceBrowser(); renderVariants(); };
        image.onerror = () => { atlasImage = null; renderSourceBrowser(); };
        image.src = '/' + working.texture + '?tsls=' + Date.now();
    }

    function renderSourceBrowser() {
        const host = el('tsls-source');
        if (!host || !working) return;
        if (sourceBrowserMode === 'model' && !modelRole(selectedRole)) sourceBrowserMode = 'image';
        el('tsls-tab-image').classList.toggle('active', sourceBrowserMode === 'image');
        el('tsls-tab-model').classList.toggle('active', sourceBrowserMode === 'model');
        el('tsls-tab-model').disabled = !modelRole(selectedRole);
        if (sourceBrowserMode === 'model') {
            host.innerHTML = `<div id="tsls-models">${models.length ? models.map(path => `<div class="tsls-model" data-model="${escapeHtml(path)}">${escapeHtml(path)}</div>`).join('') : '<div class="tsls-muted" style="padding:6px">No OBJ inventory returned for this Project.</div>'}</div>`;
            host.querySelectorAll('[data-model]').forEach(row => row.onclick = () => {
                if (!selectedVariant) return;
                selectedVariant.model = row.dataset.model;
                mutate(() => {}, true);
            });
            return;
        }
        const textureOptions = textures.map(name => {
            const path = String(name).startsWith('assets/') ? name : `assets/tilesets/${name}`;
            return `<option value="${escapeHtml(path)}" ${working.texture === path ? 'selected' : ''}>${escapeHtml(name)}</option>`;
        }).join('');
        host.innerHTML = `<select id="tsls-texture" class="win98-input" style="width:100%;margin-bottom:5px">${textureOptions}</select><div id="tsls-atlas-wrap"><canvas id="tsls-atlas"></canvas></div><div class="tsls-muted" style="margin-top:4px">The image is a source browser: choose a semantic owner/variant first, then click the source cell. Wall selection consumes the clicked cell plus its right-hand edge cell, matching the current runtime schema.</div>`;
        el('tsls-texture').onchange = event => {
            working.texture = event.target.value;
            loadAtlas();
            mutate(() => {}, true);
        };
        drawAtlas();
    }

    function drawAtlas() {
        const canvas = el('tsls-atlas');
        if (!canvas || !atlasImage || !working) return;
        const tw = working.tileWidth || 64, th = working.tileHeight || 64;
        const scale = .72;
        canvas.width = Math.max(1, Math.round(atlasImage.width * scale));
        canvas.height = Math.max(1, Math.round(atlasImage.height * scale));
        canvas.style.width = `${canvas.width}px`; canvas.style.height = `${canvas.height}px`;
        const ctx = canvas.getContext('2d');
        ctx.imageSmoothingEnabled = false;
        ctx.drawImage(atlasImage, 0, 0, canvas.width, canvas.height);
        ctx.strokeStyle = 'rgba(255,255,255,.32)'; ctx.lineWidth = 1;
        for (let x = 0; x <= canvas.width; x += tw * scale) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke(); }
        for (let y = 0; y <= canvas.height; y += th * scale) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); ctx.stroke(); }
        if (selectedVariant) {
            const a = atlasFor(selectedVariant);
            ctx.strokeStyle = '#ffd45a'; ctx.lineWidth = 3;
            ctx.strokeRect(a[1] * tw * scale + 1, a[0] * th * scale + 1, tw * scale - 2, th * scale - 2);
        }
        canvas.onclick = event => {
            if (!selectedVariant) return;
            const rect = canvas.getBoundingClientRect();
            const col = Math.floor((event.clientX - rect.left) / (tw * scale));
            const row = Math.floor((event.clientY - rect.top) / (th * scale));
            const cols = Math.floor(atlasImage.width / tw), rows = Math.floor(atlasImage.height / th);
            if (row < 0 || col < 0 || row >= rows || col >= cols) return;
            if (selectedRole === 'wall') {
                if (col + 1 >= cols) { toast('Wall source needs the adjacent right-hand edge cell.', 'error'); return; }
                selectedVariant.middle = [row, col];
                selectedVariant.leftEdge = [row, col + 1, 0];
                selectedVariant.rightEdge = [row, col + 1, Math.floor(tw / 2)];
            } else selectedVariant.atlas = [row, col];
            if (selectedVariant.model) delete selectedVariant.model;
            mutate(() => {}, true);
        };
    }

    function updateSceneModel() {
        if (!viewport || !globalThis.ThestraEditorScene) return;
        const map = specimenMap();
        viewport.setSceneModel(globalThis.ThestraEditorScene.buildScene({}, map, null));
        viewport.frameScene();
    }

    function cleanTilesetSnapshot() {
        const value = clone(working);
        delete value._storageVersion;
        return value;
    }

    function scheduleRuntimeRefresh() {
        clearTimeout(refreshTimer);
        const status = el('tsls-status');
        if (status) status.textContent = 'Working copy changed · resolving real runtime…';
        refreshTimer = setTimeout(refreshRuntime, 180);
    }

    async function refreshRuntime() {
        if (!working || !viewport) return;
        const serial = ++refreshSerial;
        const status = el('tsls-status');
        if (status) status.textContent = `REAL RUNTIME · resolving seed ${seed}…`;
        try {
            const response = await fetch(`${RUNTIME_URL}/api/map-renderable`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ map: specimenMap(), tileset: cleanTilesetSnapshot(), seed })
            });
            const value = await response.json();
            if (!response.ok || value.error) throw new Error(value.error || `HTTP ${response.status}`);
            if (serial !== refreshSerial) return;
            renderableBundle = value;
            viewport.setRenderableBundle(value);
            const stats = value.stats || {};
            if (status) status.textContent = `REAL RUNTIME · seed ${seed} · ${stats.triangleCount || 0} triangles · transient Tileset`;
            if (selectedSemantic) selectSemantic(selectedSemantic);
            else renderOwner();
        } catch (error) {
            if (serial !== refreshSerial) return;
            renderableBundle = null;
            viewport.setRenderableBundle(null);
            if (status) status.textContent = `Runtime preview unavailable: ${error.message}`;
        }
    }

    async function dirtyChoice() {
        if (!dirty()) return 'discard';
        if (window.thestraSurfaceKind === 'tileset' && window.thestraStudio
                && typeof window.thestraStudio.chooseCloseAction === 'function') {
            return window.thestraStudio.chooseCloseAction('tileset');
        }
        return window.confirm('Discard unsaved Tileset Studio changes?') ? 'discard' : 'cancel';
    }
    async function resolveDirtyTransition(message) {
        if (!dirty()) return true;
        let choice;
        if (window.thestraSurfaceKind === 'tileset' && window.thestraStudio
                && typeof window.thestraStudio.chooseCloseAction === 'function') {
            choice = await window.thestraStudio.chooseCloseAction('tileset');
        } else choice = window.confirm(message || 'Discard unsaved Tileset changes?') ? 'discard' : 'cancel';
        if (choice === 'save') return save();
        if (choice === 'discard') { discard(); return true; }
        return false;
    }

    async function announceCommit() {
        const bridge = window.thestraStudio;
        if (bridge && typeof bridge.announceResourceCommit === 'function') {
            try { await bridge.announceResourceCommit(['tilesets']); } catch (error) { console.warn(error); }
        }
    }

    async function save() {
        if (!working) return false;
        try {
            const response = await fetch('/api/tilesets/save', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(working)
            });
            const value = await response.json();
            if (!response.ok || !value.success) throw new Error(value.message || `HTTP ${response.status}`);
            if (value.version) working._storageVersion = value.version;
            baselineJson = JSON.stringify(working);
            const at = tilesets.findIndex(item => String(item.id) === String(working.id));
            if (at >= 0) tilesets[at] = clone(working);
            await announceCommit();
            renderDirty();
            toast(`Tileset '${working.id}' saved.`);
            return true;
        } catch (error) {
            toast('Tileset save failed: ' + error.message, 'error');
            return false;
        }
    }

    function discard() {
        if (baselineJson == null) return true;
        applyRecord(JSON.parse(baselineJson), false);
        renderDirty();
        return true;
    }

    window.openTilesetStudioModal = async function () {
        const modal = el('tileset-studio-modal');
        if (!modal) return false;
        try {
            mount();
            modal.style.display = 'flex';
            await ensureViewport();
            await loadInventories();
            const record = currentRecord() || tilesets[0];
            if (!record) throw new Error('This Project has no Tilesets.');
            currentTilesetId = record.id;
            renderTilesetSelect();
            applyRecord(record, true);
            return true;
        } catch (error) {
            toast('Live Tileset specimen could not open: ' + error.message, 'error');
            return false;
        }
    };

    window.openTilesetStudioForCurrentMap = function () {
        const selector = el('prop-map-tileset');
        if (selector && selector.value) currentTilesetId = selector.value;
        return window.openTilesetStudioModal();
    };

    window.closeTilesetStudioModal = async function (force) {
        const modal = el('tileset-studio-modal');
        if (!modal) return true;
        if (!force && dirty()) {
            const choice = await dirtyChoice();
            if (choice === 'save') { if (!(await save())) return false; }
            else if (choice === 'discard') discard();
            else return false;
        }
        modal.style.display = 'none';
        return true;
    };

    window.saveTilesetStudioData = save;
    window.thestraTilesetLiveSpecimen = Object.freeze({
        refresh: refreshRuntime,
        selectRole,
        setSeed(value) { seed = Math.trunc(Number(value) || seed); if (el('tsls-seed')) el('tsls-seed').value = seed; return refreshRuntime(); },
        specimenMap: () => clone(specimenMap()),
        workingCopy: () => clone(working),
        bundle: () => clone(renderableBundle)
    });
    window.thestraTilesetStudioTransaction = Object.freeze({
        isDirty: dirty,
        save,
        discard,
        currentId: () => currentTilesetId,
        workingCopy: () => clone(working),
        baseline: () => baselineJson == null ? null : JSON.parse(baselineJson)
    });
}());
