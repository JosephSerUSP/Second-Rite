(function () {
    'use strict';

    const host = window.ThestraEditorHost;
    const Adapter = window.SecondRiteEditorAdapter;
    if (!host || !Adapter) return;

    const legacyCanvas = document.getElementById('map-canvas');
    const area = legacyCanvas && legacyCanvas.parentElement;
    if (!legacyCanvas || !area) return;

    let backend = null;
    let backendPromise = null;
    let currentMode = 'legacy';
    let refreshSerial = 0;

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
    const perspectiveButton = button('Perspective', 'perspective', 'Shared Thestra Editor Scene — perspective camera');
    const topButton = button('Top Ortho', 'top', 'Shared Thestra Editor Scene — orthographic top camera');
    toolbar.append(legacyButton, perspectiveButton, topButton, status);
    area.appendChild(toolbar);

    function elementIsVisible(element) {
        if (!element || !element.getClientRects().length) return false;
        const style = window.getComputedStyle(element);
        return style.display !== 'none' && style.visibility !== 'hidden';
    }

    function hasBlockingOverlay() {
        // Studio intentionally keeps the map editor mounted behind dialogs and
        // tool surfaces. Some overlays toggle an `.active` class; older tools
        // such as Tileset Studio toggle `style.display` directly. Visibility,
        // not one particular activation convention, is the real boundary.
        const overlays = document.querySelectorAll('[id$="-modal"], .modal, .modal-overlay, .picker-overlay');
        for (const element of overlays) {
            if (element === toolbar || element === viewport || area.contains(element)) continue;
            if (elementIsVisible(element)) return true;
        }
        return false;
    }

    function mapSurfaceIsActive() {
        // `visibility:hidden` is our own 2D->3D swap and deliberately preserves
        // layout. `display:none` ancestors still mean the map surface is absent.
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

    // Studio surfaces are switched by class/style changes rather than by
    // mounting a fresh map editor. Watch that explicit UI state so map-only
    // chrome follows modal/tool open and close transitions immediately.
    const surfaceObserver = new MutationObserver(syncWorkspaceVisibility);
    surfaceObserver.observe(document.body, {
        subtree: true,
        attributes: true,
        attributeFilter: ['class', 'style', 'hidden']
    });

    function updateButtons() {
        [legacyButton, perspectiveButton, topButton].forEach(el => {
            const active = el.dataset.mode === currentMode;
            el.disabled = active;
            el.style.fontWeight = active ? 'bold' : 'normal';
        });
    }

    function ensureImportMap() {
        if (document.getElementById('thestra-three-import-map')) return;
        const map = document.createElement('script');
        map.id = 'thestra-three-import-map';
        map.type = 'importmap';
        map.textContent = JSON.stringify({ imports: { three: '/vendor/three/three.module.js' } });
        document.head.appendChild(map);
    }

    function ensureBackend() {
        if (backend) return Promise.resolve(backend);
        if (backendPromise) return backendPromise;
        ensureImportMap();
        backendPromise = import('/js/three-editor-viewport.js').then(module => {
            backend = module.createThreeEditorViewport(viewport, {
                onSelection(selection) {
                    if (selection.kind === 'cell') setStatus(`Cell ${selection.cell.x}, ${selection.cell.y}`);
                    else setStatus(`Event ${selection.id}`);
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

    function modeLabel() {
        return currentMode === 'top' ? 'Top' : '3D';
    }

    function fallbackLabel(error) {
        if (error && error.code === 'bridge-refused') return 'bridge refused · fallback';
        if (error && error.code === 'bridge-unreachable') return 'bridge offline · fallback';
        if (error && error.code === 'bridge-runtime-error') return 'runtime error · fallback';
        return 'semantic fallback';
    }

    async function refreshScene() {
        if (currentMode === 'legacy') return;
        const serial = ++refreshSerial;
        const payload = host.getPayload();
        const mapIndex = host.getMapIndex();
        const map = payload && payload.maps && payload.maps[mapIndex];
        const three = await ensureBackend();
        const sceneModel = await Adapter.buildScene(payload, mapIndex);
        if (serial !== refreshSerial || currentMode === 'legacy') return;

        // Semantic proxies are immediate and remain the picking/editing model.
        // They are deliberately not a second renderer: until #287's LÖVE
        // compiler responds they use neutral fallback surfaces only.
        three.setSceneModel(sceneModel);
        three.setMode(currentMode);
        three.setRenderableBundle(null);
        const provisional = sceneModel.map.provisionalGeometry ? ' · layout preview' : '';
        setStatus(`${modeLabel()} · compiling${provisional}`);

        try {
            const bundle = await Adapter.loadRenderable(map);
            if (serial !== refreshSerial || currentMode === 'legacy') return;
            three.setRenderableBundle(bundle);
            setStatus(`${modeLabel()} · runtime geometry`);
        } catch (error) {
            if (serial !== refreshSerial || currentMode === 'legacy') return;
            // Browser-only / external-project sessions are still useful. The
            // fallback is intentionally neutral and loudly labelled rather than
            // reimplementing runtime tileset/geometry rules in JavaScript.
            three.setRenderableBundle(null);
            setStatus(`${modeLabel()} · ${fallbackLabel(error)}${provisional}`, error.message);
            console.warn('Authoritative map renderable unavailable:', error.message);
        }
    }

    async function activate(mode) {
        if (mode === 'legacy') {
            currentMode = 'legacy';
            refreshSerial++;
            setDisplayIfNeeded(viewport, 'none');
            legacyCanvas.style.visibility = 'visible';
            setStatus('2D edit');
            updateButtons();
            syncWorkspaceVisibility();
            return;
        }

        currentMode = mode;
        legacyCanvas.style.visibility = 'hidden';
        setStatus('Loading 3D…');
        updateButtons();
        syncWorkspaceVisibility();
        try {
            await refreshScene();
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
            if (currentMode !== 'legacy') refreshScene().catch(console.error);
            return result;
        };
    }

    syncWorkspaceVisibility();
    updateButtons();
}());
