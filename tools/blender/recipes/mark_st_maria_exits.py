"""Extend the Praca's set to the camera's reach and mark its unmarked exits.

Two findings from the full-width capture of map 17:

- The set stops at the quay end. Standing on ``quay_stair`` the camera still
  sees to y = -4.67, so roughly a third of that screen is void. Buildings ran
  y 0..32; the lane plus half a screen either side needs -4.67..28.37.
- Three of the five exits have no architecture at all. ``quay_stair``,
  ``churchyard_stair`` and ``east_backstreet`` are invisible anchors on blank
  wall, so a player cannot see where to go.

The portals here are deliberately plain massing named ``MARKER_*``: they say
WHERE an exit is without pretending to design the transition, and they are
meant to be replaced. ``chapel_door`` and ``alicia_door`` already read as
doorways in the modelled houses and are left alone.

A surgical edit, not a rebuild -- ``st_maria_praca.py`` would destroy hand
authoring. Blender must not have the document open; it holds no lock, so a
running session would overwrite this on its next save.

    blender -b -noaudio --factory-startup -P tools/blender/recipes/mark_st_maria_exits.py

``plan()`` is separate from the applier so the same geometry can be pushed over
the live bridge instead, without a second copy of the numbers.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

try:
    import bpy
except ImportError:  # plan() is importable outside Blender, so the live bridge
    bpy = None       # can push the same geometry without a second copy of it.

ROOT = Path(__file__).resolve().parents[3]
DOCUMENT = ROOT / "projects/hichaukitoden-game/assets/authoring/environments/st_maria_praca.blend"
COLLECTION = "20_ARCHITECTURE"
LIMESTONE, DARK = "sr_old_limestone", "sr_dark_wood"
#: Wall face sits at x=14; portals are set into it and read from the lane.
WALL_FACE = 14.0
#: Exits with no architecture. chapel_door and alicia_door already have doorways.
UNMARKED_EXITS = (("quay", 0.43), ("churchyard", 9.83), ("backstreet", 23.70))


def plan():
    """Every box this recipe adds: (name, centre, dimensions, material)."""
    boxes = []
    for tag, y in UNMARKED_EXITS:
        boxes += [
            (f"MARKER_{tag}_recess", (WALL_FACE + 0.6, y, 1.35), (1.6, 2.2, 2.7), DARK),
            (f"MARKER_{tag}_jamb_a", (WALL_FACE - 0.15, y - 1.35, 1.5), (0.5, 0.5, 3.0), LIMESTONE),
            (f"MARKER_{tag}_jamb_b", (WALL_FACE - 0.15, y + 1.35, 1.5), (0.5, 0.5, 3.0), LIMESTONE),
            (f"MARKER_{tag}_lintel", (WALL_FACE - 0.15, y, 3.15), (0.5, 3.2, 0.3), LIMESTONE),
        ]
    return boxes


def _box(name, centre, dims, material, collection):
    mesh = bpy.data.meshes.new(name + "_mesh")
    hx, hy, hz = (d * .5 for d in dims)
    verts = [(sx * hx, sy * hy, sz * hz)
             for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1),
             (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    if material:
        existing = bpy.data.materials.get(material)
        if existing is None:
            raise SystemExit(f"material {material!r} is missing from the document")
        mesh.materials.append(existing)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.location = centre
    return obj


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--document", type=Path, default=DOCUMENT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    if bpy is None:
        raise SystemExit("this applier must run inside Blender")
    bpy.ops.wm.open_mainfile(filepath=str(args.document.resolve()))
    collection = bpy.data.collections.get(COLLECTION)
    if collection is None:
        raise SystemExit(f"collection {COLLECTION} is missing; wrong document?")
    boxes = plan()
    clashes = [name for name, *_ in boxes if bpy.data.objects.get(name)]
    if clashes:
        raise SystemExit("already marked; remove first: " + ", ".join(clashes))

    print(f"extending the set past the quay end and adding {len(boxes)} marker boxes")
    if args.dry_run:
        for name, centre, dims, _m in boxes:
            print(f"  {name:30} at {centre} size {dims}")
        print("DRY RUN, nothing written")
        return

    source = bpy.data.objects.get("ARCH_west_house")
    if source is None:
        raise SystemExit("ARCH_west_house is missing; wrong document?")
    if bpy.data.objects.get("ARCH_quay_end_house") is None:
        end = source.copy()
        end.data = source.data.copy()
        end.name = "ARCH_quay_end_house"
        collection.objects.link(end)
        end.location = (16.0, -5.0, 0.0)

    curb = bpy.data.objects.get("ARCH_low_curb")
    if curb is not None:
        # The curb ended at y=24.1 and -0.4; carry it to the camera's reach.
        curb.scale.y = 33.04 / 24.5

    for name, centre, dims, material in boxes:
        _box(name, centre, dims, material, collection)

    backup = args.document.with_suffix(".blend.bak")
    shutil.copy2(args.document, backup)
    bpy.ops.wm.save_mainfile(filepath=str(args.document.resolve()))
    print(f"SAVED {args.document} (previous version kept at {backup.name})")


if __name__ == "__main__":
    main()
