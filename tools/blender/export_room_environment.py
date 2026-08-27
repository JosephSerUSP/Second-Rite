"""Bake one authored interior into a real-3D town environment package.

The Padaria and the smith ship twice: once as a pre-rendered plate, and once
as coarse 3D geometry carrying a baked beauty atlas. This builds the second.

It does NOT re-derive the room. It opens the shipped `.blend` and sorts what
is already there into the TH_* contract collections, so the walkable 3D room
is provably the same room the plate photographs -- if the recipe changes, both
outputs change together, and if it does not, neither drifts.

    blender -b -noaudio --python tools/blender/export_room_environment.py -- \
        --blend projects/.../alicias_padaria.blend \
        --output projects/.../environments/st_maria_town/alicias_padaria_3d

## Why the mesh comes out mirrored

The runtime town camera builds its basis as `right = (-dirY, dirX)`, which at
yaw 0 is **+Y**, while `forward x up` for forward +X and up +Z is **-Y**. That
is a determinant -1 basis (issue #935): the engine's screen-right is the
opposite of Blender's. Exported unchanged, the room would render as its own
mirror image -- the Padaria's oven on the right instead of the left -- and
nothing in the 3D path would flag it, because a reflection preserves both
point projection and transform invariance.

So the export mirrors Y into engine space, `engine_y = LANE_CENTRE - blender_y`,
and reverses face winding to keep the normals outward. That mapping is not
invented here: it is the same one the pre-rendered package uses, so both
packages share one set of lane coordinates and one set of anchors. A door at
lane Y 7.03 is the same door in both.

The mirror is applied to the exported OBJ rather than to the scene, because the
beauty bake is a selected-to-active ray cast from TH_SOURCE onto TH_RENDER and
both have to stay in the space they were authored in while it runs.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "blender"))

import town_environment_pipeline as pipeline  # noqa: E402
import stage_room_model as stager  # noqa: E402

# Shared with the pre-rendered packages; both are derived from the calibrated
# side-view camera in fixtures/town_sideview_camera.json.
LANE_CENTRE = 3.8833
NEWLINE = chr(10)
ACTION_PLANE_X = 0.0


def collection(name):
    existing = bpy.data.collections.get(name)
    if existing:
        return existing
    made = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(made)
    return made


def move(obj, target):
    for parent in list(obj.users_collection):
        parent.objects.unlink(obj)
    target.objects.link(obj)


def sort_into_contract_collections():
    """Everything the recipe built is TH_SOURCE: it is the authored appearance."""
    source = collection("TH_SOURCE")
    for obj in list(bpy.context.scene.collection.all_objects):
        move(obj, source)
    return source


def build_render_mesh(source, name, decimate):
    """Duplicate the source geometry, join it, and give it an atlas UV layout.

    Not yet a hand-authored coarse mesh: this is the whole room joined, which
    is a valid TH_RENDER (it carries the real depth and silhouette the runtime
    needs) and is honestly derived. `--decimate` below 1.0 collapses it
    further, but the default is 1.0 because these rooms are built from boxes
    and a collapse ratio applied blindly to boxes tears shared edges -- the
    lesson already recorded in town-authoring-known-good.md.
    """
    meshes = [o for o in source.objects if o.type == "MESH"]
    if not meshes:
        raise SystemExit("no mesh objects in the source .blend")

    render = collection("TH_RENDER")
    bpy.ops.object.select_all(action="DESELECT")
    copies = []
    for obj in meshes:
        copy = obj.copy()
        copy.data = obj.data.copy()
        copy.name = f"R_{obj.name}"
        render.objects.link(copy)
        copies.append(copy)

    for copy in copies:
        copy.select_set(True)
    bpy.context.view_layer.objects.active = copies[0]
    if len(copies) > 1:
        bpy.ops.object.join()
    target = bpy.context.view_layer.objects.active
    target.name = name

    if decimate < 0.999:
        modifier = target.modifiers.new("TH_DECIMATE", "DECIMATE")
        modifier.ratio = decimate
        bpy.ops.object.modifier_apply(modifier=modifier.name)

    # A selected-to-active bake needs a valid, non-overlapping receiver atlas.
    # The room's materials are world-space box projections with no UVs at all,
    # so there is nothing here to preserve and everything to create.
    bpy.ops.object.select_all(action="DESELECT")
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=0.02)
    bpy.ops.object.mode_set(mode="OBJECT")
    return target


def build_anchors(anchors):
    holder = collection("TH_ANCHORS")
    for name, lane_y in anchors.items():
        empty = bpy.data.objects.new(name, None)
        empty.empty_display_type = "PLAIN_AXES"
        # Authored directly in ENGINE space: the anchors are read straight out
        # of matrix_world by the pipeline and must not be mirrored twice.
        empty.location = Vector((ACTION_PLANE_X, lane_y, 0.0))
        holder.objects.link(empty)


def build_collision(span, ceiling):
    holder = collection("TH_COLLISION")
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    box = bpy.context.active_object
    box.name = "TH_COLLISION_FLOOR"
    box.scale = (2.0, span / 2.0, ceiling / 2.0)
    box.location = (ACTION_PLANE_X, span / 2.0, ceiling / 2.0)
    move(box, holder)


def mirror_obj_file(path: Path, centre: float) -> int:
    """Rewrite an exported OBJ so the room lands on the engine's lane axis.

    Two conversions stack here, and getting the first one wrong is silent.

    Blender's OBJ exporter writes **Y-up, forward -Z** by default, and the
    runtime reads that convention back in `obj_model.objToWorld`:

        world_x, world_y, world_z  =  obj_x, -obj_z, obj_y

    So the OBJ's SECOND component is height and its THIRD is the lane -- the
    lane axis is not where a Z-up reading of the file would put it. Mirroring
    the second component does not mirror the room, it turns it upside down.

    Composing the two: `obj_z = -blender_y`, so `world_y = blender_y` already.
    The engine's screen-right is +Y (the determinant -1 basis in the header),
    while the plate's is -Y, so the room still has to be reflected to agree
    with the pre-rendered package:

        world_y = centre - blender_y   =>   obj_z' = -obj_z - centre

    Normals get the same reflection without the translation, and face winding
    is reversed so they keep pointing out of the room rather than into it.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    out, flipped = [], 0
    for line in lines:
        if line.startswith("v "):
            parts = line.split()
            parts[3] = f"{-float(parts[3]) - centre:.6f}"
            out.append(" ".join(parts))
        elif line.startswith("vn "):
            parts = line.split()
            parts[3] = f"{-float(parts[3]):.6f}"
            out.append(" ".join(parts))
        elif line.startswith("f "):
            parts = line.split()
            out.append(" ".join([parts[0]] + list(reversed(parts[1:]))))
            flipped += 1
        else:
            out.append(line)
    path.write_text(NEWLINE.join(out) + NEWLINE, encoding="utf-8")
    return flipped


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(prog="export_room_environment")
    parser.add_argument("--blend", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--atlas-size", type=int, default=1024)
    parser.add_argument("--samples", type=int, default=24)
    parser.add_argument("--decimate", type=float, default=1.0)
    parser.add_argument("--ambient", type=float, default=0.13,
                        help="world fill strength for the bake; must match the plate render or the two presentations are lit differently")
    parser.add_argument("--lamp-scale", type=float, default=0.3,
                        help="must match the plate render or the two presentations are exposed differently")
    parser.add_argument("--window-emission-scale", type=float, default=1.0,
                        help="must match the plate render or the window grille clips differently")
    parser.add_argument("--span", type=float, default=7.7667)
    parser.add_argument("--ceiling", type=float, default=3.9)
    parser.add_argument("--exit-y", type=float, required=True,
                        help="lane Y of the exit door, in ENGINE space")
    parser.add_argument("--npc", default=None,
                        help="NAME=LANE_Y for the shopkeeper anchor")
    args = parser.parse_args(argv)

    bpy.ops.wm.open_mainfile(filepath=str(args.blend.resolve()))
    source = sort_into_contract_collections()
    build_render_mesh(source, f"{args.blend.stem}_TH_RENDER", args.decimate)

    spawn = min(max(args.exit_y - 0.9, 0.35), args.span - 0.35)
    anchors = {"spawn_player": round(spawn, 4), "exit_door": args.exit_y}
    if args.npc:
        key, value = args.npc.split("=")
        anchors[key] = float(value)
    build_anchors(anchors)
    build_collision(args.span, args.ceiling)

    # The .blend saves a black world: the stager supplies the fill at RENDER
    # time via base_lighting, so a Cycles bake that just opens the file is lit
    # by the authored lamps alone and comes out a cave. Same call, same
    # numbers, so the baked atlas and the plate see the same room.
    stager.base_lighting(args.ambient, (0.0, 0.0, 0.0), stager.INTERIOR_FILL)
    if args.lamp_scale != 1.0:
        stager.scale_lamp_energy(bpy.context.scene, args.lamp_scale)
    if args.window_emission_scale != 1.0:
        stager.scale_window_emission(bpy.context.scene,
                                     args.window_emission_scale)

    output = args.output.resolve()
    pipeline.run_pipeline_in_blender(args.blend.resolve(), output,
                                     atlas_size=args.atlas_size,
                                     bake_samples=args.samples)

    faces = mirror_obj_file(output / "environment.obj", LANE_CENTRE)
    print(f"[room3d] mirrored {faces} faces into engine space "
          f"(engine_y = {LANE_CENTRE} - blender_y)")
    print("ROOM 3D EXPORT OK")


if __name__ == "__main__":
    main()
