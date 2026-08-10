/*
 * Browser integration for the shared 3D model picker.
 *
 * model-picker.js owns parsing/rendering. This file adapts that primitive to
 * the Developer Studio's existing asset-field language and Event inheritance
 * semantics without making the browser preview authoritative for runtime art.
 */
(function (root) {
    'use strict';

    function installLayoutStyles() {
        let style = document.getElementById('model-picker-integration-style');
        if (!style) {
            style = document.createElement('style');
            style.id = 'model-picker-integration-style';
            style.textContent = `
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

                /* Asset paths remain serialized data, but asset fields in the
                   Studio are chosen visually. Do not spend authoring space on
                   assets/models/... strings. */
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
                .model-field-preview.model-picker-button {
                    cursor: pointer;
                }
                .model-field-preview.model-picker-button:focus {
                    outline: 1px dotted var(--win-black);
                    outline-offset: 1px;
                }
                .model-field-preview.model-picker-disabled {
                    cursor: default;
                }
            `;
        }
        document.head.appendChild(style);
    }

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
        if (proto.__studioTransparentBackground) return;
        proto.__studioTransparentBackground = true;
        proto.drawBackground = function (ctx, w, h) {
            ctx.clearRect(0, 0, w, h);
        };
    }

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

    function installMetadataPathScrubber() {
        const attach = () => {
            const meta = document.getElementById('model-picker-meta');
            if (!meta || meta.dataset.pathScrubber === '1') return;
            meta.dataset.pathScrubber = '1';

            const scrub = () => {
                const lines = (meta.textContent || '').split('\n');
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

    // Shared owned asset fields (Items/Common Events) follow the Studio's
    // established visual language: the preview itself is the picker button.
    function promoteModelFieldPreview(previewWrap) {
        if (!previewWrap || previewWrap.dataset.previewPickerButton === '1') return;
        if (previewWrap.closest('#event-prop-model-path-row')) return;
        if (typeof previewWrap.ondblclick !== 'function') return;

        const open = previewWrap.ondblclick;
        previewWrap.ondblclick = null;
        previewWrap.dataset.previewPickerButton = '1';
        previewWrap.classList.add('model-picker-button');
        previewWrap.tabIndex = 0;
        previewWrap.setAttribute('role', 'button');
        previewWrap.title = 'Click to choose a 3D model';
        previewWrap.onclick = event => {
            event.preventDefault();
            open(event);
        };
        previewWrap.onkeydown = event => {
            if (event.key !== 'Enter' && event.key !== ' ') return;
            event.preventDefault();
            open(event);
        };

        const group = previewWrap.closest('.form-group');
        if (group) {
            Array.from(group.querySelectorAll('button')).forEach(button => {
                if (/^Pick(?: 3D Model)?…?$/i.test((button.textContent || '').trim())) button.remove();
            });
        }
    }

    function promoteAllModelFieldPreviews(node) {
        if (!node || node.nodeType !== 1) return;
        const candidates = [];
        if (node.matches && node.matches('.model-field-preview')) candidates.push(node);
        if (node.querySelectorAll) candidates.push(...node.querySelectorAll('.model-field-preview'));
        if (candidates.length) setTimeout(() => candidates.forEach(promoteModelFieldPreview), 0);
    }

    function observeModelFieldButtons() {
        promoteAllModelFieldPreviews(document.documentElement);
        if (!root.MutationObserver || !document.documentElement) return;
        const observer = new MutationObserver(records => {
            records.forEach(record => record.addedNodes.forEach(promoteAllModelFieldPreviews));
        });
        observer.observe(document.documentElement, { childList: true, subtree: true });
    }

    function linkedCommonEventModel() {
        const select = document.getElementById('event-prop-script-id');
        if (!select || typeof dbPayload === 'undefined' || !dbPayload.commonEvents) return '';
        const ce = dbPayload.commonEvents[String(select.value)];
        return ce && typeof ce.model === 'string' ? ce.model : '';
    }

    function inheritedBaseModel() {
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

    function setEventModelFromPicker(filepath) {
        const input = document.getElementById('event-prop-model-path');
        const mode = document.getElementById('event-prop-model-mode');
        if (!input || !mode || mode.value !== 'override') return;
        input.value = String(filepath || '').replace(/\\/g, '/');
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
        if (typeof eventModalDirty !== 'undefined') eventModalDirty = true;
    }

    function openEventModelPicker() {
        const mode = document.getElementById('event-prop-model-mode');
        const input = document.getElementById('event-prop-model-path');
        if (!mode || mode.value !== 'override' || !input || typeof root.openModelPicker !== 'function') return;
        root.openModelPicker(input.value, setEventModelFromPicker, { root: 'models' });
    }

    function installMapEventPickerBridge() {
        root.openAssetPickerForEventModel = openEventModelPicker;
    }

    // Events are different from owned fields: they can inherit or suppress a
    // presentation value. The preview always shows the EFFECTIVE result, but it
    // is a picker button only while the Event explicitly owns an override.
    function installEffectiveEventModelPreview() {
        const api = root.SecondRiteModelPreview;
        const input = document.getElementById('event-prop-model-path');
        const row = document.getElementById('event-prop-model-path-row');
        if (!api || !api.ModelPreview || !input || !row || row.dataset.effectiveModelPreview === '1') return;

        const previewWrap = row.querySelector('.model-field-preview');
        if (!previewWrap) return;
        row.dataset.effectiveModelPreview = '1';

        const shell = previewWrap.parentElement;
        if (shell) {
            shell.classList.add('model-event-preview-row');
            Array.from(shell.querySelectorAll('button')).forEach(button => {
                if (/^Pick 3D Model/i.test((button.textContent || '').trim())) button.remove();
            });
        }

        const oldCanvas = previewWrap.querySelector('canvas');
        if (oldCanvas) oldCanvas.remove();
        const canvas = document.createElement('canvas');
        canvas.className = 'model-preview-canvas';
        previewWrap.appendChild(canvas);
        const preview = new api.ModelPreview(canvas, { interactive: false, autoRotate: true });
        let lastPath = null;

        previewWrap.ondblclick = null;
        previewWrap.dataset.previewPickerButton = '1';
        previewWrap.onclick = event => {
            event.preventDefault();
            openEventModelPicker();
        };
        previewWrap.onkeydown = event => {
            if (event.key !== 'Enter' && event.key !== ' ') return;
            event.preventDefault();
            openEventModelPicker();
        };

        function sync() {
            const path = String(effectiveEventModelPath() || '').replace(/\\/g, '/');
            if (path !== lastPath) {
                lastPath = path;
                preview.setPath(path);
            }

            const mode = document.getElementById('event-prop-model-mode');
            const ownsValue = !!mode && mode.value === 'override';
            if (shell) shell.style.opacity = ownsValue ? '1' : '0.55';
            previewWrap.classList.toggle('model-picker-button', ownsValue);
            previewWrap.classList.toggle('model-picker-disabled', !ownsValue);
            previewWrap.tabIndex = ownsValue ? 0 : -1;
            if (ownsValue) {
                previewWrap.setAttribute('role', 'button');
                previewWrap.removeAttribute('aria-disabled');
                previewWrap.title = path ? 'Click to choose a 3D model' : 'Click to choose a 3D model';
            } else {
                previewWrap.removeAttribute('role');
                previewWrap.setAttribute('aria-disabled', 'true');
                previewWrap.title = mode && mode.value === 'suppress'
                    ? '3D model suppressed by this Event'
                    : 'Inherited 3D model — choose Override to edit';
            }
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

        // The stock Event control hides non-owned rows. For models we keep the
        // read-only effective preview visible so inheritance is legible, while
        // the dimmed/non-interactive state communicates that it is not owned.
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
        promoteAllModelFieldPreviews(document.documentElement);
    }

    function init() {
        installLayoutStyles();
        makeCanvasTransparent();
        observePreviewCheckers();
        observeModelFieldButtons();
        installMapEventPickerBridge();
        installMetadataPathScrubber();

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', finishAfterEditorInit, { once: true });
        } else {
            finishAfterEditorInit();
        }
    }

    if (typeof document !== 'undefined') init();
})(typeof window !== 'undefined' ? window : globalThis);
