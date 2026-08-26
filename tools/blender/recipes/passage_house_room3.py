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
SOURCE_BLEND = (ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring"
                / "environments" / f"{ASSET_ID}.blend")

# --- the architecture, in metres -------------------------------------------
CAMERA = ROOT / "tools" / "blender" / "fixtures" / "town_sideview_camera.json"

FLOOR_TOP = 0.0
FLOOR_THICK = 0.35
FLOOR_EDGE_NATIVE_Y = 136.0   # a few px above the 144 character floor limit
# Room dimensions are FREE. Only the floor level is fixed by the camera; a
# room is whatever size the place should be, and may be far deeper than the
# player can walk. The proscenium below is what carries the frame edges, so
# nothing here is chosen to fill a frame.
ROOM_HALF_WIDTH = 5.4         # free: sized so the room, not its
                              # surround, carries the frame
ROOM_DEPTH = 7.4              # deliberately deep; the walkable band is shallow
CEILING_Z = 4.3
BACK_WALL_THICK = 0.5
POST = 0.22


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
    pale_patch = material("bone")
    daylight = asset_core.make_material("sr_window_daylight",
                                        color=(0.92, 0.95, 1.0),
                                        emission=(0.92, 0.95, 1.0))
    plaster = material("old_limestone")
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
    back_x = front_x + ROOM_DEPTH
    half_w = ROOM_HALF_WIDTH
    wall_h = CEILING_Z + FLOOR_THICK
    wall_cz = FLOOR_TOP - FLOOR_THICK + wall_h / 2.0

    # --- floor -------------------------------------------------------------
    part("floor", (ROOM_DEPTH, half_w * 2, FLOOR_THICK),
         ((front_x + back_x) / 2.0, 0.0, FLOOR_TOP - FLOOR_THICK / 2.0), wood)

    # --- the way out: a square of the FLOOR, extruded --------------------
    # Same material as the floor and seated in it: this is the floor stepping
    # up at the threshold, not a mat laid on top of it.
    threshold_rise = 0.15
    part("door_threshold", (1.3, 1.45, FLOOR_THICK + threshold_rise),
         (front_x + 0.8, -1.7,
          FLOOR_TOP + threshold_rise - (FLOOR_THICK + threshold_rise) / 2.0), wood)

    # --- back wall, in segments around the window ---------------------------
    wall_cx = back_x + BACK_WALL_THICK / 2.0
    win_y0, win_y1, win_z0, win_z1 = 0.7, 2.4, 1.15, 2.55
    for name, y0, y1 in (("back_wall_left", -half_w, win_y0),
                         ("back_wall_right", win_y1, half_w)):
        part(name, (BACK_WALL_THICK, y1 - y0, wall_h),
             (wall_cx, (y0 + y1) / 2.0, wall_cz), plaster)
    part("back_wall_under_window", (BACK_WALL_THICK, win_y1 - win_y0,
                                    win_z0 - (FLOOR_TOP - FLOOR_THICK)),
         (wall_cx, (win_y0 + win_y1) / 2.0,
          (FLOOR_TOP - FLOOR_THICK + win_z0) / 2.0), plaster)
    part("back_wall_over_window", (BACK_WALL_THICK, win_y1 - win_y0,
                                   (FLOOR_TOP - FLOOR_THICK + wall_h) - win_z1),
         (wall_cx, (win_y0 + win_y1) / 2.0,
          (win_z1 + FLOOR_TOP - FLOOR_THICK + wall_h) / 2.0), plaster)
    # Daylight seen THROUGH the opening. Without this the window is a hole
    # onto the black backdrop -- a void where the room's brightest thing should
    # be. Emissive, so it reads as sky rather than as a lit surface.
    part("window_daylight", (0.06, win_y1 - win_y0, win_z1 - win_z0),
         (back_x + BACK_WALL_THICK - 0.02, (win_y0 + win_y1) / 2.0,
          (win_z0 + win_z1) / 2.0), daylight)
    part("window_sill", (BACK_WALL_THICK + 0.16, win_y1 - win_y0 + 0.26, 0.1),
         (wall_cx - 0.06, (win_y0 + win_y1) / 2.0, win_z0), wood)

    # --- side walls and ceiling ---------------------------------------------
    for index, y in enumerate((-half_w, half_w)):
        sign = -1.0 if y < 0 else 1.0
        part(f"side_wall_{index}", (ROOM_DEPTH, BACK_WALL_THICK, wall_h),
             ((front_x + back_x) / 2.0, y + sign * BACK_WALL_THICK / 2.0,
              wall_cz), plaster)
    part("ceiling", (ROOM_DEPTH, half_w * 2, 0.3),
         ((front_x + back_x) / 2.0, 0.0, CEILING_Z + 0.15), wood)
    for index in range(-2, 3):
        part(f"ceiling_beam_{index + 2}", (ROOM_DEPTH, 0.24, 0.28),
             ((front_x + back_x) / 2.0, index * 1.5, CEILING_Z - 0.14), wood)

    # --- the rider's end ----------------------------------------------------
    part("bed_frame", (1.75, 1.95, 0.42), (back_x - 0.95, -2.3,
                                           FLOOR_TOP + 0.21), wood)
    part("bed_mattress", (1.62, 1.82, 0.22), (back_x - 0.95, -2.3,
                                              FLOOR_TOP + 0.53), cloth)
    part("footlocker", (0.66, 1.15, 0.5), (back_x - 0.62, -0.75,
                                           FLOOR_TOP + 0.25), wood)
    part("picture_ghost", (0.03, 1.15, 0.85), (back_x - 0.015, -2.25, 2.05), pale_patch)
    part("picture_nail", (0.06, 0.04, 0.04), (back_x - 0.03, -2.25, 2.62), iron)
    part("coat_hook_plate", (0.05, 0.16, 0.14), (back_x - 0.025, -3.2, 0.95), iron)
    part("coat_hook_arm", (0.13, 0.16, 0.05), (back_x - 0.09, -3.2, 0.90), iron)

    # --- Saban's end: straw and the chipped feed bowl from the stable -------
    for index, (sx, sy) in enumerate(((2.0, 2.2), (2.9, 1.6), (1.6, 2.9),
                                      (3.3, 2.5), (1.1, 1.9))):
        part(f"straw_{index}", (0.95, 0.8, 0.06), (sx, sy, FLOOR_TOP + 0.03),
             straw, rotation=(0.0, 0.0, 0.4 * index))
    feed_bowl(root, parts, crock)

    # --- a near post, giving the room a foreground depth layer -------------
    part("post_left", (POST, POST, CEILING_Z),
         (front_x + 0.5, -half_w + 0.55, FLOOR_TOP + CEILING_Z / 2.0), wood)

    # first_stratum.common.box emits INWARD normals (its bottom face reads
    # +Z, its top face -Z). Outward winding is load-bearing for baking and for
    # any downstream floor/surface detection, so make every part consistently
    # outward here. The shared helper is deliberately left alone: the Phase 4
    # item checks assert structural equivalence across the shipped OBJ corpus.
    recalculate_normals(parts)

    build_lights(root, front_x, back_x, (win_y0 + win_y1) / 2.0,
                 (win_z0 + win_z1) / 2.0)

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


def build_lights(root, front_x, back_x, win_y, win_z):
    """Canonical light sources, authored as part of the room.

    No sun and no key: a hard raking light is what makes an interior read as a
    diorama. Baseline visibility is the world light; every hard shadow here
    comes from something the room contains -- the window, and a lamp by the
    bed. These are ordinary Blender lights in the .blend, so they are yours to
    move, retint and re-energise.
    """
    import bpy
    from mathutils import Vector

    def light(name, kind, location, direction, energy, colour, **kw):
        data = bpy.data.lights.new(name, type=kind)
        data.energy = energy
        data.color = colour
        if kind == "AREA":
            data.shape = "RECTANGLE"
            data.size = kw.get("size", 1.0)
            data.size_y = kw.get("size_y", 1.0)
        elif kind == "SPOT":
            data.spot_size = kw.get("spot_size", math.radians(70.0))
            data.spot_blend = kw.get("spot_blend", 0.45)
        elif kind == "POINT":
            data.shadow_soft_size = kw.get("radius", 0.12)
        obj = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(obj)
        obj.location = Vector(location)
        obj.rotation_euler = Vector(direction).normalized().to_track_quat(
            "-Z", "Y").to_euler()
        obj.parent = root
        obj.matrix_parent_inverse = root.matrix_world.inverted()
        obj["sr_canonical_light"] = True
        return obj

    # Daylight through the window: the one hard source, raking forward and down
    # into the room rather than across it.
    light("light_window", "AREA", (back_x - 0.35, win_y, win_z),
          (-0.85, -0.18, -0.5), 260.0, (1.0, 0.96, 0.86),
          size=1.5, size_y=1.25)
    # A warm practical by the bed, for contrast and to model the near corner.
    light("light_bed_lamp", "POINT", (back_x - 1.1, -2.3, 0.95),
          (0.0, 0.0, -1.0), 22.0, (1.0, 0.78, 0.52), radius=0.14)
    # A very soft bounce standing in for the corridor beyond the doorway.
    light("light_doorway_bounce", "AREA", (front_x + 0.2, -1.7, 1.3),
          (1.0, 0.15, -0.1), 14.0, (0.82, 0.86, 1.0), size=1.4, size_y=1.8)


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
    parser.add_argument("--blend", type=Path, default=SOURCE_BLEND,
                        help="source-authority .blend to scaffold")
    parser.add_argument("--force", action="store_true",
                        help="overwrite an existing source .blend, DISCARDING "
                             "any hand-authoring in it")
    parser.add_argument("--obj", type=Path, default=None,
                        help="also write a compiled OBJ/MTL product")
    args = parser.parse_args(argv)

    blend = args.blend.resolve()
    if blend.exists() and not args.force:
        raise SystemExit(
            f"{blend} already exists and is the SOURCE AUTHORITY for this "
            "environment. This script only scaffolds a new one; it must never "
            "regenerate a document that has been hand-edited. Edit the .blend "
            "directly, or pass --force to discard it deliberately."
        )

    context = bpy.context
    root, parts = build(context)
    context.view_layer.update()

    bounds_objects = [o for o in parts if o.type == "MESH"]
    depsgraph = context.evaluated_depsgraph_get()
    coords = [(o.matrix_world @ v.co)
              for o in bounds_objects
              for v in o.evaluated_get(depsgraph).to_mesh().vertices]
    lo = [min(c[axis] for c in coords) for axis in range(3)]
    hi = [max(c[axis] for c in coords) for axis in range(3)]

    outputs = []
    if args.obj:
        outputs = asset_core.export_asset_root(context, root, args.obj.resolve())

    blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))

    print("RECIPE RESULT " + json.dumps({
        "assetId": ASSET_ID,
        "parts": len(parts),
        "lights": [o.name for o in bpy.data.objects if o.type == "LIGHT"],
        "blend": str(blend),
        "outputs": outputs,
        "min": [round(v, 4) for v in lo],
        "max": [round(v, 4) for v in hi],
        "extent": [round(hi[i] - lo[i], 4) for i in range(3)],
        "floorTop": FLOOR_TOP,
    }))


if __name__ == "__main__":
    main()
