/*
 * Thestra Tileset Studio — engine-resolved structural surface inspector.
 *
 * This is deliberately a CONSUMER of presentation/map_renderable_bundle.lua,
 * not a browser geometry compiler. The browser builds a tiny transient probe
 * Map whose sparse tileset override carries the current unsaved Tileset Studio
 * snapshot and forces exactly one selected structural variant. LÖVE resolves
 * that Map through the ordinary tileset/geometry path and returns triangle
 * streams. This file only projects those already-resolved triangles for an
 * authoring view and reports their provenance/material facts.
 */
(function (root, factory) {
    'use strict';
    const api = factory(root || {});
    if (typeof module === 'object' && module.exports) {
        module.exports = api;
    } else {
        root.TilesetSurfaceInspector = api;
        api.install();
    }
})(typeof window !== 'undefined' ? window : globalThis, function (root) {
    'use strict';

    const STRUCTURAL_ROLES = new Set(['wall', 'floor', 'ceiling']);
    const POOL_NAME = { wall: 'walls', floor: 'floors', ceiling: 'ceilings' };
    const PROFILE = { wall: 'authoring', floor: 'authoring', ceiling: 'play' };
    const TARGET_SOURCE = {
        wall: { x: 1, y: 0, surface: 'south-wall' },
        floor: { x: 1, y: 1, surface: 'floor' },
        ceiling: { x: 1, y: 1, surface: 'ceiling' },
    };
    const PROBE_MAP_ID = 2147483001;
    const PROBE_SEED = 424242;

    function clone(value) {
        return value == null ? value : JSON.parse(JSON.stringify(value));
    }

    function poolFor(tileset, role) {
        const name = POOL_NAME[role];
        return name && tileset && tileset.base && Array.isArray(tileset.base[name])
            ? tileset.base[name]
            : [];
    }

    function cleanSnapshot(tileset) {
        const value = clone(tileset || {});
        delete value._storageVersion;
        return value;
    }

    // Convert the unsaved Tileset Studio snapshot into a transient *Map sparse
    // override*. This is not a second tileset resolver: merge semantics remain
    // engine-owned. We only express authored intent for the probe — all current
    // values plus remove-patches that make the selected weighted variant the
    // sole candidate in its structural pool.
    function buildProbeOverride(tilesetSnapshot, canonicalTileset, role, variantId) {
        if (!STRUCTURAL_ROLES.has(role)) {
            throw new Error('resolved surface inspection supports wall, floor, or ceiling');
        }
        const snapshot = cleanSnapshot(tilesetSnapshot);
        const canonical = cleanSnapshot(canonicalTileset);
        const selected = poolFor(snapshot, role).find(v => String(v.id) === String(variantId));
        if (!selected) throw new Error(`selected ${role} variant '${variantId}' no longer exists`);

        const delta = clone(snapshot);
        delete delta.id;
        delete delta.name;
        delta.base = delta.base || {};

        const ids = new Set();
        poolFor(canonical, role).forEach(v => { if (v && v.id != null) ids.add(String(v.id)); });
        poolFor(snapshot, role).forEach(v => { if (v && v.id != null) ids.add(String(v.id)); });

        const forced = [clone(selected)];
        ids.forEach(id => {
            if (id !== String(selected.id)) forced.push({ id, remove: true });
        });
        delta.base[POOL_NAME[role]] = forced;
        return delta;
    }

    function buildProbeRequest(studioSnapshot) {
        if (!studioSnapshot || !studioSnapshot.tileset) {
            throw new Error('Tileset Studio has no loaded tileset');
        }
        const role = studioSnapshot.role;
        const variantId = studioSnapshot.variantId;
        if (!STRUCTURAL_ROLES.has(role)) {
            throw new Error('select a Wall, Floor, or Ceiling tile to inspect its resolved 3D surface');
        }
        if (!variantId) throw new Error(`select a ${role} tile first`);
        if (!studioSnapshot.canonical) {
            throw new Error('save a newly created tileset once before resolving unsaved surface edits');
        }
        const tileset = studioSnapshot.tileset;
        const override = buildProbeOverride(tileset, studioSnapshot.canonical, role, variantId);
        return {
            role,
            variantId,
            request: {
                seed: PROBE_SEED,
                geometryProfile: PROFILE[role],
                map: {
                    id: PROBE_MAP_ID,
                    title: 'Thestra Tileset Surface Probe',
                    safe: true,
                    generation: 'Fixed',
                    width: 3,
                    height: 3,
                    layout: ['###', '#.#', '###'],
                    tileset: tileset.id,
                    tilesetOverride: override,
                    ceilingStyle: 'solid',
                    events: [],
                    zones: [],
                    lightObjects: [],
                    entranceX: 2,
                    entranceY: 2,
                    exitX: 2,
                    exitY: 2,
                },
            },
        };
    }

    function sourceMatches(source, target) {
        return !!source
            && Number(source.x) === target.x
            && Number(source.y) === target.y
            && String(source.surface) === target.surface;
    }

    function filterResolvedSurfaces(bundle, role) {
        const target = TARGET_SOURCE[role];
        if (!target) return [];
        return (bundle && bundle.surfaces || []).filter(surface => sourceMatches(surface.source, target));
    }

    function materialMap(bundle) {
        const result = new Map();
        (bundle && bundle.materials || []).forEach(material => result.set(material.id, material));
        return result;
    }

    function selectedVariant(studioSnapshot) {
        return poolFor(studioSnapshot.tileset, studioSnapshot.role)
            .find(v => String(v.id) === String(studioSnapshot.variantId)) || null;
    }

    function materialSourceLabel(payload) {
        if (!payload) return 'none';
        if (payload.kind === 'project-asset') return payload.path || 'project asset';
        if (payload.kind === 'embedded-png') return `runtime composite ${payload.width || '?'}×${payload.height || '?'}`;
        return payload.kind || 'runtime material';
    }

    function roleHeightScale(tileset, role) {
        const value = tileset && tileset.heightMapScale;
        if (value && typeof value === 'object' && !Array.isArray(value)) {
            return value[role] ?? value.default ?? null;
        }
        return value ?? null;
    }

    function summarizeResolved(bundle, surfaces, studioSnapshot) {
        const materials = materialMap(bundle);
        const materialIds = Array.from(new Set(surfaces.map(s => s.material).filter(Boolean)));
        const materialFacts = materialIds.map(id => {
            const material = materials.get(id) || { id };
            return {
                id,
                albedo: materialSourceLabel(material.albedo),
                emission: materialSourceLabel(material.emission),
                color: material.color || [1, 1, 1, 1],
            };
        });
        let vertices = 0;
        surfaces.forEach(surface => { vertices += Math.floor((surface.positions || []).length / 3); });
        const variant = selectedVariant(studioSnapshot) || {};
        const ts = studioSnapshot.tileset || {};
        return {
            role: studioSnapshot.role,
            variantId: studioSnapshot.variantId,
            geometryProfile: bundle.geometryProfile,
            quality: bundle.quality || {},
            surfaceCount: surfaces.length,
            vertexCount: vertices,
            triangleCount: Math.floor(vertices / 3),
            authored: {
                tilesetId: ts.id,
                texture: ts.texture || null,
                variantAtlas: variant.middle || variant.atlas || null,
                geometry: variant.geometry || null,
                model: variant.model || null,
                heightOffset: variant.heightOffset ?? null,
                heightMap: ts.heightMap || null,
                heightMapScale: roleHeightScale(ts, studioSnapshot.role),
                heightMapOperation: ts.heightMapOperation || 'add',
                heightMapMeshColumns: ts.heightMapMeshColumns ?? 16,
                heightMapMeshRows: ts.heightMapMeshRows ?? 16,
                heightMapSampleColumns: ts.heightMapSampleColumns ?? null,
                heightMapSampleRows: ts.heightMapSampleRows ?? null,
                heightMapTriangleBudget: ts.heightMapTriangleBudget ?? 64,
                heightMapOffset: ts.heightMapOffset ?? 0.004,
                glowMap: ts.glowMap || null,
                glowStrength: ts.glowStrength ?? null,
            },
            materials: materialFacts,
        };
    }

    function triangleList(surfaces, materials) {
        const triangles = [];
        surfaces.forEach(surface => {
            const p = surface.positions || [];
            const material = materials.get(surface.material) || {};
            const color = (material.color || [1, 1, 1, 1]).slice(0, 3);
            for (let i = 0; i + 8 < p.length; i += 9) {
                triangles.push({
                    points: [
                        [p[i], p[i + 1], p[i + 2]],
                        [p[i + 3], p[i + 4], p[i + 5]],
                        [p[i + 6], p[i + 7], p[i + 8]],
                    ],
                    color,
                    material: surface.material,
                });
            }
        });
        return triangles;
    }

    function boundsFor(triangles) {
        const min = [Infinity, Infinity, Infinity], max = [-Infinity, -Infinity, -Infinity];
        triangles.forEach(t => t.points.forEach(point => {
            for (let axis = 0; axis < 3; axis++) {
                min[axis] = Math.min(min[axis], point[axis]);
                max[axis] = Math.max(max[axis], point[axis]);
            }
        }));
        if (!triangles.length) return { min: [-0.5, -0.5, -0.5], max: [0.5, 0.5, 0.5] };
        return { min, max };
    }

    function transformed(point, center, yaw, pitch) {
        const x = point[0] - center[0];
        const y = point[1] - center[1];
        const z = point[2] - center[2];
        const cy = Math.cos(yaw), sy = Math.sin(yaw);
        const rx = x * cy - y * sy;
        const ry = x * sy + y * cy;
        const cp = Math.cos(pitch), sp = Math.sin(pitch);
        return [rx, -(z * cp - ry * sp), ry * cp + z * sp];
    }

    function normal2d(a, b, c) {
        const ux = b[0] - a[0], uy = b[1] - a[1], uz = b[2] - a[2];
        const vx = c[0] - a[0], vy = c[1] - a[1], vz = c[2] - a[2];
        const nx = uy * vz - uz * vy;
        const ny = uz * vx - ux * vz;
        const nz = ux * vy - uy * vx;
        const len = Math.sqrt(nx * nx + ny * ny + nz * nz) || 1;
        return [nx / len, ny / len, nz / len];
    }

    function rgb(rgb, shade) {
        const values = (rgb || [1, 1, 1]).slice(0, 3).map(value =>
            Math.round(Math.max(0, Math.min(1, value * shade)) * 255));
        return `rgb(${values.join(',')})`;
    }

    function renderTriangles(canvas, bundle, surfaces, view) {
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const materials = materialMap(bundle);
        const triangles = triangleList(surfaces, materials);
        const bounds = boundsFor(triangles);
        const center = [0, 1, 2].map(axis => (bounds.min[axis] + bounds.max[axis]) * 0.5);
        const span = Math.max(0.001,
            bounds.max[0] - bounds.min[0], bounds.max[1] - bounds.min[1], bounds.max[2] - bounds.min[2]);
        const scale = Math.min(canvas.width, canvas.height) * 0.68 / span * (view.zoom || 1);

        ctx.clearRect(0, 0, canvas.width, canvas.height);
        const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
        gradient.addColorStop(0, '#151922');
        gradient.addColorStop(1, '#080a0f');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        const projected = triangles.map(triangle => {
            const points = triangle.points.map(point => transformed(point, center, view.yaw, view.pitch));
            return {
                points,
                screen: points.map(point => [
                    canvas.width * 0.5 + point[0] * scale,
                    canvas.height * 0.52 + point[1] * scale,
                ]),
                depth: (points[0][2] + points[1][2] + points[2][2]) / 3,
                normal: normal2d(points[0], points[1], points[2]),
                color: triangle.color,
            };
        }).sort((a, b) => a.depth - b.depth);

        projected.forEach(triangle => {
            const light = Math.max(0.32, Math.min(1,
                0.58 + triangle.normal[0] * -0.20 + triangle.normal[1] * -0.10 + Math.abs(triangle.normal[2]) * 0.28));
            ctx.beginPath();
            ctx.moveTo(triangle.screen[0][0], triangle.screen[0][1]);
            ctx.lineTo(triangle.screen[1][0], triangle.screen[1][1]);
            ctx.lineTo(triangle.screen[2][0], triangle.screen[2][1]);
            ctx.closePath();
            ctx.fillStyle = rgb(triangle.color, light);
            ctx.fill();
            ctx.strokeStyle = 'rgba(20, 25, 32, 0.42)';
            ctx.lineWidth = 0.75;
            ctx.stroke();
        });

        ctx.fillStyle = '#9aa6b8';
        ctx.font = '11px monospace';
        ctx.fillText(`${triangles.length} engine triangles`, 10, canvas.height - 12);
        canvas.dataset.previewReady = '1';
    }

    function factRow(label, value) {
        const safe = value === null || value === undefined || value === '' ? '—'
            : (typeof value === 'object' ? JSON.stringify(value) : String(value));
        return `<div style="display:grid;grid-template-columns:96px 1fr;gap:5px;margin:2px 0;">`
            + `<span style="color:#666;">${label}</span><span style="word-break:break-word;">${safe}</span></div>`;
    }

    function factsHtml(summary) {
        const a = summary.authored;
        const material = summary.materials[0] || {};
        return [
            '<div style="font-weight:bold;margin-bottom:5px;">Engine result</div>',
            factRow('Surface', `${summary.role} / ${summary.variantId}`),
            factRow('Profile', summary.geometryProfile),
            factRow('Quality', `${summary.quality.preset || '—'} · density ${summary.quality.density ?? '—'}`),
            factRow('Geometry', `${summary.surfaceCount} surfaces · ${summary.vertexCount} verts · ${summary.triangleCount} tris`),
            factRow('Albedo', material.albedo),
            factRow('Emission', material.emission),
            '<div style="font-weight:bold;margin:9px 0 4px;">Effective unsaved authoring</div>',
            factRow('Tileset', a.tilesetId),
            factRow('Atlas', a.variantAtlas),
            factRow('Geometry src', a.geometry),
            factRow('OBJ model', a.model),
            factRow('Floor offset', a.heightOffset),
            factRow('Height map', a.heightMap),
            factRow('Height scale', a.heightMapScale),
            factRow('Height op', a.heightMapOperation),
            factRow('Mesh grid', `${a.heightMapMeshColumns} × ${a.heightMapMeshRows}`),
            factRow('Sample grid', a.heightMapSampleColumns || a.heightMapSampleRows
                ? `${a.heightMapSampleColumns ?? 'auto'} × ${a.heightMapSampleRows ?? 'auto'}` : 'auto'),
            factRow('Tri budget', a.heightMapTriangleBudget),
            factRow('Depth offset', a.heightMapOffset),
            factRow('Glow map', a.glowMap),
            factRow('Glow strength', a.glowStrength),
        ].join('');
    }

    function ensureModal() {
        if (typeof document === 'undefined') return null;
        let overlay = document.getElementById('tileset-surface-inspector-modal');
        if (overlay) return overlay;
        overlay = document.createElement('div');
        overlay.id = 'tileset-surface-inspector-modal';
        overlay.className = 'modal-overlay';
        overlay.style.cssText = 'display:none;z-index:1800;align-items:center;justify-content:center;';
        overlay.innerHTML = `
            <div class="window" style="width:900px;height:650px;display:flex;flex-direction:column;">
                <div class="title-bar">
                    <div class="title-bar-text">▦ Resolved 3D Surface Inspector</div>
                    <div class="title-bar-controls"><button aria-label="Close" id="tsi-close-x"></button></div>
                </div>
                <div class="window-body" style="flex:1;min-height:0;display:flex;gap:8px;padding:8px;">
                    <div class="inset-panel" style="flex:1;min-width:0;display:flex;flex-direction:column;padding:8px;">
                        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
                            <div><b id="tsi-heading">Selected surface</b><div id="tsi-status" style="font-size:10px;color:#555;margin-top:2px;">Waiting…</div></div>
                            <div style="font-size:9px;text-align:right;line-height:1.45;color:#3d536d;">ENGINE TRIANGLES<br>TRANSIENT · NO SAVE</div>
                        </div>
                        <canvas id="tsi-canvas" width="600" height="480" style="width:100%;height:480px;max-height:480px;background:#0b0d12;border:1px solid #555;cursor:grab;"></canvas>
                        <div style="font-size:10px;color:#555;margin-top:5px;">Drag to orbit · mouse wheel to zoom. Geometry is projected from the LÖVE renderable bundle; the browser does not rebuild the surface.</div>
                    </div>
                    <div class="inset-panel" style="width:270px;overflow:auto;padding:8px;font-size:10px;">
                        <div id="tsi-facts">Resolving…</div>
                    </div>
                </div>
                <div class="dialog-footer" style="padding:6px;display:flex;justify-content:space-between;gap:6px;">
                    <span style="font-size:10px;color:#555;align-self:center;">Unsaved Tileset Studio snapshot → transient probe Map → real resolver/geometry compiler</span>
                    <div><button class="win98-btn" id="tsi-reset">Reset View</button> <button class="win98-btn" id="tsi-resolve">Resolve Again</button> <button class="win98-btn" id="tsi-close">Close</button></div>
                </div>
            </div>`;
        document.body.appendChild(overlay);
        document.getElementById('tsi-close-x').onclick = close;
        document.getElementById('tsi-close').onclick = close;
        document.getElementById('tsi-resolve').onclick = () => resolveCurrent();
        document.getElementById('tsi-reset').onclick = () => {
            state.view = { yaw: -0.62, pitch: 0.58, zoom: 1 };
            if (state.bundle) renderTriangles(document.getElementById('tsi-canvas'), state.bundle, state.surfaces, state.view);
        };
        installCanvasInteraction(document.getElementById('tsi-canvas'));
        return overlay;
    }

    const state = {
        bundle: null,
        surfaces: [],
        snapshot: null,
        view: { yaw: -0.62, pitch: 0.58, zoom: 1 },
        requestSerial: 0,
    };

    function installCanvasInteraction(canvas) {
        if (!canvas || canvas.dataset.interactionBound) return;
        canvas.dataset.interactionBound = '1';
        let dragging = false, lastX = 0, lastY = 0;
        canvas.addEventListener('pointerdown', event => {
            dragging = true; lastX = event.clientX; lastY = event.clientY;
            canvas.style.cursor = 'grabbing';
            if (canvas.setPointerCapture) canvas.setPointerCapture(event.pointerId);
        });
        canvas.addEventListener('pointermove', event => {
            if (!dragging) return;
            state.view.yaw += (event.clientX - lastX) * 0.012;
            state.view.pitch = Math.max(-1.35, Math.min(1.35,
                state.view.pitch + (event.clientY - lastY) * 0.012));
            lastX = event.clientX; lastY = event.clientY;
            if (state.bundle) renderTriangles(canvas, state.bundle, state.surfaces, state.view);
        });
        const release = event => {
            dragging = false; canvas.style.cursor = 'grab';
            if (canvas.releasePointerCapture && canvas.hasPointerCapture && canvas.hasPointerCapture(event.pointerId)) {
                canvas.releasePointerCapture(event.pointerId);
            }
        };
        canvas.addEventListener('pointerup', release);
        canvas.addEventListener('pointercancel', release);
        canvas.addEventListener('wheel', event => {
            event.preventDefault();
            state.view.zoom = Math.max(0.35, Math.min(4, state.view.zoom * (event.deltaY > 0 ? 0.9 : 1.1)));
            if (state.bundle) renderTriangles(canvas, state.bundle, state.surfaces, state.view);
        }, { passive: false });
    }

    function close() {
        const modal = typeof document !== 'undefined'
            ? document.getElementById('tileset-surface-inspector-modal') : null;
        if (modal) modal.style.display = 'none';
        state.requestSerial += 1;
        state.bundle = null;
        state.surfaces = [];
        state.snapshot = null;
    }

    function runtimeBridgeUrl() {
        return root.SECOND_RITE_RUNTIME_BRIDGE_URL || 'http://127.0.0.1:8082';
    }

    async function resolveSnapshot(studioSnapshot) {
        const probe = buildProbeRequest(studioSnapshot);
        const response = await root.fetch(`${runtimeBridgeUrl()}/api/map-renderable`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(probe.request),
        });
        let payload;
        try { payload = await response.json(); }
        catch (error) { throw new Error(`runtime bridge returned invalid JSON: ${error.message}`); }
        if (!response.ok || payload.error) throw new Error(payload.error || `HTTP ${response.status}`);
        const surfaces = filterResolvedSurfaces(payload, probe.role);
        if (!surfaces.length) {
            throw new Error(`engine returned no ${probe.role} surfaces for the selected probe cell (${payload.geometryProfile || 'unknown profile'})`);
        }
        return { bundle: payload, surfaces, probe };
    }

    async function resolveCurrent() {
        if (typeof document === 'undefined') return;
        const getter = root.getTilesetStudioInspectionSnapshot;
        if (typeof getter !== 'function') throw new Error('Tileset Studio inspection snapshot seam is unavailable');
        const snapshot = getter();
        const serial = ++state.requestSerial;
        const status = document.getElementById('tsi-status');
        const facts = document.getElementById('tsi-facts');
        const canvas = document.getElementById('tsi-canvas');
        if (canvas) canvas.removeAttribute('data-preview-ready');
        state.snapshot = snapshot;
        state.bundle = null;
        state.surfaces = [];
        if (status) status.textContent = 'Resolving through LÖVE…';
        if (facts) facts.textContent = 'Building a transient probe Map. No authored data is being saved.';
        try {
            const result = await resolveSnapshot(snapshot);
            if (serial !== state.requestSerial) return;
            state.bundle = result.bundle;
            state.surfaces = result.surfaces;
            const summary = summarizeResolved(result.bundle, result.surfaces, snapshot);
            const heading = document.getElementById('tsi-heading');
            if (heading) heading.textContent = `${summary.role.toUpperCase()} · ${summary.variantId}`;
            if (status) status.textContent = `Resolved by engine · ${summary.geometryProfile} profile · ${summary.triangleCount} triangles`;
            if (facts) facts.innerHTML = factsHtml(summary);
            renderTriangles(canvas, result.bundle, result.surfaces, state.view);
            const modal = document.getElementById('tileset-surface-inspector-modal');
            if (modal) modal.dataset.previewReady = '1';
        } catch (error) {
            if (serial !== state.requestSerial) return;
            if (status) status.textContent = 'Resolved preview unavailable';
            if (facts) facts.innerHTML = `<div style="color:#8b0000;font-weight:bold;margin-bottom:5px;">Could not resolve surface</div><div>${String(error.message || error)}</div><div style="margin-top:8px;color:#666;">The authoritative preview requires the local LÖVE runtime bridge (Developer Studio desktop or tools/editor/runtime-bridge-server.js).</div>`;
            if (canvas) {
                const ctx = canvas.getContext('2d');
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.fillStyle = '#101217'; ctx.fillRect(0, 0, canvas.width, canvas.height);
            }
        }
    }

    async function open() {
        const getter = root.getTilesetStudioInspectionSnapshot;
        if (typeof getter !== 'function') return;
        const snapshot = getter();
        if (!snapshot || !STRUCTURAL_ROLES.has(snapshot.role)) {
            if (typeof root.showToast === 'function') {
                root.showToast('Resolved 3D inspection currently supports Wall, Floor, and Ceiling tiles.');
            }
            return;
        }
        const modal = ensureModal();
        if (!modal) return;
        modal.style.display = 'flex';
        modal.removeAttribute('data-preview-ready');
        state.view = snapshot.role === 'wall'
            ? { yaw: -0.45, pitch: 0.28, zoom: 1 }
            : { yaw: -0.62, pitch: 0.72, zoom: 1 };
        await resolveCurrent();
    }

    // G6 may inject a known bundle after the semantic request path has its own
    // tests. This keeps the pixel gate focused on browser presentation rather
    // than making the screenshot harness responsible for booting a second HTTP
    // service. Production open() always resolves through LÖVE.
    function openWithBundleForVisualTest(studioSnapshot, bundle) {
        if (typeof document === 'undefined') return;
        const modal = ensureModal();
        modal.style.display = 'flex';
        const surfaces = filterResolvedSurfaces(bundle, studioSnapshot.role);
        state.snapshot = clone(studioSnapshot);
        state.bundle = clone(bundle);
        state.surfaces = surfaces;
        state.view = { yaw: -0.45, pitch: 0.28, zoom: 1 };
        const summary = summarizeResolved(bundle, surfaces, studioSnapshot);
        document.getElementById('tsi-heading').textContent = `${summary.role.toUpperCase()} · ${summary.variantId}`;
        document.getElementById('tsi-status').textContent = `Resolved by engine · ${summary.geometryProfile} profile · ${summary.triangleCount} triangles`;
        document.getElementById('tsi-facts').innerHTML = factsHtml(summary);
        renderTriangles(document.getElementById('tsi-canvas'), bundle, surfaces, state.view);
        modal.dataset.previewReady = '1';
    }

    function install() {
        if (typeof document === 'undefined') return;
        const bind = () => {
            const preview = document.getElementById('ts-preview-canvas');
            if (!preview || preview.dataset.resolvedInspectorBound) return false;
            preview.dataset.resolvedInspectorBound = '1';
            preview.style.cursor = 'pointer';
            preview.title = 'Click to inspect the selected Wall/Floor/Ceiling as engine-resolved 3D geometry';
            preview.addEventListener('click', () => open());
            return true;
        };
        if (!bind()) root.addEventListener('load', bind, { once: true });
    }

    return {
        STRUCTURAL_ROLES,
        PROFILE,
        TARGET_SOURCE,
        buildProbeOverride,
        buildProbeRequest,
        filterResolvedSurfaces,
        summarizeResolved,
        renderTriangles,
        resolveSnapshot,
        open,
        close,
        install,
        openWithBundleForVisualTest,
    };
});
