"""Cut the Passage House gate into the Registry's public back wall (a new revision).

The Registry and the Passage House are one building (layout doc section 5.1). The
house's stair hall ends in a wrought-iron gate; this adds the other half of it: a
door in the Registry's back wall, with the same iron gate in it, through which the
hall's gallery can be seen. Painting, notices and bench keep their places except
for the minimum: the painting is hung smaller beside the door and the bench slides
along to make room.

Edits an existing document into a NEW file; the adopted source is never written.
Run with the pinned Blender through run.py:

    python tools/blender/run.py tools/blender/add_registry_gate.py -- \
        --source projects/<project>/assets/authoring/environments/passage_office.blend \
        --output projects/<project>/assets/authoring/candidates/passage_office/passage_office_r14.blend
"""
import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/blender'), str(ROOT / 'tools/blender/recipes')]
import furnishings as furn  # noqa: E402
import interior as kit  # noqa: E402
import source_dependencies  # noqa: E402

GATE_Y = 2.9           # Blender Y of the door's centre (screen left is +Y)
DOOR_HALF = 0.55
DOOR_TOP = 2.3
BACK_X = 4.67          # inner face of the back wall
WALL_THICK = 0.5
PAINTING_SCALE = 0.7
PAINTING_Y = 4.12
BENCH_SHIFT = 0.7


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    if args.output.exists():
        parser.error('Preserve previous revisions; use a new output file')
    bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
    source_dependencies.assert_available()

    wall = bpy.data.objects['back_wall_0_pier_1']
    wall_mat = wall.active_material
    root = bpy.data.objects['PASSAGE_OFFICE']
    room = kit.Interior.__new__(kit.Interior)
    room.root, room.lift = root, 0
    room.half_width, room.back_x, room.wall_thick = 4.65, BACK_X, WALL_THICK
    room.parts = [o for o in bpy.data.objects if o.type == 'MESH']
    room.openings = [(GATE_Y - DOOR_HALF, GATE_Y + DOOR_HALF, 0.0, DOOR_TOP)]
    room.wood = bpy.data.materials['registry_worked_hardwood']
    room.stone = kit.material('rough_limestone')
    room.iron = kit.material('wrought_iron')
    room.bronze = kit.material('oxidized_bronze')
    room.azulejo = bpy.data.objects['azulejo_dado'].active_material
    room.lamplight = kit.emissive('sr_lamp_glow', (0.46, 0.28, 0.13))

    # --- the wall: one pier becomes a pier, a door and a pier ------------------
    corners = [(wall.matrix_world @ Vector(c))[1] for c in wall.bound_box]
    lo, hi = min(corners), max(corners)
    bpy.data.objects.remove(wall, do_unlink=True)
    z0, z1 = -0.35, 3.65
    door_lo, door_hi = GATE_Y - DOOR_HALF, GATE_Y + DOOR_HALF
    for name, a, b, za, zb in (('back_wall_gate_pier_0', lo, door_lo, z0, z1),
                               ('back_wall_gate_pier_1', door_hi, hi, z0, z1),
                               ('back_wall_gate_over', door_lo, door_hi, DOOR_TOP, z1)):
        room.part(name, (WALL_THICK, b - a, zb - za),
                  (BACK_X + WALL_THICK / 2.0, (a + b) / 2.0, (za + zb) / 2.0), wall_mat)

    # --- the tiled band stops at the door ---------------------------------------
    bpy.data.objects.remove(bpy.data.objects['azulejo_dado'], do_unlink=True)
    furn.azulejo_dado(room, height=1.0)

    # --- the door: stone surround, iron gate, the gallery beyond --------------------
    furn.door_frame(room, 'gate_frame', door_lo, door_hi, DOOR_TOP)
    x = BACK_X + WALL_THICK - 0.02
    width = DOOR_HALF * 2 - 0.1
    with room.piece('registry_gate'):
        for index in range(9):
            bar_y = GATE_Y - width / 2.0 + width * index / 8.0
            room.part(f'gate_bar_{index}', (0.035, 0.035, DOOR_TOP - 0.1), (x, bar_y, (DOOR_TOP - 0.1) / 2.0 + 0.05), room.iron)
        for index, z in enumerate((0.3, 1.1, DOOR_TOP - 0.2)):
            room.part(f'gate_rail_{index}', (0.05, width + 0.06, 0.06), (x, GATE_Y, z), room.iron)
        room.part('gate_handle', (0.05, 0.1, 0.13), (x - 0.04, GATE_Y - 0.18, 1.08), room.bronze)
    beyond = BACK_X + WALL_THICK + 1.5
    room.part('gate_beyond', (0.06, width + 0.5, DOOR_TOP), (beyond, GATE_Y, DOOR_TOP / 2.0), room.lamplight)
    kit.Interior.light(room, 'gate_beyond_lamp', 'POINT', (beyond - 0.9, GATE_Y, 1.9), (0.0, 0.0, -1.0), 40.0,
                       (1.0, 0.76, 0.46), radius=0.12)

    # --- make room: the painting hangs smaller beside the door, the bench slides ------
    painting = bpy.data.objects['harbour_painting']
    painting.scale = (1.0, PAINTING_SCALE, PAINTING_SCALE)
    bpy.context.view_layer.update()
    centre_y = sum((painting.matrix_world @ Vector(c))[1] for c in painting.bound_box) / 8.0
    painting.location.y += PAINTING_Y - centre_y
    bpy.data.objects['waiting_bench'].location.y += BENCH_SHIFT

    kit.recalculate_normals([o for o in bpy.data.objects if o.type == 'MESH'])
    source_dependencies.assert_available()
    bpy.context.scene['registry_gate_description'] = 'Back-wall door with an iron gate to the Passage House gallery'
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()))
    print('REGISTRY GATE REVISION OK')


if __name__ == '__main__':
    main()
