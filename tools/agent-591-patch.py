from pathlib import Path

path = Path('tools/editor/js/animation-controller-editor.js')
text = path.read_text(encoding='utf-8')
old = """                const state = api.getEventFieldState();
                const result = baseApply();
                try {
"""
new = """                const result = baseApply();
                // applyEventProperties restores Base when a Page tab was active;
                // read the controller field after that restore so Page state is
                // never accidentally copied onto the Base Event.
                const state = api.getEventFieldState();
                try {
"""
if old not in text:
    raise SystemExit('animation-controller apply bridge anchor not found')
path.write_text(text.replace(old, new, 1), encoding='utf-8')

# The helper/workflow are intentionally self-removing: the resulting commit
# contains only product changes and testable source, not agent infrastructure.
Path('.github/workflows/agent-591-editor-patch.yml').unlink(missing_ok=True)
Path('tools/agent-591-patch.py').unlink(missing_ok=True)
