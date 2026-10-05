"""Move the Registry's public entrance along its front edge (a new revision).

The Passage House gate shares the Registry's left end, and two transfers that close
cannot both show their prompt. This slides the entrance's floor tongue (the way out,
extruded toward the camera) and the light the street throws through it to a new lane
position, leaving everything else alone. Edits an existing document into a NEW file;
the adopted source is never written.

    python tools/blender/run.py tools/blender/move_registry_exit.py -- \
        --source <adopted passage_office.blend> --output <new revision> --shift -1.9

`--shift` is in Blender Y (screen LEFT is positive), so a negative shift moves the
entrance to the screen right. Engine lane Y moves by the opposite sign.
"""
import argparse
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/blender'), str(ROOT / 'tools/blender/recipes')]
import source_dependencies  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--shift', type=float, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    if args.output.exists():
        parser.error('Preserve previous revisions; use a new output file')
    bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
    source_dependencies.assert_available()
    for name in ('exit_threshold', 'light_doorway_bounce'):
        obj = bpy.data.objects.get(name)
        if obj is None:
            raise ValueError(f'Expected {name} in the source')
        obj.location.y += args.shift
    bpy.context.scene['registry_exit_shift'] = args.shift
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()))
    print('REGISTRY EXIT MOVE OK')


if __name__ == '__main__':
    main()
