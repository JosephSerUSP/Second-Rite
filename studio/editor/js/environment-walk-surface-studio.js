import '/js/environment-walk-surface-overlay.js';

const Overlay = globalThis.ThestraEnvironmentWalkSurfaceOverlay;
if (!Overlay) throw new Error('Environment walk-surface overlay failed to load.');

const state = {
    viewport: null,
    packagePath: null,
    manifest: null,
    status: 'idle',
    error: null,
    requestSerial: 0,
    lastPanelSignature: null,
};

function projectAssetUrl(path) {
    if (!path) return null;
    return path.startsWith('/') ? path : '/' + path;
}

function currentMap() {
    const host = globalThis.ThestraEditorHost;
    if (!host?.getPayload || !host?.getMapIndex) return null;
    const payload = host.getPayload();
    return payload?.maps?.[host.getMapIndex()] || null;
}

function packagePathFor(map) {
    return map?.traversal?.environmentPackage || null;
}

function ensureViewport() {
    const viewport = globalThis.ThestraRuntimeCameraViewport;
    if (!viewport) return null;
    if (state.viewport !== viewport) {
        state.viewport = viewport;
        Overlay.install(viewport);
        if (state.manifest) viewport.setEnvironmentWalkSurfaceManifest?.(state.manifest, state.packagePath);
    }
    return viewport;
}

function row(label, value) {
    const node = document.createElement('div');
    node.style.cssText = 'display:grid;grid-template-columns:74px minmax(0,1fr);gap:6px;align-items:center;margin:3px 0;font-size:10px;';
    const key = document.createElement('span');
    key.style.color = 'var(--win-dark-shadow)';
    key.textContent = label;
    const text = document.createElement('span');
    text.style.cssText = 'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;';
    text.textContent = value == null || value === '' ? '—' : String(value);
    text.title = text.textContent;
    node.append(key, text);
    return node;
}

function title(text) {
    const node = document.createElement('div');
    node.className = 'sidebar-title';
    node.style.marginTop = '8px';
    node.textContent = text;
    return node;
}

function note(text, error = false) {
    const node = document.createElement('p');
    node.style.cssText = `margin:3px 0 7px;font-size:10px;line-height:1.35;color:${error ? '#800000' : 'var(--win-dark-shadow)'};`;
    node.textContent = text;
    return node;
}

function action(label, handler, pressed) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'win98-btn';
    button.style.cssText = 'width:100%;margin:5px 0 2px;padding:3px 6px;';
    button.textContent = label;
    if (pressed != null) button.setAttribute('aria-pressed', String(!!pressed));
    button.addEventListener('click', handler);
    return button;
}

function panelSignature(info) {
    return JSON.stringify({
        path: state.packagePath,
        status: state.status,
        error: state.error,
        info,
    });
}

function renderPanel(force = false) {
    const body = document.getElementById('thestra-map-inspector-body');
    if (!body) return;
    let panel = body.querySelector('[data-environment-walk-surface-inspector="true"]');
    const info = ensureViewport()?.getWalkSurfaceInfo?.() || null;
    const signature = panelSignature(info);
    if (!force && panel && signature === state.lastPanelSignature) return;
    state.lastPanelSignature = signature;

    if (!panel) {
        panel = document.createElement('section');
        panel.dataset.environmentWalkSurfaceInspector = 'true';
        panel.style.cssText = 'border-top:1px solid var(--win-shadow);margin-top:9px;padding-top:2px;';
        body.appendChild(panel);
    }
    panel.replaceChildren();
    panel.append(title('Walk Surface'));

    if (!state.packagePath) {
        panel.append(note('This Map has no environment-package walk surface.'));
        return;
    }
    panel.append(row('Authority', 'Environment package'));
    if (state.status === 'loading') {
        panel.append(note('Reading exported walk authority…'));
        return;
    }
    if (state.status === 'error') {
        panel.append(note(`Walk surface could not be inspected: ${state.error}`, true));
        return;
    }
    if (!info?.available) {
        panel.append(note('The environment package does not export walkSurface.'));
        return;
    }

    panel.append(row('Ground Z', info.groundZ));
    panel.append(row('Regions', info.regionCount));
    panel.append(row('Obstacles', info.obstacleCount));
    if (info.authority) panel.append(row('Source', info.authority));
    panel.append(note('Read-only exported authority. Cyan is walkable; orange is blocking. Studio displays these Blender-authored polygons but does not own or rewrite them.'));
    panel.append(action(info.visible ? 'Hide Walk Surface' : 'Show Walk Surface', () => {
        const viewport = ensureViewport();
        viewport?.setWalkSurfaceVisible?.(!viewport.getWalkSurfaceVisible());
        renderPanel(true);
    }, info.visible));
}

async function syncPackage() {
    const viewport = ensureViewport();
    const nextPath = packagePathFor(currentMap());
    if (nextPath === state.packagePath && (state.status === 'loading' || state.manifest || state.status === 'error')) {
        renderPanel();
        return;
    }

    state.packagePath = nextPath;
    state.manifest = null;
    state.error = null;
    state.lastPanelSignature = null;
    state.requestSerial += 1;
    const serial = state.requestSerial;
    viewport?.clearEnvironmentWalkSurfaceManifest?.();
    if (!nextPath) {
        state.status = 'idle';
        renderPanel(true);
        return;
    }

    state.status = 'loading';
    renderPanel(true);
    try {
        const response = await fetch(projectAssetUrl(nextPath), { cache: 'no-store' });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const manifest = await response.json();
        if (serial !== state.requestSerial || nextPath !== state.packagePath) return;
        state.manifest = manifest;
        state.status = 'ready';
        ensureViewport()?.setEnvironmentWalkSurfaceManifest?.(manifest, nextPath);
    } catch (error) {
        if (serial !== state.requestSerial || nextPath !== state.packagePath) return;
        state.status = 'error';
        state.error = error instanceof Error ? error.message : String(error);
    }
    renderPanel(true);
}

function installInspectorObserver() {
    const inspector = document.getElementById('thestra-map-inspector');
    if (!inspector || inspector.dataset.walkSurfaceObserver === 'true') return false;
    inspector.dataset.walkSurfaceObserver = 'true';
    const observer = new MutationObserver(() => {
        queueMicrotask(() => {
            syncPackage().catch(error => console.error('Walk-surface inspection sync failed:', error));
            renderPanel();
        });
    });
    observer.observe(inspector, { childList: true, subtree: true });
    return true;
}

function install() {
    ensureViewport();
    installInspectorObserver();
    syncPackage().catch(error => console.error('Walk-surface inspection failed:', error));
}

globalThis.addEventListener('thestra-runtime-camera-viewport-ready', install);
globalThis.addEventListener('thestra-composition-preview-ready', () => {
    syncPackage().catch(error => console.error('Walk-surface inspection refresh failed:', error));
});

document.addEventListener('DOMContentLoaded', install, { once: true });
const poll = setInterval(() => {
    install();
    if (state.viewport && document.getElementById('thestra-map-inspector')) clearInterval(poll);
}, 50);
setTimeout(() => clearInterval(poll), 15000);

export const environmentWalkSurfaceStudio = { syncPackage, renderPanel, state };
