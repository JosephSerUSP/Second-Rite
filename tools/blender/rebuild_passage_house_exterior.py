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
import interior as kit  # noqa: E402
import second_rite_asset_core as core  # noqa: E402
from first_stratum.common import box  # noqa: E402
from recipes.house_grammar.recipe import (BalconySpec, BuildingRecipe, Course, Opening, PierSpec,  # noqa: E402
                                          RoofSection, Wing, build)

COLLECTION = 'B7 / Modern buildings'
MARK = 'Passage House mark / Passage House (Cortico) / '

# Island world frame: forward +Y, screen right -X. The block spans x -16..3, y 53..61.
BLOCK_X_CENTRE, BLOCK_X_WIDTH, FRONT_Y, FLOOR_Z, DEPTH = -6.5, 19.0, 52.86, 8.0, 8.0
FLANK_RECESS = 0.9
LEAF_RECESS = 0.22

REMOVE = [
    'B7 / Passage House', 'B7 / B7 / Passage House roof', 'B7 / Passage House entrance',
    'B10 / Passage House doorway', 'B10 / Passage House stone door jamb',
    'B10 / Passage House stone door jamb.001', 'B10 / Passage House door lintel',
    'B10 / Passage House shutter', 'B10 / Passage House shutter.001',
]
REMOVE_PREFIXES = ('B14 / Lodging upper window', 'B14 / Lodging upper shutter', 'B14 / Lodging window sill',
                   'B14 / Lodging ground window', 'B14 / Lodging entry canopy', 'B14 / Lodging entry post',
                   'B18 / passage-house public entry')

SEMANTIC = {
    'whitewash': 'B18 / passage-house weathered limewash',
    'rough_limestone': 'B7 / Mineral cut limestone',
    'old_limestone': 'B18 / Pale worn limestone edges',
    'dark_wood': 'B7 / Restrained warm timber',
    'roof_tile': 'sr_roof_tile.001',
    'smoked_glass': 'B10 Recessed door and window shadow',
}

DOOR_X = -4.0
PAVILION_WIDTH = 5.8


def lane(x):
    """Grammar lane offset for a world X (screen right is smaller X, positive offset)."""
    return round(-(x - BLOCK_X_CENTRE), 3)


def storeys(top_extra=0.0, frieze=False):
    return (
        Course('plinth', 0.5, 'rough_limestone'),
        Course('storey', 3.0, 'whitewash', return_semantic='rough_limestone'),
        Course('band', 0.5 if frieze else 0.16, 'azulejo' if frieze else 'old_limestone', inset=-0.07),
        Course('storey', 3.8 + top_extra, 'whitewash', return_semantic='rough_limestone'),
        Course('cornice', 0.26, 'rough_limestone', inset=-0.12),
    )


def recipe():
    """A recessed, two-storey block with a taller entrance pavilion carrying the door, a
    blue tile frieze and a balcony: the Passage House reads as one house with a front."""
    pier = PierSpec(width=0.42, project=0.12, splay=0.12, through='storey')
    body = Wing(id='body', lane_offset=0.0, width=BLOCK_X_WIDTH, depth=DEPTH - FLANK_RECESS, setback=FLANK_RECESS,
                courses=storeys(frieze=True), pier=pier)
    pavilion = Wing(id='pavilion', lane_offset=lane(DOOR_X), width=PAVILION_WIDTH, depth=DEPTH, setback=0.0,
                    courses=storeys(frieze=True), pier=pier)
    roofs = (RoofSection(wing='body', profile='hip', ridge_axis='Y', rise=2.2, overhang=0.55, thickness=0.22),
             RoofSection(wing='pavilion', profile='gable', ridge_axis='X', rise=3.2, overhang=0.5, thickness=0.2))
    openings = [Opening(id='door', kind='door', wing='pavilion', lane_offset=lane(DOOR_X), width=1.24, height=2.2,
                        profile='civic', panels=4, reveal=0.16)]
    openings.append(Opening(id='gallery', kind='window', wing='pavilion', lane_offset=lane(DOOR_X), width=1.3,
                            height=2.5, sill_z=4.6, shutters=True, pediment=True,
                            balcony=BalconySpec(width=3.4, depth=0.85, rail_height=1.0, brackets=3)))
    for index, x in enumerate((-13.8, -10.6, -7.8)):
        openings.append(Opening(id=f'ground_{index}', kind='window', wing='body', lane_offset=lane(x), width=1.0,
                                height=1.6, sill_z=1.2, grille=True, reveal=0.22))
        openings.append(Opening(id=f'upper_{index}', kind='window', wing='body', lane_offset=lane(x), width=1.05,
                                height=2.1, sill_z=4.5, shutters=True, pediment=index == 1, reveal=0.22,
                                balcony=BalconySpec(width=1.7, depth=0.6, rail_height=0.95, brackets=2)))
    openings.append(Opening(id='ground_east', kind='window', wing='body', lane_offset=lane(0.9), width=1.0,
                            height=1.6, sill_z=1.2, grille=True, reveal=0.22))
    openings.append(Opening(id='upper_east', kind='window', wing='body', lane_offset=lane(0.9), width=1.05,
                            height=2.1, sill_z=4.5, shutters=True, reveal=0.22,
                            balcony=BalconySpec(width=1.7, depth=0.6, rail_height=0.95, brackets=2)))
    return BuildingRecipe(id='passage_house', version=2, wings=(body, pavilion), roof=roofs,
                          openings=tuple(openings), baked_axes=('Y',), metadata={'register': 'island exterior'})


def add_chimneys(collection, stone, cap):
    root = bpy.data.objects.new('Passage House chimneys', None)
    collection.objects.link(root)
    for index, x in enumerate((-12.5, -1.5)):
        parts = (('stack', (0.95, 0.95, 3.0), (x, 57.4, 18.0), stone), ('cap', (1.2, 1.2, 0.18), (x, 57.4, 19.58), cap))
        for name, size, loc, material in parts:
            obj = box(f'Passage House chimney {index} / {name}', root, size, loc, material, core)
            for owner in list(obj.users_collection):
                owner.objects.unlink(obj)
            collection.objects.link(obj)


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
            semantic = name.split('.')[0][3:]
            target = bpy.data.materials.get(SEMANTIC.get(semantic, ''))
            if name.startswith('sr_') and target is None and semantic in ('azulejo', 'wrought_iron'):
                target = kit.material(semantic)
            if name.startswith('sr_') and target is not None:
                slot.material = target
    add_chimneys(bpy.data.collections[COLLECTION], kit.material('rough_limestone'), kit.material('old_limestone'))

    # The pavilion face is the old wall plane, so the plaque and lantern stay; the leaf drops into the reveal.
    for obj in bpy.data.objects:
        if obj.name.startswith(MARK) and obj.name[len(MARK):].split(' ')[0] in ('leaf', 'panel', 'band', 'ring'):
            obj.location.y += LEAF_RECESS

    bpy.ops.file.pack_all()
    source_dependencies.assert_available()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()))
    print('PASSAGE HOUSE EXTERIOR OK')


if __name__ == '__main__':
    main()
