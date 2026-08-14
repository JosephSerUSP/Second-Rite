(function () {
    'use strict';

    const host = window.ThestraEditorHost;
    const Adapter = window.SecondRiteEditorAdapter;
    const WorkspaceState = window.ThestraWorkspaceState;
    if (!host || !Adapter || !WorkspaceState) return;

    const legacyCanvas = document.getElementById('map-canvas');
    const area = legacyCanvas && legacyCanvas.parentElement;
    if (!legacyCanvas || !area) return;

    let backend = null;
    let backendPromise = null;
    let currentBundle = null;
    let currentMode = 'perspective';
    let semanticSerial = 0;
    let bundleSerial = 0;
    let semanticRefreshQueued = false;
    let bundleTimer = null;
    let loadedMapIndex = null;
    let bundleStatus = 'runtime geometry';

    area.style.position = 'relative';

    const viewport = document.createElement('div');
    viewport.id = 'thestra-map-viewport';
    viewport.style.cssText = 'position:absolute;inset:0;display:none;overflow:hidden;background:#24282d;';
    area.appendChild(viewport);

    const toolbar = document.createElement('div');
    toolbar.id = 'thestra-map-view-toolbar';
    toolbar.style.cssText = [
        'position:absolute', 'top:6px', 'right:6px', 'z-index:20', 'display:flex',
        'gap:2px', 'align-items:center', 'padding:2px', 'background:var(--win-gray)',
        'border:2px solid',
        'border-color:var(--win-white) var(--win-shadow) var(--win-shadow) var(--win-white)',
        'font-size:10px'
    ].join(';');

    const status = document.createElement('span');
    status.style.cssText = 'padding:0 4px;min-width:122px;color:var(--win-dark-shadow);white-space:nowrap;';
    status.textContent = 'Loading 3D…';

    function setStatus(text, detail) {
        status.textContent = text;
        status.title = detail || '';
    }

    function layerLabel() {
        const layer = host.getEditingMode ? host.getEditingMode() : null;
        return ({ map: 'Map', event: 'Event', light: 'Light', override: 'Override' })[layer] || 'Select';
    }

    function modeLabel() { return currentMode === 'top' ? 'Top' : '3D'; }

    function button(label, mode, title) {
        const el = document.createElement('button');
        el.type = 'button';
        el.className = 'win98-btn';
        el.style.cssText = 'font-size:10px;padding:2px 6px;';
        el.textContent = label;
        el.title = title;
        el.dataset.mode = mode;
        el.addEventListener('click', () => activate(mode));
        return el;
    }

    const perspectiveButton = button('Perspective', 'perspective', 'Shared Thestra Editor Scene — perspective authoring camera');
    const topButton = button('Top Ortho', 'top', 'Shared Thestra Editor Scene — orthographic authoring camera');
    const navigationHelp = document.createElement('button');
    navigationHelp.type = 'button';
    navigationHelp.className = 'win98-btn';
    navigationHelp.style.cssText = 'font-size:10px;padding:2px 6px;';
    navigationHelp.textContent = 'Keys';
    navigationHelp.title = 'Viewport keys: Numpad 1 Perspective; Numpad 7 Top; Numpad 5 Toggle; Home Frame Map; Numpad . Frame Selection; Esc Cancel transition.';
    navigationHelp.addEventListener('click', () => alert(navigationHelp.title));
    toolbar.append(perspectiveButton, topButton, navigationHelp, status);
    area.appendChild(toolbar);

    // #482: vertex shading is map/environment authoring, not another spatial
    // brush mode. Keep it in the Map palette and update the current resolved
    // geometry locally: no LÖVE lighting bake belongs on this feedback path.
    const shadingPanel = document.createElement('div');
    shadingPanel.id = 'vertex-shading-section';
    shadingPanel.style.cssText = 'margin-top:10px;padding-top:8px;border-top:1px solid var(--win-shadow);';
    const mapPalette = document.getElementById('map-palette-section');
    if (mapPalette) mapPalette.appendChild(shadingPanel);

    function currentMap() {
        const payload = host.getPayload && host.getPayload();
        const index = host.getMapIndex && host.getMapIndex();
        return payload && payload.maps && payload.maps[index];
    }

    function channelHex(value) {
        return Math.round(Math.max(0, Math.min(1, Number(value) || 0)) * 255)
            .toString(16).padStart(2, '0');
    }

    function rgbToHex(rgb) {
        const value = Array.isArray(rgb) ? rgb : [1, 1, 1];
        return `#${channelHex(value[0])}${channelHex(value[1])}${channelHex(value[2])}`;
    }

    function hexToRgb(hex) {
        const value = String(hex || '#ffffff').replace('#', '');
        return [0, 2, 4].map(offset => parseInt(value.slice(offset, offset + 2), 16) / 255);
    }

    function localShadingPreview() {
        const map = currentMap();
        if (!map) return;
        if (host.markMapDirty) host.markMapDirty();
        if (!backend || !currentBundle) return;
        try {
            Adapter.applyVertexModulation(currentBundle, map.vertexShadingLayers || []);
            backend.setRenderableBundle(currentBundle);
            setStatus(`${layerLabel()} · ${modeLabel()} · vertex shading`);
        } catch (error) {
            setStatus(`${layerLabel()} · ${modeLabel()} · invalid shading`, error.message);
        }
    }

    function controlRow(label, control) {
        const row = document.createElement('label');
        row.style.cssText = 'display:flex;align-items:center;gap:5px;margin:3px 0;font-size:10px;';
        const text = document.createElement('span');
        text.textContent = label;
        text.style.cssText = 'width:54px;flex:0 0 54px;';
        control.style.flex = '1';
        row.append(text, control);
        return row;
    }

    function renderVertexShadingPanel() {
        if (!shadingPanel) return;
        const map = currentMap();
        shadingPanel.innerHTML = '';
        const title = document.createElement('div');
        title.className = 'sidebar-title';
        title.textContent = 'Vertex Shading';
        shadingPanel.appendChild(title);

        const help = document.createElement('p');
        help.style.cssText = 'font-size:10px;color:var(--win-dark-shadow);line-height:1.3;margin:0 0 6px;';
        help.textContent = 'Smooth deterministic map-space tint. This changes environmental color, not illumination.';
        shadingPanel.appendChild(help);
        if (!map) return;

        const layers = Array.isArray(map.vertexShadingLayers) ? map.vertexShadingLayers : [];
        layers.forEach((layer, index) => {
            const box = document.createElement('div');
            box.style.cssText = 'margin:5px 0;padding:5px;border:1px solid var(--win-shadow);';
            const heading = document.createElement('div');
            heading.style.cssText = 'display:flex;justify-content:space-between;align-items:center;font-size:10px;font-weight:bold;';
            const name = document.createElement('span');
            name.textContent = `Color Noise ${index + 1}`;
            const remove = document.createElement('button');
            remove.type = 'button';
            remove.className = 'win98-btn';
            remove.style.cssText = 'font-size:9px;padding:1px 4px;';
            remove.textContent = 'Remove';
            remove.addEventListener('click', () => {
                map.vertexShadingLayers.splice(index, 1);
                if (map.vertexShadingLayers.length === 0) delete map.vertexShadingLayers;
                localShadingPreview();
                renderVertexShadingPanel();
            });
            heading.append(name, remove);
            box.appendChild(heading);

            const colorA = document.createElement('input');
            colorA.type = 'color';
            colorA.value = rgbToHex(layer.colorA);
            colorA.addEventListener('input', () => { layer.colorA = hexToRgb(colorA.value); localShadingPreview(); });
            box.appendChild(controlRow('Color A', colorA));

            const colorB = document.createElement('input');
            colorB.type = 'color';
            colorB.value = rgbToHex(layer.colorB);
            colorB.addEventListener('input', () => { layer.colorB = hexToRgb(colorB.value); localShadingPreview(); });
            box.appendChild(controlRow('Color B', colorB));

            const strengthWrap = document.createElement('div');
            strengthWrap.style.cssText = 'display:flex;align-items:center;gap:4px;flex:1;';
            const strength = document.createElement('input');
            strength.type = 'range'; strength.min = '0'; strength.max = '1'; strength.step = '0.01';
            strength.value = String(Number(layer.strength));
            strength.style.flex = '1';
            const strengthValue = document.createElement('span');
            strengthValue.style.cssText = 'width:28px;text-align:right;font-size:9px;';
            strengthValue.textContent = Number(layer.strength).toFixed(2);
            strength.addEventListener('input', () => {
                layer.strength = Number(strength.value);
                strengthValue.textContent = layer.strength.toFixed(2);
                localShadingPreview();
            });
            strengthWrap.append(strength, strengthValue);
            box.appendChild(controlRow('Strength', strengthWrap));

            const scale = document.createElement('input');
            scale.type = 'number'; scale.min = '0.1'; scale.max = '128'; scale.step = '0.1';
            scale.value = String(layer.scale);
            scale.addEventListener('input', () => {
                const value = Number(scale.value);
                if (Number.isFinite(value) && value > 0) { layer.scale = value; localShadingPreview(); }
            });
            box.appendChild(controlRow('Scale', scale));

            const seed = document.createElement('input');
            seed.type = 'number'; seed.step = '1';
            seed.value = String(layer.seed);
            seed.addEventListener('change', () => {
                const value = Number(seed.value);
                if (Number.isSafeInteger(value) && Math.abs(value) <= 2147483646) {
                    layer.seed = value;
                    localShadingPreview();
                }
            });
            box.appendChild(controlRow('Seed', seed));
            shadingPanel.appendChild(box);
        });

        const add = document.createElement('button');
        add.type = 'button';
        add.className = 'win98-btn';
        add.style.cssText = 'font-size:10px;padding:2px 6px;width:100%;';
        add.textContent = '+ Color Noise';
        add.addEventListener('click', () => {
            map.vertexShadingLayers = map.vertexShadingLayers || [];
            map.vertexShadingLayers.push({
                type: 'colorNoise',
                colorA: [0.88, 0.94, 0.90],
                colorB: [0.96, 0.88, 0.93],
                strength: 0.12,
                scale: 5,
                seed: 1729 + map.vertexShadingLayers.length * 101
            });
            localShadingPreview();
            renderVertexShadingPanel();
        });
        shadingPanel.appendChild(add);
    }

    function elementIsVisible(element) {
        if (!element || !element.getClientRects().length) return false;
        const style = window.getComputedStyle(element);
        return style.display !== 'none' && style.visibility !== 'hidden';
    }

    function hasBlockingOverlay() {
        const overlays = document.querySelectorAll('[id$="-modal"], .modal, .modal-overlay, .picker-overlay');
        for (const element of overlays) {
            if (element === toolbar || element === viewport || area.contains(element)) continue;
            if (elementIsVisible(element)) return true;
        }
        return false;
    }

    function mapSurfaceIsActive() {
        const active = legacyCanvas.getClientRects().length > 0 && !hasBlockingOverlay();
        return active;
    }

    function setDisplayIfNeeded(element, value) {
        if (element.style.display !== value) element.style.display = value;
    }

    function syncWorkspaceVisibility() {
        const active = mapSurfaceIsActive();
        setDisplayIfNeeded(toolbar, active ? 'flex' : 'none');
        setDisplayIfNeeded(viewport, active ? 'block' : 'none');
    }

    const surfaceObserver = new MutationObserver(syncWorkspaceVisibility);
    surfaceObserver.observe(document.body, { subtree: true, attributes: true, attributeFilter: ['class', 'style', 'hidden'] });

    function updateButtons() {
        [perspectiveButton, topButton].forEach(el => {
            const active = el.dataset.mode === currentMode;
            el.disabled = active;
            el.style.fontWeight = active ? 'bold' : 'normal';
        });
    }

    function ensureImportMap() {
        if (document.querySelector('script[type="importmap"]')) return;
        throw new Error('Three.js import map is missing from index.html; the 3D backend cannot resolve "three".');
    }

    function describeSelection(selection) {
        if (!selection) return `${layerLabel()} · ${modeLabel()}`;
        if (selection.kind === 'cell') return `${layerLabel()} · Cell ${selection.cell.x}, ${selection.cell.y}`;
        if (selection.kind === 'event') return `${layerLabel()} · Event ${selection.id}`;
        if (selection.kind === 'light') return `${layerLabel()} · Light ${selection.cell.x}, ${selection.cell.y}`;
        if (selection.kind === 'override') return `${layerLabel()} · Override ${selection.cell.x}, ${selection.cell.y}`;
        if (selection.kind === 'spawn') return `${layerLabel()} · Player Start`;
        return `${layerLabel()} · ${selection.kind}`;
    }

    function clearAuthoritativeForSemanticFallback() {
        currentBundle = null;
        if (backend) backend.setRenderableBundle(null);
        setStatus(`${layerLabel()} · ${modeLabel()} · syncing runtime geometry`);
    }

    function scheduleMutation(kind) {
        const plan = WorkspaceState.mutationPlan(kind);
        if (plan.bundleRefresh) {
            // Invalidate an already-running compile immediately. Waiting until
            // the debounced replacement starts leaves a window where stale
            // runtime geometry can overwrite a newer authored edit.
            bundleSerial += 1;
        }
        if (plan.clearBundleImmediately) clearAuthoritativeForSemanticFallback();
        if (plan.semanticRefresh) scheduleSemanticRefresh();
        if (plan.bundleRefresh) scheduleBundleRefresh();
    }

    function handleMutationResult(result, kind) {
        if (result && result.changed) scheduleMutation(kind);
        return result;
    }

    function ensureBackend() {
        if (backend) return Promise.resolve(backend);
        if (backendPromise) return backendPromise;
        ensureImportMap();
        backendPromise = import('/js/three-editor-viewport.js').then(module => {
            backend = module.createThreeEditorViewport(viewport, {
                getInteractionMode: () => host.getEditingMode ? host.getEditingMode() : null,
                onSelection(selection) {
                    if (host.selectSemantic) host.selectSemantic(selection);
                    setStatus(describeSelection(selection));
                },
                onPaintCell(cell) {
                    return handleMutationResult(
                        host.paintCell ? host.paintCell(cell.cell.x, cell.cell.y) : null,
                        'topology'
                    );
                },
                canMoveEvent(eventSelection, cell) {
                    return host.canMoveEvent ? host.canMoveEvent(eventSelection.id, cell.cell.x, cell.cell.y) : { ok: false };
                },
                onMoveEvent(eventSelection, cell) {
                    return handleMutationResult(
                        host.moveEvent ? host.moveEvent(eventSelection.id, cell.cell.x, cell.cell.y) : null,
                        'event-move'
                    );
                },
                canMoveLight(lightSelection, cell) {
                    return host.canMoveLight ? host.canMoveLight(lightSelection.index, cell.cell.x, cell.cell.y) : { ok: false };
                },
                onMoveLight(lightSelection, cell) {
                    return handleMutationResult(
                        host.moveLight ? host.moveLight(lightSelection.index, cell.cell.x, cell.cell.y) : null,
                        'light-move'
                    );
                },
                onOpenAt(selection) {
                    if (host.openAt) host.openAt(selection);
                }
            });
            return backend;
        }).catch(error => {
            backendPromise = null;
            setStatus('3D unavailable', error.message);
            console.error('Thestra Editor Scene backend failed to load:', error);
            throw error;
        });
        return backendPromise;
    }

    async function refreshSemanticScene(options) {
        options = options || {};
        const serial = ++semanticSerial;
        const payload = host.getPayload();
        const mapIndex = host.getMapIndex();
        const three = await ensureBackend();
        const inspection = host.getMapInspection ? host.getMapInspection() : null;
        const sceneModel = await Adapter.buildScene(payload, mapIndex, inspection);
        if (serial !== semanticSerial) return;
        three.setSceneModel(sceneModel);
        three.setMode(currentMode);
        loadedMapIndex = mapIndex;
        if (options.clearBundle) {
            currentBundle = null;
            three.setRenderableBundle(null);
        }
        renderVertexShadingPanel();
        const suffix = sceneModel.map.provisionalGeometry ? ' · layout preview' : '';
        setStatus(`${layerLabel()} · ${modeLabel()}${suffix}`);
    }

    async function refreshAuthoritativeBundle(options) {
        options = options || {};
        const serial = ++bundleSerial;
        const payload = host.getPayload();
        const mapIndex = host.getMapIndex();
        const map = payload && payload.maps && payload.maps[mapIndex];
        const three = await ensureBackend();
        if (options.clearFirst) {
            currentBundle = null;
            three.setRenderableBundle(null);
        }
        setStatus(`${layerLabel()} · ${modeLabel()} · compiling`);
        try {
            const inspection = host.getMapInspection ? host.getMapInspection() : null;
            const bundle = await Adapter.loadRenderable(map, {
                seed: inspection && inspection.request && inspection.request.seed
            });
            if (serial !== bundleSerial) return;
            currentBundle = bundle;
            three.setRenderableBundle(bundle);
            bundleStatus = 'runtime geometry';
            setStatus(`${layerLabel()} · ${modeLabel()} · runtime geometry`);
        } catch (error) {
            if (serial !== bundleSerial) return;
            currentBundle = null;
            three.setRenderableBundle(null);
            setStatus(`${layerLabel()} · ${modeLabel()} · ${WorkspaceState.fallbackStatusLabel()}`, error.message);
            console.warn('Authoritative map renderable unavailable:', error.message);
        }
    }

    function scheduleSemanticRefresh() {
        if (semanticRefreshQueued) return;
        semanticRefreshQueued = true;
        requestAnimationFrame(() => {
            semanticRefreshQueued = false;
            refreshSemanticScene().catch(console.error);
        });
    }

    function scheduleBundleRefresh() {
        if (bundleTimer) clearTimeout(bundleTimer);
        bundleTimer = setTimeout(() => {
            bundleTimer = null;
            refreshAuthoritativeBundle({ clearFirst: false }).catch(console.error);
        }, 180);
    }

    function scheduleAfterAuthoredMutation() {
        scheduleMutation('authoritative-property');
    }

    async function refreshAll(options) {
        options = options || {};
        await refreshSemanticScene({ clearBundle: !!options.clearBundle });
        // Runtime authority catches up independently. The semantic viewport is
        // already usable when this function resolves.
        refreshAuthoritativeBundle({ clearFirst: false }).catch(console.error);
    }

    async function activate(mode) {
        const plan = WorkspaceState.transitionPlan(
            currentMode, mode, loadedMapIndex, host.getMapIndex()
        );
        currentMode = mode;
        legacyCanvas.style.visibility = 'hidden';
        setStatus('Loading 3D…');
        updateButtons();
        syncWorkspaceVisibility();
        try {
            if (plan.cameraOnly) {
                const three = await ensureBackend();
                await three.transitionToMode(currentMode);
                setStatus(`${layerLabel()} · ${modeLabel()} · runtime geometry`);
                return;
            }
            if (plan.reloadScene) await refreshAll({ clearBundle: true });
        } catch (error) {
            currentMode = 'perspective';
            setDisplayIfNeeded(viewport, 'block');
            updateButtons();
            syncWorkspaceVisibility();
            alert('The 3D authoring viewport could not start. Run npm install and launch the editor with npm start so the Three.js vendor files are prepared.\n\n' + error.message);
        }
    }

    const originalLoadActiveMap = window.loadActiveMap;
    if (typeof originalLoadActiveMap === 'function') {
        window.loadActiveMap = function () {
            const result = originalLoadActiveMap.apply(this, arguments);
            renderVertexShadingPanel();
            refreshAll({ clearBundle: true }).catch(console.error);
            return result;
        };
    }

    const eventModal = document.getElementById('event-modal');
    if (eventModal) {
        let wasVisible = elementIsVisible(eventModal);
        new MutationObserver(() => {
            const visible = elementIsVisible(eventModal);
            if (wasVisible && !visible) scheduleAfterAuthoredMutation();
            wasVisible = visible;
        }).observe(eventModal, { attributes: true, attributeFilter: ['class', 'style', 'hidden'] });
    }

    function inspectorMutation(event) {
        const id = event.target && event.target.id || '';
        if (id.startsWith('light-object-')) {
            scheduleMutation('light-property');
            return;
        }
        if (id.startsWith('override-')) scheduleAfterAuthoredMutation();
    }
    document.addEventListener('input', inspectorMutation);
    document.addEventListener('change', inspectorMutation);
    window.addEventListener('thestra-map-inspection-changed', () => {
        refreshAll({ clearBundle: true }).catch(console.error);
    });

    legacyCanvas.style.visibility = 'hidden';
    syncWorkspaceVisibility();
    updateButtons();
    renderVertexShadingPanel();
    activate('perspective').catch(console.error);
}());