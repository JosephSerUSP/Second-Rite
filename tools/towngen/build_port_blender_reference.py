"""Build the Port's depth-aware Blender conditioning scene.

Run through Blender, with the owner's baseline already opened::

    blender --background <baseline.blend> --python tools/towngen/build_port_blender_reference.py -- \
        --output <port-reference.blend> --render <spatial-final-1065x240.png>

The source camera is intentionally left unchanged. The coherent 1065x240 final
frame is authored and rendered first using a pixel aspect that preserves the
camera's 256x240 projection. The model-facing 2160x720 (3:1) conditioning guide
is then derived mechanically from that completed frame as the exact inverse of
final normalization. The camera never renders a second aspect ratio.

Every gameplay transition uses the same triangular-prism marker at its trigger
origin. Colour identifies the interaction class; marker geometry never depicts
a door, stair, ramp, corridor, or destination shape. The rendered floor and
camera provide spatial depth without turning gameplay annotations into art
direction.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector


PLATE_WIDTH = 1065
NATIVE_WIDTH = 256
HEIGHT = 240
WORKING_WIDTH = 2160
WORKING_HEIGHT = 720
HORIZON_Y = 66
ACTOR_GROUND_Y = 136
UI_TOP_Y = 144
PLATE_TO_CAMERA_X_SCALE = NATIVE_WIDTH / PLATE_WIDTH
GUIDE_RELATIVE_X_SCALE = ((WORKING_WIDTH / PLATE_WIDTH) /
                          (WORKING_HEIGHT / HEIGHT))
OUTPUT_RELATIVE_X_SCALE = 1.0 / GUIDE_RELATIVE_X_SCALE

# The owner's baseline puts the canonical 3D actor plane at X=-2.2 (row 128).
# The 2D plate actor stands at row 136, which this nearer plane projects to
# without changing the carefully authored camera.
TRIGGER_X = -4.2

OPENING_ROLES = {
    "west_quay": ("CLEAR WALKABLE CONTINUATION TO THE QUAY", "street"),
    "forge_door": ("READABLE ACCESSIBLE ENTRANCE TO THE ACTIVE FORGE", "door"),
    "smith_3d_door": ("SECOND READABLE ACCESSIBLE SMITHY ENTRANCE", "door"),
    "cortico_stair": ("DISTINCT UPWARD ROUTE TO THE CORTICO", "stair"),
    "climb_churchyard": ("DISTINCT LONG EXTERIOR CLIMB TO THE CHURCHYARD", "climb"),
}


def args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--render", required=True, type=Path)
    parser.add_argument("--style-reference", required=True, type=Path)
    parser.add_argument("--layout", required=True, type=Path)
    parser.add_argument("--force", action="store_true")
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(values)


def collection(name: str) -> bpy.types.Collection:
    found = bpy.data.collections.get(name)
    if found is not None:
        return found
    made = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(made)
    return made


def retire_baseline_collections() -> None:
    """Keep the owner's objects, but remove their Praça semantics from authority."""
    for old in ("10_LEVEL_DESIGN", "11_SCALE_GUIDES", "TH_ANCHORS", "TH_COLLISION"):
        found = bpy.data.collections.get(old)
        if found is None:
            continue
        found.name = "BASELINE_" + old
        found.hide_render = True
        found.hide_viewport = True


def material(name: str, rgba: tuple[float, float, float, float], *, emission=0.0):
    found = bpy.data.materials.get(name)
    if found is None:
        found = bpy.data.materials.new(name)
    found.diffuse_color = rgba
    found.use_nodes = True
    bsdf = found.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = 0.82
    if emission:
        emission_input = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
        if emission_input is not None:
            emission_input.default_value = rgba
        strength = bsdf.inputs.get("Emission Strength")
        if strength is not None:
            strength.default_value = emission
    return found


def link_object(obj: bpy.types.Object, target: bpy.types.Collection) -> None:
    if obj.name not in target.objects:
        target.objects.link(obj)


def cube(name: str, location, dimensions, mat, target, *, parent=None, rotation=None):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    if rotation is not None:
        obj.rotation_euler = rotation
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    link_object(obj, target)
    obj.parent = parent
    return obj


def mesh_object(name: str, vertices, faces, mat, target, *, parent=None):
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(mat)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    target.objects.link(obj)
    obj.parent = parent
    return obj


def sphere(name: str, location, radius, mat, target, *, parent=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6,
                                        radius=radius, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    link_object(obj, target)
    obj.parent = parent
    return obj


def camera_x_for_plate_x(plate_x: float) -> float:
    return float(plate_x) * PLATE_TO_CAMERA_X_SCALE


def world_y_for_plate_x(scene, camera, plate_x: float, depth_x: float) -> float:
    """Unproject one final plate X onto a plane of constant world X."""
    wanted = camera_x_for_plate_x(plate_x) / NATIVE_WIDTH
    base_y = camera.location.y
    p0 = world_to_camera_view(scene, camera, Vector((depth_x, base_y, 0.0))).x
    p1 = world_to_camera_view(scene, camera, Vector((depth_x, base_y + 1.0, 0.0))).x
    slope = p1 - p0
    if abs(slope) < 1e-9:
        raise SystemExit("camera has no horizontal Y projection")
    return base_y + (wanted - p0) / slope


def plate_span_at_depth(scene, camera, center_px, width_px, depth_x):
    left = world_y_for_plate_x(scene, camera, center_px - width_px / 2.0, depth_x)
    right = world_y_for_plate_x(scene, camera, center_px + width_px / 2.0, depth_x)
    return (left + right) / 2.0, abs(right - left)


def trigger_prism(name, scene, camera, plate_x, width_px, mat, target,
                  *, parent=None):
    """One universal 3D map pin whose point is the gameplay trigger origin."""
    near_x = TRIGGER_X - 0.24
    far_x = TRIGGER_X + 0.24
    vertices = []
    for depth_x in (near_x, far_x):
        left = world_y_for_plate_x(
            scene, camera, plate_x - width_px / 2.0, depth_x)
        right = world_y_for_plate_x(
            scene, camera, plate_x + width_px / 2.0, depth_x)
        centre = world_y_for_plate_x(scene, camera, plate_x, depth_x)
        vertices.extend(((depth_x, left, 0.72),
                         (depth_x, right, 0.72),
                         (depth_x, centre, 0.035)))
    faces = ((0, 2, 1), (3, 4, 5), (0, 1, 4, 3),
             (1, 2, 5, 4), (2, 0, 3, 5))
    return mesh_object(name, vertices, faces, mat, target, parent=parent)


def build(values: argparse.Namespace) -> dict:
    output = values.output.resolve()
    render = values.render.resolve()
    style_reference = values.style_reference.resolve()
    layout_path = values.layout.resolve()
    if output.exists() and not values.force:
        raise SystemExit(f"refusing to overwrite hand-editable source: {output}")
    if not style_reference.exists():
        raise SystemExit(f"missing in-house style reference: {style_reference}")
    if not layout_path.exists():
        raise SystemExit(f"missing generated Port layout: {layout_path}")
    layout = json.loads(layout_path.read_text(encoding="utf-8"))
    if layout.get("mapId") != 31 or layout.get("plateWidth") != PLATE_WIDTH:
        raise SystemExit(f"not the expected Port layout contract: {layout_path}")
    found_names = [item["anchor"] for item in layout.get("openings", [])]
    if found_names != list(OPENING_ROLES):
        raise SystemExit(f"Port anchor order drifted: {found_names}")
    openings = []
    for item in layout["openings"]:
        label, role = OPENING_ROLES[item["anchor"]]
        openings.append((item["anchor"], label, float(item["pixelX"]), role))

    scene = bpy.context.scene
    camera = scene.camera
    if camera is None or camera.data.type != "PERSP":
        raise SystemExit("the baseline must have an active perspective camera")

    retire_baseline_collections()
    source = collection("TH_SOURCE")
    collection("TH_RENDER")
    anchors = collection("TH_ANCHORS")
    collision = collection("TH_COLLISION")
    camera_collection = collection("TH_CAMERA_PREVIEW")
    link_object(camera, camera_collection)

    root = bpy.data.objects.new("PORT_SPATIAL_REFERENCE", None)
    source.objects.link(root)
    root["sr_plate"] = "port_bg.png"
    root["sr_plate_size"] = [PLATE_WIDTH, HEIGHT]
    root["sr_camera_frame_size"] = [NATIVE_WIDTH, HEIGHT]
    root["sr_render_size"] = [PLATE_WIDTH, HEIGHT]
    root["sr_derived_working_size"] = [WORKING_WIDTH, WORKING_HEIGHT]
    root["sr_final_plate_size"] = [PLATE_WIDTH, HEIGHT]
    root["sr_guide_relative_x_scale"] = GUIDE_RELATIVE_X_SCALE
    root["sr_output_relative_x_scale"] = OUTPUT_RELATIVE_X_SCALE
    root["sr_render_pixel_aspect"] = [1.0, PLATE_WIDTH / NATIVE_WIDTH]
    root["sr_horizon_y"] = HORIZON_Y
    root["sr_actor_ground_y"] = ACTOR_GROUND_Y
    root["sr_ui_top_y"] = UI_TOP_Y
    root["sr_style_reference"] = str(style_reference)
    root["sr_layout_authority"] = str(layout_path)
    root["sr_note"] = (
        "Render the coherent 1065x240 frame here. Compress that completed PNG "
        "to the model's 3:1 landscape aspect, then add labels. Fit the complete "
        "generated output once back to 1065x240.")

    # The in-house sheet is a viewport-only camera background: useful while
    # hand editing, impossible to bake or accidentally render as world texture.
    image = bpy.data.images.load(str(style_reference), check_existing=True)
    image.pack()
    camera.data.show_background_images = True
    background = camera.data.background_images.new()
    background.image = image
    background.alpha = 0.32
    background.display_depth = "BACK"
    background.frame_method = "FIT"
    background.show_background_image = True

    ground = material("PORT_GUIDE_GROUND", (0.24, 0.34, 0.34, 1.0))
    water = material("PORT_GUIDE_WATER", (0.10, 0.25, 0.39, 1.0))
    grid = material("PORT_GUIDE_GRID", (0.20, 0.85, 0.55, 1.0), emission=0.7)
    street = material("PORT_GUIDE_STREET", (0.14, 0.58, 0.95, 1.0), emission=0.45)
    active = material("PORT_GUIDE_DOOR", (0.95, 0.08, 0.06, 1.0), emission=0.55)
    route = material("PORT_GUIDE_ROUTE", (1.00, 0.66, 0.08, 1.0), emission=0.45)
    actor = material("PORT_GUIDE_ACTOR", (0.86, 0.22, 0.72, 1.0), emission=0.3)

    # Retain the owner's checker objects for inspection but let the authored
    # Port surfaces own the conditioning render.
    for baseline_name in ("FloorPlane", "WallPlane"):
        baseline = bpy.data.objects.get(baseline_name)
        if baseline is not None:
            baseline.hide_render = True

    y0 = world_y_for_plate_x(scene, camera, -24, TRIGGER_X)
    y1 = world_y_for_plate_x(scene, camera, PLATE_WIDTH + 24, TRIGGER_X)
    full_y = abs(y1 - y0)
    centre_y = (y0 + y1) / 2.0
    cube("port_quay_ground", (-4.1, centre_y, -0.18),
         (16.2, full_y, 0.36), ground, source, parent=root)
    # Extend effectively to the camera horizon. A short finite plane creates a
    # false dark seam below the authored horizon and weakens the depth lesson.
    water_near = 4.0
    water_far = 5000.0
    cube("port_water", ((water_near + water_far) / 2.0, centre_y, -0.31),
         (water_far - water_near, full_y * 3.0, 0.18),
         water, source, parent=root)

    # Continuous floor rulers. Constant-Y lines recede naturally toward the
    # camera centre; constant-depth cross-lines span the whole final plate.
    for index, depth in enumerate((-10.0, -7.5, -5.5, TRIGGER_X, -2.0, 0.0, 2.0, 4.0)):
        lo = world_y_for_plate_x(scene, camera, -24, depth)
        hi = world_y_for_plate_x(scene, camera, PLATE_WIDTH + 24, depth)
        cube(f"GRID_cross_{index:02d}", (depth, (lo + hi) / 2.0, 0.025),
             (0.035, abs(hi - lo), 0.035), grid, source, parent=root)
    for index, plate_x in enumerate(range(0, PLATE_WIDTH + 1, 96)):
        line_y = world_y_for_plate_x(scene, camera, plate_x, TRIGGER_X)
        cube(f"GRID_recede_{index:02d}", (-3.0, line_y, 0.03),
             (14.0, 0.025, 0.04), grid, source, parent=root)

    # Exact gameplay markers and authoritative anchors on the row-136 plane.
    # All event classes deliberately share one marker shape. The marker point,
    # not its volume, owns the transition location.
    projected = []
    for anchor_name, label, plate_x, kind in openings:
        ay = world_y_for_plate_x(scene, camera, plate_x, TRIGGER_X)
        marker_mat = street if kind == "street" else (active if kind == "door" else route)
        trigger_prism(f"TRIGGER_{anchor_name}", scene, camera, plate_x,
                      22.0, marker_mat, source, parent=root)
        empty = bpy.data.objects.new(anchor_name, None)
        anchors.objects.link(empty)
        empty.location = (TRIGGER_X, ay, 0.0)
        empty.empty_display_type = "ARROWS"
        empty.empty_display_size = 0.45
        empty["sr_anchor"] = anchor_name
        empty["sr_label"] = label
        empty["sr_plate_x"] = plate_x
        empty["sr_transition_kind"] = kind
        p = world_to_camera_view(scene, camera, empty.location)
        projected.append({"anchor": anchor_name, "targetPlateX": plate_x,
                          "nativeX": round(p.x * NATIVE_WIDTH, 4),
                          "workingX": round(p.x * WORKING_WIDTH, 4),
                          "plateX": round(p.x * PLATE_WIDTH, 4),
                          "workingRow": round((1.0 - p.y) * WORKING_HEIGHT, 4),
                          "plateRow": round((1.0 - p.y) * HEIGHT, 4)})

    # One unmistakably humanoid proxy in the live gameplay strip, sized to the
    # plate's 48 px sprite envelope rather than pretending it is rendered art.
    actor_x = -4.13
    actor_plate_x = 300.0
    actor_y = world_y_for_plate_x(scene, camera, actor_plate_x, actor_x)
    _, torso_width = plate_span_at_depth(scene, camera, actor_plate_x, 15.0, actor_x)
    _, head_width = plate_span_at_depth(scene, camera, actor_plate_x, 11.0, actor_x)
    cube("ACTOR_TORSO", (actor_x, actor_y, 0.83),
         (0.20, torso_width, 0.66), actor, source, parent=root)
    sphere("ACTOR_HEAD", (actor_x, actor_y, 1.27), head_width / 2.0,
           actor, source, parent=root)
    for offset, suffix in ((-4.0, "WEST"), (4.0, "EAST")):
        leg_y = world_y_for_plate_x(scene, camera, actor_plate_x + offset, actor_x)
        _, leg_width = plate_span_at_depth(scene, camera,
                                           actor_plate_x + offset, 4.0, actor_x)
        cube(f"ACTOR_LEG_{suffix}", (actor_x, leg_y, 0.27),
             (0.17, leg_width, 0.54), actor, source, parent=root)

    lane = cube("COL_port_walkable_surface", (TRIGGER_X, centre_y, -0.07),
                (0.7, full_y, 0.12), ground, collision, parent=root)
    lane.hide_render = True
    lane["sr_lane_min_y"] = 0.0
    lane["sr_lane_max_y"] = 29.48
    lane["sr_anamorphic_authoring"] = True

    # Soft directional shading makes prism depth legible while keeping this a
    # geometry guide rather than a proposed final art treatment.
    for obj in list(scene.objects):
        if obj.type == "LIGHT" and obj.name.startswith("PORT_GUIDE_"):
            bpy.data.objects.remove(obj, do_unlink=True)
    light_data = bpy.data.lights.new("PORT_GUIDE_SKY", "AREA")
    light_data.energy = 1250.0
    light_data.shape = "RECTANGLE"
    light_data.size = 22.0
    light_data.size_y = 22.0
    light = bpy.data.objects.new("PORT_GUIDE_SKY", light_data)
    source.objects.link(light)
    light.location = (-7.0, 0.0, 14.0)
    light.rotation_euler = (math.radians(18.0), 0.0, math.radians(-90.0))
    world = scene.world or bpy.data.worlds.new("PORT_GUIDE_WORLD")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.07, 0.09, 0.12, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.55

    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = PLATE_WIDTH
    scene.render.resolution_y = HEIGHT
    scene.render.resolution_percentage = 100
    scene.render.pixel_aspect_x = 1.0
    scene.render.pixel_aspect_y = PLATE_WIDTH / NATIVE_WIDTH
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.filepath = str(render)
    scene.render.use_file_extension = True
    camera.data.sensor_fit = "AUTO"
    camera.data.clip_end = max(camera.data.clip_end, 6000.0)

    scene["sr_port_spatial_reference"] = True
    scene["sr_style_authority"] = "in-house live captures: maps 17, 28, 29"
    scene["sr_layout_authority"] = str(layout_path)
    scene["sr_generated_images_allowed_as_input"] = False
    scene["sr_output_transform"] = (
        "author 1065x240 -> compress completed render to 2160x720 (3:1) -> "
        "add labels -> fit one complete generated 3:1 frame back to 1065x240; "
        "no second camera render, crop, or stitch")
    scene["sr_anchor_projection"] = json.dumps(projected, separators=(",", ":"))

    output.parent.mkdir(parents=True, exist_ok=True)
    render.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output))
    bpy.ops.render.render(write_still=True)
    return {"output": str(output), "render": str(render), "anchors": projected}


if __name__ == "__main__":
    result = build(args())
    print("PORT_REFERENCE=" + json.dumps(result, separators=(",", ":")))
