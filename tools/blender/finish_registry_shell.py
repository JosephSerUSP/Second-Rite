"""Close the retained Registry ceiling junction without regenerating the room."""
import argparse, json, sys
from pathlib import Path
import bpy
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'tools/blender'), str(ROOT/'tools/blender/recipes')]
import interior as kit
import source_dependencies
from shell_geometry import ceiling_members
from fit_registry_ceiling import bounds, signature

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
    if a.output.exists(): p.error('Use a new source revision')
    bpy.ops.wm.open_mainfile(filepath=str(a.source.resolve()))
    source_dependencies.assert_available()
    original = [o for o in bpy.data.objects if o.type == 'MESH' and o.name != 'ceiling']
    before = signature(original)
    ceiling = bpy.data.objects['ceiling']; low, high = bounds(ceiling)
    wall_low, wall_high = bounds(bpy.data.objects['side_wall_0_pier_0'])
    thickness = wall_high[1] - wall_low[1]
    members = ceiling_members(low[0], high[0], high[1], thickness, low[2], high[2]-low[2])
    # Preserve the existing ceiling mesh, UVs and material; expand its outer footprint.
    for vertex in ceiling.data.vertices:
        world = ceiling.matrix_world @ vertex.co
        if abs(world.x-high[0]) < 1e-5: world.x += thickness
        if abs(abs(world.y)-high[1]) < 1e-5: world.y += thickness if world.y > 0 else -thickness
        vertex.co = ceiling.matrix_world.inverted() @ world
    room = kit.Interior.__new__(kit.Interior)
    room.root = bpy.data.objects['PASSAGE_OFFICE']; room.lift = 0; room.parts = []
    wood = bpy.data.materials['registry_worked_hardwood']
    for name, size, location in members[1:]: room.part(name, size, location, wood)
    kit.recalculate_normals(room.parts)
    bpy.context.view_layer.update()
    assert signature(original) == before, 'Existing walls, beams or furniture changed'
    new_low, new_high = bounds(ceiling)
    assert new_low[1] <= wall_low[1]+1e-5 and new_high[0] >= high[0]+thickness-1e-5
    bpy.context.scene['registry_shell_finish'] = json.dumps(dict(wallThickness=thickness,
        preservedExistingMeshes=True, ceilingOuterBounds=[new_low,new_high]))
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(a.output.resolve()))
    print('REGISTRY SHELL JUNCTION OK')

if __name__ == '__main__': main()
