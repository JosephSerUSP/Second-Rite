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

WHAT THE PLACE IS. The Passage House boards Summoners with their mounts, so
Room 3 is a single large room shared by a rider and a Moa -- "This'll be home
for both of you", with a feed bowl "dragged in from the stable". The player is
IN this room; the other rooms are reached from the corridor and are never
visible from here. One screen shows one room.

THE WAY OUT is an extruded square on the floor, not a door in a wall. The floor
therefore terminates a few pixels above the character floor limit so that
square has room to read, and the slab's front fascia covers the rest of the
frame down past the limit -- no void, and nothing load-bearing under the menu.

FRAMING IS DERIVED, NOT EYEBALLED. `floor_edge_x()` inverts the camera
projection: give it a native scanline and it returns the world X where the
floor plane crosses it. The room is then sized so its walls and ceiling fill
the frame at that depth.

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

import material_library  # noqa: E402
import second_rite_asset_core as asset_core  # noqa: E402
from first_stratum.common import box  # noqa: E402

ASSET_ID = "passage_house_room3"

# --- the architecture, in metres -------------------------------------------
CAMERA = ROOT / "tools" / "blender" / "fixtures" / "town_sideview_camera.json"

FLOOR_TOP = 0.0
FLOOR_THICK = 0.35
FLOOR_EDGE_NATIVE_Y = 136.0   # a few px above the 144 character floor limit
BACK_WALL_X = 3.2
BACK_WALL_THICK = 0.5
CEILING_Z = 4.4
WALL_MARGIN = 0.5             # push side walls just outside the frame edge
POST = 0.24


def camera_record():
    return json.loads(CAMERA.read_text(encoding="utf-8"))


def floor_edge_x(native_y, record=None):
    """World X where the floor plane (z=0) crosses a native scanline.

    Inverts the projection: a point at height 0 sits
    (baseHeight * eyeZ) / (2 * fovHalfY * depth) pixels below the horizon.
    """
    record = record or camera_record()
    k = record["baseViewportHeight"] / (2.0 * record["fovHalfY"])
    depth = k * record["eye"]["z"] / (float(native_y) - record["viewportCenterY"])
    return record["eye"]["x"] + depth, depth


def half_width_at(depth, record=None):
    record = record or camera_record()
    return record["fovHalfX"] * depth * (record["targetWidth"]
                                         / record["baseViewportWidth"])


def material(semantic_id):
    """Bind a semantic ID; the library supplies textures when they exist."""
    return material_library.build_material(asset_core, semantic_id)


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

    record = camera_record()
    front_x, front_depth = floor_edge_x(FLOOR_EDGE_NATIVE_Y, record)
    half_w = half_width_at(front_depth, record) + WALL_MARGIN
    depth = BACK_WALL_X - front_x

    # --- floor, and the fascia that carries the frame down past the limit ---
    part("floor", (depth, half_w * 2, FLOOR_THICK),
         ((front_x + BACK_WALL_X) / 2.0, 0.0, FLOOR_TOP - FLOOR_THICK / 2.0), wood)

    # --- the way out: an extruded square on the floor -----------------------
    part("door_threshold", (1.25, 1.35, 0.09),
         (front_x + 0.95, -1.65, FLOOR_TOP + 0.045), stone)

    # --- back wall, in segments around the window ---------------------------
    wall_h = CEILING_Z + FLOOR_THICK
    wall_cx = BACK_WALL_X + BACK_WALL_THICK / 2.0
    wall_cz = FLOOR_TOP - FLOOR_THICK + wall_h / 2.0
    win_y0, win_y1, win_z0, win_z1 = 1.6, 3.3, 1.9, 3.3
    for name, y0, y1 in (("back_wall_left", -half_w, win_y0),
                         ("back_wall_right", win_y1, half_w)):
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
    part("window_sill", (BACK_WALL_THICK + 0.16, win_y1 - win_y0 + 0.26, 0.1),
         (wall_cx - 0.06, (win_y0 + win_y1) / 2.0, win_z0), wood)

    # --- side walls: just outside the frame edge, so no void at the sides ---
    for index, y in enumerate((-half_w, half_w)):
        sign = -1.0 if y < 0 else 1.0
        part(f"side_wall_{index}", (depth, BACK_WALL_THICK, wall_h),
             ((front_x + BACK_WALL_X) / 2.0, y + sign * BACK_WALL_THICK / 2.0,
              wall_cz), stone)

    # --- ceiling and its exposed beams --------------------------------------
    part("ceiling", (depth, half_w * 2, 0.3),
         ((front_x + BACK_WALL_X) / 2.0, 0.0, CEILING_Z + 0.15), wood)
    for index in range(-3, 4):
        part(f"ceiling_beam_{index + 3}", (depth, 0.26, 0.3),
             ((front_x + BACK_WALL_X) / 2.0, index * 1.9, CEILING_Z - 0.15), wood)
    part("wall_plate_left", (depth, 0.3, 0.34),
         ((front_x + BACK_WALL_X) / 2.0, -half_w + 0.2, CEILING_Z - 0.4), wood)
    part("wall_plate_right", (depth, 0.3, 0.34),
         ((front_x + BACK_WALL_X) / 2.0, half_w - 0.2, CEILING_Z - 0.4), wood)

    # --- the rider's end ----------------------------------------------------
    part("bed_frame", (1.75, 1.95, 0.42), (BACK_WALL_X - 0.95, -3.1,
                                           FLOOR_TOP + 0.21), wood)
    part("bed_mattress", (1.62, 1.82, 0.22), (BACK_WALL_X - 0.95, -3.1,
                                              FLOOR_TOP + 0.53), cloth)
    part("footlocker", (0.66, 1.15, 0.5), (BACK_WALL_X - 0.62, -1.55,
                                           FLOOR_TOP + 0.25), wood)

    # The pale rectangle where a picture used to hang, and the nail left behind.
    part("picture_ghost", (0.03, 1.15, 0.85),
         (BACK_WALL_X - 0.015, -3.05, 2.45), pale)
    part("picture_nail", (0.06, 0.04, 0.04),
         (BACK_WALL_X - 0.03, -3.05, 3.02), iron)

    # The coat hook, set low enough to belong to whoever lived here before.
    part("coat_hook_plate", (0.05, 0.16, 0.14),
         (BACK_WALL_X - 0.025, -5.0, 0.95), iron)
    part("coat_hook_arm", (0.13, 0.16, 0.05),
         (BACK_WALL_X - 0.09, -5.0, 0.90), iron)

    # --- Saban's end: straw and the chipped feed bowl from the stable -------
    for index, (sx, sy) in enumerate(((1.4, 3.4), (2.1, 2.6), (1.0, 4.4),
                                      (2.4, 4.1), (0.4, 3.0))):
        part(f"straw_{index}", (0.95, 0.8, 0.06), (sx, sy, FLOOR_TOP + 0.03),
             straw, rotation=(0.0, 0.0, 0.4 * index))
    feed_bowl(root, parts, crock)

    # --- a support post, giving the room a near depth layer ----------------
    part("post_left", (POST, POST, CEILING_Z),
         (front_x + 0.6, -half_w + 1.3, FLOOR_TOP + CEILING_Z / 2.0), wood)
    part("post_right", (POST, POST, CEILING_Z),
         (front_x + 0.6, half_w - 1.3, FLOOR_TOP + CEILING_Z / 2.0), wood)

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
    asset_core.parent_local(obj, root, loc=(1.7, 3.55, FLOOR_TOP))
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
