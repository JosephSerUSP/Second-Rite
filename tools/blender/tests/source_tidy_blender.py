"""source_tidy joins repeated pieces, keeps everything else, and cannot change geometry."""
import sys
from pathlib import Path
import bpy
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/blender/recipes'))
import source_tidy as tidy

bpy.ops.wm.read_factory_settings(use_empty=True)
collection = bpy.data.collections.new('TH_SOURCE')
bpy.context.scene.collection.children.link(collection)
clay, glass = bpy.data.materials.new('clay'), bpy.data.materials.new('glass')


def box(name, x, material, parent=None, hide=False, role='source', bevel=False):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(x, 0, 0))
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.append(material)
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    collection.objects.link(obj)
    obj.parent = parent
    obj['sr_bake_role'] = role
    obj.hide_render = hide
    if bevel:
        obj.modifiers.new('bevel', 'BEVEL').width = 0.05
    return obj


roof = bpy.data.objects.new('East volume', None)
collection.objects.link(roof)
for i in range(6): box(f'East tile barrel 0 {i}', i * 2.0, clay, roof)          # one roof plane
for i in range(5): box(f'East tile barrel 1 {i}', 20 + i * 2.0, clay, roof)      # another, own group
for i in range(3): box(f'Lonely pier {i}', 40 + i * 2.0, clay, roof)             # too few: stays
for i in range(4): box(f'West tile barrel 0 {i}', i * 2.0, glass, roof)          # other material: own group
for i in range(5): box(f'Slat {i}', 60 + i, clay, roof, bevel=True)              # modifiers applied, not lost
for i in range(5): box(f'Target {i}', 80 + i, clay, roof, role='receiver')       # bake receivers never join
for i in range(5): box(f'Hidden {i}', 90 + i, clay, roof, hide=True)             # hidden never joins
for i in range(3):
    for k in range(3): box(f'Drain slot {i} {k}', 100 + i * 2 + k * 0.4, clay)   # grid: needs the array pass (9 >= 8)

before = tidy.geometry_summary(collection)
meshes_before = len([o for o in collection.all_objects if o.type == 'MESH'])
joined = tidy.consolidate(collection)
bpy.context.view_layer.update()
after = tidy.geometry_summary(collection)
names = {o.name for o in collection.all_objects}

assert tidy.summaries_match(before, after), 'Consolidation changed the geometry'
assert 'East tile barrel 0' in names and 'East tile barrel 1' in names, names
assert not any(n.startswith('East tile barrel 0 ') for n in names), 'Tiles were not joined'
assert 'West tile barrel 0' in names, 'A different material must form its own group'
assert sum(1 for n in names if n.startswith('Lonely pier')) == 3, 'Fewer than the minimum must stay as authored'
assert 'Slat' in names and not [o for o in collection.all_objects if o.type == 'MESH' and o.modifiers], \
    'Joined pieces must carry their modifiers applied, not dropped'
assert sum(1 for n in names if n.startswith('Target ')) == 5, 'Bake receivers must never be joined'
assert sum(1 for n in names if n.startswith('Hidden ')) == 5, 'Hidden objects must never be joined'
assert 'Drain slot' in names, 'The array pass should join a grid of eight or more'
assert len([o for o in collection.all_objects if o.type == 'MESH']) < meshes_before
assert joined['East volume / East tile barrel 0'] == 6, joined

# The parity check must notice a moved piece.
moved = next(o for o in collection.all_objects if o.name == 'East tile barrel 0')
moved.location.x += 0.01
bpy.context.view_layer.update()
assert not tidy.summaries_match(before, tidy.geometry_summary(collection)), 'A 1 cm move went unnoticed'

parts = tidy.file_by_part(collection)
assert 'East tile' in parts and all(o.users_collection[0] is not collection for o in collection.all_objects if o.type == 'MESH')
print('SOURCE TIDY OK')
