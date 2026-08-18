(function (root, factory) {
    if (typeof module === 'object' && module.exports) {
        module.exports = factory(require('./generated/vertex-shading.js'));
    } else {
        root.ThestraVertexShading = factory(root.ThestraVertexShadingSemantics);
    }
}(typeof self !== 'undefined' ? self : this, function (Semantics) {
    'use strict';
    if (!Semantics) {
        throw new Error('ThestraVertexShading requires generated shared vertex-shading semantics.');
    }
    return Semantics;
}));

// Environment-lighting authoring bootstrap. This deliberately performs only
// bounded DOM ownership work: no dynamic Three import, no prototype mutation,
// and no MutationObserver. The retired Paint/Blur UI stays out of the visible
// workflow while legacy map.light data remains readable by runtime/editor code.
(function installEnvironmentLightingAuthoring(root) {
    if (typeof window === 'undefined' || typeof document === 'undefined') return;

    function hide(element) {
        if (element) element.style.display = 'none';
    }

    function bridgeLampPropertyInputs(palette) {
        let proxy = document.getElementById('light-object-live-property-proxy');
        if (!proxy) {
            proxy = document.createElement('span');
            proxy.id = 'light-object-live-property-proxy';
            proxy.hidden = true;
            palette.appendChild(proxy);
        }
        ['lamp-color', 'lamp-radius', 'lamp-falloff', 'lamp-material'].forEach(id => {
            const input = document.getElementById(id);
            if (!input || input.dataset.thestraLiveLightingBridge === 'true') return;
            input.dataset.thestraLiveLightingBridge = 'true';
            input.addEventListener('input', () => {
                // map-editor's inline input handler has already mutated the
                // authored Lamp. Reuse the workspace's existing light-property
                // invalidation seam so Three relights on the next frame while
                // LÖVE authority catches up asynchronously. #493 will replace
                // this legacy-control bridge with the contextual Inspector.
                proxy.dispatchEvent(new Event('input', { bubbles: true }));
            });
        });
    }

    function reconcilePalette() {
        const palette = document.getElementById('light-palette-section');
        if (!palette) return false;

        const title = palette.querySelector('.sidebar-title');
        if (title) title.textContent = 'Environment Lighting';
        const intro = title && title.nextElementSibling;
        if (intro && intro.tagName === 'P') {
            intro.textContent = 'Author semantic lamp sources here. Vertex Shading adds environmental color variation independently of illumination.';
        }

        const lampRadio = palette.querySelector('input[name="light-tool"][value="object"]');
        if (lampRadio) {
            lampRadio.checked = true;
            hide(lampRadio.closest('.field-row-stacked'));
        }
        if (typeof root.setLightTool === 'function') root.setLightTool('object');

        hide(document.getElementById('light-color-row'));
        hide(document.getElementById('light-blur-hint'));
        const radius = document.getElementById('light-brush-radius');
        hide(radius && radius.closest('.field-row-stacked'));
        const reset = palette.querySelector('button[onclick*="clearMapLight"]');
        hide(reset);
        const bake = palette.querySelector('button[onclick*="bakeMapLighting"]');
        if (bake) bake.remove();
        bridgeLampPropertyInputs(palette);

        const lampHint = document.getElementById('light-object-hint');
        if (lampHint) {
            lampHint.style.display = 'block';
            lampHint.textContent = 'Click a cell to add/select a lamp, then use the 3D gizmo to move it. Lamps affect illumination and do not alter collision.';
        }
        if (!palette.querySelector('[data-thestra-lamp-heading]') && lampHint) {
            const heading = document.createElement('div');
            heading.className = 'sidebar-title';
            heading.dataset.thestraLampHeading = 'true';
            heading.style.marginTop = '6px';
            heading.textContent = 'Lamp Sources';
            lampHint.parentElement.insertBefore(heading, lampHint);
        }

        // The workspace script is loaded after this module, so give its
        // Vertex Shading panel a short bounded handoff window rather than
        // observing the whole document forever.
        const shading = document.getElementById('vertex-shading-section');
        if (shading && shading.parentElement !== palette) palette.appendChild(shading);
        return !!shading;
    }

    reconcilePalette();
    let attempts = 0;
    function finishPaletteOwnership() {
        if (reconcilePalette()) return;
        attempts += 1;
        if (attempts < 120) window.requestAnimationFrame(finishPaletteOwnership);
    }
    window.requestAnimationFrame(finishPaletteOwnership);
}(typeof self !== 'undefined' ? self : this));
