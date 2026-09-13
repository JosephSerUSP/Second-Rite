(function (root, factory) {
    if (typeof module === 'object' && module.exports) module.exports = factory();
    else root.ThestraStudioHistory = factory();
}(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    function clone(value) {
        if (value == null || typeof value !== 'object') return value;
        if (Array.isArray(value)) return value.map(clone);
        const out = {};
        Object.keys(value).forEach(key => { out[key] = clone(value[key]); });
        return out;
    }

    function editableTarget(event) {
        const target = event && event.target;
        const tag = target && String(target.tagName || '').toLowerCase();
        return !!(target && (target.isContentEditable
            || ['input', 'textarea', 'select'].includes(tag)));
    }

    function historyShortcut(event) {
        if (!event || editableTarget(event) || event.altKey) return null;
        const primary = !!(event.ctrlKey || event.metaKey);
        if (!primary || event.code !== 'KeyZ') return null;
        return event.shiftKey ? 'redo' : 'undo';
    }

    function normalizeEntry(entry) {
        if (!entry || typeof entry !== 'object') return null;
        if (!entry.kind || !entry.target || entry.before == null || entry.after == null) return null;
        return Object.freeze({
            kind: String(entry.kind),
            target: clone(entry.target),
            before: clone(entry.before),
            after: clone(entry.after),
            label: entry.label ? String(entry.label) : String(entry.kind)
        });
    }

    function cloneProfile(profile) {
        return Array.isArray(profile)
            ? profile.map(point => ({ y: Number(point.y), z: Number(point.z) }))
            : null;
    }

    function normalizeWalkProfileTransaction(transaction, afterProfile, mapId) {
        if (!transaction) return null;
        if (transaction.kind === 'walk-profile') return normalizeEntry(transaction);
        const after = cloneProfile(afterProfile);
        if (!after) return null;
        let before = cloneProfile(after);

        if (transaction.kind === 'move') {
            if (Array.isArray(transaction.before?.points)) {
                for (const point of transaction.before.points) {
                    const index = Number(point.index);
                    if (!Number.isInteger(index) || !before[index]) return null;
                    before[index] = { y: Number(point.Y), z: Number(point.Z) };
                }
            } else {
                const index = Number(transaction.target?.index);
                if (!Number.isInteger(index) || !before[index]) return null;
                before[index] = {
                    y: Number(transaction.before?.Y),
                    z: Number(transaction.before?.Z)
                };
            }
            return normalizeEntry({
                kind: 'walk-profile',
                target: { mapId },
                before: { profile: before },
                after: { profile: after },
                label: 'Move Walk Profile'
            });
        }

        if (transaction.kind === 'extrude') {
            const index = Number(transaction.target?.index);
            if (!Number.isInteger(index) || after.length < 3) return null;
            before = index === 0 ? after.slice(1) : after.slice(0, -1);
            return normalizeEntry({
                kind: 'walk-profile',
                target: { mapId },
                before: { profile: before },
                after: { profile: after },
                label: 'Extrude Walk Profile'
            });
        }
        return null;
    }

    function createHistory(options = {}) {
        const limit = Number.isInteger(options.limit) && options.limit > 0 ? options.limit : 100;
        const past = [];
        const future = [];

        function snapshot() {
            return {
                undoCount: past.length,
                redoCount: future.length,
                undoLabel: past.length ? past[past.length - 1].label : null,
                redoLabel: future.length ? future[future.length - 1].label : null
            };
        }

        function emit() {
            const state = snapshot();
            if (typeof options.onChange === 'function') options.onChange(state);
            return state;
        }

        return {
            snapshot,
            clear() {
                past.length = 0;
                future.length = 0;
                return emit();
            },
            commit(entry) {
                const normalized = normalizeEntry(entry);
                if (!normalized) return null;
                past.push(normalized);
                if (past.length > limit) past.splice(0, past.length - limit);
                future.length = 0;
                emit();
                return normalized;
            },
            async undo(apply) {
                if (!past.length || typeof apply !== 'function') return null;
                const entry = past[past.length - 1];
                const result = await apply(entry, 'before');
                if (result === false || result?.ok === false) return null;
                past.pop();
                future.push(entry);
                emit();
                return entry;
            },
            async redo(apply) {
                if (!future.length || typeof apply !== 'function') return null;
                const entry = future[future.length - 1];
                const result = await apply(entry, 'after');
                if (result === false || result?.ok === false) return null;
                future.pop();
                past.push(entry);
                emit();
                return entry;
            }
        };
    }

    return { createHistory, historyShortcut, normalizeWalkProfileTransaction };
}));
