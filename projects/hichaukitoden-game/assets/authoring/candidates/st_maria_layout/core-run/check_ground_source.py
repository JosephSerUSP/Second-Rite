"""Read-only Blender source verification; writes derived evidence beside the contract.

Run Blender in background with the contract's sourceBlend and this Python file.
This verifies paving samples and climb terrain clearance, not swept-body gameplay.
"""
import bpy, hashlib, json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

candidate = Path(__file__).resolve().parent
contract = json.loads((candidate / 'screen-contract.json').read_text(encoding='utf8'))
assert Path(bpy.data.filepath).name == contract['sourceBlend']
assert hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest() == contract['sourceSHA256']
scene = bpy.data.scenes['B7 Churchyard plate and ecological material study']
bpy.context.window.scene = scene
bpy.context.view_layer.update()

def tree(obj):
    return BVHTree.FromPolygons([obj.matrix_world @ v.co for v in obj.data.vertices],
                               [list(p.vertices) for p in obj.data.polygons])

checks = []
for row in contract['screens']:
    obj = next((o for o in scene.objects if o.get('street_support') == row['id']), None)
    if obj is None:
        continue
    paving = tree(obj)
    for point in row['profile']:
        pos = Vector(point['p'])
        if point['s'] == 0:
            pos += Vector(row['right']) * .0001
        elif abs(point['s'] - row['span']) < .00001:
            pos -= Vector(row['right']) * .0001
        hit = paving.ray_cast(pos + Vector((0, 0, 5)), Vector((0, 0, -1)), 10)[0]
        assert hit is not None, (row['id'], point)
        gap = pos.z - hit.z
        assert abs(gap - .015) < .005, (row['id'], point, gap)
        checks.append(dict(screen=row['id'], s=point['s'], gap=gap))
    heights = [p['z'] for p in row['groundProfile']]
    assert all(b >= a for a, b in zip(heights, heights[1:])) or all(b <= a for a, b in zip(heights, heights[1:]))
assert {p['screen'] for p in checks} == {'court', 'market'}
record = dict(sourceSHA256=contract['sourceSHA256'], samples=len(checks),
              maximumGap=max(p['gap'] for p in checks), monotonicStreetGrades=True, checks=checks)
(candidate / 'ground-support-checks.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf8')

terrain = tree(next(o for o in scene.objects if 'landforms' in o))
climb = next(c for c in contract['connections'] if c.get('traversalKind') == 'climb')
assert all(scene.objects.get(name) is not None for name in climb['sourceObjects'])
intrusions = []
for a, b in zip(climb['knots'], climb['knots'][1:]):
    for step in range(21):
        pos = Vector(a).lerp(Vector(b), step / 20)
        hit = terrain.ray_cast(pos + Vector((0, 0, 100)), Vector((0, 0, -1)))[0]
        intrusions.append(max(0, hit.z - pos.z) if hit else 0)
assert max(intrusions) < .035
record = dict(sourceSHA256=contract['sourceSHA256'], samples=len(intrusions),
              maximumTerrainIntrusion=max(intrusions), scope='Point terrain clearance and named ladder objects; not swept body or physical Android acceptance')
(candidate / 'service-climb-checks.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf8')
print('SOURCE WALKING SUPPORT OK', len(checks), 'paving samples;', len(intrusions), 'climb samples', flush=True)
