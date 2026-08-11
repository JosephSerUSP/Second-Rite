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

    function parseOBJ(text) {
        // OBJ uses one-based indices, so slot zero is deliberately unused.
        const vertices = [[0, 0, 0]];
        const faces = [];
        const mtllibs = [];
        const materialNames = new Set();
        let material = '__default';

        String(text || '').split(/\r?\n/).forEach(raw => {
            const line = raw.trim();
            if (!line || line[0] === '#') return;
            const match = line.match(/^(\S+)\s*(.*)$/);
            if (!match) return;
            const tag = match[1];
            const rest = match[2].trim();

            if (tag === 'v') {
                const p = rest.split(/\s+/).slice(0, 3).map(Number);
                if (p.length === 3 && p.every(Number.isFinite)) vertices.push(p);
                return;
            }
            if (tag === 'mtllib') {
                // Current authored assets use one library per declaration. Treat
                // the remainder as a path so filenames containing spaces work.
                if (rest) mtllibs.push(rest);
                return;
            }
            if (tag === 'usemtl') {
                material = rest || '__default';
                materialNames.add(material);
                return;
            }
            if (tag !== 'f') return;

            const indices = rest.split(/\s+/).map(token => {
                const n = parseInt(token.split('/')[0], 10);
                if (!Number.isFinite(n) || n === 0) return null;
                return n < 0 ? vertices.length + n : n;
            }).filter(n => n !== null && vertices[n]);

            // OBJ permits quads/ngons. Fan triangulation is enough for the
            // editor preview and leaves the authored file completely untouched.
            for (let i = 1; i + 1 < indices.length; i++) {
                faces.push({ indices: [indices[0], indices[i], indices[i + 1]], material });
            }
        });

        if (!materialNames.size) materialNames.add('__default');

        let min = [Infinity, Infinity, Infinity];
        let max = [-Infinity, -Infinity, -Infinity];
        for (let i = 1; i < vertices.length; i++) {
            for (let axis = 0; axis < 3; axis++) {
                min[axis] = Math.min(min[axis], vertices[i][axis]);
                max[axis] = Math.max(max[axis], vertices[i][axis]);
            }
        }
        if (vertices.length === 1) {
            min = [-0.5, -0.5, -0.5];
            max = [0.5, 0.5, 0.5];
        }

        return {
            vertices,
            faces,
            mtllibs,
            materialNames: Array.from(materialNames),
            bounds: { min, max },
            vertexCount: Math.max(0, vertices.length - 1),
            triangleCount: faces.length
        };
    }

    function parseMTL(text) {
        const materials = { __default: [0.72, 0.72, 0.72] };
        let current = null;
        String(text || '').split(/\r?\n/).forEach(raw => {
            const line = raw.trim();
            if (!line || line[0] === '#') return;
            const parts = line.split(/\s+/);
            if (parts[0] === 'newmtl') {
                current = parts.slice(1).join(' ') || '__default';
                if (!materials[current]) materials[current] = [0.72, 0.72, 0.72];
            } else if (parts[0] === 'Kd' && current && parts.length >= 4) {
                const rgb = parts.slice(1, 4).map(Number);
                if (rgb.every(Number.isFinite)) {
                    materials[current] = rgb.map(v => Math.max(0, Math.min(1, v)));
                }
            }
        });
        return materials;
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
            const obj = parseOBJ(await fetchText(path));
            const materials = { __default: [0.72, 0.72, 0.72] };
            const materialLibraries = [];

            for (const lib of obj.mtllibs) {
                const resolved = resolveSibling(path, lib);
                try {
                    Object.assign(materials, parseMTL(await fetchText(resolved)));
                    materialLibraries.push({ path: resolved, ok: true });
                } catch (err) {
                    materialLibraries.push({
                        path: resolved,
                        ok: false,
                        error: String(err.message || err)
                    });
                }
            }

            return Object.assign(obj, { path, materials, materialLibraries });
        })();

        MODEL_CACHE.set(path, promise);
        try {
            return await promise;
        } catch (err) {
            MODEL_CACHE.delete(path);
            throw err;
        }
    }

    // Mirrors buildItemShader's meaningful geometry transform: local-Y tilt,
    // then a Z-axis turntable. Returned coordinates are [screenX, screenY-up,
    // depth], which lets the simple canvas renderer use the same authored axes
    // without copying the runtime shader itself.
    function transformVertex(v, angle, tilt) {
        const cosT = Math.cos(tilt), sinT = Math.sin(tilt);
        const tiltX = v[0] * cosT + v[2] * sinT;
        const tiltY = v[1];
        const tiltZ = -v[0] * sinT + v[2] * cosT;

        const cosA = Math.cos(angle), sinA = Math.sin(angle);
        const rotX = tiltX * cosA - tiltY * sinA;
        const rotY = tiltX * sinA + tiltY * cosA;
        const rotZ = tiltZ;
        return [rotX, -rotZ, rotY];
    }

    function faceNormal(a, b, c) {
        const ux = b[0] - a[0], uy = b[1] - a[1], uz = b[2] - a[2];
        const vx = c[0] - a[0], vy = c[1] - a[1], vz = c[2] - a[2];
        let x = uy * vz - uz * vy;
        let y = uz * vx - ux * vz;
        let z = ux * vy - uy * vx;
        const length = Math.sqrt(x*x + y*y + z*z) || 1;
        return [x / length, y / length, z / length];
    }

    function rgbCss(rgb, shade) {
        const c = rgb || [0.72, 0.72, 0.72];
        const values = c.slice(0, 3).map(v =>
            Math.round(Math.max(0, Math.min(1, v * shade)) * 255)
        );
        return `rgb(${values.join(',')})`;
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
            this.lastFrame = performance.now();
            this.alive = true;
            this.installEvents();
            this.frame = this.frame.bind(this);
            requestAnimationFrame(this.frame);
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
                this.tilt += (e.clientY - this.lastY) * 0.012;
                this.tilt = Math.max(-1.35, Math.min(1.35, this.tilt));
                this.lastX = e.clientX;
                this.lastY = e.clientY;
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
                this.zoom *= Math.exp(-e.deltaY * 0.0012);
                this.zoom = Math.max(0.35, Math.min(4, this.zoom));
            }, { passive: false });
            canvas.addEventListener('dblclick', () => this.resetView());
        }

        resetView() {
            this.angle = Math.PI * 0.2;
            this.tilt = DEFAULT_TILT;
            this.zoom = 1;
        }

        async setPath(path) {
            this.path = normalizePath(path);
            this.model = null;
            this.error = '';
            this.canvas.removeAttribute('data-preview-ready');
            const requested = this.path;
            if (!requested) return;
            try {
                const model = await loadModel(requested);
                if (this.path === requested) this.model = model;
            } catch (err) {
                if (this.path === requested) this.error = String(err.message || err);
            }
        }

        stop() {
            this.alive = false;
        }

        resize() {
            const rect = this.canvas.getBoundingClientRect();
            const dpr = Math.min(2, root.devicePixelRatio || 1);
            const w = Math.max(1, Math.round(rect.width * dpr));
            const h = Math.max(1, Math.round(rect.height * dpr));
            if (this.canvas.width !== w || this.canvas.height !== h) {
                this.canvas.width = w;
                this.canvas.height = h;
            }
            return { w, h };
        }

        drawBackground(ctx, w, h) {
            ctx.fillStyle = '#505050';
            ctx.fillRect(0, 0, w, h);
            const step = Math.max(12, Math.round(Math.min(w, h) / 12));
            ctx.strokeStyle = 'rgba(255,255,255,0.055)';
            ctx.lineWidth = 1;
            ctx.beginPath();
            for (let x = 0; x < w; x += step) { ctx.moveTo(x, 0); ctx.lineTo(x, h); }
            for (let y = 0; y < h; y += step) { ctx.moveTo(0, y); ctx.lineTo(w, y); }
            ctx.stroke();
        }

        drawMessage(ctx, w, h, message) {
            ctx.fillStyle = '#e8e8e8';
            ctx.font = `${Math.max(10, Math.round(Math.min(w, h) * 0.055))}px monospace`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(message, w / 2, h / 2, w * 0.85);
        }

        render() {
            if (!this.canvas.isConnected) {
                this.alive = false;
                return;
            }
            // Hidden editor forms and a closed picker keep their canvas nodes,
            // but should cost essentially nothing until visible again.
            if (this.canvas.getClientRects().length === 0) return;

            const { w, h } = this.resize();
            const ctx = this.canvas.getContext('2d');
            if (!ctx) return;
            this.drawBackground(ctx, w, h);

            if (!this.path) return this.drawMessage(ctx, w, h, '(none)');
            if (this.error) return this.drawMessage(ctx, w, h, 'Preview unavailable');
            if (!this.model) return this.drawMessage(ctx, w, h, 'Loading…');

            const model = this.model;
            if (!model.faces.length) return this.drawMessage(ctx, w, h, 'No drawable faces');
            const min = model.bounds.min;
            const max = model.bounds.max;
            const center = [
                (min[0] + max[0]) * 0.5,
                (min[1] + max[1]) * 0.5,
                (min[2] + max[2]) * 0.5
            ];
            const extent = Math.max(
                max[0] - min[0],
                max[1] - min[1],
                max[2] - min[2],
                0.0001
            );
            const scale = Math.min(w, h) * 0.78 / extent * this.zoom;
            const transformed = new Array(model.vertices.length);

            for (let i = 1; i < model.vertices.length; i++) {
                const v = model.vertices[i];
                transformed[i] = transformVertex([
                    v[0] - center[0],
                    v[1] - center[1],
                    v[2] - center[2]
                ], this.angle, this.tilt);
            }

            // Runtime depth is rotY and uses "less". Therefore larger depth is
            // farther away and must be painted first by this 2D preview.
            const faces = model.faces.map(face => {
                const a = transformed[face.indices[0]];
                const b = transformed[face.indices[1]];
                const c = transformed[face.indices[2]];
                return { face, a, b, c, depth: (a[2] + b[2] + c[2]) / 3 };
            }).sort((a, b) => b.depth - a.depth);

            const light = [-0.35, 0.76, 0.55];
            ctx.lineWidth = Math.max(0.7, Math.min(1.4, w / 420));
            faces.forEach(entry => {
                const n = faceNormal(entry.a, entry.b, entry.c);
                const dot = Math.abs(n[0]*light[0] + n[1]*light[1] + n[2]*light[2]);
                const shade = 0.34 + 0.66 * dot;
                const rgb = model.materials[entry.face.material] || model.materials.__default;

                ctx.beginPath();
                [entry.a, entry.b, entry.c].forEach((v, i) => {
                    const sx = w * 0.5 + v[0] * scale;
                    const sy = h * 0.5 - v[1] * scale;
                    if (i === 0) ctx.moveTo(sx, sy); else ctx.lineTo(sx, sy);
                });
                ctx.closePath();
                ctx.fillStyle = rgbCss(rgb, shade);
                ctx.fill();
                ctx.strokeStyle = 'rgba(0,0,0,0.22)';
                ctx.stroke();
            });
            // Publish readiness only after actual model faces have been drawn.
            // Canvas existence and a completed fetch are not content signals.
            this.canvas.setAttribute('data-preview-ready', '1');
        }

        frame(now) {
            if (!this.alive) return;
            const dt = Math.min(0.05, Math.max(0, (now - this.lastFrame) / 1000));
            this.lastFrame = now;
            if (this.options.autoRotate && !prefersReducedMotion() && !this.dragging && this.model && this.canvas.getClientRects().length) {
                this.angle += dt * 0.42;
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
        parseOBJ,
        parseMTL,
        loadModel,
        ModelPreview,
        normalizePath,
        resolveSibling,
        transformVertex,
        prefersReducedMotion,
        initEditorHooks
    };

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = {
            parseOBJ,
            parseMTL,
            normalizePath,
            resolveSibling,
            transformVertex,
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
