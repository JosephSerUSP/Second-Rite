/*
 * Browser integration fixes for the shared 3D model picker.
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
                }
                .model-picker-path {
                    min-width: 40px;
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

    function finishAfterEditorInit() {
        releaseHardCodedPreviewBackgrounds();
        installLayoutStyles();
        markPreviewCheckers(document.documentElement);
    }

    function init() {
        installLayoutStyles();
        makeCanvasTransparent();
        observePreviewCheckers();
        installMapEventPickerBridge();

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
