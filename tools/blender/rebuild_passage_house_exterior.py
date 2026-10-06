"""Rebuild the Passage House's Cortico facade with the house grammar (a new revision).

The adopted island builds this block as a flat limewash box with dark decal windows laid on
it. The interiors were authored with real depth (reveals, surrounds, courses); the
exterior should read at the same level. This replaces the flat mass, its hip roof and the
decal windows/door trim with a grammar building at the SAME footprint, door and window
rhythm, so every transfer, lane and approach is unchanged:

  plinth, two storeys, a projecting storey band and cornice, grilled ground windows with
  stone surrounds, shuttered upper windows, a recessed door, a hipped tile roof with eaves.

Materials are the island's own (the grammar names semantics; they are mapped onto the
island's limewash, limestone, timber and roof tile, not the interior library's).

The existing pilasters, lintel, canopy, posts and the Passage House mark (leaf, plaque,
lantern) are kept and re-seated against the new wall depth. Edits an existing island
source into a NEW file; the adopted source is never written.

    python tools/blender/run.py tools/blender/rebuild_passage_house_exterior.py -- \
        --source <adopted st_maria_core.blend> --output <new revision>
"""
import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/blender'), str(ROOT / 'tools/blender/recipes')]
import source_dependencies  # noqa: E402
from recipes.house_grammar import emit_blender  # noqa: E402
from recipes.house_grammar.recipe import (BuildingRecipe, Course, Opening, PierSpec, RoofSection,  # noqa: E402
                                          Wing, build)

COLLECTION = 'B7 / Modern buildings'
MARK = 'Passage House mark / Passage House (Cortico) / '

# Island world frame: forward +Y, screen right -X. The block spans x -16..3, y 53..61.
BLOCK_X_CENTRE, BLOCK_X_WIDTH, FRONT_Y, FLOOR_Z, DEPTH = -6.5, 19.0, 53.0, 8.0, 8.0

REMOVE = [
    'B7 / Passage House', 'B7 / B7 / Passage House roof', 'B7 / Passage House entrance',
    'B10 / Passage House doorway', 'B10 / Passage House stone door jamb',
    'B10 / Passage House stone door jamb.001', 'B10 / Passage House door lintel',
    'B10 / Passage House shutter', 'B10 / Passage House shutter.001',
]
REMOVE_PREFIXES = ('B14 / Lodging upper window', 'B14 / Lodging upper shutter', 'B14 / Lodging window sill',
                   'B14 / Lodging ground window')

SEMANTIC = {
    'whitewash': 'B18 / passage-house weathered limewash',
    'rough_limestone': 'B7 / Mineral cut limestone',
    'old_limestone': 'B18 / Pale worn limestone edges',
    'dark_wood': 'B7 / Restrained warm timber',
    'roof_tile': 'sr_roof_tile.001',
    'smoked_glass': 'B10 Recessed door and window shadow',
    'wrought_iron': 'sr_wrought_iron',
}

# World X of each opening's centre.
GROUND_X = (-13.0, -9.0, -1.0)
UPPER_X = (-13.0, -9.0, -5.0, -1.0)
DOOR_X = -4.0


def lane(x):
    """Grammar lane offset for a world X (screen right is smaller X, positive offset)."""
    return round(-(x - BLOCK_X_CENTRE), 3)


def recipe():
    courses = (
        Course('plinth', 0.4, 'rough_limestone'),
        Course('storey', 3.0, 'whitewash', return_semantic='rough_limestone'),
        Course('band', 0.14, 'old_limestone', inset=-0.06),
        Course('storey', 3.8, 'whitewash', return_semantic='rough_limestone'),
        Course('cornice', 0.22, 'rough_limestone', inset=-0.10),
    )
    wing = Wing(id='main', lane_offset=0.0, width=BLOCK_X_WIDTH, depth=DEPTH, courses=courses,
                pier=PierSpec(width=0.30, project=0.10, splay=0.10, through='storey'))
    roof = RoofSection(wing='main', profile='hip', ridge_axis='Y', rise=2.2, overhang=0.5, thickness=0.2)
    openings = [Opening(id='door', kind='door', wing='main', lane_offset=lane(DOOR_X), width=1.24, height=2.2,
                        profile='plain', panels=4, drip=False, reveal=0.16)]
    for index, x in enumerate(GROUND_X):
        openings.append(Opening(id=f'ground_{index}', kind='window', wing='main', lane_offset=lane(x), width=0.96,
                                height=1.1, sill_z=1.15, grille=True, shutters=False))
    for index, x in enumerate(UPPER_X):
        openings.append(Opening(id=f'upper_{index}', kind='window', wing='main', lane_offset=lane(x), width=1.1,
                                height=1.3, sill_z=4.55, shutters=True))
    return BuildingRecipe(id='passage_house', version=1, wings=(wing,), roof=(roof,), openings=tuple(openings),
                          baked_axes=('Y',), metadata={'register': 'island exterior'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    if args.output.exists():
        parser.error('Preserve previous revisions; use a new output file')
    bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
    source_dependencies.assert_available()

    doomed = [bpy.data.objects[name] for name in REMOVE]
    doomed += [o for o in bpy.data.objects if o.name.startswith(REMOVE_PREFIXES)]
    for obj in doomed:
        bpy.data.objects.remove(obj, do_unlink=True)

    spec = recipe()
    records = build(spec)
    result = emit_blender.emit(records, name='passage_house', collection=bpy.data.collections[COLLECTION],
                               lane_y=0.0, back_x=0.0, namespace='PH_', recipe=spec)
    root = result['root']
    # Scaffold frame (depth X, screen right -Y) to the island's mirrored frame (depth Y, right -X).
    root.matrix_world = Matrix(((0, 1, 0, BLOCK_X_CENTRE), (1, 0, 0, FRONT_Y), (0, 0, 1, FLOOR_Z), (0, 0, 0, 1)))
    for obj in root.children:
        for slot in obj.material_slots:
            name = slot.material.name if slot.material else ''
            target = bpy.data.materials.get(SEMANTIC.get(name.split('.')[0][3:], ''))
            if name.startswith('sr_') and target is not None:
                slot.material = target

    # The wall is now a real wall 0.0 to -0.14 in front of the old decal plane: seat the mark on it.
    for obj in bpy.data.objects:
        if obj.name.startswith(MARK):
            obj.location.y += 0.14
            if obj.name[len(MARK):].split(' ')[0] in ('leaf', 'panel', 'band', 'ring'):
                obj.location.y += 0.14

    bpy.ops.file.pack_all()
    source_dependencies.assert_available()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()))
    print('PASSAGE HOUSE EXTERIOR OK')


if __name__ == '__main__':
    main()
