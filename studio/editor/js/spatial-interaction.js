(function (root, factory) {
    if (typeof module === 'object' && module.exports) module.exports = factory();
    else root.ThestraSpatialInteraction = factory();
}(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    // Authored/runtime space is Z-up while Three.js is Y-up. Keep that
    // backend permutation out of the interaction language: users author in
    // semantic X/Y/Z and Studio maps those constraints onto viewport axes.
    const SEMANTIC_TO_VIEWPORT_AXIS = Object.freeze({ X: 'X', Y: 'Z', Z: 'Y' });
    const VIEWPORT_TO_SEMANTIC_AXIS = Object.freeze({ X: 'X', Y: 'Z', Z: 'Y' });
    const SEMANTIC_AXIS_COLORS = Object.freeze({
        X: 0xff4d4f,
        Y: 0x42d66a,
        Z: 0x3d8cff
    });

    function normalizedAxis(axis) {
        const value = String(axis || '').toUpperCase();
        return Object.prototype.hasOwnProperty.call(SEMANTIC_TO_VIEWPORT_AXIS, value) ? value : null;
    }

    function semanticAxisToViewport(axis) {
        const value = normalizedAxis(axis);
        return value ? SEMANTIC_TO_VIEWPORT_AXIS[value] : null;
    }

    function viewportAxisToSemantic(axis) {
        const value = String(axis || '').toUpperCase();
        return Object.prototype.hasOwnProperty.call(VIEWPORT_TO_SEMANTIC_AXIS, value)
            ? VIEWPORT_TO_SEMANTIC_AXIS[value] : null;
    }

    function semanticAxisColor(axis) {
        const value = normalizedAxis(axis);
        return value ? SEMANTIC_AXIS_COLORS[value] : null;
    }

    function viewportAxisColorSources() {
        // createMoveGizmo assigns these sources to Three X/Y/Z respectively.
        // Three Y therefore receives semantic Z blue; Three Z receives
        // semantic Y green.
        return ['X', 'Z', 'Y'];
    }

    function editableTarget(event) {
        const target = event && event.target;
        const tag = target && String(target.tagName || '').toLowerCase();
        return !!(target && (target.isContentEditable
            || ['input', 'textarea', 'select'].includes(tag)));
    }

    function transformShortcut(event, viewportFocused, operation) {
        if (!viewportFocused || !event || event.metaKey || event.altKey || event.ctrlKey
                || editableTarget(event)) return null;
        if (!operation && event.code === 'KeyG') return { kind: 'begin-move' };
        if (operation === 'move') {
            if (['KeyX', 'KeyY', 'KeyZ'].includes(event.code)) {
                return { kind: 'constraint', axis: event.code.slice(3) };
            }
            if (event.code === 'Enter' || event.code === 'NumpadEnter') return { kind: 'confirm' };
            if (event.code === 'Escape') return { kind: 'cancel' };
        }
        return null;
    }

    const REASON_MESSAGES = Object.freeze({
        'profile-order': 'Cannot move this profile point past an adjacent profile point.',
        'profile-fixed-depth': 'Walk Profile depth X is fixed; move along authored Y or Z.',
        'profile-view-underdetermined': 'This view sees the Walk Profile edge-on; constrain to Y or Z, or orbit to reveal the profile plane.',
        'profile-axis-edge-on': 'That axis points into the current view; choose another axis or orbit the viewport.',
        'profile-endpoint': 'Walk Profile endpoints cannot be deleted.',
        'no-profile-segment-selected': 'Select a Walk Profile segment first.',
        'no-profile-point-selected': 'Select a Walk Profile point first.',
        'invalid-ground-profile': 'The Walk Profile contains invalid coordinates.',
        'invalid-profile-point': 'The Walk Profile point is invalid.',
        'invalid-profile-segment': 'The Walk Profile segment is invalid.',
        'missing-ground-profile': 'This lane has no authored Walk Profile.',
        'missing-bounded-lane': 'Walk Profile editing is only available for bounded lanes.'
    });

    function reasonMessage(reason) {
        if (!reason) return 'The spatial operation could not be completed.';
        return REASON_MESSAGES[reason] || String(reason).replace(/-/g, ' ');
    }

    function projectedAxisDelta(startPointer, currentPointer, axisPixels, minimumLength = 0.5) {
        if (!startPointer || !currentPointer || !axisPixels) return null;
        const ax = Number(axisPixels.x), ay = Number(axisPixels.y);
        const lengthSq = ax * ax + ay * ay;
        if (!Number.isFinite(lengthSq) || lengthSq < minimumLength * minimumLength) return null;
        const dx = Number(currentPointer.x) - Number(startPointer.x);
        const dy = Number(currentPointer.y) - Number(startPointer.y);
        if (![dx, dy].every(Number.isFinite)) return null;
        return (dx * ax + dy * ay) / lengthSq;
    }

    function cloneRecord(value) {
        if (value == null || typeof value !== 'object') return value;
        if (Array.isArray(value)) return value.map(cloneRecord);
        const copy = {};
        Object.keys(value).forEach(key => { copy[key] = cloneRecord(value[key]); });
        return copy;
    }

    function createTransaction(kind, selection, before, after) {
        if (!kind || !selection || before == null || after == null) return null;
        return Object.freeze({
            kind: String(kind),
            target: cloneRecord(selection),
            before: cloneRecord(before),
            after: cloneRecord(after)
        });
    }

    function cloneState(state) {
        return {
            hover: state.hover,
            selection: state.selection,
            operation: state.operation,
            constraint: state.constraint,
            value: state.value,
            feedback: state.feedback,
            revision: state.revision
        };
    }

    function createState(onChange) {
        const state = {
            hover: null,
            selection: null,
            operation: null,
            constraint: null,
            value: null,
            feedback: null,
            revision: 0
        };

        function emit() {
            state.revision += 1;
            const snapshot = cloneState(state);
            if (typeof onChange === 'function') onChange(snapshot);
            return snapshot;
        }

        return {
            snapshot: () => cloneState(state),
            setHover(hover) {
                if (state.hover === (hover || null)) return cloneState(state);
                state.hover = hover || null;
                return emit();
            },
            setSelection(selection) {
                state.selection = selection || null;
                state.feedback = null;
                return emit();
            },
            beginMove() {
                if (!state.selection) return null;
                state.operation = 'move';
                state.constraint = null;
                state.value = null;
                state.feedback = null;
                return emit();
            },
            constrain(axis) {
                if (state.operation !== 'move') return cloneState(state);
                const semantic = normalizedAxis(axis);
                if (!semantic) return cloneState(state);
                state.constraint = semantic;
                state.feedback = null;
                return emit();
            },
            setValue(value) {
                if (!state.operation) return cloneState(state);
                state.value = value;
                state.feedback = null;
                return emit();
            },
            reject(reason) {
                state.feedback = reasonMessage(reason);
                return emit();
            },
            confirm() {
                state.operation = null;
                state.constraint = null;
                state.value = null;
                state.feedback = null;
                return emit();
            },
            cancel() {
                state.operation = null;
                state.constraint = null;
                state.value = null;
                state.feedback = null;
                return emit();
            }
        };
    }

    return {
        SEMANTIC_TO_VIEWPORT_AXIS,
        VIEWPORT_TO_SEMANTIC_AXIS,
        SEMANTIC_AXIS_COLORS,
        semanticAxisToViewport,
        viewportAxisToSemantic,
        semanticAxisColor,
        viewportAxisColorSources,
        transformShortcut,
        reasonMessage,
        projectedAxisDelta,
        createTransaction,
        createState
    };
}));
