"""Photograph an interior source using camera records from native staged captures.

Reflect the runtime camera into the interior's authored frame, using the same
mapping as export_room_environment. Never save the source or rederive optics.
"""
import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_profiles
import stage_room_model as stager
import thestra_camera
import source_dependencies


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--frames', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--positions', type=float, nargs='+')
    parser.add_argument('--centre', type=float, default=3.8833)
    parser.add_argument('--clay', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    before = hashlib.sha256(args.source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
    source_dependencies.assert_available()
    scene = bpy.context.scene
    stager.base_lighting(0.13, (0,0,0), stager.INTERIOR_FILL)
    stager.scale_lamp_energy(scene, 0.3, 0.4)
    profile = render_profiles.resolve('draft')
    render_profiles.apply(scene, profile, device='AUTO')
    scene.view_settings.view_transform = 'AgX'
    if args.clay:
        scene.render.engine = 'BLENDER_WORKBENCH'
        scene.display.shading.light = 'STUDIO'
        scene.display.shading.color_type = 'SINGLE'
        scene.display.shading.single_color = (.65,.65,.65)
        scene.display.shading.show_shadows = True
        scene.display.shading.show_cavity = True
        scene.display.shading.show_backface_culling = True
    rows = []
    args.output.mkdir(parents=True, exist_ok=True)
    for frame in json.loads(args.frames.read_text(encoding='utf-8'))['frames']:
        if args.positions and not any(abs(frame['y'] - y) < 1e-7 for y in args.positions):
            continue
        record = copy.deepcopy(frame['cameraRecord'])
        record['eye']['y'] = args.centre - record['eye']['y']
        record['orientation']['forwardY'] *= -1
        record['orientation']['rightY'] *= -1
        camera = thestra_camera.create_or_update_camera(record, scene=scene, make_active=True)
        assert camera.matrix_world.to_3x3().determinant() > 0, 'Mirrored source camera basis'
        scene.render.image_settings.file_format = 'PNG'
        scene.render.filepath = str((args.output / f"{frame['y']:g}.png").resolve())
        bpy.ops.render.render(write_still=True)
        rows.append(dict(y=frame['y'], width=frame['width'], height=frame['height']))
    if not rows:
        raise ValueError('No matching native camera records')
    assert before == hashlib.sha256(args.source.read_bytes()).hexdigest()
    (args.output / 'review.json').write_text(json.dumps(dict(sourceSHA256=before,
        nativeFrames=str(args.frames), profile=profile.record(), clay=args.clay, frames=rows), indent=2)+'\n', encoding='utf-8')
    print('ROOM SOURCE REVIEW OK')


if __name__ == '__main__':
    main()
