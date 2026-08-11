from pathlib import Path
p = Path('presentation/viewport_3d.lua')
text = p.read_text(encoding='utf-8')
old = '        if not (mapData and mapData.ceilingStyle == "sky") then\n'
new = '        if geometryVisibility.walkableCeilingVisible("play",\n                mapData and mapData.ceilingStyle) then\n'
if text.count(old) != 1:
    raise SystemExit(f'expected one runtime ceiling policy match, found {text.count(old)}')
p.write_text(text.replace(old, new, 1), encoding='utf-8')
