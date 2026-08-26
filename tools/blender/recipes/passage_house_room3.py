"""Passage House, Room 3 -- St. Maria boarding-house interior.

Authored for the town side-view camera (`tools/blender/fixtures/
town_sideview_camera.json`), in the camera's own frame:

    +X = camera forward (depth)   -Y = screen right   +Z = up
    metres, walkable floor at Z = 0, action plane at X = 0

NOTE ON UNITS. The asset contract's `world_cell` is 2.5 m, but the town camera
solves against a 1.75 **metre** Walker. This recipe is therefore authored in
metres, in the `preview` authoring space, and declared `preview_only`: per
`docs/design/town-authoring-known-good.md`, experimental town output stays
explicitly non-consumable until a separate architecture task establishes an
environment-package contract. Do not promote it by editing the metadata.

WHAT THE PLACE IS. The Passage House is a converted stable: Summoners board
here with their mounts, so the upper floor is an aisle with open stall-bays
rather than a corridor of sealed rooms. Room 3 is one bay. That comes straight
out of the authored opening text -- "This'll be home for both of you", the feed
bowl "dragged in from the stable", and "the other Summoner rooms are empty",
which the cutaway shows literally: dark bare bays flanking the lit one.

Partitions stop well below the roof, so one roof structure runs the whole
building and the frame reads as a real interior continuing past both edges
rather than a decorated slab.

Run:

    blender --background --factory-startup \
        --python tools/blender/recipes/passage_house_room3.py -- --out out/room3
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import second_rite_asset_core as asset_core  # noqa: E402
from first_stratum.common import box  # noqa: E402

ASSET_ID = "passage_house_room3"

# --- the architecture, in metres -------------------------------------------
FLOOR_TOP = 0.0
FLOOR_THICK = 0.28
AISLE_FRONT_X = -6.0          # floor runs toward camera, under the status menu
BAY_MOUTH_X = 1.0             # stall openings / post line
BAY_BACK_X = 5.0              # inner face of the back wall
BACK_WALL_THICK = 0.5
FORE_POST_X = -1.6            # foreground occlusion layer
HALF_WIDTH = 13.0             # authored overscan beyond the tracking envelope
BAY_EDGES = (-12.0, -4.0, 4.0, 12.0)   # Room 3 is the centre bay
PARTITION_H = 2.6
PARTITION_T = 0.12
TIE_Z = 4.2
RIDGE_Z = 5.8
RIDGE_X = (FORE_POST_X + BAY_BACK_X + BACK_WALL_THICK) / 2.0
POST = 0.22


def material(semantic_id):
    return asset_core.make_material(f"sr_{semantic_id}", semantic_id=semantic_id)


def build(context):
    asset_core.reset_scene()
    root = bpy.data.objects.new("PASSAGE_HOUSE_ROOM3", None)
    context.collection.objects.link(root)
    root.empty_display_type = "PLAIN_AXES"

    wood = material("dark_wood")
    stone = material("rough_limestone")
    pale = material("old_limestone")
    cloth = material("aged_cloth")
    iron = material("wrought_iron")
    straw = material("wax")
    crock = material("bone")

    parts = []

    def part(name, size, location, mat, **kw):
        obj = box(name, root, size, location, mat, asset_core, **kw)
        parts.append(obj)
        return obj

    # --- ground: floor slab, continuing toward camera past the frame --------
    depth = (BAY_BACK_X + BACK_WALL_THICK) - AISLE_FRONT_X
    part("floor", (depth, HALF_WIDTH * 2, FLOOR_THICK),
         ((AISLE_FRONT_X + BAY_BACK_X + BACK_WALL_THICK) / 2.0, 0.0,
          FLOOR_TOP - FLOOR_THICK / 2.0), wood)

    # --- back wall, built in segments around Room 3's window ----------------
    wall_h = TIE_Z + 0.4
    wall_cx = BAY_BACK_X + BACK_WALL_THICK / 2.0
    wall_cz = FLOOR_TOP - FLOOR_THICK + wall_h / 2.0
    win_y0, win_y1, win_z0, win_z1 = 0.9, 2.5, 1.9, 3.3
    for name, y0, y1 in (("back_wall_left", -HALF_WIDTH, win_y0),
                         ("back_wall_right", win_y1, HALF_WIDTH)):
        part(name, (BACK_WALL_THICK, y1 - y0, wall_h),
             (wall_cx, (y0 + y1) / 2.0, wall_cz), stone)
    part("back_wall_under_window", (BACK_WALL_THICK, win_y1 - win_y0,
                                    win_z0 - (FLOOR_TOP - FLOOR_THICK)),
         (wall_cx, (win_y0 + win_y1) / 2.0,
          (FLOOR_TOP - FLOOR_THICK + win_z0) / 2.0), stone)
    part("back_wall_over_window", (BACK_WALL_THICK, win_y1 - win_y0,
                                   (FLOOR_TOP - FLOOR_THICK + wall_h) - win_z1),
         (wall_cx, (win_y0 + win_y1) / 2.0,
          (win_z1 + FLOOR_TOP - FLOOR_THICK + wall_h) / 2.0), stone)
    part("window_sill", (BACK_WALL_THICK + 0.14, win_y1 - win_y0 + 0.24, 0.1),
         (wall_cx - 0.05, (win_y0 + win_y1) / 2.0, win_z0), wood)

    # --- stall partitions and the aisle post line ---------------------------
    bay_depth = (BAY_BACK_X - BAY_MOUTH_X)
    for index, y in enumerate(BAY_EDGES):
        part(f"partition_{index}", (bay_depth, PARTITION_T, PARTITION_H),
             ((BAY_MOUTH_X + BAY_BACK_X) / 2.0, y,
              FLOOR_TOP + PARTITION_H / 2.0), wood)
        part(f"aisle_post_{index}", (POST, POST, TIE_Z),
             (BAY_MOUTH_X, y, FLOOR_TOP + TIE_Z / 2.0), wood)

    # --- foreground layer: aisle-side posts, well in front of the action ----
    for index, y in enumerate((-8.4, 8.4)):
        part(f"fore_post_{index}", (POST * 1.3, POST * 1.3, TIE_Z),
             (FORE_POST_X, y, FLOOR_TOP + TIE_Z / 2.0), wood)

    # --- roof: tie beams the whole length, then two slopes to a ridge -------
    for name, x in (("tie_beam_bays", BAY_MOUTH_X), ("tie_beam_aisle", FORE_POST_X)):
        part(name, (0.3, HALF_WIDTH * 2, 0.34), (x, 0.0, TIE_Z), wood)
    for index in range(-6, 7):
        y = index * 2.0
        part(f"rafter_{index + 6}", (0.16, 0.16, 0.16), (RIDGE_X, y, RIDGE_Z), wood)
    part("ridge_beam", (0.28, HALF_WIDTH * 2, 0.3), (RIDGE_X, 0.0, RIDGE_Z), wood)
    for name, near_x in (("roof_front", FORE_POST_X), ("roof_back",
                                                       BAY_BACK_X + BACK_WALL_THICK)):
        run = RIDGE_X - near_x
        slope = math.atan2(RIDGE_Z - TIE_Z, abs(run))
        length = math.hypot(run, RIDGE_Z - TIE_Z)
        part(name, (length, HALF_WIDTH * 2, 0.16),
             ((near_x + RIDGE_X) / 2.0, 0.0, (TIE_Z + RIDGE_Z) / 2.0), wood,
             rotation=(0.0, -slope if run > 0 else slope, 0.0))

    # --- Room 3: the bay that is actually lived in --------------------------
    # Bed against the back wall.
    part("bed_frame", (1.7, 1.9, 0.42), (BAY_BACK_X - 0.95, -2.4,
                                         FLOOR_TOP + 0.21), wood)
    part("bed_mattress", (1.6, 1.8, 0.22), (BAY_BACK_X - 0.95, -2.4,
                                            FLOOR_TOP + 0.53), cloth)
    part("footlocker", (0.62, 1.1, 0.5), (BAY_BACK_X - 0.6, -0.85,
                                          FLOOR_TOP + 0.25), wood)

    # The pale rectangle where a picture used to hang, and the nail left behind.
    part("picture_ghost", (0.03, 1.15, 0.85),
         (BAY_BACK_X - 0.015, -2.35, 2.45), pale)
    part("picture_nail", (0.06, 0.04, 0.04),
         (BAY_BACK_X - 0.03, -2.35, 3.02), iron)

    # The coat hook, set low enough to belong to whoever lived here before.
    part("coat_hook_plate", (0.16, 0.05, 0.14),
         (BAY_MOUTH_X + 1.1, -4.0 + PARTITION_T / 2.0 + 0.02, 0.95), iron)
    part("coat_hook_arm", (0.16, 0.13, 0.05),
         (BAY_MOUTH_X + 1.1, -4.0 + PARTITION_T / 2.0 + 0.09, 0.90), iron)

    # Saban's end of the bay: straw, and the chipped feed bowl from the stable.
    for index, (sx, sy) in enumerate(((2.9, 2.5), (3.6, 1.9), (3.1, 3.1),
                                      (4.1, 2.7), (2.5, 1.6))):
        part(f"straw_{index}", (0.9, 0.75, 0.06), (sx, sy, FLOOR_TOP + 0.03),
             straw, rotation=(0.0, 0.0, 0.4 * index))
    feed_bowl(root, parts, crock)

    # A plank door, hinged on the partition and standing open into the aisle.
    hinge_y, width, angle = -3.95, 0.95, math.radians(72.0)
    part("bay_door", (0.06, width, 2.1),
         (BAY_MOUTH_X - math.sin(angle) * width / 2.0,
          hinge_y + math.cos(angle) * width / 2.0, FLOOR_TOP + 1.05),
         wood, rotation=(0.0, 0.0, angle))

    # --- the empty neighbour: a bare frame, nothing on it ------------------
    part("neighbour_bed_frame", (1.7, 1.9, 0.42),
         (BAY_BACK_X - 0.95, 7.4, FLOOR_TOP + 0.21), wood)

    # first_stratum.common.box emits INWARD normals (its bottom face reads
    # +Z, its top face -Z). Outward winding is load-bearing for baking and for
    # any downstream floor/surface detection, so make every part consistently
    # outward here. The shared helper is deliberately left alone: the Phase 4
    # item checks assert structural equivalence across the shipped OBJ corpus.
    recalculate_normals(parts)

    for obj in parts:
        obj.name = obj.name.lower()

    asset_core.tag_asset_target(
        root,
        asset_id=ASSET_ID,
        representation="full_model",
        role="preview_only",
        authoring_space="preview",
        placement_frame="preview_frame",
        states=["default"],
        variants=[],
        extra={"sr_preview_only": True,
               "sr_authoring_units": "metre",
               "sr_town_camera": "tools/blender/fixtures/town_sideview_camera.json"},
    )
    asset_core.validate_asset_metadata(root)
    return root, parts


def recalculate_normals(objects):
    import bmesh
    for obj in objects:
        if obj.type != "MESH":
            continue
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()


def feed_bowl(root, parts, mat):
    """An eight-sided crock with one rim vertex knocked down: the chip."""
    import bmesh
    bm = bmesh.new()
    rim, base = [], []
    for index in range(8):
        angle = math.tau * index / 8.0
        cos, sin = math.cos(angle), math.sin(angle)
        rim.append(bm.verts.new((cos * 0.30, sin * 0.30, 0.17)))
        base.append(bm.verts.new((cos * 0.19, sin * 0.19, 0.0)))
    bm.faces.new(reversed(base))
    for index in range(8):
        nxt = (index + 1) % 8
        bm.faces.new((base[index], base[nxt], rim[nxt], rim[index]))
    bm.faces.new(rim)
    rim[3].co.z -= 0.06          # the chip, deterministic
    obj = asset_core.mesh_object_from_bmesh("feed_bowl", bm)
    asset_core.parent_local(obj, root, loc=(3.35, 2.15, FLOOR_TOP))
    asset_core.assign_material(obj, mat)
    asset_core.flat_shade(obj)
    parts.append(obj)
    return obj


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(prog="passage_house_room3")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--blend", type=Path, default=None)
    args = parser.parse_args(argv)

    context = bpy.context
    root, parts = build(context)
    context.view_layer.update()

    out = args.out.resolve()
    outputs = asset_core.export_asset_root(context, root, out)

    bounds_objects = [o for o in parts if o.type == "MESH"]
    depsgraph = context.evaluated_depsgraph_get()
    lo = [min(( (o.matrix_world @ v.co)[axis]
                for o in bounds_objects
                for v in o.evaluated_get(depsgraph).to_mesh().vertices))
          for axis in range(3)]
    hi = [max(( (o.matrix_world @ v.co)[axis]
                for o in bounds_objects
                for v in o.evaluated_get(depsgraph).to_mesh().vertices))
          for axis in range(3)]

    if args.blend:
        blend = args.blend.resolve()
        blend.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))

    print("RECIPE RESULT " + json.dumps({
        "assetId": ASSET_ID,
        "parts": len(parts),
        "outputs": outputs,
        "min": [round(v, 4) for v in lo],
        "max": [round(v, 4) for v in hi],
        "extent": [round(hi[i] - lo[i], 4) for i in range(3)],
        "floorTop": FLOOR_TOP,
        "blend": str(args.blend.resolve()) if args.blend else None,
    }))


if __name__ == "__main__":
    main()
