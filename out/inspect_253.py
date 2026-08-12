import tempfile, shutil, json, os, sys
import importlib.util

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("editor_screens", os.path.join(ROOT, "tools", "golden", "editor-screens.py"))
editor_screens = importlib.util.module_from_spec(spec)
spec.loader.exec_module(editor_screens)

Chrome = editor_screens.Chrome
EditorServer = editor_screens.EditorServer
free_port = editor_screens.free_port
VIEWPORT = editor_screens.VIEWPORT
DETERMINISM_JS = editor_screens.DETERMINISM_JS
RESET_JS = editor_screens.RESET_JS

server = EditorServer()
profile = tempfile.mkdtemp(prefix='g6-inspect-')
try:
    chrome = Chrome(free_port(), profile)
    chrome.call('Page.enable')
    chrome.call('Runtime.enable')
    chrome.call('Emulation.setDeviceMetricsOverride', width=VIEWPORT[0], height=VIEWPORT[1], deviceScaleFactor=1, mobile=False)
    chrome.call('Emulation.setEmulatedMedia', features=[{'name': 'prefers-reduced-motion', 'value': 'reduce'}])
    chrome.call('Page.addScriptToEvaluateOnNewDocument', source=DETERMINISM_JS)
    chrome.call('Page.navigate', url=server.url + '/')
    chrome.wait_for('typeof dbPayload !== "undefined" && dbPayload.maps && dbPayload.maps.length', 'db payload')
    chrome.evaluate(RESET_JS)
    chrome.evaluate('openMapProperties();')
    chrome.wait_for("document.getElementById('map-properties-modal').classList.contains('active')", 'map properties')
    
    info = chrome.evaluate('''
        (function() {
            var el1 = document.elementFromPoint(386, 480);
            var el2 = document.elementFromPoint(450, 480);
            var el3 = document.elementFromPoint(500, 480);
            
            function desc(el) {
                if (!el) return 'null';
                return {
                    tag: el.tagName,
                    id: el.id,
                    className: el.className,
                    text: (el.innerText || el.textContent || el.value || '').substring(0, 50),
                    rect: JSON.parse(JSON.stringify(el.getBoundingClientRect())),
                    outerHTML: el.outerHTML.substring(0, 200)
                };
            }
            return {
                pt1: desc(el1),
                pt2: desc(el2),
                pt3: desc(el3)
            };
        })()
    ''', await_promise=False)
    print(json.dumps(info, indent=2))
finally:
    chrome.close()
    server.close()
    shutil.rmtree(profile, ignore_errors=True)
