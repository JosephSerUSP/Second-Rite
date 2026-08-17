from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
workspace = (ROOT / "tools/editor/js/thestra-editor-workspace.js").read_text(encoding="utf-8")
world = (ROOT / "tools/editor/js/world-presentation-studio.js").read_text(encoding="utf-8")
widgets = (ROOT / "tools/editor/js/widgets.js").read_text(encoding="utf-8")
scene_canvas = (ROOT / "tools/editor/js/scene-canvas.js").read_text(encoding="utf-8")
adapter = (ROOT / "tools/editor/js/second-rite-editor-adapter.js").read_text(encoding="utf-8")
g6 = (ROOT / "tools/golden/editor-screens-core.py").read_text(encoding="utf-8")
check = (ROOT / "tools/golden/check-editor.ps1").read_text(encoding="utf-8")

assert "ThestraMapWorkspaceToolbar" in workspace
assert "thestra-map-view-toolbar-extensions" in workspace
assert "mount(key, nodes)" in workspace
assert "projectionButtons()" in workspace

assert "root.ThestraMapWorkspaceToolbar" in world
assert "toolbar.mount('world-presentation'" in world
assert "getElementById('thestra-map-view-toolbar')" not in world
assert "toolbar.insertBefore(" not in world

assert "class HarnessStall" in g6
assert "raise HarnessStall(what, expression, last)" in g6
assert 'print("G6 HARNESS STALL"' in g6
assert "raise SystemExit(2)" in g6

# #683: the Map workspace can be pixel-stable while an async authoritative
# bundle still belongs to the previous Map. Capture must use the production
# revision guard both around reset and after step-triggered refreshes.
assert "workspaceReadiness = WorkspaceState.createReadiness()" in workspace
assert "status.dataset.workspaceReady = '0'" in workspace
assert "status.dataset.workspaceReady = '1'" in workspace
assert "WORKSPACE_READY_JS" in g6
assert g6.count("chrome.wait_for(WORKSPACE_READY_JS") >= 3

# #687: animated sprite fields use detached Image probes, so document.images
# cannot tell G6 when the Small Battler thumbnail has painted. The field owns a
# positive latest-generation readiness signal and Units waits for it.
assert "spritePreviewGeneration" in widgets
assert "previewGeneration !== spritePreviewGeneration" in widgets
assert "thumbWrap.dataset.spritePreviewReady = '1'" in widgets
assert "data-sprite-preview-animated" in g6 and "data-sprite-preview-ready" in g6
assert r'''[data-sprite-preview-animated=\"1\"][data-sprite-preview-ready=\"1\"]''' in g6
assert '"units":' in g6

# #715: a Scene Visual Preview is not ready merely because its canvas exists or
# has stopped repainting. The producer clears stale readiness while loading and
# publishes readiness only after the current preview successfully paints. The
# Flows engine tab waits on that exact canvas inside its form panel.
assert "canvas.removeAttribute('data-preview-ready')" in scene_canvas
assert "canvas.setAttribute('data-preview-ready', '1')" in scene_canvas
assert '"flows": " && document.querySelector(\'#engine-form-panel canvas[data-preview-ready]\')"' in g6

# The runtime renderable bridge is a host process Electron starts alongside the
# editor. G6 booted only server.js, so every 3D frame it photographed was the
# semantic fallback. The gate now runs its own bridge on a free port -- never
# the default 8082, which belongs to a developer's running Studio -- and refuses
# to photograph the fallback rather than recording it as the editor's look.
assert "class RuntimeBridge(NodeService)" in g6
assert "RuntimeBridge(editor_port=server.port)" in g6
assert "THESTRA_RENDERABLE_URL" in g6 and "THESTRA_RENDERABLE_URL" in adapter
assert "8082" not in g6, "G6 must never target the default bridge port"
assert "runtime unavailable" in g6, "G6 must fail loud on the semantic fallback"
assert "bridge.close()" in g6

# The map workspace waits are now identity-based; keep positional selectors out
# of the G6 harness rather than making the next toolbar extension reorder a test.
for positional in (":nth-child", ":nth-of-type", "#thestra-map-view-toolbar span"):
    assert positional not in g6, f"positional G6 selector remains: {positional}"

assert "$g6Exit -eq 1" in check and "G6 visual mismatch" in check
assert "$g6Exit -eq 2" in check and "G6 harness stalled before pixel comparison" in check

print("G6 harness boundaries: OK")