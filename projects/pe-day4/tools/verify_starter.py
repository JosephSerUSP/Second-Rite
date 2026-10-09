"""Check generated starter data and its standalone asset boundary."""
import json
from pathlib import Path
import compile_starter

project = Path(__file__).resolve().parents[1]
for name, data in compile_starter.compile_data().items():
    actual = json.loads((project / name).read_text(encoding='utf8'))
    assert actual == data, f'stale generated file: {name}'

for path in (project / 'data').rglob('*.json'):
    text = path.read_text(encoding='utf8')
    for forbidden in ('hichaukitoden-game', 'pe-day1', 'projects/experiments/'):
        assert forbidden not in text, f'external Project dependency in {path}'

for binding in compile_starter.load('starter.json')['maps']:
    data = compile_starter.load(f"data/maps/{binding['mapId']}.json")
    traversal = data['traversal']
    assert not {'regions', 'obstacles', 'groundZ'}.intersection(traversal['surface']), 'duplicate Map walk authority'
    package = compile_starter.load(traversal['environmentPackage'])
    assert package['walkSurface']['regions'], 'missing package walk authority'
    assert (project / traversal['actorAppearance']['character']).is_file()
    anchor = package['anchors'][binding['door']]['position']
    assert data['events'][0]['worldPosition'] == anchor, 'route door has drifted from its visible anchor'
print('HOSPITAL STARTER BOUNDARY OK')
