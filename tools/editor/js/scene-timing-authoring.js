(function (root, factory) {
    'use strict';
    const api = factory();
    if (typeof module !== 'undefined' && module.exports) module.exports = api;
    if (root) root.ThestraSceneTimingAuthoring = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
    'use strict';

    // The runtime deliberately has no default for fixed update.step. Studio
    // needs a concrete initial value when the author explicitly turns fixed
    // timing on, so this is an authoring seed only — not a runtime fallback.
    const AUTHORING_STEP_SEED = 1 / 60;
    const DEFAULT_MAX_CATCH_UP = 8;
    const MAX_CATCH_UP = 120;
    const TIMING_KEYS = new Set(['mode', 'step', 'maxCatchUp']);

    function own(value, key) {
        return !!value && Object.prototype.hasOwnProperty.call(value, key);
    }

    function updateObject(scene) {
        const update = scene && scene.update;
        return update && typeof update === 'object' && !Array.isArray(update) ? update : null;
    }

    function fixedUpdate(scene) {
        const update = updateObject(scene);
        return update && update.mode === 'fixed' ? update : null;
    }

    function number(value, label) {
        const parsed = typeof value === 'number' ? value : Number(value);
        if (!Number.isFinite(parsed)) throw new Error(`${label} must be a finite number`);
        return parsed;
    }

    function snapshot(scene) {
        const update = updateObject(scene);
        const fixed = fixedUpdate(scene);
        return {
            mode: fixed ? 'fixed' : 'legacy',
            authored: scene != null && own(scene, 'update'),
            step: fixed && own(fixed, 'step') ? fixed.step : AUTHORING_STEP_SEED,
            maxCatchUp: fixed && own(fixed, 'maxCatchUp') ? fixed.maxCatchUp : DEFAULT_MAX_CATCH_UP
        };
    }

    function validateUpdate(update) {
        if (update == null) return [];
        if (typeof update !== 'object' || Array.isArray(update)) {
            return ['Scene update must be an object when authored'];
        }
        if (update.mode !== 'fixed') {
            return ['Scene update.mode must be "fixed"; omit update for legacy/default timing'];
        }
        const errors = [];
        const step = Number(update.step);
        if (!own(update, 'step') || !Number.isFinite(step) || step <= 0) {
            errors.push('Scene fixed update.step must be a finite positive number of seconds');
        }
        const maxCatchUp = Number(update.maxCatchUp);
        if (own(update, 'maxCatchUp')
            && (!Number.isInteger(maxCatchUp) || maxCatchUp < 1 || maxCatchUp > MAX_CATCH_UP)) {
            errors.push(`Scene fixed update.maxCatchUp must be an integer from 1 to ${MAX_CATCH_UP}`);
        }
        return errors;
    }

    function validateScene(scene) {
        return validateUpdate(scene && scene.update);
    }

    function unknownUpdateKeys(update) {
        return updateObject({ update })
            ? Object.keys(update).filter(key => !TIMING_KEYS.has(key))
            : [];
    }

    function setMode(scene, mode) {
        if (!scene || typeof scene !== 'object') {
            throw new Error('Scene timing authoring requires a Scene object');
        }
        if (mode === 'legacy') {
            if (!own(scene, 'update')) return null;
            const update = updateObject(scene);
            if (!update) {
                throw new Error('Cannot switch to legacy/default while Scene update is not an object');
            }
            const unknown = unknownUpdateKeys(update);
            if (unknown.length > 0) {
                throw new Error('Cannot switch to legacy/default without discarding unknown Scene update fields: '
                    + unknown.join(', '));
            }
            delete scene.update;
            return null;
        }
        if (mode !== 'fixed') throw new Error(`Unknown Scene timing mode: ${mode}`);

        if (own(scene, 'update') && !updateObject(scene)) {
            throw new Error('Scene update must be an object before fixed timing can be enabled');
        }
        const update = Object.assign({}, updateObject(scene) || {});
        update.mode = 'fixed';
        if (!own(update, 'step')) update.step = AUTHORING_STEP_SEED;
        if (!own(update, 'maxCatchUp')) update.maxCatchUp = DEFAULT_MAX_CATCH_UP;
        const errors = validateUpdate(update);
        if (errors.length) throw new Error(errors[0]);
        scene.update = update;
        return update;
    }

    function requireFixed(scene) {
        const update = fixedUpdate(scene);
        if (!update) throw new Error('Scene fixed timing must be enabled before editing fixed timing fields');
        return update;
    }

    function setStep(scene, value) {
        const parsed = number(value, 'Scene fixed update.step');
        if (parsed <= 0) {
            throw new Error('Scene fixed update.step must be a finite positive number of seconds');
        }
        requireFixed(scene).step = parsed;
        return parsed;
    }

    function setMaxCatchUp(scene, value) {
        const parsed = number(value, 'Scene fixed update.maxCatchUp');
        if (!Number.isInteger(parsed) || parsed < 1 || parsed > MAX_CATCH_UP) {
            throw new Error(`Scene fixed update.maxCatchUp must be an integer from 1 to ${MAX_CATCH_UP}`);
        }
        requireFixed(scene).maxCatchUp = parsed;
        return parsed;
    }

    return Object.freeze({
        AUTHORING_STEP_SEED,
        DEFAULT_MAX_CATCH_UP,
        MAX_CATCH_UP,
        fixedUpdate,
        snapshot,
        validateUpdate,
        validateScene,
        unknownUpdateKeys,
        setMode,
        setStep,
        setMaxCatchUp
    });
}));
