(function (root, factory) {
    if (typeof define === 'function' && define.amd) {
        define([], factory);
    } else if (typeof module === 'object' && module.exports) {
        module.exports = factory();
    } else {
        root.EventPresentation = factory();
    }
}(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    function readPresentationField(object, key) {
        if (!object) return undefined;
        return object[key];
    }

    function writePresentationField(object, key, mode, value, isCommonEvent) {
        if (!object) return;
        if (isCommonEvent) {
            if (mode === 'none' || mode === 'inherit' || value === '' || value === null || value === undefined || value === false) {
                delete object[key];
            } else {
                object[key] = value;
            }
        } else {
            if (mode === 'inherit' || mode === undefined || mode === null) {
                delete object[key];
            } else if (mode === 'suppress' || value === false) {
                object[key] = false;
            } else if (mode === 'override' || mode === 'value') {
                if (value === '' || value === null || value === undefined) {
                    delete object[key];
                } else {
                    object[key] = value;
                }
            }
        }
        return object;
    }

    function serializeEventPresentation(formState, target) {
        target = target || {};
        writePresentationField(target, 'model', formState.modelMode, formState.modelValue, false);
        writePresentationField(target, 'interactionFocus', formState.focusMode, formState.focusValue, false);
        return target;
    }

    function serializeCommonEventPresentation(formState, target) {
        target = target || {};
        writePresentationField(target, 'model', formState.modelValue ? 'value' : 'none', formState.modelValue, true);
        writePresentationField(target, 'interactionFocus', formState.focusValue ? 'value' : 'none', formState.focusValue, true);
        return target;
    }

    return {
        readPresentationField: readPresentationField,
        writePresentationField: writePresentationField,
        serializeEventPresentation: serializeEventPresentation,
        serializeCommonEventPresentation: serializeCommonEventPresentation
    };
}));

// #277 PR1 bootstrap. Keep the neutral scene/project adapter independent from
// the rendering backend: this classic-script bridge is the only place that
// exposes the editor's lexical state to the new workspace. The 3D backend is
// lazy-loaded only when an author chooses Perspective or Top Ortho, so the
// existing 2D map path remains the default and remains usable if WebGL or the
// optional vendor bundle is unavailable.
(function installThestraEditorSceneBootstrap() {
    if (typeof window === 'undefined' || typeof document === 'undefined') return;

    function loadScript(src) {
        return new Promise((resolve, reject) => {
            const existing = document.querySelector(`script[data-thestra-scene-src="${src}"]`);
            if (existing) {
                if (existing.dataset.loaded === 'true') resolve();
                else existing.addEventListener('load', resolve, { once: true });
                return;
            }
            const script = document.createElement('script');
            script.src = src;
            script.dataset.thestraSceneSrc = src;
            script.addEventListener('load', () => {
                script.dataset.loaded = 'true';
                resolve();
            }, { once: true });
            script.addEventListener('error', () => reject(new Error(`Failed to load ${src}`)), { once: true });
            document.head.appendChild(script);
        });
    }

    window.addEventListener('DOMContentLoaded', () => {
        window.ThestraEditorHost = {
            getPayload: () => dbPayload,
            getMapIndex: () => currentMapIndex
        };

        loadScript('/js/thestra-editor-scene.js')
            .then(() => loadScript('/js/second-rite-editor-adapter.js'))
            .then(() => loadScript('/js/thestra-editor-workspace.js'))
            .catch(error => console.error('Thestra Editor Scene bootstrap failed:', error));
    }, { once: true });
}());
