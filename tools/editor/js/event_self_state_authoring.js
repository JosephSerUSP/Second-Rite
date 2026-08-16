(function (root, factory) {
    const api = factory();
    if (typeof module !== 'undefined' && module.exports) module.exports = api;
    if (root) root.EventSelfStateAuthoring = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';

    function createInstanceId(randomUUID) {
        const uuid = randomUUID || (globalThis.crypto && globalThis.crypto.randomUUID
            ? globalThis.crypto.randomUUID.bind(globalThis.crypto) : null);
        if (typeof uuid !== 'function') {
            throw new Error('Stable Event identity requires crypto.randomUUID(); refusing numeric-id fallback');
        }
        const value = String(uuid());
        if (!value) throw new Error('Stable Event identity generator returned an empty value');
        return 'event:' + value;
    }

    function ensureInstanceId(eventData, randomUUID) {
        if (eventData && typeof eventData.instanceId === 'string' && eventData.instanceId.trim()) {
            return eventData.instanceId;
        }
        return createInstanceId(randomUUID);
    }

    function assignFreshInstanceId(eventData, randomUUID) {
        if (!eventData || typeof eventData !== 'object') {
            throw new Error('Fresh Event identity requires a placed Event object');
        }
        eventData.instanceId = createInstanceId(randomUUID);
        return eventData.instanceId;
    }

    function parseTypedLiteral(kind, raw) {
        if (kind === 'number') {
            const value = Number(raw);
            if (!Number.isFinite(value)) throw new Error('SELF Variable condition needs a finite number');
            return value;
        }
        if (kind === 'boolean') return String(raw) === 'true';
        return String(raw == null ? '' : raw);
    }

    function serializePageConditions(form) {
        form = form || {};
        const out = {};
        if (form.switchEnabled) {
            const name = String(form.switchName || '').trim();
            if (!name) throw new Error('SELF Switch condition needs a name');
            out.switch = { name, value: form.switchValue !== false };
        }
        if (form.variableEnabled) {
            const name = String(form.variableName || '').trim();
            if (!name) throw new Error('SELF Variable condition needs a name');
            const operator = form.variableOperator || '==';
            const allowed = new Set(['==', '!=', '>', '>=', '<', '<=', 'is_set', 'is_unset']);
            if (!allowed.has(operator)) throw new Error('Unsupported SELF Variable condition operator: ' + operator);
            out.variable = { name, operator };
            if (operator !== 'is_set' && operator !== 'is_unset') {
                const type = form.variableType || 'number';
                if (['>', '>=', '<', '<='].includes(operator) && type !== 'number') {
                    throw new Error('Relational SELF Variable conditions require a Number value');
                }
                out.variable.value = parseTypedLiteral(type, form.variableValue);
            }
        }
        return Object.keys(out).length ? out : undefined;
    }

    function literalType(value) {
        if (typeof value === 'boolean') return 'boolean';
        if (typeof value === 'number') return 'number';
        return 'string';
    }

    function pageFormState(spec) {
        spec = spec || {};
        const sw = spec.switch || {};
        const variable = spec.variable || {};
        const op = variable.operator || '==';
        return {
            switchEnabled: !!spec.switch,
            switchName: sw.name || '',
            switchValue: sw.value !== false,
            variableEnabled: !!spec.variable,
            variableName: variable.name || '',
            variableOperator: op,
            variableType: literalType(variable.value),
            variableValue: variable.value == null ? '' : String(variable.value),
        };
    }

    function summarize(spec) {
        if (!spec) return '';
        const parts = [];
        if (spec.switch) {
            parts.push('SELF ' + (spec.switch.name || '?') + '=' + (spec.switch.value === false ? 'OFF' : 'ON'));
        }
        if (spec.variable) {
            const op = spec.variable.operator || '==';
            if (op === 'is_set' || op === 'is_unset') {
                parts.push('SELF ' + (spec.variable.name || '?') + ' ' + op.replace('_', ' '));
            } else {
                parts.push('SELF ' + (spec.variable.name || '?') + ' ' + op + ' ' + JSON.stringify(spec.variable.value));
            }
        }
        return parts.join(' & ');
    }

    return {
        createInstanceId,
        ensureInstanceId,
        assignFreshInstanceId,
        parseTypedLiteral,
        serializePageConditions,
        pageFormState,
        summarize,
    };
});
