/*
 * Browser integration for the shared 3D model picker.
 *
 * Keep this small: model-picker.js owns parsing/rendering; this file adapts
 * that primitive to the Developer Studio shell and its existing event UI.
 */
(function (root) {
    'use strict';

    function installLayoutStyles() {
        let style = document.getElementById('model-picker-integration-style');
        if (!style) {
            style = document.createElement('style');
            style.id = 'model-picker-integration-style';
            style.textContent = `
                /* Flex/grid children default to min-height:auto. With a long
                   model library that lets the list's min-content height enlarge
                   the grid item past the modal instead of scrolling inside it. */
                .model-picker-window {
                    overflow: hidden;
                    box-sizing: border-box;
                }
                .model-picker-body {
                    min-height: 0;
                    overflow: hidden;
                }
                .model-picker-left,
                .model-picker-right {
                    min-height: 0;
                    overflow: hidden;
                }
                .model-picker-list {
                    min-height: 0;
                    overflow: auto;
                }
                .model-picker-preview {
                    flex: 1 1 0;
                    min-height: 0;
                    overflow: hidden;
                    --checker-size: 24px;
                }
                .model-picker-meta {
                    flex: 0 0 76px;
                    min-height: 0;
                    max-height: 76px;
                    overflow: auto;
                    box-sizing: border-box;
                }
                .model-picker-footer {
                    flex: 0 0 auto;
                    min-width: 0;
                    overflow: hidden;
                    box-sizing: border-box;
                    justify-content: flex-end;
                }
                /* Asset paths are implementation data, not useful authoring UI.
                   Keep them serialized internally but do not spend preview space
                   showing assets/models/... strings. */
                .model-picker-path,
                .model-field-path,
                #event-prop-model-path {
                    display: none !important;
                }
                #event-prop-model-path-row > button[onclick*="openAssetPickerForEventModel"] {
                    display: none !important;
                }
                #event-prop-model-path-row .model-event-preview-row {
                    flex: 1 1 auto;
                    width: 100%;
                    min-width: 0;
                }
                .model-field-preview {
                    --checker-size: 12px;
                }
            `;
        }
        // model-picker.js injects its base stylesheet during editor init. Move
        // this sheet to the end whenever we install/reinstall so these layout
        // constraints remain the final word.
        document.head.appendChild(style);
    }

    // The Studio already defines .transparent-checker as its one visual
    // language for art over transparency. Model preview wrappers are created
    // dynamically, so mark them as they enter the DOM rather than duplicating
    // the checker gradient here.
    function markPreviewCheckers(node) {
        if (!node || node.nodeType !== 1) return;
        if (node.matches && node.matches('.model-field-preview, .model-picker-preview')) {
            node.classList.add('transparent-checker');
        }
        if (node.querySelectorAll) {
            node.querySelectorAll('.model-field-preview, .model-picker-preview').forEach(el => {
                el.classList.add('transparent-checker');
            });
        }
    }

    function observePreviewCheckers() {
        markPreviewCheckers(document.documentElement);
        if (!root.MutationObserver || !document.documentElement) return;
        const observer = new MutationObserver(records => {
            records.forEach(record => record.addedNodes.forEach(markPreviewCheckers));
        });
        observer.observe(document.documentElement, { childList: true, subtree: true });
    }

    function makeCanvasTransparent() {
        const api = root.SecondRiteModelPreview;
        if (!api || !api.ModelPreview) return;
        const proto = api.ModelPreview.prototype;
        if (!proto.__studioTransparentBackground) {
            proto.__studioTransparentBackground = true;
            proto.drawBackground = function (ctx, w, h) {
                ctx.clearRect(0, 0, w, h);
            };
        }
    }

    // model-picker.js's injected CSS currently gives preview wrappers a solid
    // gray background. Remove only that declaration after the base stylesheet
    // exists; then the Studio's canonical .transparent-checker rule is what
    // actually paints the surface.
    function releaseHardCodedPreviewBackgrounds() {
        const style = document.getElementById('model-picker-style');
        const sheet = style && style.sheet;
        if (!sheet) return;
        try {
            Array.from(sheet.cssRules || []).forEach(rule => {
                const selector = rule.selectorText || '';
                if (selector === '.model-field-preview' || selector === '.model-picker-preview') {
                    rule.style.removeProperty('background');
                }
            });
        } catch (err) {
            console.warn('[model-picker] could not release preview background CSS:', err);
        }
    }

    // Picker metadata is useful (mesh size, bounds, materials) but raw project
    // paths are not. model-picker.js currently emits them as the first line and
    // in mtllib status lines; strip only those lines from the visible text.
    function installMetadataPathScrubber() {
        const attach = () => {
            const meta = document.getElementById('model-picker-meta');
            if (!meta || meta.dataset.pathScrubber === '1') return;
            meta.dataset.pathScrubber = '1';

            const scrub = () => {
                const original = meta.textContent || '';
                const lines = original.split('\n');
                let changed = false;
                const cleaned = [];
                lines.forEach(line => {
                    const trimmed = line.trim();
                    if (/^assets\/models\/.*\.obj$/i.test(trimmed)) {
                        changed = true;
                        return;
                    }
                    if (/^materials:\s*/i.test(trimmed) && /assets\/models\//i.test(trimmed)) {
                        cleaned.push('materials: loaded');
                        changed = true;
                        return;
                    }
                    if (/^[✓⚠]\s+assets\/models\//i.test(trimmed)) {
                        changed = true;
                        return;
                    }
                    cleaned.push(line);
                });
                while (cleaned.length && cleaned[0].trim() === '') cleaned.shift();
                if (changed) meta.textContent = cleaned.join('\n');
            };
            const observer = new MutationObserver(scrub);
            observer.observe(meta, { childList: true, characterData: true, subtree: true });
            scrub();
        };

        attach();
        if (!root.MutationObserver || !document.body) return;
        const observer = new MutationObserver(attach);
        observer.observe(document.body, { childList: true, subtree: true });
    }

    function linkedCommonEventModel() {
        const select = document.getElementById('event-prop-script-id');
        if (!select || typeof dbPayload === 'undefined' || !dbPayload.commonEvents) return '';
        const ce = dbPayload.commonEvents[String(select.value)];
        return ce && typeof ce.model === 'string' ? ce.model : '';
    }

    function inheritedBaseModel() {
        // Page tabs inherit their Base event first; Base in turn may inherit the
        // linked Common Event. This mirrors resolvePage's overlay semantics.
        if (typeof eventBaseFieldStash !== 'undefined' && eventBaseFieldStash) {
            if (eventBaseFieldStash.model === false) return '';
            if (typeof eventBaseFieldStash.model === 'string' && eventBaseFieldStash.model) {
                return eventBaseFieldStash.model;
            }
        }
        return linkedCommonEventModel();
    }

    function effectiveEventModelPath() {
        const mode = document.getElementById('event-prop-model-mode');
        const input = document.getElementById('event-prop-model-path');
        const currentMode = mode ? mode.value : 'inherit';
        if (currentMode === 'suppress') return '';
        if (currentMode === 'override') return input ? input.value : '';

        if (typeof activeEventPageIdx !== 'undefined' && activeEventPageIdx !== -1) {
            return inheritedBaseModel();
        }
        return linkedCommonEventModel();
    }

    // events.js predates the 3D picker and its fixed "..." button still calls
    // the image-only openAssetPicker('models'). Make that established action
    // open the same 3D picker used everywhere else; event serialization stays
    // owned by events.js / EventPresentation.
    function installMapEventPickerBridge() {
        root.openAssetPickerForEventModel = function () {
            const input = document.getElementById('event-prop-model-path');
            if (!input || typeof root.openModelPicker !== 'function') return;

            root.openModelPicker(input.value, filepath => {
                input.value = String(filepath || '').replace(/\\/g, '/');
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.dispatchEvent(new Event('change', { bubbles: true }));
                if (typeof eventModalDirty !== 'undefined') eventModalDirty = true;
            }, { root: 'models' });
        };
    }

    // The core model field was originally wired only to event-prop-model-path,
    // which is intentionally blank while a regular event inherits its Common
    // Event model. Replace that canvas with an integration-owned ModelPreview
    // driven by the EFFECTIVE model so inherited events actually show 3D art.
    function installEffectiveEventModelPreview() {
        const api = root.SecondRiteModelPreview;
        const input = document.getElementById('event-prop-model-path');
        const row = document.getElementById('event-prop-model-path-row');
        if (!api || !api.ModelPreview || !input || !row || row.dataset.effectiveModelPreview === '1') return;

        const previewWrap = row.querySelector('.model-field-preview');
        if (!previewWrap) return;
        row.dataset.effectiveModelPreview = '1';

        const shell = previewWrap.parentElement;
        if (shell) shell.classList.add('model-event-preview-row');

        // Disconnect the core preview canvas so its RAF loop naturally stops,
        // then create the one preview whose input is the resolved presentation.
        const oldCanvas = previewWrap.querySelector('canvas');
        if (oldCanvas) oldCanvas.remove();
        const canvas = document.createElement('canvas');
        canvas.className = 'model-preview-canvas';
        previewWrap.appendChild(canvas);
        const preview = new api.ModelPreview(canvas, { interactive: false, autoRotate: true });
        let lastPath = null;

        function sync() {
            const path = String(effectiveEventModelPath() || '').replace(/\\/g, '/');
            if (path !== lastPath) {
                lastPath = path;
                preview.setPath(path);
            }
            const mode = document.getElementById('event-prop-model-mode');
            if (shell) shell.style.opacity = mode && mode.value === 'suppress' ? '0.55' : '1';
            previewWrap.title = path ? 'Effective 3D model' : 'No effective 3D model';
        }

        input.addEventListener('input', sync);
        input.addEventListener('change', sync);
        const mode = document.getElementById('event-prop-model-mode');
        if (mode) mode.addEventListener('change', sync);
        const common = document.getElementById('event-prop-script-id');
        if (common) common.addEventListener('change', sync);

        if (typeof root.setPresentationFormUI === 'function' && !root.__effectiveModelPresentationBridgeInstalled) {
            root.__effectiveModelPresentationBridgeInstalled = true;
            const original = root.setPresentationFormUI;
            root.setPresentationFormUI = function () {
                const result = original.apply(this, arguments);
                sync();
                return result;
            };
        }

        // Keep the preview visible in inherit/suppress modes too. The controls
        // may be disabled there, but hiding the entire row hid the authored
        // result and left the sprite image as the only visible preview.
        if (typeof root.updateEventPresentationControls === 'function' && !root.__effectiveModelControlsBridgeInstalled) {
            root.__effectiveModelControlsBridgeInstalled = true;
            const original = root.updateEventPresentationControls;
            root.updateEventPresentationControls = function () {
                const result = original.apply(this, arguments);
                const modelRow = document.getElementById('event-prop-model-path-row');
                if (modelRow) modelRow.style.display = 'flex';
                sync();
                return result;
            };
        }

        row.style.display = 'flex';
        sync();
    }

    function finishAfterEditorInit() {
        releaseHardCodedPreviewBackgrounds();
        installLayoutStyles();
        markPreviewCheckers(document.documentElement);
        installMetadataPathScrubber();
        installEffectiveEventModelPreview();
    }

    function init() {
        installLayoutStyles();
        makeCanvasTransparent();
        observePreviewCheckers();
        installMapEventPickerBridge();
        installMetadataPathScrubber();

        // If model-picker.js deferred its own init until DOMContentLoaded, its
        // base CSS is inserted before this listener because it registered first.
        // Re-run the tiny shell adaptation afterwards so source order is stable.
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', finishAfterEditorInit, { once: true });
        } else {
            finishAfterEditorInit();
        }
    }

    if (typeof document !== 'undefined') init();
})(typeof window !== 'undefined' ? window : globalThis);
