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

// #277 PR2 bridge. Keep the neutral scene/project adapter independent from the
// renderer: Three reports semantic selections/actions here, and this host
// executes legal project writes or reuses existing inspectors/modals.
(function installThestraEditorSceneBootstrap() {
    if (typeof window === 'undefined' || typeof document === 'undefined') return;

    // event_presentation.js is loaded before map-editor.js. Hide the retired 2D
    // canvas synchronously here, before map-editor can paint its first frame and
    // before the asynchronous Three workspace bootstrap begins. The workspace
    // still keeps this element as its Map-tab/layout sentinel; it is never a
    // visible authoring surface anymore.
    const legacyMapCanvas = document.getElementById('map-canvas');
    if (legacyMapCanvas) legacyMapCanvas.style.visibility = 'hidden';

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
            getMapIndex: () => currentMapIndex,
            getEditingMode: () => editingMode,
            getMapInspection: () => typeof currentMapInspection === 'function' ? currentMapInspection() : null,

            markMapDirty() {
                setDirty(true);
                renderGridCells();
            },

            selectSemantic(selection) {
                const map = dbPayload.maps[currentMapIndex];
                if (!map || !selection) return;
                if (selection.kind === 'event') {
                    selectedEvent = (map.events || []).find((event, index) => String(event.id != null ? event.id : index) === String(selection.id)) || null;
                    renderGridCells();
                } else if (selection.kind === 'light') {
                    selectedLightObject = (map.lightObjects || [])[selection.index] || null;
                    refreshSelectedLampSettings();
                    renderGridCells();
                } else if (selection.kind === 'override') {
                    selectedOverride = (map.overrides || [])[selection.index] || null;
                    selectedOverrideIsPending = false;
                    refreshSelectedOverrideSettings();
                    renderGridCells();
                } else if (selection.kind === 'cell') {
                    if (editingMode === 'event') selectedEvent = null;
                    if (editingMode === 'light') {
                        selectedLightObject = null;
                        refreshSelectedLampSettings();
                    }
                    if (editingMode === 'override') {
                        selectedOverride = null;
                        selectedOverrideIsPending = false;
                        refreshSelectedOverrideSettings();
                    }
                    renderGridCells();
                }
            },

            paintCell(x, y) {
                const Commands = window.SecondRiteEditorCommands;
                const tile = Commands && Commands.tileForTool(activePaintTool);
                if (!Commands || !tile) return { ok: false, reason: 'unsupported-paint-tool' };
                const result = Commands.paintCell(dbPayload, currentMapIndex, x, y, tile);
                if (result.changed) {
                    setDirty(true);
                    renderGridCells();
                }
                return result;
            },

            canMoveEvent(eventId, x, y) {
                return window.SecondRiteEditorCommands.canMoveEvent(dbPayload, currentMapIndex, eventId, x, y);
            },

            moveEvent(eventId, x, y) {
                const result = window.SecondRiteEditorCommands.moveEvent(dbPayload, currentMapIndex, eventId, x, y);
                if (result.changed) {
                    selectedEvent = result.entity;
                    setDirty(true);
                    renderGridCells();
                }
                return result;
            },

            canMoveLight(lightIndex, x, y) {
                return window.SecondRiteEditorCommands.canMoveLight(dbPayload, currentMapIndex, lightIndex, x, y);
            },

            moveLight(lightIndex, x, y) {
                const result = window.SecondRiteEditorCommands.moveLight(dbPayload, currentMapIndex, lightIndex, x, y);
                if (result.changed) {
                    selectedLightObject = result.entity;
                    refreshSelectedLampSettings();
                    setDirty(true);
                    renderGridCells();
                }
                return result;
            },

            openAt(selection) {
                if (!selection || !selection.cell) return;
                const x = selection.cell.x, y = selection.cell.y;
                if (editingMode === 'event') openEventModal(x, y);
                else if (editingMode === 'light') selectOrCreateLightObjectAt(x, y);
                else if (editingMode === 'override') selectOrCreateOverrideAt(x, y);
            }
        };

        loadScript('/js/thestra-editor-scene.js')
            .then(() => loadScript('/js/second-rite-editor-commands.js'))
            .then(() => loadScript('/js/vertex-shading.js'))
            .then(() => loadScript('/js/second-rite-editor-adapter.js'))
            .then(() => loadScript('/js/thestra-workspace-state.js'))
            .then(() => loadScript('/js/thestra-editor-workspace.js'))
            .catch(error => console.error('Thestra Editor Scene bootstrap failed:', error));
    }, { once: true });
}());