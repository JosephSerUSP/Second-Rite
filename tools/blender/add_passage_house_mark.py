"""Give the Passage House one mark on both of its street faces (a new revision).

The house has a public front on the Praca (the Registry) and a lower, domestic face on
the Cortico, and the player crosses between them. Inside, they are one house: a dark
panelled hardwood door with iron bands, blue-and-white azulejo, a wrought-iron lantern.
Outside, the two doors were different buildings: a near-black leaf on one, a grey-blue
one on the other, and nothing in common. This adds the same three things to both, in the
same places, so the doors read as one house from either street:

  * a dark panelled hardwood leaf, iron-banded, with a brass ring, in the doorway;
  * a small azulejo plaque on the wall to the screen RIGHT of the door;
  * a wrought-iron lantern, with a real warm light, to the screen LEFT of the door.

Edits an existing island source into a NEW file; the adopted source is never written.

    python tools/blender/run.py tools/blender/add_passage_house_mark.py -- \
        --source projects/<project>/assets/authoring/environments/st_maria_core.blend \
        --output projects/<project>/assets/authoring/candidates/st_maria_core/st_maria_core_r2.blend
"""
import argparse
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/blender'), str(ROOT / 'tools/blender/recipes')]
import interior as kit  # noqa: E402
import second_rite_asset_core as core  # noqa: E402
import source_dependencies  # noqa: E402
from first_stratum.common import box  # noqa: E402

COLLECTION = 'B10 Addresses, doors and terrain-following service routes'

# Door centre x, wall's front face y, door floor z, door top z. The camera looks along +Y
# with screen RIGHT toward -X, so "right of the door" is smaller x.
HOUSES = {
    'Passage Office (Praca)': dict(cx=4.0, wall=70.86, z0=14.07, z1=16.23),
    'Passage House (Cortico)': dict(cx=-4.0, wall=52.86, z0=8.07, z1=10.23),
}


def build_mark(label, spec, mats, collection):
    cx, wall, z0, z1 = spec['cx'], spec['wall'], spec['z0'], spec['z1']
    root = bpy.data.objects.new(f'Passage House mark / {label}', None)
    collection.objects.link(root)
    made = []

    def part(name, size, loc, material):
        obj = box(f'Passage House mark / {label} / {name}', root, size, loc, material, core)
        for owner in list(obj.users_collection):
            owner.objects.unlink(obj)
        collection.objects.link(obj)
        made.append(obj)
        return obj

    # --- the leaf: dark hardwood, two raised panels, iron bands, a brass ring -------------
    height = z1 - z0 - 0.08
    leaf_y = wall + 0.015
    part('leaf', (1.18, 0.04, height), (cx, leaf_y, z0 + height / 2.0), mats['wood'])
    for index, dx in enumerate((-0.28, 0.28)):
        part(f'panel {index}', (0.44, 0.02, height * 0.62), (cx + dx, leaf_y - 0.02, z0 + height * 0.5), mats['wood_dark'])
    for index, frac in enumerate((0.16, 0.5, 0.84)):
        part(f'band {index}', (1.2, 0.03, 0.06), (cx, leaf_y - 0.035, z0 + height * frac), mats['iron'])
    part('ring', (0.09, 0.03, 0.09), (cx - 0.38, leaf_y - 0.06, z0 + height * 0.48), mats['bronze'])

    # --- the plaque: screen right of the door, azulejo in a stone frame --------------------
    px, pz = cx - 1.1, z0 + 1.2
    part('plaque frame', (0.5, 0.05, 0.5), (px, wall - 0.025, pz), mats['stone'])
    part('plaque tile', (0.42, 0.03, 0.42), (px, wall - 0.06, pz), mats['azulejo'])

    # --- the lantern: screen left of the door, wrought iron, a real light --------------------
    lx, lz = cx + 1.0, z1 + 0.15
    part('lantern bracket', (0.04, 0.2, 0.04), (lx, wall - 0.1, lz + 0.18), mats['iron'])
    part('lantern cage', (0.16, 0.16, 0.24), (lx, wall - 0.2, lz), mats['iron'])
    part('lantern flame', (0.09, 0.09, 0.14), (lx, wall - 0.2, lz), mats['flame'])
    data = bpy.data.lights.new(f'Passage House mark / {label} / lantern light', 'POINT')
    data.energy, data.color, data.shadow_soft_size = 60.0, (1.0, 0.78, 0.5), 0.12
    light = bpy.data.objects.new(data.name, data)
    collection.objects.link(light)
    light.parent = root
    light.location = (lx, wall - 0.3, lz)
    return root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    if args.output.exists():
        parser.error('Preserve previous revisions; use a new output file')
    bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
    source_dependencies.assert_available()
    collection = bpy.data.collections[COLLECTION]
    mats = dict(wood=kit.material('dark_wood'), iron=kit.material('wrought_iron'),
                bronze=kit.material('oxidized_bronze'), stone=kit.material('rough_limestone'),
                azulejo=kit.material('azulejo'), flame=kit.emissive('sr_lamp_glow', (0.46, 0.28, 0.13)))
    mats['wood_dark'] = kit.material('charcoal')
    for label, spec in HOUSES.items():
        build_mark(label, spec, mats, collection)
    # Pack the images: a revision is copied between folders, and relative paths do not travel.
    bpy.ops.file.pack_all()
    source_dependencies.assert_available()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()))
    print('PASSAGE HOUSE MARK OK')


if __name__ == '__main__':
    main()
