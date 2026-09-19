(function (root, factory) {
    if (typeof module === 'object' && module.exports) module.exports = factory();
    else root.ThestraStudioHistory = factory();
}(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    // History is deliberately semantic data only.  Renderer/DOM state has no
    // place here: the owning surface rebuilds its presentation from the
    // restored authored value after a successful replay.
    function clone(value) {
        if (value == null || typeof value !== 'object') return value;
        if (Array.isArray(value)) return value.map(clone);
        const copy = {};
        Object.keys(value).forEach(key => { copy[key] = clone(value[key]); });
        return copy;
    }

    function editableTarget(target) {
        const tag = target && String(target.tagName || '').toLowerCase();
        return !!(target && (target.isContentEditable
            || tag === 'input' || tag === 'textarea' || tag === 'select'));
    }

    function historyShortcut(event) {
        if (!event || event.defaultPrevented || editableTarget(event.target)) return null;
        if (!event.ctrlKey || event.metaKey || event.altKey || event.code !== 'KeyZ') return null;
        return event.shiftKey ? 'redo' : 'undo';
    }

    function validRecord(record) {
        return !!(record && record.authority && record.target
            && record.before !== undefined && record.after !== undefined);
    }

    function create(options) {
        options = options || {};
        const getAuthority = typeof options.getAuthority === 'function' ? options.getAuthority : () => null;
        const apply = typeof options.apply === 'function' ? options.apply : () => false;
        const limit = Number.isInteger(options.limit) && options.limit > 0 ? options.limit : 100;
        const undo = [];
        const redo = [];

        function clear() {
            undo.length = 0;
            redo.length = 0;
        }

        function commit(record) {
            if (!validRecord(record) || record.authority !== getAuthority()) return false;
            undo.push(clone(record));
            if (undo.length > limit) undo.splice(0, undo.length - limit);
            redo.length = 0;
            return true;
        }

        function replay(direction) {
            const from = direction === 'undo' ? undo : redo;
            const to = direction === 'undo' ? redo : undo;
            const record = from[from.length - 1];
            if (!record) return false;
            // A reload/project switch is a new authority. Never replay a
            // valid-looking transaction into a coincidentally shaped resource.
            if (record.authority !== getAuthority()) {
                clear();
                return false;
            }
            if (apply(clone(record), direction) !== true) return false;
            from.pop();
            to.push(record);
            return true;
        }

        return Object.freeze({
            clear,
            commit,
            undo: () => replay('undo'),
            redo: () => replay('redo'),
            snapshot: () => ({ undo: undo.map(clone), redo: redo.map(clone) }),
            handleKeydown(event) {
                const action = historyShortcut(event);
                if (!action || !this[action]()) return false;
                event.preventDefault();
                return true;
            }
        });
    }

    return { clone, editableTarget, historyShortcut, create };
}));
