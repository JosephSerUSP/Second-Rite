(function (root, factory) {
    if (typeof module === 'object' && module.exports) module.exports = factory();
    else root.ThestraMapInspector = factory();
}(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    const MIN_WIDTH = 220;
    const MAX_WIDTH = 520;
    const DEFAULT_WIDTH = 284;

    function clampWidth(value) {
        const n = Number(value);
        if (!Number.isFinite(n)) return DEFAULT_WIDTH;
        return Math.max(MIN_WIDTH, Math.min(MAX_WIDTH, Math.round(n)));
    }

    function selectionContext(payload, mapIndex, selection) {
        const maps = payload && Array.isArray(payload.maps) ? payload.maps : [];
        const map = maps[mapIndex] || null;
        if (!map) return { kind: 'empty', map: null, source: null };
        if (!selection || !selection.kind) return { kind: 'environment', map, source: map };

        if (selection.kind === 'light') {
            const source = (map.lightObjects || [])[Number(selection.index)] || null;
            return source ? { kind: 'light', map, source, selection } : { kind: 'environment', map, source: map };
        }
        if (selection.kind === 'override') {
            const source = (map.overrides || [])[Number(selection.index)] || null;
            return source ? { kind: 'override', map, source, selection } : { kind: 'environment', map, source: map };
        }
        if (selection.kind === 'event') {
            const source = (map.events || []).find((event, index) =>
                String(event && event.id != null ? event.id : index) === String(selection.id));
            return source ? { kind: 'event', map, source, selection } : { kind: 'environment', map, source: map };
        }
        if (selection.kind === 'spawn') {
            const source = payload && payload.system && payload.system.spawn;
            return source ? { kind: 'spawn', map, source, selection } : { kind: 'environment', map, source: map };
        }
        if (selection.kind === 'cell') return { kind: 'cell', map, source: selection, selection };
        return { kind: 'environment', map, source: map };
    }

    function numericInputIsValid(id, value) {
        if (id !== 'lamp-radius' && id !== 'lamp-falloff') return true;
        const n = Number(value);
        return Number.isFinite(n) && n >= 0.1;
    }

    return { MIN_WIDTH, MAX_WIDTH, DEFAULT_WIDTH, clampWidth, selectionContext, numericInputIsValid };
}));

(function installMapInspector() {
    if (typeof window === 'undefined' || typeof document === 'undefined') return;
    const Contract = window.ThestraMapInspector;
    const host = window.ThestraEditorHost;
    const legacyCanvas = document.getElementById('map-canvas');
    if (!Contract || !host || !legacyCanvas) return;

    const workspace = legacyCanvas.closest('.workspace') || document.querySelector('.workspace');
    if (!workspace || document.getElementById('thestra-map-inspector')) return;

    let currentSelection = null; // render mirror only; authored selection remains owned by the Editor Scene/host.
    let lastMapIndex = host.getMapIndex ? host.getMapIndex() : 0;
    let collapsed = false;
    let width = Contract.clampWidth(Number(localStorage.getItem('thestra-map-inspector-width')) || Contract.DEFAULT_WIDTH);

    const parking = document.createElement('div');
    parking.id = 'thestra-map-inspector-parking';
    parking.hidden = true;
    document.body.appendChild(parking);

    const inspector = document.createElement('aside');
    inspector.id = 'thestra-map-inspector';
    inspector.setAttribute('aria-label', 'Map Inspector');
    inspector.style.cssText = [
        'position:relative', 'flex:0 0 auto', `width:${width}px`, 'min-width:0',
        'background:var(--win-gray)', 'border-left:1px solid var(--win-shadow)',
        'box-sizing:border-box', 'display:flex', 'flex-direction:column', 'overflow:hidden'
    ].join(';');

    const splitter = document.createElement('div');
    splitter.id = 'thestra-map-inspector-splitter';
    splitter.title = 'Drag to resize Inspector';
    splitter.style.cssText = 'position:absolute;left:0;top:0;bottom:0;width:5px;cursor:ew-resize;z-index:5;background:transparent;';

    const header = document.createElement('div');
    header.style.cssText = 'height:25px;flex:0 0 25px;display:flex;align-items:center;gap:5px;padding:0 4px 0 8px;border-bottom:1px solid var(--win-shadow);box-sizing:border-box;font-weight:bold;';
    const heading = document.createElement('span');
    heading.textContent = 'Inspector';
    heading.style.cssText = 'flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;';
    const collapse = document.createElement('button');
    collapse.type = 'button';
    collapse.className = 'win98-btn';
    collapse.style.cssText = 'width:20px;height:18px;padding:0;font-size:10px;line-height:14px;';
    collapse.title = 'Collapse Inspector';
    collapse.textContent = '▶';
    header.append(heading, collapse);

    const body = document.createElement('div');
    body.id = 'thestra-map-inspector-body';
    body.style.cssText = 'flex:1;min-height:0;overflow:auto;padding:8px 8px 12px 10px;box-sizing:border-box;';

    const error = document.createElement('div');
    error.id = 'thestra-map-inspector-error';
    error.setAttribute('role', 'alert');
    error.style.cssText = 'display:none;margin:0 0 6px;padding:4px;border:1px solid #800000;background:#fff4f4;color:#800000;font-size:10px;line-height:1.3;';

    inspector.append(splitter, header, body);
    workspace.appendChild(inspector);

    function sectionTitle(text) {
        const el = document.createElement('div');
        el.className = 'sidebar-title';
        el.textContent = text;
        el.style.marginTop = '2px';
        return el;
    }

    function muted(text) {
        const el = document.createElement('p');
        el.style.cssText = 'margin:3px 0 7px;color:var(--win-dark-shadow);font-size:10px;line-height:1.35;';
        el.textContent = text;
        return el;
    }

    function infoRow(label, value) {
        const row = document.createElement('div');
        row.style.cssText = 'display:grid;grid-template-columns:74px minmax(0,1fr);gap:6px;align-items:center;margin:3px 0;font-size:10px;';
        const key = document.createElement('span');
        key.style.color = 'var(--win-dark-shadow)';
        key.textContent = label;
        const val = document.createElement('span');
        val.style.cssText = 'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;';
        val.title = String(value == null ? '' : value);
        val.textContent = String(value == null || value === '' ? '—' : value);
        row.append(key, val);
        return row;
    }

    function actionButton(label, handler) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'win98-btn';
        button.style.cssText = 'width:100%;margin:5px 0 2px;padding:3px 6px;';
        button.textContent = label;
        button.addEventListener('click', handler);
        return button;
    }

    function parkOwnedPanels() {
        for (const id of ['light-object-settings', 'override-settings', 'vertex-shading-section']) {
            const panel = document.getElementById(id);
            if (panel && panel.parentElement !== parking) parking.appendChild(panel);
        }
    }

    function adopt(id, display, hideLegacyTitle) {
        const panel = document.getElementById(id);
        if (!panel) return null;
        panel.style.display = display || 'block';
        panel.style.marginTop = '6px';
        const legacyTitle = panel.querySelector(':scope > .sidebar-title');
        if (legacyTitle) legacyTitle.style.display = hideLegacyTitle ? 'none' : '';
        body.appendChild(panel);
        return panel;
    }

    function renderEnvironment(context) {
        const map = context.map;
        body.append(sectionTitle('Map / Environment'));
        body.append(infoRow('Title', map.title || map.name || `Map ${map.id != null ? map.id : ''}`.trim()));
        body.append(infoRow('Map ID', map.id));
        body.append(infoRow('Category', map.category || '—'));
        body.append(actionButton('Map Properties…', () => {
            if (typeof window.openMapProperties === 'function') window.openMapProperties();
            else if (typeof openMapProperties === 'function') openMapProperties();
        }));
        body.append(muted('Map-wide environmental controls live here; creation and layer tools remain on the left.'));
        const shading = adopt('vertex-shading-section', 'block', false);
        if (!shading) body.append(muted('Vertex Shading is not available for this Map surface.'));
    }

    function renderTransform(source) {
        body.append(sectionTitle('Transform'));
        body.append(infoRow('Cell X', source && source.x));
        body.append(infoRow('Cell Y', source && source.y));
    }

    function renderLight(context) {
        body.append(sectionTitle('Lamp Source'));
        renderTransform(context.source);
        const panel = adopt('light-object-settings', 'block', true);
        if (!panel) body.append(muted('Lamp properties are unavailable.'));
    }

    function renderOverride(context) {
        body.append(sectionTitle('Override'));
        renderTransform(context.source);
        const panel = adopt('override-settings', 'block', true);
        if (!panel) body.append(muted('Override properties are unavailable.'));
    }

    function renderEvent(context) {
        const event = context.source;
        body.append(sectionTitle('Event'));
        body.append(infoRow('Name', event.label || event.name || `Event ${event.id != null ? event.id : ''}`.trim()));
        body.append(infoRow('Event ID', event.id));
        body.append(infoRow('Script ID', event.scriptId));
        body.append(infoRow('Model', event.model === false ? 'Suppressed' : (event.model || 'Inherited')));
        renderTransform(event);
        body.append(actionButton('Edit Event…', () => {
            if (typeof window.openEventModal === 'function') window.openEventModal(event.x, event.y);
            else if (typeof openEventModal === 'function') openEventModal(event.x, event.y);
        }));
        body.append(muted('Full Event pages/commands remain in the existing Event editor; the Inspector does not duplicate that staged-edit surface.'));
    }

    function renderSpawn(context) {
        body.append(sectionTitle('Player Start'));
        renderTransform(context.source);
        body.append(infoRow('Map ID', context.source.mapId));
        body.append(muted('Player Start has no separate property form today; the Inspector shows only authored facts that already exist.'));
    }

    function renderCell(context) {
        body.append(sectionTitle('Cell'));
        renderTransform(context.source.cell || context.source);
        body.append(muted('This cell has no standalone authored property object. Use the left Map tools to change topology, or select an authored Event, Lamp, or Override.'));
    }

    function contextStillExists(context) {
        if (!currentSelection) return true;
        return context.kind === currentSelection.kind || context.kind === 'environment';
    }

    function render() {
        const mapIndex = host.getMapIndex ? host.getMapIndex() : 0;
        if (mapIndex !== lastMapIndex) {
            lastMapIndex = mapIndex;
            currentSelection = null;
        }
        const context = Contract.selectionContext(host.getPayload && host.getPayload(), mapIndex, currentSelection);
        if (!contextStillExists(context)) currentSelection = null;

        parkOwnedPanels();
        body.replaceChildren();
        body.appendChild(error);
        error.style.display = 'none';
        error.textContent = '';

        const resolved = Contract.selectionContext(host.getPayload && host.getPayload(), mapIndex, currentSelection);
        if (resolved.kind === 'light') renderLight(resolved);
        else if (resolved.kind === 'override') renderOverride(resolved);
        else if (resolved.kind === 'event') renderEvent(resolved);
        else if (resolved.kind === 'spawn') renderSpawn(resolved);
        else if (resolved.kind === 'cell') renderCell(resolved);
        else if (resolved.kind === 'environment') renderEnvironment(resolved);
        else {
            body.append(sectionTitle('No Map'));
            body.append(muted('Open or create a Project with a Map to inspect authored properties.'));
        }
    }

    function showValidation(message, target) {
        error.textContent = message;
        error.style.display = 'block';
        if (target) target.setAttribute('aria-invalid', 'true');
    }

    body.addEventListener('input', event => {
        const target = event.target;
        if (!target || !target.id) return;
        if (!Contract.numericInputIsValid(target.id, target.value)) {
            event.preventDefault();
            event.stopImmediatePropagation();
            showValidation(`${target.id === 'lamp-radius' ? 'Radius' : 'Falloff'} must be a number of at least 0.1.`, target);
            return;
        }
        target.removeAttribute('aria-invalid');
        if (error.style.display !== 'none') {
            error.style.display = 'none';
            error.textContent = '';
        }
    }, true);

    body.addEventListener('click', () => {
        requestAnimationFrame(() => {
            const context = Contract.selectionContext(host.getPayload && host.getPayload(), host.getMapIndex ? host.getMapIndex() : 0, currentSelection);
            if (currentSelection && context.kind === 'environment') currentSelection = null;
            render();
        });
    });

    const originalSelectSemantic = host.selectSemantic;
    if (typeof originalSelectSemantic === 'function') {
        host.selectSemantic = function (selection) {
            const result = originalSelectSemantic.apply(this, arguments);
            currentSelection = selection || null;
            render();
            return result;
        };
    }

    const mapTree = document.getElementById('map-tree');
    if (mapTree) {
        new MutationObserver(() => {
            const mapIndex = host.getMapIndex ? host.getMapIndex() : 0;
            if (mapIndex !== lastMapIndex) {
                currentSelection = null;
                lastMapIndex = mapIndex;
                render();
            }
        }).observe(mapTree, { subtree: true, attributes: true, attributeFilter: ['class'] });
    }

    for (const id of ['tool-map-btn', 'tool-event-btn', 'tool-light-btn', 'tool-override-btn']) {
        const button = document.getElementById(id);
        if (button) button.addEventListener('click', () => requestAnimationFrame(render));
    }

    for (const id of ['event-modal', 'map-properties-modal']) {
        const modal = document.getElementById(id);
        if (!modal) continue;
        new MutationObserver(() => {
            if (!modal.classList.contains('active')) render();
        }).observe(modal, { attributes: true, attributeFilter: ['class', 'style', 'hidden'] });
    }

    window.addEventListener('thestra-map-inspection-changed', render);

    collapse.addEventListener('click', () => {
        collapsed = !collapsed;
        body.style.display = collapsed ? 'none' : 'block';
        heading.style.display = collapsed ? 'none' : 'inline';
        splitter.style.display = collapsed ? 'none' : 'block';
        inspector.style.width = collapsed ? '27px' : `${width}px`;
        collapse.textContent = collapsed ? '◀' : '▶';
        collapse.title = collapsed ? 'Expand Inspector' : 'Collapse Inspector';
    });

    splitter.addEventListener('pointerdown', event => {
        if (collapsed || event.button !== 0) return;
        event.preventDefault();
        splitter.setPointerCapture(event.pointerId);
        const startX = event.clientX;
        const startWidth = width;
        function move(moveEvent) {
            width = Contract.clampWidth(startWidth + (startX - moveEvent.clientX));
            inspector.style.width = `${width}px`;
        }
        function finish(finishEvent) {
            if (splitter.hasPointerCapture(finishEvent.pointerId)) splitter.releasePointerCapture(finishEvent.pointerId);
            splitter.removeEventListener('pointermove', move);
            splitter.removeEventListener('pointerup', finish);
            splitter.removeEventListener('pointercancel', finish);
            localStorage.setItem('thestra-map-inspector-width', String(width));
        }
        splitter.addEventListener('pointermove', move);
        splitter.addEventListener('pointerup', finish);
        splitter.addEventListener('pointercancel', finish);
    });

    render();
    // vertex-shading.js starts a bounded pre-workspace ownership handoff. It is
    // loaded earlier, so its pending first-frame callback runs before this one;
    // re-render once afterwards so the final visible owner is deterministically
    // the Inspector even when all dynamic scripts came from cache in one frame.
    requestAnimationFrame(render);
}());
