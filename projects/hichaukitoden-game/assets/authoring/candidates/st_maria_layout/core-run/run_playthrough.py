import os
import subprocess
from pathlib import Path

candidate = Path(__file__).resolve().parent
root = Path(__file__).resolve().parents[7]
stage = root / 'out/st-maria-playtest/game'
(stage / 'tests').mkdir(exist_ok=True)
(stage / 'tests/check_playthrough.lua').write_bytes((candidate / 'check_playthrough.lua').read_bytes())
main = stage / 'main.lua'
original = main.read_bytes()
marker = b'cli_tools.runTownProofFrames(loader)'
assert original.count(marker) == 1
try:
    main.write_bytes(original.replace(marker, b'local ok, err = pcall(require("tests.check_playthrough").run, loader); if not ok then print("PLAYTEST FAILED: " .. tostring(err)); love.event.quit(1) end'))
    love = os.environ.get('LOVEC_PATH', 'C:/Program Files/LOVE/lovec.exe')
    result = subprocess.run([love, str(stage), 'town-proof-frames'], cwd=stage,
        capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
    log = result.stdout + result.stderr
    (stage.parent / 'playthrough.log').write_text(log, encoding='utf-8')
    print(log)
    assert result.returncode == 0 and 'PLAYTEST LOOP OK' in log
finally:
    main.write_bytes(original)
