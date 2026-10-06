"""Rebuild every St. Maria island building with the house grammar (a new revision).

The adopted island builds each building as a flat limewash box under a plain prism roof, with
dark decal doors, windows and shutters laid on the wall. The interiors were authored with real
depth (reveals, surrounds, courses); the exterior should read at the same level. This replaces
each box, its roof and its decal trim with a grammar building at the SAME footprint, door
positions and base height, so every lane, transfer, anchor and approach is unchanged:

  plinth, one or two storeys, projecting bands and a cornice, stone-surrounded and grilled
  windows, shuttered upper windows with iron balconettes, recessed doors, and a hipped or
  gabled tile roof with eaves.

The Passage House keeps its bespoke recipe (recessed flanks, gabled entrance pavilion, blue
tile frieze, gallery balcony, chimneys) and the Passage House mark (leaf, plaque, lantern).
Materials are the island's own: each building keeps its own limewash.

Edits an existing island source into a NEW file; the adopted source is never written.

    python tools/blender/run.py tools/blender/rebuild_island_exteriors.py -- \
        --source <adopted st_maria_core.blend> --output <new revision>
"""
import argparse
import re
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/blender'), str(ROOT / 'tools/blender/recipes')]
import source_dependencies  # noqa: E402
import interior as kit  # noqa: E402
import second_rite_asset_core as core  # noqa: E402
from first_stratum.common import box  # noqa: E402
from recipes.house_grammar import emit_blender  # noqa: E402
from recipes.house_grammar.recipe import (BalconySpec, BuildingRecipe, Course, Opening, PierSpec,  # noqa: E402
                                          RoofSection, Wing, build)

COLLECTION = 'B7 / Modern buildings'
MARK = 'Passage House mark / Passage House (Cortico) / '
LEAF_PARTS = ('leaf', 'panel', 'band', 'ring')
LEAF_RECESS = 0.22

# The Passage House's own recipe is kept apart: it is the pilot the others follow.
PASSAGE_HOUSE = 'Passage House'
BLOCK_X_CENTRE, BLOCK_X_WIDTH, FRONT_Y, FLOOR_Z, DEPTH = -6.5, 19.0, 52.86, 8.0, 8.0
FLANK_RECESS, DOOR_X, PAVILION_WIDTH = 0.9, -4.0, 5.8

# Island masses and their roofs. Style: house (shuttered, balconettes), shop (ground-floor shop
# door, board over the street), civic (deep reveals, plain bands), service (shed: few openings).
BUILDINGS = {
    'Forge': dict(style='shop'),
    'Pub': dict(style='shop'),
    'Bakery: one building': dict(style='shop'),
    'Passage House': dict(style='bespoke'),
    'Household west': dict(style='house'),
    'Household east': dict(style='house'),
    'Chapel': dict(style='civic', roof='gable_front'),
    'Pub neighbour west': dict(style='house'),
    'Quay stores': dict(style='service'),
    'Forge rear shed': dict(style='service'),
    'Market west frontage': dict(style='house'),
    'Market east frontage': dict(style='house'),
    'Market north corner': dict(style='house'),
    'Residential northeast wing': dict(style='house'),
    'Residential west wing': dict(style='house'),
    'Praca south frontage': dict(style='house'),
    'Praca east frontage': dict(style='civic'),
    'Upper quarter west': dict(style='house'),
    'Upper quarter north': dict(style='house'),
}

TRIM_NAME = re.compile(r'(doorway|door jamb|door lintel|shutter|private door|window|shop door)')
DOOR_NAME = re.compile(r'(doorway|private door|shop door)')
KEEP_NAME = re.compile(r'(mark|home upper|approach|landing|well|bench)')
EXTRA_REMOVE = (
    'B13 / Registry upper window', 'B13 / Registry blue shutter', 'B13 / Registry blue lintel',
    'B14 / Lodging ', 'B18 / passage-house public entry',
)
KEEP_ENTRANCE = 'B7 / Bakery upper home entrance'

SEMANTIC = {
    'rough_limestone': 'B7 / Mineral cut limestone',
    'old_limestone': 'B18 / Pale worn limestone edges',
    'dark_wood': 'B7 / Restrained warm timber',
    'roof_tile': 'sr_roof_tile.001',
    'smoked_glass': 'B10 Recessed door and window shadow',
}


# --- geometry helpers ---------------------------------------------------------------------
def world_box(obj):
    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    return ([min(c[i] for c in corners) for i in range(3)], [max(c[i] for c in corners) for i in range(3)])


def lane_of(x, cx):
    """Grammar lane offset for a world X (screen right is smaller X, positive offset)."""
    return round(-(x - cx), 3)


# --- the generic building -----------------------------------------------------------------
def storeys_for(height, frieze=False):
    plinth, cornice, band = 0.45, 0.24, 0.16
    rest = height - plinth - cornice
    count = max(1, round(rest / 3.1))
    storey = (rest - (count - 1) * band) / count
    courses = [Course('plinth', plinth, 'rough_limestone')]
    for index in range(count):
        courses.append(Course('storey', round(storey, 4), 'whitewash', return_semantic='rough_limestone'))
        if index < count - 1:
            courses.append(Course('band', band, 'old_limestone', inset=-0.06))
    courses.append(Course('cornice', cornice, 'rough_limestone', inset=-0.11))
    return tuple(courses), count, round(storey, 4), plinth, band


def bays(length, doors, clearance, edge=1.0, spacing=3.1):
    """Window positions along a face of ``length``, centred on 0, clear of the doors."""
    usable = length - 2.0 * edge
    if usable < 1.0:
        return []
    count = max(1, round(usable / spacing))
    step = usable / count
    positions = [-usable / 2.0 + step * (index + 0.5) for index in range(count)]
    return [p for p in positions if all(abs(p - d) >= clearance for d in doors)]


def generic_recipe(name, spec, lo, hi, doors):
    """doors: list of (face, along, width, height) with ``along`` in world coordinate."""
    width, depth, height = hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]
    cx = (lo[0] + hi[0]) / 2.0
    cy = (lo[1] + hi[1]) / 2.0
    courses, count, storey, plinth, band = storeys_for(height)
    wing = Wing(id='main', lane_offset=0.0, width=round(width, 3), depth=round(depth, 3), courses=courses,
                pier=PierSpec(width=0.34, project=0.10, splay=0.10, through='storey'))
    gable_front = spec.get('roof') == 'gable_front' or depth > width * 1.15
    ridge_axis = 'X' if gable_front else 'Y'
    span = width if gable_front else depth
    rise = max(1.5, min(3.4, span * 0.26))
    roof = RoofSection(wing='main', profile='gable' if gable_front else 'hip', ridge_axis=ridge_axis,
                       rise=round(rise, 3), overhang=0.5, thickness=0.2)

    openings = []
    taken = {'front': [], 'left': [], 'right': []}
    style = spec['style']
    for index, (face, along, door_w, door_h) in enumerate(doors):
        centred = (along - cx) if face == 'front' else (along - cy)
        taken[face].append(centred)
        offset = lane_of(along, cx) if face == 'front' else round(along - lo[1], 3)
        profile = 'plain'
        openings.append(Opening(id=f'door_{face}_{index}', kind='door', wing='main', lane_offset=offset,
                                width=door_w, height=door_h, profile=profile, panels=4,
                                elevation=face, reveal=0.16, drip=False))
    for face in ('front', 'left', 'right'):
        length = width if face == 'front' else depth
        for position in bays(length, taken[face], clearance=1.9):
            offset = round(-position, 3) if face == 'front' else round(position + depth / 2.0, 3)
            slug = f'{face}_{offset}'.replace('.', '_').replace('-', 'm')
            for level in range(count):
                base = plinth + level * (storey + band)
                ground = level == 0
                if count == 1:
                    sill, height = round(plinth + 1.0, 3), round(min(1.7, storey - 1.4), 3)
                else:
                    sill, height = round(base + (0.7 if ground else 0.8), 3), round(min(1.35, storey - 1.25), 3)
                balcony = None
                if style == 'house' and not ground and face == 'front':
                    balcony = BalconySpec(width=1.6, depth=0.55, rail_height=0.95, brackets=2)
                openings.append(Opening(
                    id=f'w{level}_{slug}', kind='window', wing='main', lane_offset=offset, width=1.0,
                    height=height, sill_z=sill, grille=ground and style != 'civic', shutters=not ground,
                    reveal=0.2, pediment=style == 'civic' and not ground and face == 'front', elevation=face,
                    balcony=balcony))
    return BuildingRecipe(id=name.lower().replace(' ', '_').replace(':', ''), version=2, wings=(wing,),
                          roof=(roof,), openings=tuple(openings), baked_axes=('Y',),
                          metadata={'register': 'island exterior', 'style': style}), cx


# --- the Passage House (bespoke) ---------------------------------------------------------------
def passage_house_recipe():
    def stack():
        return (
            Course('plinth', 0.5, 'rough_limestone'),
            Course('storey', 3.0, 'whitewash', return_semantic='rough_limestone'),
            Course('band', 0.5, 'azulejo', inset=-0.07),
            Course('storey', 3.8, 'whitewash', return_semantic='rough_limestone'),
            Course('cornice', 0.26, 'rough_limestone', inset=-0.12),
        )

    pier = PierSpec(width=0.42, project=0.12, splay=0.12, through='storey')
    lane = lambda x: lane_of(x, BLOCK_X_CENTRE)  # noqa: E731
    body = Wing(id='body', lane_offset=0.0, width=BLOCK_X_WIDTH, depth=DEPTH - FLANK_RECESS, setback=FLANK_RECESS,
                courses=stack(), pier=pier)
    pavilion = Wing(id='pavilion', lane_offset=lane(DOOR_X), width=PAVILION_WIDTH, depth=DEPTH, setback=0.0,
                    courses=stack(), pier=pier)
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


def add_chimneys(collection, label, positions, stone, cap, base_z):
    root = bpy.data.objects.new(f'{label} chimneys', None)
    collection.objects.link(root)
    for index, (x, y) in enumerate(positions):
        parts = (('stack', (0.95, 0.95, 3.0), (x, y, base_z + 1.5), stone),
                 ('cap', (1.2, 1.2, 0.18), (x, y, base_z + 3.08), cap))
        for name, size, loc, material in parts:
            obj = box(f'{label} chimney {index} / {name}', root, size, loc, material, core)
            for owner in list(obj.users_collection):
                owner.objects.unlink(obj)
            collection.objects.link(obj)


# --- the revision ---------------------------------------------------------------------------
def place(root, cx, front_y, floor_z):
    """Scaffold frame (depth X, screen right -Y) to the island's mirrored frame (depth Y, right -X)."""
    root.matrix_world = Matrix(((0, 1, 0, cx), (1, 0, 0, front_y), (0, 0, 1, floor_z), (0, 0, 0, 1)))


def apply_materials(root, limewash):
    for obj in root.children:
        for slot in obj.material_slots:
            name = slot.material.name if slot.material else ''
            if not name.startswith('sr_'):
                continue
            semantic = name.split('.')[0][3:]
            target = limewash if semantic == 'whitewash' else bpy.data.materials.get(SEMANTIC.get(semantic, ''))
            if target is None and semantic in ('azulejo', 'wrought_iron'):
                target = kit.material(semantic)
            if target is not None:
                slot.material = target


def collect_doors(masses):
    """Door-like decals sitting on a face of each mass, read before anything is removed."""
    found = {name: [] for name in masses}
    for obj in bpy.data.objects:
        if obj.type != 'MESH' or not DOOR_NAME.search(obj.name) or KEEP_NAME.search(obj.name):
            continue
        if obj.name.startswith('Passage House mark'):
            continue
        lo, hi = world_box(obj)
        c = [(lo[i] + hi[i]) / 2.0 for i in range(3)]
        for name, (mlo, mhi) in masses.items():
            if not (mlo[2] - 0.2 <= lo[2] <= mhi[2]):
                continue
            width = max(hi[0] - lo[0], hi[1] - lo[1])
            height = hi[2] - lo[2]
            if abs(c[1] - mlo[1]) < 0.3 and mlo[0] < c[0] < mhi[0]:
                found[name].append(('front', c[0], width, height, lo[2] - mlo[2]))
            elif abs(c[0] - mhi[0]) < 0.3 and mlo[1] < c[1] < mhi[1]:
                found[name].append(('left', c[1], width, height, lo[2] - mlo[2]))
            elif abs(c[0] - mlo[0]) < 0.3 and mlo[1] < c[1] < mhi[1]:
                found[name].append(('right', c[1], width, height, lo[2] - mlo[2]))
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--only', nargs='*', help='Rebuild only these buildings (a trial)')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    if args.output.exists():
        parser.error('Preserve previous revisions; use a new output file')
    bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
    source_dependencies.assert_available()
    collection = bpy.data.collections[COLLECTION]

    names = [n for n in BUILDINGS if not args.only or n in args.only]
    masses, roofs, limewash = {}, {}, {}
    for name in names:
        mass = bpy.data.objects[f'B7 / {name}']
        masses[name] = world_box(mass)
        limewash[name] = mass.data.materials[0]
        roofs[name] = bpy.data.objects[f'B7 / B7 / {name} roof']
    doors = collect_doors(masses)

    doomed = []
    for name in names:
        doomed += [bpy.data.objects[f'B7 / {name}'], roofs[name]]
    for obj in bpy.data.objects:
        if obj.name.startswith(EXTRA_REMOVE) and (not args.only or 'Passage House' in args.only or 'Lodging' not in obj.name):
            doomed.append(obj)
        elif obj.type == 'MESH' and obj.name.startswith('B7 / ') and obj.name.endswith(' entrance') \
                and obj.name != KEEP_ENTRANCE:
            doomed.append(obj)
        elif obj.type == 'MESH' and obj.name.startswith('B10 / ') and TRIM_NAME.search(obj.name) \
                and not KEEP_NAME.search(obj.name):
            lo, hi = world_box(obj)
            c = [(lo[i] + hi[i]) / 2.0 for i in range(3)]
            for mlo, mhi in masses.values():
                if mlo[0] - 0.4 <= c[0] <= mhi[0] + 0.4 and mlo[1] - 0.4 <= c[1] <= mhi[1] + 0.4 \
                        and mlo[2] - 0.2 <= c[2] <= mhi[2]:
                    doomed.append(obj)
                    break
    for obj in {o.name: o for o in doomed if o.name in bpy.data.objects}.values():
        bpy.data.objects.remove(obj, do_unlink=True)

    built = {}
    for name in names:
        lo, hi = masses[name]
        if name == PASSAGE_HOUSE:
            spec = passage_house_recipe()
            cx, front_y, floor = BLOCK_X_CENTRE, FRONT_Y, FLOOR_Z
        else:
            door_list = [(f, a, round(max(w, 0.9), 2), round(min(max(h, 1.9), 2.2), 2))
                         for f, a, w, h, _ in doors[name]]
            spec, cx = generic_recipe(name, BUILDINGS[name], lo, hi, door_list)
            front_y, floor = lo[1], lo[2]
        records = build(spec)
        result = emit_blender.emit(records, name=spec.id, collection=collection, lane_y=0.0, back_x=0.0,
                                   namespace=spec.id[:3].upper() + '_', recipe=spec)
        place(result['root'], cx, front_y, floor)
        apply_materials(result['root'], limewash[name])
        built[name] = result['root']

    if PASSAGE_HOUSE in names:
        add_chimneys(collection, 'Passage House', [(-12.5, 57.4), (-1.5, 57.4)], kit.material('rough_limestone'),
                     kit.material('old_limestone'), 16.5)
        # The pavilion face is the old wall plane, so the plaque and lantern stay; the leaf drops into the reveal.
        for obj in bpy.data.objects:
            if obj.name.startswith(MARK) and obj.name[len(MARK):].split(' ')[0] in LEAF_PARTS:
                obj.location.y += LEAF_RECESS

    bpy.ops.file.pack_all()
    source_dependencies.assert_available()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()))
    print('ISLAND EXTERIORS OK', len(built), 'buildings')


if __name__ == '__main__':
    main()
