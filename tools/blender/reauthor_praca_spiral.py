"""Re-author st_maria_praca.blend for the spiral layout.

    blender --background <praca.blend> --python tools/blender/reauthor_praca_spiral.py -- --write

The blend was authored for the town as it stood BEFORE the spiral rewiring. Its
anchors sit at the old door positions and it still carries an `alicia_door` and
an `east_backstreet`, neither of which the Praca has any more. Rendering it as
it stands produces a picture of the previous town whose painted doors miss the
wired doorways.

This is deliberately SURGICAL. The file is owner-authored - it was last touched
by hand - so nothing here rebuilds architecture, re-lights, or re-materials
anything. It moves anchors, moves the single modelled door to the one interior
the Praca still has, and deletes what the rewiring genuinely removed.

World positions, not pixels. The lane is 23.699 world units long in both the old
900px plate at 34.6 px/unit and a new 730px plate at 27.4286 - the two scales
agree about world LENGTH and disagree about pixel DENSITY. So the door positions
below are lane y in world units, and the plate width follows from the render
scale rather than the other way round.

Run without `--write` to see what it would do.
"""

import argparse
import sys

import bpy

# Lane y, in world units, from SCREENS["praca"] in tools/towngen/build_town.py.
# west_churchyard and east_cortico sit ON the lane bounds: they are street
# continuations, not doors.
MOVES = {
    "quay_stair": 3.179,        # was 0.434
    "chapel_door": 16.763,      # was 20.810
    "east_cortico": 23.699,     # renamed from east_backstreet, was 23.700
    "west_churchyard": 0.0,     # renamed from churchyard_stair, was 9.827
}
RENAMES = {
    "churchyard_stair": "west_churchyard",   # now the WEST STREET BOUND
    "east_backstreet": "east_cortico",       # the Backstreet became the Cortico
}
# Alicia lives over the padaria on Market Row now; Celina works in the Passage
# House rather than standing in the square.
DELETIONS = ("alicia_door", "npc_registrar", "Alicia_door")

DOOR_MESH = "BUILD_door1"
DOOR_TARGET = 16.763            # the Chapel: the Praca's only interior door


def argv():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--write", action="store_true", help="save the .blend")
    return p.parse_args(a)


def base_name(name):
    """`LD_quay_stair` and `quay_stair` are the same anchor, authored twice."""
    return name[3:] if name.startswith("LD_") else name


def main():
    a = argv()
    changed, removed = [], []

    for o in list(bpy.data.objects):
        stem = base_name(o.name)
        if any(stem == d or stem.endswith(d) for d in DELETIONS):
            removed.append(o.name)
            if a.write:
                bpy.data.objects.remove(o, do_unlink=True)
            continue
        if stem in RENAMES:
            new_stem = RENAMES[stem]
            new_name = ("LD_" + new_stem) if o.name.startswith("LD_") else new_stem
            target = MOVES[new_stem]
            changed.append("%-34s -> %-22s y %.3f -> %.3f"
                           % (o.name, new_name, o.location.y, target))
            if a.write:
                o.name = new_name
                o.location.y = target
            continue
        if stem in MOVES and abs(o.location.y - MOVES[stem]) > 1e-4:
            changed.append("%-34s    %-22s y %.3f -> %.3f"
                           % (o.name, "", o.location.y, MOVES[stem]))
            if a.write:
                o.location.y = MOVES[stem]

    # The one modelled door follows the one interior that is left.
    door = bpy.data.objects.get(DOOR_MESH)
    if door is not None and abs(door.location.y - DOOR_TARGET) > 1e-4:
        changed.append("%-34s    %-22s y %.3f -> %.3f  (the Chapel)"
                       % (DOOR_MESH, "", door.location.y, DOOR_TARGET))
        if a.write:
            door.location.y = DOOR_TARGET
    guide = bpy.data.objects.get("SCALE_Chapel_door_1.05x2.15m")
    if guide is not None and abs(guide.location.y - DOOR_TARGET) > 1e-4:
        changed.append("%-34s    %-22s y %.3f -> %.3f"
                       % (guide.name, "", guide.location.y, DOOR_TARGET))
        if a.write:
            guide.location.y = DOOR_TARGET

    print("MOVED / RENAMED")
    for c in changed:
        print("  " + c)
    print("REMOVED")
    for r in removed:
        print("  " + r)

    if a.write:
        bpy.ops.wm.save_mainfile()
        print("REAUTHOR OK  saved %s" % bpy.data.filepath)
    else:
        print("REAUTHOR DRY RUN  (pass --write to save)")


if __name__ == "__main__":
    main()
