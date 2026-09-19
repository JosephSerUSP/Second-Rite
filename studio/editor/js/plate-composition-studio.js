(function (root) {
    'use strict';

    // #1116: Map camera and plate calibration deliberately have different
    // persistence authorities. This panel makes that boundary visible.
    let mounted = false, loadedPath = null, manifest = null, version = null;
    let loadSerial = 0, calibrationDirty = false;
    const clone = value => JSON.parse(JSON.stringify(value));
    const finite = value => Number.isFinite(Number(value));
    const host = () => root.ThestraEditorHost;

    function currentMap() {
        const payload = host()?.getPayload?.() || root.dbPayload;
        const index = host()?.getMapIndex?.() ?? root.currentMapIndex;
        return payload?.maps?.[index] || null;
    }
    function note(text) {
        const node = document.createElement('div');
        node.style.cssText = 'font-size:9px;color:var(--win-dark-shadow);line-height:1.3;margin:3px 0;';
        node.textContent = text;
        return node;
    }
    function button(text, callback) {
        const node = document.createElement('button');
        node.type = 'button'; node.className = 'win98-btn';
        node.style.cssText = 'font-size:10px;padding:2px 5px;';
        node.textContent = text; node.addEventListener('click', callback);
        return node;
    }
    function field(label, value, change, hint, attrs) {
        const row = document.createElement('label');
        row.style.cssText = 'display:flex;align-items:center;gap:5px;margin:3px 0;font-size:10px;';
        const name = document.createElement('span');
        name.style.cssText = 'width:84px;flex:0 0 84px;'; name.textContent = label;
        const input = document.createElement('input');
        input.type = 'number'; input.className = 'win98-input'; input.style.width = '66px';
        input.step = attrs?.step || '0.01'; input.value = String(value);
        if (attrs?.min != null) input.min = String(attrs.min);
        input.addEventListener('change', () => {
            if (!finite(input.value)) { input.style.background = '#ffcccc'; return; }
            try { change(Number(input.value)); input.style.background = ''; }
            catch (error) { input.style.background = '#ffcccc'; }
        });
        row.append(name, input);
        if (hint) { const help = note(hint); help.style.margin = '0'; row.append(help); }
        return row;
    }
    function setPath(object, parts, value) {
        let cursor = object;
        for (let index = 0; index < parts.length - 1; index++) cursor = cursor[parts[index]];
        cursor[parts[parts.length - 1]] = value;
    }
    function refreshPreview() {
        root.ThestraRuntimeCameraViewport?.setPlateManifestOverride?.(loadedPath, manifest)?.catch(console.error);
    }
    function stageCalibration(parts, value, render) {
        setPath(manifest, parts, value);
        calibrationDirty = true; refreshPreview(); render();
    }
    function mutateCamera(map, parts, value) {
        const before = clone(map);
        setPath(map, ['traversal', 'camera'].concat(parts), value);
        root.setDirty?.(true);
        root.dispatchEvent(new CustomEvent('thestra-spatial-transaction-committed', { detail: {
            kind: 'plate-camera', authority: `maps:${map.id}`,
            target: { kind: 'map', key: `maps:${map.id}` },
            before: { map: before }, after: { map: clone(map) }
        }}));
        root.dispatchEvent(new CustomEvent('thestra-map-inspection-changed'));
    }
    async function load(packagePath) {
        const serial = ++loadSerial;
        const response = await fetch(`/api/plate-composition?path=${encodeURIComponent(packagePath)}`);
        const payload = await response.json();
        if (!response.ok || !payload.success) throw new Error(payload.message || 'Could not load plate package.');
        if (serial !== loadSerial) return false;
        loadedPath = payload.path; manifest = payload.manifest; version = payload.version;
        calibrationDirty = false; refreshPreview(); return true;
    }
    function panel() {
        const box = document.createElement('div'); box.className = 'thestra-toolbar-group';
        const title = document.createElement('div'); title.className = 'thestra-toolbar-group-title';
        title.textContent = 'PLATE COMPOSITION'; box.append(title);
        const content = document.createElement('div'); box.append(content);
        const render = () => {
            content.replaceChildren();
            const map = currentMap(), packagePath = map?.traversal?.environmentPackage;
            if (!packagePath) { content.append(note('No environment package on this Map.')); return; }
            content.append(note(`Map ${map.id}: camera is Map data; plate calibration is ${packagePath}.`));
            if (!manifest || loadedPath !== packagePath) {
                content.append(note('Loading package calibration…'));
                load(packagePath).then(render).catch(error => content.append(note(error.message)));
                return;
            }
            const camera = map.traversal.camera;
            const cameraHead = document.createElement('strong'); cameraHead.style.fontSize = '10px';
            cameraHead.textContent = 'Map camera — Save Changes'; content.append(cameraHead);
            content.append(field('Target Y', camera.target.y, value => mutateCamera(map, ['target', 'y'], value), 'runtime aim'));
            content.append(field('Distance', camera.distance, value => mutateCamera(map, ['distance'], value), 'camera distance', { min: 0.001 }));
            content.append(field('Pitch', camera.pitchDegrees, value => mutateCamera(map, ['pitchDegrees'], value), 'degrees'));
            content.append(field('FOV', camera.fovDegrees, value => mutateCamera(map, ['fovDegrees'], value), 'degrees', { min: 0.001 }));
            content.append(field('Frame X', camera.projectionFrame.canonicalCenterX, value => mutateCamera(map, ['projectionFrame', 'canonicalCenterX'], value), 'projection window'));
            const plateHead = document.createElement('strong');
            plateHead.style.cssText = 'font-size:10px;display:block;margin-top:6px;';
            plateHead.textContent = 'Plate calibration — Save package'; content.append(plateHead);
            const pre = manifest.preRendered, projection = pre.playerProjection;
            content.append(field('Image width', pre.imageSize[0], value => stageCalibration(['preRendered', 'imageSize', 0], value, render), 'design px', { min: 1, step: 1 }));
            content.append(field('Image height', pre.imageSize[1], value => stageCalibration(['preRendered', 'imageSize', 1], value, render), 'design px', { min: 1, step: 1 }));
            content.append(field('Slice Y', pre.slicePositions[0], value => stageCalibration(['preRendered', 'slicePositions', 0], value, render), 'selected layer'));
            content.append(field('Lane center', pre.lane.runtimeCenterY, value => stageCalibration(['preRendered', 'lane', 'runtimeCenterY'], value, render), 'runtime slice'));
            content.append(field('Player X', projection.centerX, value => stageCalibration(['preRendered', 'playerProjection', 'centerX'], value, render), 'plate px'));
            content.append(field('Player Y', projection.screenY, value => stageCalibration(['preRendered', 'playerProjection', 'screenY'], value, render), 'foot line'));
            content.append(field('Player width', projection.width, value => stageCalibration(['preRendered', 'playerProjection', 'width'], value, render), 'plate px', { min: 0.001 }));
            content.append(field('Player height', projection.height, value => stageCalibration(['preRendered', 'playerProjection', 'height'], value, render), 'plate px', { min: 0.001 }));
            content.append(field('Pixels / Y', projection.pixelsPerRuntimeY, value => stageCalibration(['preRendered', 'playerProjection', 'pixelsPerRuntimeY'], value, render), 'scroll rate', { min: 0.001 }));
            const actions = document.createElement('div'); actions.style.cssText = 'display:flex;gap:5px;margin-top:5px;flex-wrap:wrap;';
            const save = button(calibrationDirty ? 'Save package *' : 'Save package', async () => {
                save.disabled = true;
                try {
                    const response = await fetch('/api/plate-composition/save', {
                        method: 'POST', headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ path: loadedPath, manifest, version })
                    });
                    const payload = await response.json();
                    if (!response.ok || !payload.success) throw new Error(payload.message || 'Could not save package.');
                    manifest = payload.manifest; version = payload.version; calibrationDirty = false; refreshPreview(); render();
                } catch (error) { alert(error.message); } finally { save.disabled = false; }
            });
            actions.append(save, button('Discard package edits', () => load(packagePath).then(render).catch(error => alert(error.message))));
            content.append(actions);
            content.append(note(`Read-only references: ${Object.keys(manifest.anchors || {}).length} package anchors; ${(map.events || []).length} Map Events. Ground profile is authored with Edit Ground Profile.`));
            content.append(note('Player X and camera Frame X are intentionally independent; no equality is inferred. Image assistance is review-only and is not invoked here.'));
        };
        render(); return box;
    }
    function install() {
        if (mounted) return;
        const toolbar = root.ThestraMapWorkspaceToolbar;
        if (!toolbar?.mount) { setTimeout(install, 50); return; }
        mounted = true; toolbar.mount('plate-composition', [panel()]);
        root.addEventListener('thestra-map-inspection-changed', () => toolbar.mount('plate-composition', [panel()]));
    }
    install();
}(window));
