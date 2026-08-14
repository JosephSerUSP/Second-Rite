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
    let currentMode = 'legacy';
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
    status.textContent = '2D edit';

    function setStatus(text, detail) {
        status.textContent = text;
        status.title = detail || '';
    }

    function layerLabel() {
        const layer = host.getEditingMode ? host.getEditingMode() : null;
        return ({ map: 'Map', event: 'Event', light: 'Light', override: 'Override' })[layer] || 'Select';
    }

    function modeLabel() { return currentMode === 'top' ? 'Top' : '3D'; }

    function fallbackLabel(error) {
        if (error && error.code === 'bridge-refused') return 'bridge refused · fallback';
        if (error && error.code === 'bridge-unreachable') return 'bridge offline · fallback';
        if (error && error.code === 'bridge-runtime-error') return 'runtime error · fallback';
        return 'semantic fallback';
    }

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

    const legacyButton = button('2D Edit', 'legacy', 'Existing map editor canvas');
    const perspectiveButton = button('Perspective', 'perspective', 'Shared Thestra Editor Scene — perspective authoring camera');
    const topButton = button('Top Ortho', 'top', 'Shared Thestra Editor Scene — orthographic authoring camera');
    toolbar.append(legacyButton, perspectiveButton, topButton, status);
    area.appendChild(toolbar);

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
        return legacyCanvas.getClientRects().length > 0 && !hasBlockingOverlay();
    }

    function setDisplayIfNeeded(element, value) {
        if (element.style.display !== value) element.style.display = value;
    }

    function syncWorkspaceVisibility() {
        const active = mapSurfaceIsActive();
        setDisplayIfNeeded(toolbar, active ? 'flex' : 'none');
        setDisplayIfNeeded(viewport, active && currentMode !== 'legacy' ? 'block' : 'none');
    }

    const surfaceObserver = new MutationObserver(syncWorkspaceVisibility);
    surfaceObserver.observe(document.body, { subtree: true, attributes: true, attributeFilter: ['class', 'style', 'hidden'] });

    function updateButtons() {
        [legacyButton, perspectiveButton, topButton].forEach(el => {
            const active = el.dataset.mode === currentMode;
            el.disabled = active;
            el.style.fontWeight = active ? 'bold' : 'normal';
        });
    }

    // The import map is declared statically in index.html: a map must precede
    // the first module import, and it is now shared with the item model
    // preview, so injecting a second copy lazily would be both a race and a
    // duplicate. Fail loudly rather than silently importing nothing.
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

    function handleMutationResult(result) {
        if (result && result.changed) scheduleAfterAuthoredMutation();
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
                    return handleMutationResult(host.paintCell ? host.paintCell(cell.cell.x, cell.cell.y) : null);
                },
                canMoveEvent(eventSelection, cell) {
                    return host.canMoveEvent ? host.canMoveEvent(eventSelection.id, cell.cell.x, cell.cell.y) : { ok: false };
                },
                onMoveEvent(eventSelection, cell) {
                    return handleMutationResult(host.moveEvent ? host.moveEvent(eventSelection.id, cell.cell.x, cell.cell.y) : null);
                },
                canMoveLight(lightSelection, cell) {
                    return host.canMoveLight ? host.canMoveLight(lightSelection.index, cell.cell.x, cell.cell.y) : { ok: false };
                },
                onMoveLight(lightSelection, cell) {
                    return handleMutationResult(host.moveLight ? host.moveLight(lightSelection.index, cell.cell.x, cell.cell.y) : null);
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
        if (currentMode === 'legacy') return;
        const serial = ++semanticSerial;
        const payload = host.getPayload();
        const mapIndex = host.getMapIndex();
        const three = await ensureBackend();
        const sceneModel = await Adapter.buildScene(payload, mapIndex);
        if (serial !== semanticSerial || currentMode === 'legacy') return;
        three.setSceneModel(sceneModel);
        three.setMode(currentMode);
        loadedMapIndex = mapIndex;
        if (options.clearBundle) three.setRenderableBundle(null);
        const suffix = sceneModel.map.provisionalGeometry ? ' · layout preview' : '';
        setStatus(`${layerLabel()} · ${modeLabel()}${suffix}`);
    }

    async function refreshAuthoritativeBundle(options) {
        options = options || {};
        if (currentMode === 'legacy') return;
        const serial = ++bundleSerial;
        const payload = host.getPayload();
        const mapIndex = host.getMapIndex();
        const map = payload && payload.maps && payload.maps[mapIndex];
        const three = await ensureBackend();
        if (options.clearFirst) three.setRenderableBundle(null);
        setStatus(`${layerLabel()} · ${modeLabel()} · compiling`);
        try {
            const bundle = await Adapter.loadRenderable(map);
            if (serial !== bundleSerial || currentMode === 'legacy') return;
            three.setRenderableBundle(bundle);
            bundleStatus = 'runtime geometry';
            setStatus(`${layerLabel()} · ${modeLabel()} · runtime geometry`);
        } catch (error) {
            if (serial !== bundleSerial || currentMode === 'legacy') return;
            // A failed refresh must not leave stale runtime geometry covering
            // the newly-authored semantic state. Reveal the neutral proxies.
            three.setRenderableBundle(null);
            setStatus(`${layerLabel()} · ${modeLabel()} · ${fallbackLabel(error)}`, error.message);
            console.warn('Authoritative map renderable unavailable:', error.message);
        }
    }

    function scheduleSemanticRefresh() {
        if (currentMode === 'legacy' || semanticRefreshQueued) return;
        semanticRefreshQueued = true;
        requestAnimationFrame(() => {
            semanticRefreshQueued = false;
            refreshSemanticScene().catch(console.error);
        });
    }

    function scheduleBundleRefresh() {
        if (currentMode === 'legacy') return;
        if (bundleTimer) clearTimeout(bundleTimer);
        bundleTimer = setTimeout(() => {
            bundleTimer = null;
            // Keep the last authoritative mesh visible while the new bundle is
            // compiled. Semantic proxies already show the edit immediately.
            refreshAuthoritativeBundle({ clearFirst: false }).catch(console.error);
        }, 180);
    }

    function scheduleAfterAuthoredMutation() {
        scheduleSemanticRefresh();
        scheduleBundleRefresh();
    }

    async function refreshAll(options) {
        options = options || {};
        await refreshSemanticScene({ clearBundle: !!options.clearBundle });
        await refreshAuthoritativeBundle({ clearFirst: false });
    }

    async function activate(mode) {
        if (mode === 'legacy') {
            currentMode = 'legacy';
            semanticSerial++;
            bundleSerial++;
            if (bundleTimer) { clearTimeout(bundleTimer); bundleTimer = null; }
            setDisplayIfNeeded(viewport, 'none');
            legacyCanvas.style.visibility = 'visible';
            setStatus('2D edit');
            updateButtons();
            syncWorkspaceVisibility();
            return;
        }

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
            currentMode = 'legacy';
            setDisplayIfNeeded(viewport, 'none');
            legacyCanvas.style.visibility = 'visible';
            updateButtons();
            syncWorkspaceVisibility();
            alert('The 3D authoring viewport could not start. Run npm install and launch the editor with npm start so the Three.js vendor files are prepared.\n\n' + error.message);
        }
    }

    const originalLoadActiveMap = window.loadActiveMap;
    if (typeof originalLoadActiveMap === 'function') {
        window.loadActiveMap = function () {
            const result = originalLoadActiveMap.apply(this, arguments);
            if (currentMode !== 'legacy') refreshAll({ clearBundle: true }).catch(console.error);
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
        if (currentMode !== 'legacy' && (id.startsWith('light-object-') || id.startsWith('override-'))) scheduleAfterAuthoredMutation();
    }
    document.addEventListener('input', inspectorMutation);
    document.addEventListener('change', inspectorMutation);

    syncWorkspaceVisibility();
    updateButtons();
}());
