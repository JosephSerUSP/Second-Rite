"""Scaffold the Registry: writing light, narrow ledger, waiting space.

Narrative authority: map 17's Registrar Celina commands and arrival walkthrough.
This scaffolds a new source once; subsequent authored changes belong in the blend.
"""
import argparse
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/blender'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import interior as kit
import furnishings as furn
import render_profiles

ASSET_ID = 'passage_office'
EXIT_Y = 1.0833
NPC_Y = 5.5333


def build():
    room = kit.Interior(ASSET_ID, half_width=4.65, depth=6.8, ceiling_z=3.65)
    room.floor(mat=room.terracotta)
    window = (-3.6, -1.7, 1.4, 2.95)
    room.back_wall(openings=[window])
    room.side_walls()
    room.ceiling(beams=3)
    room.window(*window)
    furn.window_dressing(room, 'writing_window', *window)
    furn.azulejo_dado(room, height=0.95)
    tab_x, tab_y = room.exit_threshold(2.8)

    # The desk is deep enough to leave the actor lane clear at X=0.
    furn.table(room, 'registrar_desk', (1.75, -1.65), length=2.25, width=1.05, height=0.83)
    with room.surface(0.87):
        furn.ledger(room, 'current_ledger', (1.58, -1.8), open_book=True)
        furn.ledger(room, 'previous_ledger', (1.85, -0.9))
        furn.seal_stamp(room, 'registration_seal', (1.48, -2.38))
    furn.chair(room, 'registrar_chair', (2.55, -1.65))
    furn.cabinet(room, 'archive_cabinet', (room.back_x - 0.55, 2.9),
                 width=1.5, depth=0.65, height=2.35)
    furn.table(room, 'visitor_bench', (1.2, 1.3), length=1.65, width=0.43, height=0.44)
    furn.jar(room, 'water_jar', (room.back_x - 0.4, -0.5))
    furn.lantern(room, 'office_lantern', y=0.2, z=2.5)
    room.window_light(-2.65, 2.2)
    room.doorway_light(tab_x, tab_y)
    room.finish()
    render_profiles.apply(bpy.context.scene, render_profiles.resolve('export'), device='AUTO')
    bpy.context.scene.view_settings.view_transform = 'AgX'
    bpy.context.scene.render.resolution_x = 256
    bpy.context.scene.render.resolution_y = 240
    bpy.context.scene['registry_exit_y'] = EXIT_Y
    bpy.context.scene['registry_npc_y'] = NPC_Y
    return room


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blend', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    if args.blend.exists():
        parser.error('Source already exists; edit the blend directly.')
    room = build()
    bpy.context.view_layer.update()
    blend = kit.save_source_blend(args.blend, force=False)
    kit.report(room, blend)


if __name__ == '__main__':
    main()
