/*
 * Shared 3D model picker + preview for the Developer Studio.
 *
 * This is deliberately an authoring preview rather than a second copy of the
 * runtime renderer. It reads the same OBJ/MTL assets, auto-fits them, shows
 * material colours, and uses the runtime item viewer's Z-up / Z-axis-turntable
 * orientation. LÖVE remains authoritative for textures, affine UVs, vertex
 * snapping, dithering, and the rest of Second Rite's presentation shader.
 */
(function (root) {
    'use strict';

    const MODEL_CACHE = new Map();
    const DEFAULT_TILT = Math.PI / 18; // runtime item_model_view: 10 degrees

    function prefersReducedMotion() {
        return typeof root.matchMedia === 'function'
            && root.matchMedia('(prefers-reduced-motion: reduce)').matches;
    }

    let activePickerCallback = null;
    let activePickerOptions = null;
    let activePickerPath = '';
    let pickerFiles = [];
    let pickerPreview = null;
    let pickerRequestId = 0;

    function normalizePath(value) {
        return String(value || '').replace(/\\/g, '/').replace(/^\/+/, '');
    }

    function dirname(value) {
        const p = normalizePath(value);
        const at = p.lastIndexOf('/');
        return at >= 0 ? p.slice(0, at) : '';
    }

    function resolveSibling(basePath, relative) {
        const stack = dirname(basePath).split('/').filter(Boolean);
        normalizePath(relative).split('/').forEach(part => {
            if (!part || part === '.') return;
            if (part === '..') stack.pop();
            else stack.push(part);
        });
        return stack.join('/');
    }

    function parseGeometryStats(object, THREE) {
        const bounds = new THREE.Box3().setFromObject(object);
        const materialNames = new Set();
        let triangleCount = 0;
        object.traverse(node => {
            if (!node.isMesh) return;
            const position = node.geometry && node.geometry.getAttribute('position');
            if (position) triangleCount += position.count / 3;
            const materials = Array.isArray(node.material) ? node.material : [node.material];
            materials.forEach(material => {
                if (material && material.name) materialNames.add(material.name);
            });
        });
        return {
            bounds: { min: bounds.min.toArray(), max: bounds.max.toArray() },
            triangleCount,
            materialNames: Array.from(materialNames)
        };
    }

    function countObjVertices(text) {
        return (String(text || '').match(/^v\s+/gm) || []).length;
    }

    function loadThree() {
        return Promise.all([
            import('/vendor/three/three.module.js'),
            import('/vendor/three/OBJLoader.js'),
            import('/vendor/three/MTLLoader.js')
        ]).then(([THREE, { OBJLoader }, { MTLLoader }]) => ({ THREE, OBJLoader, MTLLoader }));
    }

    async function fetchText(path) {
        const response = await fetch('/' + normalizePath(path));
        if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
        return response.text();
    }

    async function loadModel(path) {
        path = normalizePath(path);
        if (!path) throw new Error('No model selected.');
        if (MODEL_CACHE.has(path)) return MODEL_CACHE.get(path);

        const promise = (async () => {
            const { THREE, OBJLoader, MTLLoader } = await loadThree();
            const objText = await fetchText(path);
            const objLoader = new OBJLoader();
            const materialLibraries = [];
            const libraryNames = objText.split(/\r?\n/).map(line => {
                const match = line.trim().match(/^mtllib\s+(.+)$/i);
                return match && match[1];
            }).filter(Boolean);

            for (const libraryName of libraryNames) {
                const resolved = resolveSibling(path, libraryName);
                try {
                    const creator = new MTLLoader().parse(
                        await fetchText(resolved),
                        dirname(resolved) + '/'
                    );
                    creator.preload();
                    Object.values(creator.materials).forEach(material => {
                        material.color.setRGB(
                            Math.max(0, Math.min(1, material.color.r)),
                            Math.max(0, Math.min(1, material.color.g)),
                            Math.max(0, Math.min(1, material.color.b))
                        );
                        material.transparent = false;
                        material.opacity = 1;
                        material.side = THREE.DoubleSide;
                        material.depthWrite = true;
                    });
                    objLoader.setMaterials(creator);
                    materialLibraries.push({ path: resolved, ok: true });
                } catch (err) {
                    materialLibraries.push({ path: resolved, ok: false, error: String(err.message || err) });
                }
            }

            const object = objLoader.parse(objText);
            return Object.assign(parseGeometryStats(object, THREE), {
                path,
                object,
                vertexCount: countObjVertices(objText),
                materialLibraries
            });
        })();

        MODEL_CACHE.set(path, promise);
        try {
            return await promise;
        } catch (err) {
            MODEL_CACHE.delete(path);
            throw err;
        }
    }

    class ModelPreview {
        constructor(canvas, options) {
            this.canvas = canvas;
            this.options = Object.assign({ interactive: false, autoRotate: true }, options || {});
            this.model = null;
            this.path = '';
            this.error = '';
            this.angle = Math.PI * 0.2;
            this.tilt = DEFAULT_TILT;
            this.zoom = 1;
            this.dragging = false;
            this.lastX = 0;
            this.lastY = 0;
            this.alive = true;
            this.frame = this.frame.bind(this);
            this.installEvents();
            this.ready = loadThree().then(dependencies => this.initialize(dependencies));
        }

        initialize({ THREE }) {
            if (!this.alive) return;
            this.THREE = THREE;
            this.renderer = new THREE.WebGLRenderer({
                canvas: this.canvas,
                antialias: true,
                alpha: true
            });
            this.renderer.setPixelRatio(Math.min(2, root.devicePixelRatio || 1));
            this.scene = new THREE.Scene();
            this.camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.01, 100);
            this.camera.position.set(0, 10, 0);
            this.camera.up.set(0, 0, -1);
            this.camera.lookAt(0, 0, 0);
            this.turntable = new THREE.Group();
            this.scene.add(this.turntable);
            this.scene.add(new THREE.HemisphereLight(0xffffff, 0x242424, 2.2));
            const light = new THREE.DirectionalLight(0xffffff, 1.7);
            light.position.set(-3, -4, 5);
            this.scene.add(light);
            // No grid object. The software renderer's grid was a screen-space
            // backdrop drawn behind the model, which a scene object cannot
            // faithfully be: under this top-down orthographic camera a
            // GridHelper sits edge-on and draws a line straight through the
            // subject. The panel's own background supplies the backdrop.
            this.ensureMessage();
            this.render();

            // Reduced motion renders a single fixed frame: no rAF loop, no time-derived angle.
            if (!prefersReducedMotion()) requestAnimationFrame(this.frame);
        }

        ensureMessage() {
            const parent = this.canvas.parentElement;
            if (!parent) return;
            parent.style.position = parent.style.position || 'relative';
            this.message = document.createElement('div');
            this.message.className = 'model-preview-message';
            this.message.style.cssText = 'position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#e8e8e8;font:11px monospace;pointer-events:none;text-align:center;padding:8px;box-sizing:border-box;';
            parent.appendChild(this.message);
        }

        installEvents() {
            if (!this.options.interactive) return;
            const canvas = this.canvas;
            canvas.style.cursor = 'grab';
            canvas.addEventListener('pointerdown', e => {
                this.dragging = true;
                this.lastX = e.clientX;
                this.lastY = e.clientY;
                canvas.style.cursor = 'grabbing';
                if (canvas.setPointerCapture) canvas.setPointerCapture(e.pointerId);
            });
            canvas.addEventListener('pointermove', e => {
                if (!this.dragging) return;
                this.angle += (e.clientX - this.lastX) * 0.012;
                this.tilt = Math.max(-1.35, Math.min(1.35, this.tilt + (e.clientY - this.lastY) * 0.012));
                this.lastX = e.clientX;
                this.lastY = e.clientY;
                this.render();
            });
            const release = e => {
                this.dragging = false;
                canvas.style.cursor = 'grab';
                if (canvas.releasePointerCapture && canvas.hasPointerCapture && canvas.hasPointerCapture(e.pointerId)) {
                    canvas.releasePointerCapture(e.pointerId);
                }
            };
            canvas.addEventListener('pointerup', release);
            canvas.addEventListener('pointercancel', release);
            canvas.addEventListener('wheel', e => {
                e.preventDefault();
                this.zoom = Math.max(0.35, Math.min(4, this.zoom * Math.exp(-e.deltaY * 0.0012)));
                this.render();
            }, { passive: false });
            canvas.addEventListener('dblclick', () => this.resetView());
        }

        resetView() {
            this.angle = Math.PI * 0.2;
            this.tilt = DEFAULT_TILT;
            this.zoom = 1;
            this.render();
        }

        async setPath(path) {
            this.path = normalizePath(path);
            this.model = null;
            this.error = '';
            this.canvas.removeAttribute('data-preview-ready');
            this.render();
            const requested = this.path;
            if (!requested) return;
            try {
                const model = await loadModel(requested);
                if (this.path === requested) {
                    this.model = model;
                    this.render();
                }
            } catch (err) {
                if (this.path === requested) {
                    this.error = String(err.message || err);
                    this.render();
                }
            }
        }

        stop() {
            this.alive = false;
            if (this.renderer) this.renderer.dispose();
        }

        drawBackground(ctx) {
            ctx.fillRect(0, 0, 1, 1);
        }

        render() {
            if (!this.alive || !this.renderer || !this.canvas.isConnected) return;
            // Hidden editor forms retain canvases but should have near-zero rendering cost.
            if (this.canvas.getClientRects().length === 0) return;

            const rect = this.canvas.getBoundingClientRect();
            const w = Math.max(1, Math.round(rect.width));
            const h = Math.max(1, Math.round(rect.height));
            this.renderer.setSize(w, h, false);

            let transparent = false;
            this.drawBackground({
                fillRect: () => {},
                clearRect: () => { transparent = true; }
            }, w, h);
            this.renderer.setClearColor(0x505050, transparent ? 0 : 1);
            this.turntable.clear();

            const message = !this.path ? '(none)'
                : this.error ? 'Preview unavailable'
                : !this.model ? 'Loading…'
                : !this.model.triangleCount ? 'No drawable faces'
                : '';

            if (!message) {
                const { THREE, model } = this;
                const min = model.bounds.min;
                const max = model.bounds.max;
                const center = new THREE.Vector3(
                    (min[0] + max[0]) * 0.5,
                    (min[1] + max[1]) * 0.5,
                    (min[2] + max[2]) * 0.5
                );
                const extent = Math.max(max[0] - min[0], max[1] - min[1], max[2] - min[2], 0.0001);
                const object = model.object.clone(true);
                object.position.sub(center);
                object.scale.setScalar((1.56 / extent) * this.zoom);
                // Runtime item viewer semantics: local-Y tilt, then a Z-axis turntable.
                this.turntable.rotation.set(0, this.tilt, this.angle, 'XYZ');
                this.turntable.add(object);
                // Set readiness only after WebGL receives drawable model faces.
                this.canvas.setAttribute('data-preview-ready', '1');
            }

            this.renderer.render(this.scene, this.camera);
            if (this.message) {
                this.message.textContent = message;
                this.message.style.display = message ? 'flex' : 'none';
            }
        }

        frame() {
            if (!this.alive || prefersReducedMotion()) return;
            if (this.options.autoRotate && !this.dragging && this.model && this.canvas.getClientRects().length) {
                this.angle += 0.007;
            }
            this.render();
            requestAnimationFrame(this.frame);
        }
    }

    function injectStyles() {
        if (typeof document === 'undefined' || document.getElementById('model-picker-style')) return;
        const style = document.createElement('style');
        style.id = 'model-picker-style';
        style.textContent = `
            .model-preview-canvas { display:block; width:100%; height:100%; }
            .model-field-preview { width:84px; height:84px; border:2px solid; border-color:var(--win-shadow) var(--win-white) var(--win-white) var(--win-shadow); background:#505050; flex:0 0 auto; overflow:hidden; }
            .model-field-path { font-family:monospace; font-size:10px; overflow-wrap:anywhere; color:var(--text-color); min-height:28px; }
            .model-picker-window { width:760px; height:560px; max-width:94vw; max-height:92vh; display:flex; flex-direction:column; background:var(--win-gray); border:2px solid; border-color:var(--win-white) var(--win-dark-shadow) var(--win-dark-shadow) var(--win-white); box-shadow:4px 4px 14px rgba(0,0,0,.45); }
            .model-picker-body { flex:1; min-height:0; display:grid; grid-template-columns:270px 1fr; gap:6px; padding:6px; }
            .model-picker-left { display:flex; flex-direction:column; gap:4px; min-width:0; }
            .model-picker-list { flex:1; overflow:auto; background:#fff; border:2px solid; border-color:var(--win-shadow) var(--win-white) var(--win-white) var(--win-shadow); outline:none; }
            .model-picker-row { display:flex; align-items:center; gap:5px; padding:3px 5px; font-size:10px; white-space:nowrap; overflow:hidden; cursor:default; }
            .model-picker-row:nth-child(even) { background:#f1f1f1; }
            .model-picker-row.selected { background:var(--selection-bg); color:var(--selection-text); }
            .model-picker-row-name { overflow:hidden; text-overflow:ellipsis; flex:1; }
            .model-picker-right { display:flex; flex-direction:column; min-width:0; gap:4px; }
            .model-picker-preview { flex:1; min-height:260px; background:#505050; border:2px solid; border-color:var(--win-shadow) var(--win-white) var(--win-white) var(--win-shadow); overflow:hidden; }
            .model-picker-meta { min-height:72px; padding:5px; background:#fff; border:1px solid var(--win-shadow); font:10px monospace; white-space:pre-wrap; overflow-wrap:anywhere; }
            .model-picker-footer { display:flex; gap:4px; align-items:center; padding:5px 6px 6px; }
            .model-picker-path { flex:1; min-width:0; font:10px monospace; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
        `;
        document.head.appendChild(style);
    }

    function makeButton(label, handler) {
        const button = document.createElement('button');
        button.className = 'win98-btn';
        button.type = 'button';
        button.textContent = label;
        button.onclick = handler;
        return button;
    }

    function ensurePickerDOM() {
        injectStyles();
        let overlay = document.getElementById('model-picker-modal');
        if (overlay) return overlay;

        overlay = document.createElement('div');
        overlay.id = 'model-picker-modal';
        overlay.className = 'modal-overlay';
        overlay.innerHTML = `
            <div class="model-picker-window">
                <div class="title-bar">
                    <div class="title-bar-text">Select 3D Model</div>
                    <div class="title-bar-controls"><button class="win-btn-small outset-bevel" type="button" data-model-close>×</button></div>
                </div>
                <div class="model-picker-body">
                    <div class="model-picker-left">
                        <input id="model-picker-search" class="win98-input" type="search" placeholder="Search models…" autocomplete="off">
                        <select id="model-picker-dir" class="win98-select"><option value="">All folders</option></select>
                        <div id="model-picker-list" class="model-picker-list" tabindex="0"></div>
                    </div>
                    <div class="model-picker-right">
                        <div class="model-picker-preview"><canvas id="model-picker-canvas" class="model-preview-canvas"></canvas></div>
                        <div id="model-picker-meta" class="model-picker-meta">Select a model to preview it.</div>
                    </div>
                </div>
                <div class="model-picker-footer">
                    <div id="model-picker-path" class="model-picker-path">(none)</div>
                    <button class="win98-btn" type="button" data-model-reset>Reset View</button>
                    <button class="win98-btn" type="button" data-model-clear>Clear</button>
                    <button class="win98-btn" type="button" data-model-cancel>Cancel</button>
                    <button class="win98-btn" type="button" data-model-apply>Select</button>
                </div>
            </div>`;
        document.body.appendChild(overlay);

        overlay.querySelector('[data-model-close]').onclick = closeModelPicker;
        overlay.querySelector('[data-model-cancel]').onclick = closeModelPicker;
        overlay.querySelector('[data-model-apply]').onclick = applyModelPickerSelection;
        overlay.querySelector('[data-model-clear]').onclick = () => {
            activePickerPath = '';
            updatePickerSelection();
        };
        overlay.querySelector('[data-model-reset]').onclick = () => {
            if (pickerPreview) pickerPreview.resetView();
        };

        document.getElementById('model-picker-search').oninput = renderPickerList;
        document.getElementById('model-picker-dir').onchange = renderPickerList;
        document.getElementById('model-picker-list').onkeydown = pickerListKeydown;
        overlay.addEventListener('mousedown', e => {
            if (e.target === overlay) closeModelPicker();
        });

        pickerPreview = new ModelPreview(
            document.getElementById('model-picker-canvas'),
            { interactive: true, autoRotate: true }
        );
        return overlay;
    }

    function folderForModel(path, rootPath) {
        const p = normalizePath(path);
        const rootPrefix = normalizePath(rootPath || 'assets/models').replace(/\/$/, '') + '/';
        const rel = p.startsWith(rootPrefix) ? p.slice(rootPrefix.length) : p;
        const at = rel.lastIndexOf('/');
        return at > 0 ? rel.slice(0, at) : '';
    }

    async function openModelPicker(currentPath, callback, options) {
        const requestId = ++pickerRequestId;
        const overlay = ensurePickerDOM();
        activePickerCallback = callback || null;
        activePickerOptions = Object.assign({ root: 'models' }, options || {});
        activePickerPath = normalizePath(currentPath);
        pickerFiles = [];

        const list = document.getElementById('model-picker-list');
        list.innerHTML = '<div style="padding:8px;color:#666">Loading models…</div>';
        document.getElementById('model-picker-search').value = '';
        document.getElementById('model-picker-dir').innerHTML = '<option value="">All folders</option>';
        overlay.classList.add('active');

        try {
            const rootParam = encodeURIComponent(activePickerOptions.root || 'models');
            const response = await fetch(`${root.API_URL || ''}/api/models?root=${rootParam}`);
            if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
            const data = await response.json();
            if (requestId !== pickerRequestId) return;
            pickerFiles = Array.isArray(data.files)
                ? data.files.map(entry => typeof entry === 'string' ? { path: entry } : entry)
                : [];

            const dirs = Array.from(new Set(
                pickerFiles.map(f => folderForModel(f.path, data.root)).filter(Boolean)
            )).sort();
            const select = document.getElementById('model-picker-dir');
            dirs.forEach(dir => {
                const option = document.createElement('option');
                option.value = dir;
                option.textContent = dir;
                select.appendChild(option);
            });

            renderPickerList();
            updatePickerSelection();
            const selected = list.querySelector('.selected');
            if (selected) selected.scrollIntoView({ block: 'center' });
            list.focus();
        } catch (err) {
            if (requestId !== pickerRequestId) return;
            list.innerHTML = `<div style="padding:8px;color:#800">Could not list models: ${escapeHtml(String(err.message || err))}</div>`;
            updatePickerSelection();
        }
    }

    function escapeHtml(text) {
        const chars = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
        return String(text).replace(/[&<>"']/g, c => chars[c]);
    }

    function filteredPickerFiles() {
        const query = document.getElementById('model-picker-search').value.trim().toLowerCase();
        const dir = document.getElementById('model-picker-dir').value;
        const rootPath = 'assets/' + normalizePath(
            (activePickerOptions && activePickerOptions.root) || 'models'
        );
        return pickerFiles.filter(entry => {
            const p = normalizePath(entry.path);
            if (query && !p.toLowerCase().includes(query)) return false;
            if (dir && folderForModel(p, rootPath) !== dir) return false;
            return true;
        });
    }

    function renderPickerList() {
        const list = document.getElementById('model-picker-list');
        if (!list) return;
        list.innerHTML = '';
        const files = filteredPickerFiles();
        if (!files.length) {
            list.innerHTML = '<div style="padding:8px;color:#777">No matching OBJ models.</div>';
            return;
        }

        files.forEach(entry => {
            const row = document.createElement('div');

            row.className = 'model-picker-row' +
                (normalizePath(entry.path) === activePickerPath ? ' selected' : '');
            row.dataset.path = normalizePath(entry.path);
            row.title = row.dataset.path;

            const bullet = document.createElement('span');
            bullet.textContent = '◆';
            bullet.style.fontSize = '8px';
            row.appendChild(bullet);

            const name = document.createElement('span');
            name.className = 'model-picker-row-name';
            name.textContent = row.dataset.path.split('/').pop().replace(/\.obj$/i, '');
            row.appendChild(name);

            row.onclick = () => selectPickerRow(row);
            row.ondblclick = () => {
                selectPickerRow(row);
                applyModelPickerSelection();
            };
            list.appendChild(row);
        });
    }

    function selectPickerRow(row) {
        activePickerPath = normalizePath(row.dataset.path);
        updatePickerSelection();
    }

    function pickerListKeydown(e) {
        if (!['ArrowDown', 'ArrowUp', 'Enter'].includes(e.key)) return;
        e.preventDefault();
        const rows = Array.from(document.querySelectorAll('#model-picker-list .model-picker-row'));
        if (!rows.length) return;
        const current = rows.findIndex(row => row.classList.contains('selected'));
        if (e.key === 'Enter') {
            if (current >= 0) applyModelPickerSelection();
            return;
        }
        const next = e.key === 'ArrowDown'
            ? Math.min(rows.length - 1, current + 1)
            : Math.max(0, current < 0 ? 0 : current - 1);
        selectPickerRow(rows[next]);
        rows[next].scrollIntoView({ block: 'nearest' });
    }

    async function updatePickerSelection() {
        document.querySelectorAll('#model-picker-list .model-picker-row').forEach(row => {
            row.classList.toggle('selected', normalizePath(row.dataset.path) === activePickerPath);
        });

        const pathBox = document.getElementById('model-picker-path');
        const meta = document.getElementById('model-picker-meta');
        if (pathBox) pathBox.textContent = activePickerPath || '(none)';
        if (pickerPreview) pickerPreview.setPath(activePickerPath);
        if (meta) meta.removeAttribute('data-model-ready');
        if (!meta) return;
        if (!activePickerPath) {
            meta.textContent = 'No model selected.';
            return;
        }

        meta.textContent = 'Loading model metadata…';
        const requested = activePickerPath;
        try {
            const model = await loadModel(requested);
            if (requested !== activePickerPath) return;
            const entry = pickerFiles.find(f => normalizePath(f.path) === requested) || {};
            const size = Number(entry.size);
            const sizeLabel = Number.isFinite(size)
                ? `${Math.max(1, Math.round(size / 1024))} KB`
                : 'unknown size';
            const dims = model.bounds.max.map((v, i) => Math.abs(v - model.bounds.min[i]));
            const libraries = model.materialLibraries.length
                ? model.materialLibraries.map(lib => `${lib.ok ? '✓' : '⚠'} ${lib.path}`).join('\n')
                : '(no mtllib declaration)';

            meta.textContent = [
                requested,
                `${model.vertexCount} vertices · ${model.triangleCount} triangles · ${model.materialNames.length} material${model.materialNames.length === 1 ? '' : 's'} · ${sizeLabel}`,
                `bounds ${dims.map(n => Number(n.toFixed(3))).join(' × ')}`,
                `materials: ${libraries}`,
                '',
                'Drag to orbit · wheel to zoom · double-click to reset'
            ].join('\n');
            meta.setAttribute('data-model-ready', '1');
        } catch (err) {
            if (requested !== activePickerPath) return;
            meta.textContent = `${requested}\n\n⚠ Preview failed: ${String(err.message || err)}`;
        }
    }

    function applyModelPickerSelection() {
        const callback = activePickerCallback;
        const path = activePickerPath;
        closeModelPicker();
        if (callback) callback(path);
    }

    function closeModelPicker() {

        pickerRequestId += 1;
        const overlay = document.getElementById('model-picker-modal');
        if (overlay) overlay.classList.remove('active');
        activePickerCallback = null;
        activePickerOptions = null;
        activePickerPath = '';
        pickerFiles = [];
        if (pickerPreview) pickerPreview.setPath('');
    }

    function createModelField(container, labelText, value, onChange, options) {
        injectStyles();
        options = Object.assign({ root: 'models' }, options || {});
        let currentPath = normalizePath(value);

        const group = document.createElement('div');
        group.className = 'form-group';
        const label = document.createElement('label');
        label.textContent = labelText;
        label.style.marginBottom = '2px';
        group.appendChild(label);

        const row = document.createElement('div');
        row.style.cssText = 'display:flex; align-items:stretch; gap:6px; min-width:0;';
        const previewWrap = document.createElement('div');
        previewWrap.className = 'model-field-preview';
        previewWrap.title = 'Double-click to choose a model';
        const canvas = document.createElement('canvas');
        canvas.className = 'model-preview-canvas';
        previewWrap.appendChild(canvas);
        row.appendChild(previewWrap);

        const side = document.createElement('div');
        side.style.cssText = 'display:flex; flex:1; min-width:0; flex-direction:column; justify-content:space-between; gap:4px;';
        const pathLabel = document.createElement('div');
        pathLabel.className = 'model-field-path';
        side.appendChild(pathLabel);

        const buttons = document.createElement('div');
        buttons.style.cssText = 'display:flex; gap:4px;';
        const pick = makeButton('Pick…', () => openModelPicker(currentPath, setValue, options));
        const clear = makeButton('Clear', () => setValue(''));
        buttons.appendChild(pick);
        buttons.appendChild(clear);
        side.appendChild(buttons);
        row.appendChild(side);
        group.appendChild(row);
        container.appendChild(group);

        const preview = new ModelPreview(canvas, { interactive: false, autoRotate: true });
        function setValue(path, notify = true) {
            currentPath = normalizePath(path);
            pathLabel.textContent = currentPath || '(none)';
            pathLabel.title = currentPath;
            clear.disabled = !currentPath;
            preview.setPath(currentPath);
            if (notify && onChange) onChange(currentPath);
        }
        previewWrap.ondblclick = () => openModelPicker(currentPath, setValue, options);
        setValue(currentPath, false);
        return { element: group, preview, setValue, getValue: () => currentPath };
    }

    function isModelFieldLabel(label, value) {
        const text = String(label || '');
        if (/3D\s+Model/i.test(text) || /Model\s*\(\.obj/i.test(text)) return true;
        return /\bmodel\b/i.test(text) &&
            typeof value === 'string' &&
            /\.obj$/i.test(value.trim());
    }

    function installFormFieldBridge() {
        if (root.__modelFormFieldBridgeInstalled || typeof root.createFormField !== 'function') return;
        root.__modelFormFieldBridgeInstalled = true;
        const original = root.createFormField;
        root.createFormField = function (container, labelText, value, onChange) {
            if (isModelFieldLabel(labelText, value)) {
                return createModelField(container, labelText, value, onChange, { root: 'models' });
            }
            return original.apply(this, arguments);
        };
    }

    function installItemModelField() {
        try {
            if (typeof ENTITY_FORM_SCHEMAS === 'undefined' || !ENTITY_FORM_SCHEMAS.items) return;
            const fields = ENTITY_FORM_SCHEMAS.items.fields;
            if (fields.some(field => field && (field.key === 'model' || field._modelPickerField))) return;

            const field = {
                kind: 'custom',
                _modelPickerField: true,
                build: (container, item) => createModelField(
                    container,
                    '3D Model',
                    item.model || '',
                    path => {
                        if (path) item.model = path;
                        else delete item.model;
                        if (typeof setDirty === 'function') setDirty(true);

                    },
                    { root: 'models/items' }
                )
            };
            const descriptionAt = fields.findIndex(f => f && f.key === 'description');
            fields.splice(descriptionAt >= 0 ? descriptionAt + 1 : fields.length, 0, field);
        } catch (err) {
            console.warn('[model-picker] could not install item model field:', err);
        }
    }

    function enhanceEventModelControl() {
        const input = document.getElementById('event-prop-model-path');
        if (!input || input.dataset.modelPickerEnhanced === '1') return;
        input.dataset.modelPickerEnhanced = '1';
        input.readOnly = true;

        const host = input.parentElement;
        if (!host) return;
        const wrap = document.createElement('div');
        wrap.style.cssText = 'display:flex; gap:5px; align-items:stretch; margin-top:4px;';

        const previewWrap = document.createElement('div');
        previewWrap.className = 'model-field-preview';
        previewWrap.style.width = '72px';
        previewWrap.style.height = '72px';
        const canvas = document.createElement('canvas');
        canvas.className = 'model-preview-canvas';
        previewWrap.appendChild(canvas);
        wrap.appendChild(previewWrap);

        const controls = document.createElement('div');
        controls.style.cssText = 'display:flex; flex:1; flex-direction:column; gap:4px; justify-content:flex-end;';
        const pick = makeButton('Pick 3D Model…', () => {
            openModelPicker(input.value, path => {
                input.value = path;
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.dispatchEvent(new Event('change', { bubbles: true }));
                sync();
                if (typeof eventModalDirty !== 'undefined') eventModalDirty = true;
            }, { root: 'models' });
        });
        const clear = makeButton('Clear Override', () => {
            input.value = '';
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
            sync();
            if (typeof eventModalDirty !== 'undefined') eventModalDirty = true;
        });
        controls.appendChild(pick);
        controls.appendChild(clear);
        wrap.appendChild(controls);
        host.appendChild(wrap);

        const preview = new ModelPreview(canvas, { interactive: false, autoRotate: true });
        let lastPath = null;
        function sync() {
            const path = normalizePath(input.value);
            if (path !== lastPath) {
                lastPath = path;
                preview.setPath(path);
            }
            const mode = document.getElementById('event-prop-model-mode');
            const enabled = !mode || mode.value === 'override';
            pick.disabled = !enabled;
            clear.disabled = !enabled || !path;
            wrap.style.opacity = enabled ? '1' : '0.55';
        }
        input.addEventListener('input', sync);
        input.addEventListener('change', sync);
        const mode = document.getElementById('event-prop-model-mode');
        if (mode) mode.addEventListener('change', sync);

        // Event pages reuse this fixed DOM. Keep the preview synchronized when
        // events.js swaps model values between Base and page tabs.
        if (typeof root.setPresentationFormUI === 'function' && !root.__modelPresentationBridgeInstalled) {
            root.__modelPresentationBridgeInstalled = true;
            const original = root.setPresentationFormUI;
            root.setPresentationFormUI = function () {
                const result = original.apply(this, arguments);
                sync();
                return result;
            };
        }
        sync();
    }

    function initEditorHooks() {
        if (typeof document === 'undefined') return;
        injectStyles();
        installFormFieldBridge();
        installItemModelField();
        enhanceEventModelControl();
    }

    root.openModelPicker = openModelPicker;
    root.closeModelPicker = closeModelPicker;
    root.applyModelPickerSelection = applyModelPickerSelection;
    root.createModelField = createModelField;
    root.SecondRiteModelPreview = {

        parseGeometryStats,
        loadModel,
        ModelPreview,
        normalizePath,
        resolveSibling,
        prefersReducedMotion,
        initEditorHooks
    };

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = {
            parseGeometryStats,
            normalizePath,
            resolveSibling,
            prefersReducedMotion
        };
    }

    if (typeof document !== 'undefined') {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initEditorHooks, { once: true });
        } else {
            initEditorHooks();
        }
    }
})(typeof window !== 'undefined' ? window : globalThis);
