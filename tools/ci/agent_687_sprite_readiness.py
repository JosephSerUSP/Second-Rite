from pathlib import Path

widgets = Path('tools/editor/js/widgets.js')
text = widgets.read_text(encoding='utf-8')

anchor = """            thumbWrap.title = 'Double-click to select image';
            let timingTitleGeneration = 0;

            const refreshTimingTitle = (spriteKey) => {
"""
replacement = """            thumbWrap.title = 'Double-click to select image';
            thumbWrap.dataset.spritePreviewAnimated = animate ? '1' : '0';
            thumbWrap.dataset.spritePreviewReady = '1';
            let timingTitleGeneration = 0;
            let spritePreviewGeneration = 0;

            const refreshTimingTitle = (spriteKey) => {
"""
assert text.count(anchor) == 1, 'sprite field generation anchor drifted'
text = text.replace(anchor, replacement, 1)

anchor = """            function updateThumb(path) {
                refreshTimingTitle(path);
                animLayer.classList.remove('sprite-sheet-anim');
"""
replacement = """            function updateThumb(path) {
                const previewGeneration = ++spritePreviewGeneration;
                thumbWrap.dataset.spritePreviewReady = (animate && path) ? '0' : '1';
                refreshTimingTitle(path);
                animLayer.classList.remove('sprite-sheet-anim');
"""
assert text.count(anchor) == 1, 'updateThumb anchor drifted'
text = text.replace(anchor, replacement, 1)

anchor = """                        probe.onload = () => {
                            const boxPx = thumbWrap.clientWidth || 48;
"""
replacement = """                        probe.onload = () => {
                            if (previewGeneration !== spritePreviewGeneration) return;
                            const boxPx = thumbWrap.clientWidth || 48;
"""
assert text.count(anchor) == 1, 'animated probe onload anchor drifted'
text = text.replace(anchor, replacement, 1)

anchor = """                            animLayer.style.display = 'block';
                            animLayer.classList.add('sprite-sheet-anim');
                        };
                        probe.onerror = () => { noneTxt.style.display = 'block'; };
"""
replacement = """                            animLayer.style.display = 'block';
                            animLayer.classList.add('sprite-sheet-anim');
                            thumbWrap.dataset.spritePreviewReady = '1';
                        };
                        probe.onerror = () => {
                            if (previewGeneration !== spritePreviewGeneration) return;
                            noneTxt.style.display = 'block';
                            thumbWrap.dataset.spritePreviewReady = '1';
                        };
"""
assert text.count(anchor) == 1, 'animated probe settle anchor drifted'
text = text.replace(anchor, replacement, 1)
widgets.write_text(text, encoding='utf-8')

# G6's Units tab contains an animated Small Battler sprite field. Pixel
# stability and document.images cannot certify it because createSpriteField
# probes animation strips through detached Image(). Wait for the field's own
# latest-probe completion signal instead.
g6 = Path('tools/golden/editor-screens-core.py')
text = g6.read_text(encoding='utf-8')
anchor = """    DB_TAB_READY = {
        "animations": " && document.querySelector('#anim-preview-img[data-preview-ready]')",
"""
replacement = """    DB_TAB_READY = {
        "units": " && document.querySelector('[data-sprite-preview-animated=\\\"1\\\"]'"
                 " '[data-sprite-preview-ready=\\\"1\\\"]')",
        "animations": " && document.querySelector('#anim-preview-img[data-preview-ready]')",
"""
assert text.count(anchor) == 1, 'DB_TAB_READY anchor drifted'
text = text.replace(anchor, replacement, 1)
g6.write_text(text, encoding='utf-8')

boundary = Path('tools/golden/test-g6-harness-boundaries.py')
text = boundary.read_text(encoding='utf-8')
anchor = """workspace = (ROOT / "tools/editor/js/thestra-editor-workspace.js").read_text(encoding="utf-8")
world = (ROOT / "tools/editor/js/world-presentation-studio.js").read_text(encoding="utf-8")
g6 = (ROOT / "tools/golden/editor-screens-core.py").read_text(encoding="utf-8")
"""
replacement = """workspace = (ROOT / "tools/editor/js/thestra-editor-workspace.js").read_text(encoding="utf-8")
world = (ROOT / "tools/editor/js/world-presentation-studio.js").read_text(encoding="utf-8")
widgets = (ROOT / "tools/editor/js/widgets.js").read_text(encoding="utf-8")
g6 = (ROOT / "tools/golden/editor-screens-core.py").read_text(encoding="utf-8")
"""
assert text.count(anchor) == 1, 'boundary source-list anchor drifted'
text = text.replace(anchor, replacement, 1)

anchor = """assert g6.count("chrome.wait_for(WORKSPACE_READY_JS") >= 3
# The map workspace waits are now identity-based; keep positional selectors out
"""
replacement = """assert g6.count("chrome.wait_for(WORKSPACE_READY_JS") >= 3

# #687: animated sprite fields use detached Image probes, so document.images
# cannot tell G6 when the Small Battler thumbnail has painted. The field owns a
# positive latest-generation readiness signal and Units waits for it.
assert "spritePreviewGeneration" in widgets
assert "previewGeneration !== spritePreviewGeneration" in widgets
assert "thumbWrap.dataset.spritePreviewReady = '1'" in widgets
assert "data-sprite-preview-animated" in g6 and "data-sprite-preview-ready" in g6
assert '"units":' in g6
# The map workspace waits are now identity-based; keep positional selectors out
"""
assert text.count(anchor) == 1, 'boundary assertion anchor drifted'
text = text.replace(anchor, replacement, 1)
boundary.write_text(text, encoding='utf-8')
