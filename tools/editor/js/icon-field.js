function createIconField(container, labelText, value, onChange, compact) {
    const group = document.createElement('div');

    const lbl = document.createElement('label');
    lbl.textContent = labelText;
    lbl.style.marginBottom = '2px';
    group.appendChild(lbl);

    const swatch = document.createElement('div');
    swatch.style.width = '24px';
    swatch.style.height = '24px';
    swatch.style.border = '1px solid #ccc';
    swatch.style.imageRendering = 'pixelated';
    swatch.style.flexShrink = '0';
    swatch.style.cursor = 'pointer';
    swatch.title = 'Click to pick icon & palette';

    let currentSpec = (typeof value === 'object' && value !== null)
        ? { id: parseInt(value.id || value.icon) || 0, palette: value.palette || value.iconPalette || null }
        : { id: parseInt(value) || 0, palette: null };

    function updateSwatch(spec) {
        currentSpec = (typeof spec === 'object' && spec !== null)
            ? { id: parseInt(spec.id || spec.icon) || 0, palette: spec.palette || spec.iconPalette || null }
            : { id: parseInt(spec) || 0, palette: null };

        if (window.renderIconSwatch) {
            window.renderIconSwatch(swatch, currentSpec);
        } else {
            const id = currentSpec.id || 0;
            const { x, y } = iconGridPos(id, 24);
            const iconPath = window.getIconsetPath ? window.getIconsetPath() : '/assets/system/iconset.png';
            swatch.style.backgroundImage = `url("${iconPath}")`;
            swatch.style.backgroundPosition = `-${x}px -${y}px`;
            swatch.style.backgroundSize = `240px auto`;
        }
    }
    updateSwatch(value);

    const handleOpen = (e) => {
        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }
        if (window.openIconPicker) {
            window.openIconPicker(currentSpec, (res) => {
                const newId = (typeof res === 'object' && res !== null) ? (parseInt(res.id) || 0) : (parseInt(res) || 0);
                const newPalette = (typeof res === 'object' && res !== null) ? (res.palette || null) : null;
                const newSpec = { id: newId, palette: newPalette };
                updateSwatch(newSpec);
                if (onChange) onChange(newId, newPalette);
            });
        }
    };

    swatch.onclick = handleOpen;

    group.appendChild(swatch);

    if (compact) {
        group.style.cssText = 'display: flex; flex-direction: column; align-items: flex-start; flex-shrink: 0; margin-right: 0;';
    } else {
        group.className = 'form-group';
    }

    container.appendChild(group);
}
window.createIconField = createIconField;

// Model previews are another asset-field primitive, but unlike the image/icon
// pickers they build their modal DOM on demand. Keep the editor's canonical
// API base visible to the dynamically loaded module: state.js deliberately
// declares API_URL with `const`, so it is shared across classic scripts but is
// not automatically a `window` property. The model picker originally read
// `window.API_URL`, which silently collapsed to same-origin and broke the
// file:// fallback that the working image/sprite picker supports.
(function loadModelPickerAssetField() {
    if (typeof API_URL !== 'undefined') window.API_URL = API_URL;

    function loadStudioIntegration() {
        if (document.querySelector('script[data-model-picker-integration]')) return;
        const integration = document.createElement('script');
        integration.src = 'js/model-picker-integration.js';
        integration.dataset.modelPickerIntegration = '1';
        integration.async = false;
        integration.onerror = () => console.error('[model-picker] failed to load js/model-picker-integration.js');
        document.head.appendChild(integration);
    }

    if (window.SecondRiteModelPreview) {
        loadStudioIntegration();
        return;
    }
    if (document.querySelector('script[data-model-picker]')) return;

    const script = document.createElement('script');
    script.src = 'js/model-picker.js';
    script.dataset.modelPicker = '1';
    script.async = false;
    script.onload = loadStudioIntegration;
    script.onerror = () => console.error('[model-picker] failed to load js/model-picker.js');
    document.head.appendChild(script);
})();
