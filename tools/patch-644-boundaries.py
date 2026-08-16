from pathlib import Path


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)

# ---------------------------------------------------------------------------
# Workspace-owned toolbar extension membrane.
# ---------------------------------------------------------------------------
workspace_path = Path("tools/editor/js/thestra-editor-workspace.js")
workspace = workspace_path.read_text(encoding="utf-8")
old_toolbar = """    toolbar.append(perspectiveButton, topButton, navigationHelp, status);\n    area.appendChild(toolbar);\n"""
new_toolbar = """    // Declared extension membrane: the Map workspace owns its toolbar DOM.\n    // Other surfaces may contribute controls only through this mount API; they\n    // never query/mutate the workspace toolbar or depend on child position.\n    const toolbarExtensions = document.createElement('span');\n    toolbarExtensions.id = 'thestra-map-view-toolbar-extensions';\n    toolbarExtensions.style.display = 'contents';\n    const toolbarExtensionSlots = new Map();\n    window.ThestraMapWorkspaceToolbar = Object.freeze({\n        mount(key, nodes) {\n            if (typeof key !== 'string' || !key) throw new Error('toolbar extension key is required');\n            let slot = toolbarExtensionSlots.get(key);\n            if (!slot) {\n                slot = document.createElement('span');\n                slot.dataset.thestraToolbarExtension = key;\n                slot.style.display = 'contents';\n                toolbarExtensionSlots.set(key, slot);\n                toolbarExtensions.appendChild(slot);\n            }\n            slot.replaceChildren(...Array.from(nodes || []));\n            return slot;\n        },\n        projectionButtons() {\n            return [perspectiveButton, topButton];\n        },\n    });\n    toolbar.append(toolbarExtensions, perspectiveButton, topButton, navigationHelp, status);\n    area.appendChild(toolbar);\n"""
workspace = replace_once(workspace, old_toolbar, new_toolbar, "workspace toolbar extension seam")
workspace_path.write_text(workspace, encoding="utf-8", newline="\n")

world_path = Path("tools/editor/js/world-presentation-studio.js")
world = world_path.read_text(encoding="utf-8")
old_open = """    function installRuntimeToolbar() {\n        if (runtimeControls) return true;\n        const toolbar = document.getElementById('thestra-map-view-toolbar');\n        if (!toolbar) return false;\n        const projectionButtons = Array.from(toolbar.querySelectorAll('[data-mode]'));\n"""
new_open = """    function installRuntimeToolbar() {\n        if (runtimeControls) return true;\n        const toolbar = root.ThestraMapWorkspaceToolbar;\n        if (!toolbar || typeof toolbar.mount !== 'function'\n            || typeof toolbar.projectionButtons !== 'function') return false;\n        const projectionButtons = toolbar.projectionButtons();\n"""
world = replace_once(world, old_open, new_open, "world presentation toolbar ownership")
old_insert = """        toolbar.insertBefore(info, toolbar.firstChild);\n        toolbar.insertBefore(sceneSelect, toolbar.firstChild);\n        toolbar.insertBefore(runtime, toolbar.firstChild);\n        toolbar.insertBefore(free, toolbar.firstChild);\n        runtimeControls = { free, runtime, sceneSelect, info, projectionButtons, projectionDisabled: null };\n"""
new_insert = """        toolbar.mount('world-presentation', [free, runtime, sceneSelect, info]);\n        runtimeControls = { free, runtime, sceneSelect, info, projectionButtons, projectionDisabled: null };\n"""
world = replace_once(world, old_insert, new_insert, "world presentation declared toolbar mount")
world_path.write_text(world, encoding="utf-8", newline="\n")

# ---------------------------------------------------------------------------
# Typed G6 stall result. A wait predicate that never becomes true is not a
# pixel mismatch and must never tell the owner to recapture references.
# ---------------------------------------------------------------------------
g6_path = Path("tools/golden/editor-screens-core.py")
g6 = g6_path.read_text(encoding="utf-8")
chrome_marker = """class Chrome(object):\n"""
stall_class = """class HarnessStall(RuntimeError):\n    def __init__(self, step, predicate, last_error=None):\n        super().__init__(step)\n        self.step = step\n        self.predicate = predicate\n        self.last_error = last_error\n\n\nclass Chrome(object):\n"""
g6 = replace_once(g6, chrome_marker, stall_class, "typed harness stall class")
old_wait = """        raise SystemExit(\"editor-screens.py: timed out waiting for %s (%s)%s\"\n                         % (what, expression, (\"\\n  last error: %s\" % last) if last else \"\"))\n"""
new_wait = """        raise HarnessStall(what, expression, last)\n"""
g6 = replace_once(g6, old_wait, new_wait, "wait predicate stall classification")
old_entry = """if __name__ == \"__main__\":\n    main()\n"""
new_entry = """if __name__ == \"__main__\":\n    try:\n        main()\n    except HarnessStall as stall:\n        print(\"G6 HARNESS STALL\", file=sys.stderr)\n        print(\"  step: %s\" % stall.step, file=sys.stderr)\n        print(\"  predicate: %s\" % stall.predicate, file=sys.stderr)\n        if stall.last_error:\n            print(\"  last error: %s\" % stall.last_error, file=sys.stderr)\n        print(\"  No pixel comparison completed for this step.\", file=sys.stderr)\n        raise SystemExit(2)\n"""
g6 = replace_once(g6, old_entry, new_entry, "G6 typed stall entry point")
g6_path.write_text(g6, encoding="utf-8", newline="\n")

check_path = Path("tools/golden/check-editor.ps1")
check = check_path.read_text(encoding="utf-8")
old_check = """& python \"tools/golden/editor-screens.py\" check\nif ($LASTEXITCODE -ne 0) {\n    throw \"Golden editor screenshot gate failed\"\n}\n"""
new_check = """& python \"tools/golden/editor-screens.py\" check\n$g6Exit = $LASTEXITCODE\nif ($g6Exit -eq 1) {\n    throw \"G6 visual mismatch: inspect actual vs owner-signed references before any recapture\"\n}\nif ($g6Exit -eq 2) {\n    throw \"G6 harness stalled before pixel comparison; this is not a visual mismatch\"\n}\nif ($g6Exit -ne 0) {\n    throw \"G6 harness execution failed (exit $g6Exit)\"\n}\n"""
check = replace_once(check, old_check, new_check, "PowerShell G6 result classification")

# Gate the structural boundary before booting Chrome.
needle = """& python \"tools/golden/test-g6-dependency-preflight.py\"\n"""
prepend = """& python \"tools/golden/test-g6-harness-boundaries.py\"\nif ($LASTEXITCODE -ne 0) {\n    throw \"G6 harness boundary regression test failed\"\n}\n\n& python \"tools/golden/test-g6-dependency-preflight.py\"\n"""
check = replace_once(check, needle, prepend, "G6 structural boundary test registration")
check_path.write_text(check, encoding="utf-8", newline="\n")

print("#644 toolbar ownership + typed harness-stall patch applied")
