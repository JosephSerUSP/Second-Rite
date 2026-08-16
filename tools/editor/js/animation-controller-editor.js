(function (root, factory) {
    if (typeof define === 'function' && define.amd) {
        define([], factory);
    } else if (typeof module === 'object' && module.exports) {
        module.exports = factory();
    } else {
        root.AnimationControllerEditor = factory();
    }
}(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    const SUPPORTED_FACTS = new Set([
        'event.moving',
        'event.interacting',
        'event.enabled',
        'animation.finished'
    ]);

    function conditionBase(value) {
        const raw = String(value || '');
        return raw.startsWith('not ') ? raw.slice(4) : raw;
    }

    function validCondition(value) {
        const base = conditionBase(value);
        return SUPPORTED_FACTS.has(base) || /^signal\.[A-Za-z0-9_.-]+$/.test(base);
    }

    function validateController(definition) {
        const errors = [];
        if (!definition || Array.isArray(definition) || typeof definition !== 'object') {
            return ['Controller must be an object.'];
        }
        if (!definition.initial || typeof definition.initial !== 'string') {
            errors.push('Initial state is required.');
        }
        const states = definition.states;
        if (!states || Array.isArray(states) || typeof states !== 'object' || !Object.keys(states).length) {
            errors.push('At least one state is required.');
        } else {
            if (definition.initial && !states[definition.initial]) {
                errors.push(`Initial state '${definition.initial}' is not declared.`);
            }
            Object.entries(states).forEach(([id, state]) => {
                if (!id) errors.push('State ids must be non-empty.');
                if (!state || typeof state !== 'object' || Array.isArray(state)) {
                    errors.push(`State '${id}' must be an object.`);
                } else if (!state.animation || typeof state.animation !== 'string') {
                    errors.push(`State '${id}' requires a semantic animation.`);
                }
            });
        }
        (definition.transitions || []).forEach((transition, index) => {
            const label = `Transition ${index + 1}`;
            const from = transition && (transition.from || '*');
            if (from !== '*' && (!states || !states[from])) errors.push(`${label} has unknown from state '${from}'.`);
            if (!transition || !transition.to || !states || !states[transition.to]) {
                errors.push(`${label} has unknown to state '${transition && transition.to}'.`);
            }
            if (!transition || !validCondition(transition.when)) {
                errors.push(`${label} has unsupported condition '${transition && transition.when}'.`);
            }
        });
        return errors;
    }

    function createPreview(definition) {
        const errors = validateController(definition);
        if (errors.length) throw new Error(errors.join('\n'));
        return {
            state: definition.initial,
            elapsed: 0,
            signals: Object.create(null),
            animationFinished: false
        };
    }

    function positiveSignal(condition) {
        return !String(condition || '').startsWith('not ') && /^signal\./.test(String(condition || ''));
    }

    function factValue(instance, condition, facts) {
        let raw = String(condition || '');
        let negate = false;
        if (raw.startsWith('not ')) {
            negate = true;
            raw = raw.slice(4);
        }
        facts = facts || {};
        let value = false;
        if (raw === 'event.moving') value = !!(facts.event && facts.event.moving);
        else if (raw === 'event.interacting') value = !!(facts.event && facts.event.interacting);
        else if (raw === 'event.enabled') value = !facts.event || facts.event.enabled !== false;
        else if (raw === 'animation.finished') value = !!instance.animationFinished;
        else if (raw.startsWith('signal.')) value = !!instance.signals[raw.slice(7)];
        return negate ? !value : value;
    }

    function tryTransitions(instance, definition, facts, signalsOnly) {
        for (const transition of definition.transitions || []) {
            if (positiveSignal(transition.when) !== signalsOnly) continue;
            const from = transition.from || '*';
            if (from !== '*' && from !== instance.state) continue;
            if (!factValue(instance, transition.when, facts)) continue;
            if (positiveSignal(transition.when)) delete instance.signals[String(transition.when).slice(7)];
            instance.state = transition.to;
            instance.elapsed = 0;
            instance.animationFinished = false;
            return true;
        }
        return false;
    }

    function stepPreview(instance, definition, dt, facts) {
        if (!instance) throw new Error('Preview instance required.');
        if (typeof dt !== 'number' || dt < 0) throw new Error('Preview dt must be non-negative.');
        const errors = validateController(definition);
        if (errors.length) throw new Error(errors.join('\n'));
        instance.elapsed += dt;
        const changed = tryTransitions(instance, definition, facts, true)
            || tryTransitions(instance, definition, facts, false);
        if (!changed) instance.animationFinished = false;
        return snapshotPreview(instance, definition);
    }

    function signalPreview(instance, name) {
        if (!instance || !/^[A-Za-z0-9_.-]+$/.test(String(name || ''))) {
            throw new Error('Signal name must be a semantic identifier.');
        }
        instance.signals[name] = true;
    }

    function completePreview(instance) {
        if (!instance) throw new Error('Preview instance required.');
        instance.animationFinished = true;
    }

    function snapshotPreview(instance, definition) {
        const state = definition.states[instance.state];
        return {
            state: instance.state,
            animation: state.animation,
            loop: state.loop !== false,
            elapsed: instance.elapsed
        };
    }

    const api = {
        validateController,
        createPreview,
        stepPreview,
        signalPreview,
        completePreview,
        snapshotPreview
    };

    if (typeof window === 'undefined' || typeof document === 'undefined') return api;

    let modeSelect = null;
    let idSelect = null;
    let editButton = null;
    let previewLabel = null;
    let installed = false;
    let editingOriginalId = null;
    let previewInstance = null;

    function registry() {
        if (typeof dbPayload === 'undefined') return {};
        if (!dbPayload.animationControllers || typeof dbPayload.animationControllers !== 'object') {
            dbPayload.animationControllers = {};
        }
        return dbPayload.animationControllers;
    }

    function markDirty() {
        try { eventModalDirty = true; } catch (_) {}
        try { setDirty(true); } catch (_) {}
    }

    function selectedId() {
        return idSelect && idSelect.value ? idSelect.value : '';
    }

    function refreshPicker(selected) {
        if (!idSelect) return;
        const wanted = selected !== undefined ? selected : idSelect.value;
        idSelect.innerHTML = '';
        const none = document.createElement('option');
        none.value = '';
        none.textContent = '(choose controller)';
        idSelect.appendChild(none);
        Object.keys(registry()).sort().forEach(id => {
            const option = document.createElement('option');
            option.value = id;
            option.textContent = id;
            idSelect.appendChild(option);
        });
        if (wanted && Object.prototype.hasOwnProperty.call(registry(), wanted)) idSelect.value = wanted;
        updatePickerEnabled();
    }

    function updatePickerEnabled() {
        if (!modeSelect || !idSelect) return;
        const override = modeSelect.value === 'override';
        idSelect.disabled = !override;
        if (editButton) editButton.disabled = !override || !selectedId();
        if (previewLabel) {
            if (modeSelect.value === 'inherit') previewLabel.textContent = 'inherits presentation controller';
            else if (modeSelect.value === 'suppress') previewLabel.textContent = 'controller suppressed';
            else previewLabel.textContent = selectedId() || 'choose a controller';
        }
    }

    api.getEventFieldState = function () {
        if (!modeSelect) return { mode: 'inherit', value: undefined };
        const mode = modeSelect.value;
        if (mode === 'suppress') return { mode, value: false };
        if (mode === 'override') return { mode, value: selectedId() || undefined };
        return { mode: 'inherit', value: undefined };
    };

    api.setEventField = function (raw) {
        if (!modeSelect || !idSelect) return;
        if (raw === false) {
            modeSelect.value = 'suppress';
            refreshPicker('');
        } else if (typeof raw === 'string' && raw) {
            modeSelect.value = 'override';
            refreshPicker(raw);
        } else {
            modeSelect.value = 'inherit';
            refreshPicker('');
        }
        updatePickerEnabled();
    };

    api.refreshEventControllerOptions = refreshPicker;

    function makeButton(text, fn) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'win98-btn';
        button.style.fontSize = '10px';
        button.textContent = text;
        button.onclick = fn;
        return button;
    }

    function installPicker() {
        if (document.getElementById('event-prop-controller-mode')) {
            modeSelect = document.getElementById('event-prop-controller-mode');
            idSelect = document.getElementById('event-prop-controller-id');
            return;
        }
        const focus = document.getElementById('event-prop-focus-mode');
        const fieldset = focus && focus.closest('fieldset');
        if (!fieldset) return;

        const divider = document.createElement('div');
        divider.style.cssText = 'border-top:1px solid #999; margin:5px 0 4px; padding-top:4px;';
        const title = document.createElement('div');
        title.textContent = 'Animation Controller';
        title.style.cssText = 'font-size:10px; font-weight:bold; margin-bottom:3px;';
        divider.appendChild(title);

        const row = document.createElement('div');
        row.style.cssText = 'display:flex; gap:4px; align-items:center;';
        modeSelect = document.createElement('select');
        modeSelect.id = 'event-prop-controller-mode';
        modeSelect.className = 'win98-select';
        modeSelect.style.cssText = 'font-size:10px; width:82px;';
        [['inherit', 'Inherit'], ['override', 'Use'], ['suppress', 'Suppress']].forEach(([value, label]) => {
            const option = document.createElement('option');
            option.value = value;
            option.textContent = label;
            modeSelect.appendChild(option);
        });
        idSelect = document.createElement('select');
        idSelect.id = 'event-prop-controller-id';
        idSelect.className = 'win98-select';
        idSelect.style.cssText = 'font-size:10px; flex:1; min-width:90px;';
        editButton = makeButton('Edit…', () => openEditor(selectedId()));
        const newButton = makeButton('New…', () => openEditor(null));
        row.append(modeSelect, idSelect, editButton, newButton);
        divider.appendChild(row);
        previewLabel = document.createElement('div');
        previewLabel.id = 'event-controller-summary';
        previewLabel.style.cssText = 'font-size:9px; color:#555; margin-top:2px;';
        divider.appendChild(previewLabel);
        fieldset.appendChild(divider);

        modeSelect.onchange = () => { updatePickerEnabled(); markDirty(); };
        idSelect.onchange = () => { updatePickerEnabled(); markDirty(); };
        refreshPicker('');
        api.setEventField(undefined);
    }

    function ensureModal() {
        let modal = document.getElementById('animation-controller-modal');
        if (modal) return modal;
        modal = document.createElement('div');
        modal.id = 'animation-controller-modal';
        modal.className = 'modal-overlay';
        modal.style.zIndex = '1450';
        modal.innerHTML = `
          <div class="window outset-bevel" style="width:760px; max-height:88vh; display:flex; flex-direction:column;">
            <div class="title-bar"><div class="title-bar-text">Animation Controller</div>
              <div class="title-bar-controls"><button type="button" class="win-btn-small outset-bevel" id="ac-close">×</button></div>
            </div>
            <div class="window-body" style="padding:7px; overflow:auto; display:flex; flex-direction:column; gap:7px;">
              <div style="display:grid; grid-template-columns:90px 1fr 90px 1fr; gap:4px; align-items:center; font-size:10px;">
                <label>Controller ID</label><input id="ac-id" class="win98-input" />
                <label>Initial state</label><select id="ac-initial" class="win98-select"></select>
              </div>
              <fieldset style="margin:0; padding:5px;"><legend>States</legend>
                <div id="ac-states" style="display:flex; flex-direction:column; gap:3px;"></div>
                <button type="button" class="win98-btn" id="ac-add-state" style="margin-top:4px; font-size:10px;">+ State</button>
              </fieldset>
              <fieldset style="margin:0; padding:5px;"><legend>Transitions</legend>
                <div style="font-size:9px; color:#555; margin-bottom:3px;">Facts: event.moving, event.interacting, event.enabled, animation.finished, signal.&lt;name&gt; · prefix with “not ” to negate.</div>
                <div id="ac-transitions" style="display:flex; flex-direction:column; gap:3px;"></div>
                <button type="button" class="win98-btn" id="ac-add-transition" style="margin-top:4px; font-size:10px;">+ Transition</button>
              </fieldset>
              <fieldset style="margin:0; padding:5px;"><legend>Deterministic Preview</legend>
                <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap; font-size:10px;">
                  <label><input id="ac-preview-moving" type="checkbox" /> Event moving</label>
                  <input id="ac-preview-signal" class="win98-input" value="interact" style="width:100px;" />
                  <button type="button" class="win98-btn" id="ac-preview-send">Send signal</button>
                  <button type="button" class="win98-btn" id="ac-preview-finish">Animation finished</button>
                  <button type="button" class="win98-btn" id="ac-preview-step">Step 1/60 s</button>
                  <button type="button" class="win98-btn" id="ac-preview-reset">Reset</button>
                </div>
                <div id="ac-preview-status" style="margin-top:5px; padding:4px; background:#fff; border:1px inset #999; font-family:monospace; font-size:10px;"></div>
              </fieldset>
              <div id="ac-errors" style="font-size:10px; color:#800000; white-space:pre-wrap;"></div>
              <div style="display:flex; justify-content:flex-end; gap:6px;">
                <button type="button" class="win98-btn win98-btn-success" id="ac-save">Save Controller</button>
                <button type="button" class="win98-btn" id="ac-cancel">Cancel</button>
              </div>
            </div>
          </div>`;
        document.body.appendChild(modal);
        modal.querySelector('#ac-close').onclick = closeEditor;
        modal.querySelector('#ac-cancel').onclick = closeEditor;
        modal.querySelector('#ac-add-state').onclick = () => addStateRow({ id: 'state', animation: 'idle', loop: true });
        modal.querySelector('#ac-add-transition').onclick = () => addTransitionRow({ from: '*', to: '', when: 'event.moving' });
        modal.querySelector('#ac-save').onclick = saveEditor;
        modal.querySelector('#ac-preview-reset').onclick = resetPreview;
        modal.querySelector('#ac-preview-step').onclick = () => stepEditorPreview(1 / 60);
        modal.querySelector('#ac-preview-moving').onchange = () => stepEditorPreview(0);
        modal.querySelector('#ac-preview-send').onclick = () => {
            try {
                ensurePreview();
                signalPreview(previewInstance, modal.querySelector('#ac-preview-signal').value.trim());
                stepEditorPreview(0);
            } catch (error) { showErrors([error.message]); }
        };
        modal.querySelector('#ac-preview-finish').onclick = () => {
            try {
                ensurePreview();
                completePreview(previewInstance);
                stepEditorPreview(0);
            } catch (error) { showErrors([error.message]); }
        };
        return modal;
    }

    function stateRows() {
        return Array.from(document.querySelectorAll('#ac-states .ac-state-row'));
    }

    function transitionRows() {
        return Array.from(document.querySelectorAll('#ac-transitions .ac-transition-row'));
    }

    function refreshInitialOptions(wanted) {
        const select = document.getElementById('ac-initial');
        if (!select) return;
        const previous = wanted !== undefined ? wanted : select.value;
        select.innerHTML = '';
        stateRows().forEach(row => {
            const id = row.querySelector('.ac-state-id').value.trim();
            if (!id) return;
            const option = document.createElement('option');
            option.value = id;
            option.textContent = id;
            select.appendChild(option);
        });
        if (previous && Array.from(select.options).some(option => option.value === previous)) select.value = previous;
    }

    function addStateRow(state) {
        const container = document.getElementById('ac-states');
        const row = document.createElement('div');
        row.className = 'ac-state-row';
        row.style.cssText = 'display:grid; grid-template-columns:120px 1fr 72px 28px; gap:4px; align-items:center; font-size:10px; padding:2px;';
        row.innerHTML = `<input class="win98-input ac-state-id" placeholder="state id" />
          <input class="win98-input ac-state-animation" placeholder="semantic animation" />
          <label><input class="ac-state-loop" type="checkbox" /> loop</label>
          <button type="button" class="win98-btn ac-state-delete">×</button>`;
        row.querySelector('.ac-state-id').value = state.id || '';
        row.querySelector('.ac-state-animation').value = state.animation || '';
        row.querySelector('.ac-state-loop').checked = state.loop !== false;
        row.querySelector('.ac-state-id').oninput = () => { refreshInitialOptions(); resetPreview(); };
        row.querySelector('.ac-state-animation').oninput = resetPreview;
        row.querySelector('.ac-state-loop').onchange = resetPreview;
        row.querySelector('.ac-state-delete').onclick = () => { row.remove(); refreshInitialOptions(); resetPreview(); };
        container.appendChild(row);
        refreshInitialOptions();
    }

    function addTransitionRow(transition) {
        const container = document.getElementById('ac-transitions');
        const row = document.createElement('div');
        row.className = 'ac-transition-row';
        row.style.cssText = 'display:grid; grid-template-columns:110px 110px 1fr 28px; gap:4px; align-items:center; font-size:10px;';
        row.innerHTML = `<input class="win98-input ac-transition-from" placeholder="from or *" />
          <input class="win98-input ac-transition-to" placeholder="to" />
          <input class="win98-input ac-transition-when" placeholder="event.moving / signal.wave" />
          <button type="button" class="win98-btn ac-transition-delete">×</button>`;
        row.querySelector('.ac-transition-from').value = transition.from || '*';
        row.querySelector('.ac-transition-to').value = transition.to || '';
        row.querySelector('.ac-transition-when').value = transition.when || '';
        row.querySelectorAll('input').forEach(input => { input.oninput = resetPreview; });
        row.querySelector('.ac-transition-delete').onclick = () => { row.remove(); resetPreview(); };
        container.appendChild(row);
    }

    function definitionFromForm() {
        const states = {};
        stateRows().forEach(row => {
            const id = row.querySelector('.ac-state-id').value.trim();
            if (!id) return;
            states[id] = {
                animation: row.querySelector('.ac-state-animation').value.trim(),
                loop: row.querySelector('.ac-state-loop').checked
            };
        });
        return {
            id: document.getElementById('ac-id').value.trim(),
            initial: document.getElementById('ac-initial').value,
            states,
            transitions: transitionRows().map(row => ({
                from: row.querySelector('.ac-transition-from').value.trim() || '*',
                to: row.querySelector('.ac-transition-to').value.trim(),
                when: row.querySelector('.ac-transition-when').value.trim()
            }))
        };
    }

    function showErrors(errors) {
        const box = document.getElementById('ac-errors');
        if (box) box.textContent = errors.length ? errors.join('\n') : '';
    }

    function highlightPreview(stateId) {
        stateRows().forEach(row => {
            row.style.background = row.querySelector('.ac-state-id').value.trim() === stateId ? '#d8e6ff' : '';
        });
    }

    function ensurePreview() {
        if (previewInstance) return;
        previewInstance = createPreview(definitionFromForm());
    }

    function stepEditorPreview(dt) {
        try {
            const definition = definitionFromForm();
            const errors = validateController(definition);
            if (errors.length) { showErrors(errors); return; }
            ensurePreview();
            const snap = stepPreview(previewInstance, definition, dt, {
                event: {
                    moving: document.getElementById('ac-preview-moving').checked,
                    interacting: false,
                    enabled: true
                }
            });
            document.getElementById('ac-preview-status').textContent =
                `state=${snap.state}  animation=${snap.animation}  loop=${snap.loop}  t=${snap.elapsed.toFixed(3)}s`;
            highlightPreview(snap.state);
            showErrors([]);
        } catch (error) { showErrors([error.message]); }
    }

    function resetPreview() {
        previewInstance = null;
        try {
            ensurePreview();
            const snap = snapshotPreview(previewInstance, definitionFromForm());
            const status = document.getElementById('ac-preview-status');
            if (status) status.textContent = `state=${snap.state}  animation=${snap.animation}  loop=${snap.loop}  t=0.000s`;
            highlightPreview(snap.state);
            showErrors([]);
        } catch (error) {
            const status = document.getElementById('ac-preview-status');
            if (status) status.textContent = 'Fix controller errors to preview.';
            showErrors([error.message]);
        }
    }

    function openEditor(controllerId) {
        const modal = ensureModal();
        editingOriginalId = controllerId || null;
        const existing = controllerId && registry()[controllerId];
        const definition = existing ? JSON.parse(JSON.stringify(existing)) : {
            id: '',
            initial: 'idle',
            states: { idle: { animation: 'idle', loop: true }, move: { animation: 'walk', loop: true } },
            transitions: [
                { from: 'idle', to: 'move', when: 'event.moving' },
                { from: 'move', to: 'idle', when: 'not event.moving' }
            ]
        };
        document.getElementById('ac-id').value = definition.id || controllerId || '';
        document.getElementById('ac-states').innerHTML = '';
        Object.entries(definition.states || {}).forEach(([id, state]) => addStateRow(Object.assign({ id }, state)));
        refreshInitialOptions(definition.initial);
        document.getElementById('ac-transitions').innerHTML = '';
        (definition.transitions || []).forEach(addTransitionRow);
        modal.classList.add('active');
        resetPreview();
    }

    function closeEditor() {
        const modal = document.getElementById('animation-controller-modal');
        if (modal) modal.classList.remove('active');
        previewInstance = null;
        editingOriginalId = null;
    }

    function saveEditor() {
        const definition = definitionFromForm();
        const errors = validateController(definition);
        if (!definition.id || !/^[A-Za-z0-9_.-]+$/.test(definition.id)) {
            errors.unshift('Controller ID must be a semantic identifier.');
        }
        const existing = registry()[definition.id];
        if (existing && definition.id !== editingOriginalId) errors.unshift(`Controller '${definition.id}' already exists.`);
        if (errors.length) { showErrors(errors); return; }
        if (editingOriginalId && editingOriginalId !== definition.id) delete registry()[editingOriginalId];
        registry()[definition.id] = JSON.parse(JSON.stringify(definition));
        markDirty();
        refreshPicker(definition.id);
        modeSelect.value = 'override';
        updatePickerEnabled();
        closeEditor();
    }

    api.open = openEditor;

    function installIntegration() {
        if (installed) return;
        installPicker();
        if (!modeSelect) return;
        installed = true;

        // Extend the existing Event/Page serialization surface without creating
        // a second editor model. Page commits already pass through this helper,
        // so absent/override/suppress semantics stay identical to model/focus.
        const presentation = window.EventPresentation;
        if (presentation && !presentation._animationControllerIntegrated) {
            const baseSerialize = presentation.serializeEventPresentation;
            presentation.serializeEventPresentation = function (formState, target) {
                const controllerState = api.getEventFieldState();
                return baseSerialize(Object.assign({}, formState, {
                    controllerMode: controllerState.mode,
                    controllerValue: controllerState.value
                }), target);
            };
            presentation._animationControllerIntegrated = true;
        }

        // Event Pages already route all presentation fields through this setter.
        // Decorate it so selecting Base/Page also swaps the controller controls.
        if (typeof window.setPresentationFormUI === 'function' && !window.setPresentationFormUI._animationControllerIntegrated) {
            const baseSet = window.setPresentationFormUI;
            const wrapped = function (target) {
                baseSet(target);
                api.setEventField(target && target.animationController);
            };
            wrapped._animationControllerIntegrated = true;
            window.setPresentationFormUI = wrapped;
        }

        // Base Event Apply historically copies explicit presentation fields out
        // of its working stash one-by-one. Persist this third field after that
        // operation while Pages continue using the ordinary serializer above.
        if (typeof window.applyEventProperties === 'function' && !window.applyEventProperties._animationControllerIntegrated) {
            const baseApply = window.applyEventProperties;
            const wrapped = function () {
                const title = document.getElementById('event-modal-title');
                const match = title && title.textContent.match(/ID:\s*(\d+)/);
                const id = match ? Number(match[1]) : null;
                const state = api.getEventFieldState();
                const result = baseApply();
                try {
                    const map = dbPayload.maps[currentMapIndex];
                    const event = map && (map.events || []).find(candidate => Number(candidate.id) === id);
                    if (event) {
                        if (state.mode === 'suppress') event.animationController = false;
                        else if (state.mode === 'override' && state.value) event.animationController = state.value;
                        else delete event.animationController;
                    }
                } catch (_) {}
                return result;
            };
            wrapped._animationControllerIntegrated = true;
            window.applyEventProperties = wrapped;
        }

        // Initial Base-tab opening does not currently call the shared presentation
        // setter, so decorate openEventModal and seed the picker from the Event.
        if (typeof window.openEventModal === 'function' && !window.openEventModal._animationControllerIntegrated) {
            const baseOpen = window.openEventModal;
            const wrapped = function (x, y) {
                const result = baseOpen(x, y);
                try {
                    const map = dbPayload.maps[currentMapIndex];
                    const event = map && (map.events || []).find(candidate => candidate.x === x && candidate.y === y);
                    api.setEventField(event && event.animationController);
                } catch (_) { api.setEventField(undefined); }
                return result;
            };
            wrapped._animationControllerIntegrated = true;
            window.openEventModal = wrapped;
        }
    }

    api.install = installIntegration;
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', installIntegration, { once: true });
    } else {
        installIntegration();
    }

    return api;
}));