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
    status.style.cssText = 'padding:0 4px;min-width:88px;color:var(--win-dark-shadow);white-space:nowrap;';
    status.textContent = '2D edit';

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
                    if (selection.kind === 'cell') status.textContent = `Cell ${selection.cell.x}, ${selection.cell.y}`;
                    else status.textContent = `Event ${selection.id}`;
                }
            });
            return backend;
        }).catch(error => {
            backendPromise = null;
            status.textContent = '3D unavailable';
            console.error('Thestra Editor Scene backend failed to load:', error);
            throw error;
        });
        return backendPromise;
    }

    async function refreshScene() {
        if (currentMode === 'legacy') return;
        const serial = ++refreshSerial;
        const payload = host.getPayload();
        const mapIndex = host.getMapIndex();
        const three = await ensureBackend();
        const sceneModel = await Adapter.buildScene(payload, mapIndex);
        if (serial !== refreshSerial || currentMode === 'legacy') return;
        three.setSceneModel(sceneModel);
        three.setMode(currentMode);
        const suffix = sceneModel.map.provisionalGeometry ? ' · layout preview' : '';
        status.textContent = `${currentMode === 'top' ? 'Top' : '3D'}${suffix}`;
    }

    async function activate(mode) {
        if (mode === 'legacy') {
            currentMode = 'legacy';
            viewport.style.display = 'none';
            legacyCanvas.style.visibility = 'visible';
            status.textContent = '2D edit';
            updateButtons();
            return;
        }

        currentMode = mode;
        viewport.style.display = 'block';
        legacyCanvas.style.visibility = 'hidden';
        status.textContent = 'Loading 3D…';
        updateButtons();
        try {
            await refreshScene();
        } catch (error) {
            currentMode = 'legacy';
            viewport.style.display = 'none';
            legacyCanvas.style.visibility = 'visible';
            updateButtons();
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

    updateButtons();
}());
