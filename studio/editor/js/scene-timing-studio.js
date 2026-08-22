(function (root) {
    'use strict';

    const Timing = root.ThestraSceneTimingAuthoring;
    if (!Timing || typeof document === 'undefined') return;

    function markDirty() {
        if (typeof root.setDirty === 'function') root.setDirty(true);
    }

    function smallNote(text) {
        const note = document.createElement('div');
        note.style.cssText = 'font-size:10px;color:var(--win-dark-shadow);line-height:1.35;margin:3px 0 6px;';
        note.textContent = text;
        return note;
    }

    function fieldRow(labelText, control, hint) {
        const row = document.createElement('label');
        row.style.cssText = 'display:flex;align-items:center;gap:6px;margin:4px 0;font-size:10px;';
        const label = document.createElement('span');
        label.style.cssText = 'width:92px;flex:0 0 92px;';
        label.textContent = labelText;
        row.append(label, control);
        if (hint) {
            const help = document.createElement('span');
            help.style.cssText = 'color:var(--win-dark-shadow);font-size:9px;';
            help.textContent = hint;
            row.appendChild(help);
        }
        return row;
    }

    function installTimingPanel(container, scene) {
        if (!scene) return;

        const fieldset = document.createElement('fieldset');
        fieldset.dataset.thestraSceneTiming = 'true';
        fieldset.style.cssText = 'padding:6px;margin-bottom:6px;';
        const legend = document.createElement('legend');
        legend.textContent = 'Scene Timing';
        fieldset.appendChild(legend);

        const body = document.createElement('div');
        fieldset.appendChild(body);

        function renderBody() {
            body.innerHTML = '';
            const state = Timing.snapshot(scene);
            body.appendChild(smallNote(
                'Controls only this Scene\'s on_frame scheduling. Legacy/default follows rendered-frame updates without authoring timing fields. Fixed uses deterministic logical ticks. See Formula Help for the transient time.dt, time.tick and time.elapsed values available only during fixed on_frame.'
            ));

            const error = document.createElement('div');
            error.dataset.sceneTimingError = 'true';
            error.style.cssText = 'font-size:9px;color:#a00000;min-height:12px;margin-bottom:2px;';
            error.textContent = Timing.validateScene(scene).join(' · ');
            body.appendChild(error);

            const mode = document.createElement('select');
            mode.className = 'win98-input';
            mode.style.width = '180px';
            [['legacy', 'Legacy / default'], ['fixed', 'Fixed logical clock']].forEach(([value, text]) => {
                const option = document.createElement('option');
                option.value = value;
                option.textContent = text;
                mode.appendChild(option);
            });
            mode.value = state.mode;
            body.appendChild(fieldRow('Update mode:', mode,
                state.mode === 'fixed' ? 'deterministic on_frame ticks' : 'normal Scene behavior'));

            mode.addEventListener('change', () => {
                try {
                    Timing.setMode(scene, mode.value);
                    markDirty();
                    renderBody();
                } catch (e) {
                    mode.value = Timing.snapshot(scene).mode;
                    error.textContent = e.message || String(e);
                }
            });

            const fixed = Timing.fixedUpdate(scene);
            if (!fixed) return;

            const step = document.createElement('input');
            step.type = 'number';
            step.className = 'win98-input';
            step.dataset.sceneTimingStep = 'true';
            step.style.width = '120px';
            step.min = '0.000001';
            step.step = '0.001';
            step.value = String(fixed.step);
            body.appendChild(fieldRow('Fixed step:', step, 'seconds per logical on_frame tick'));
            step.addEventListener('input', () => {
                try {
                    Timing.setStep(scene, step.value);
                    step.style.background = '';
                    error.textContent = '';
                    markDirty();
                } catch (e) {
                    step.style.background = '#ffcccc';
                    error.textContent = e.message || String(e);
                }
            });

            const maxCatchUp = document.createElement('input');
            maxCatchUp.type = 'number';
            maxCatchUp.className = 'win98-input';
            maxCatchUp.dataset.sceneTimingMaxCatchUp = 'true';
            maxCatchUp.style.width = '120px';
            maxCatchUp.min = '1';
            maxCatchUp.max = String(Timing.MAX_CATCH_UP);
            maxCatchUp.step = '1';
            maxCatchUp.value = String(fixed.maxCatchUp == null
                ? Timing.DEFAULT_MAX_CATCH_UP : fixed.maxCatchUp);
            body.appendChild(fieldRow('Max catch-up:', maxCatchUp,
                `logical ticks allowed per rendered frame; 1–${Timing.MAX_CATCH_UP}`));
            maxCatchUp.addEventListener('input', () => {
                try {
                    Timing.setMaxCatchUp(scene, maxCatchUp.value);
                    maxCatchUp.style.background = '';
                    error.textContent = '';
                    markDirty();
                } catch (e) {
                    maxCatchUp.style.background = '#ffcccc';
                    error.textContent = e.message || String(e);
                }
            });

            body.appendChild(smallNote(
                'These time.* facts are transient Formula context: they are not Game Variables, not persistent Scene state, and are not saved.'
            ));
        }

        renderBody();
        const visualPreview = Array.from(container.children).find(child => child.tagName === 'FIELDSET'
            && child.querySelector('legend') && child.querySelector('legend').textContent === 'Visual Preview');
        container.insertBefore(fieldset, visualPreview || null);
    }

    function installSceneEditorHook() {
        if (root.__thestraSceneTimingEditorInstalled) return true;
        const original = root.renderCustomSceneEditor;
        if (typeof original !== 'function') return false;
        root.renderCustomSceneEditor = function (container, header, scene) {
            const result = original.apply(this, arguments);
            installTimingPanel(container, scene);
            return result;
        };
        root.__thestraSceneTimingEditorInstalled = true;
        return true;
    }

    installSceneEditorHook();
    root.addEventListener('load', installSceneEditorHook, { once: true });
}(typeof globalThis !== 'undefined' ? globalThis : this));
