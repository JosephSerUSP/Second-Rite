import tempfile, shutil, json, os, sys, importlib.util, time

ROOT = os.getcwd()
spec = importlib.util.spec_from_file_location('editor_screens', os.path.join(ROOT, 'tools', 'golden', 'editor-screens.py'))
editor_screens = importlib.util.module_from_spec(spec)
spec.loader.exec_module(editor_screens)

Chrome = editor_screens.Chrome
EditorServer = editor_screens.EditorServer
free_port = editor_screens.free_port
VIEWPORT = editor_screens.VIEWPORT
DETERMINISM_JS = editor_screens.DETERMINISM_JS
RESET_JS = editor_screens.RESET_JS

server = EditorServer()
profile = tempfile.mkdtemp(prefix='g6-test-')
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
    
    # Trigger openMapProperties
    chrome.evaluate('openMapProperties();')
    
    # Check options count immediately vs after waiting
    opts_before = chrome.evaluate('document.getElementById("prop-map-tileset").options.length')
    time.sleep(0.3)
    opts_after = chrome.evaluate('document.getElementById("prop-map-tileset").options.length')
    
    print(f'Options right after openMapProperties(): {opts_before}')
    print(f'Options 300ms later: {opts_after}')
finally:
    chrome.close()
    server.close()
    shutil.rmtree(profile, ignore_errors=True)
