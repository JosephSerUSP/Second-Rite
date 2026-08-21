"""Create an editable Blender calibration scene for the supplied Meshy village.

Run with Blender's bundled Python, not the game's runtime Python:

    blender --background --python tools/asset-production/create_meshy_annotation_scene.py -- \
      --source-obj <Meshy OBJ> --walker <walker.png> --reference <reference.png> \
      --output second_gate_town_annotation.blend

The generated scene is an authoring handoff.  The walkable template and named
empties are intentionally not gameplay authority until the owner edits and
returns the file.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-obj", required=True, type=Path)
    parser.add_argument("--walker", required=True, type=Path)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(argv)


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.data.collections):
        if collection.name != "Collection" and collection.users == 0:
            bpy.data.collections.remove(collection)


def ensure_collection(name: str, parent: bpy.types.Collection | None = None) -> bpy.types.Collection:
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
    if parent is None:
        parent = bpy.context.scene.collection
    if collection.name not in {child.name for child in parent.children}:
        parent.children.link(collection)
    return collection


def move_to_collection(obj: bpy.types.Object, collection: bpy.types.Collection) -> None:
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    collection.objects.link(obj)


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def make_material(name: str, color: tuple[float, float, float, float], alpha: float = 1.0) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*color[:3], alpha)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    principled = nodes.get("Principled BSDF")
    if principled is not None:
        principled.inputs["Base Color"].default_value = (*color[:3], 1.0)
        principled.inputs["Roughness"].default_value = 0.8
        principled.inputs["Alpha"].default_value = alpha
    if alpha < 1.0:
        try:
            material.surface_render_method = "DITHERED"
        except AttributeError:
            material.blend_method = "BLEND"
        if hasattr(material, "use_transparency_overlap"):
            material.use_transparency_overlap = False
    return material


def make_grid_template(name: str, minimum: Vector, maximum: Vector, ground_z: float,
                       collection: bpy.types.Collection) -> bpy.types.Object:
    columns = 12
    rows = 12
    vertices = []
    faces = []
    for row in range(rows + 1):
        y = minimum.y + (maximum.y - minimum.y) * row / rows
        for column in range(columns + 1):
            x = minimum.x + (maximum.x - minimum.x) * column / columns
            vertices.append((x, y, ground_z - 0.002))
    for row in range(rows):
        for column in range(columns):
            left = row * (columns + 1) + column
            faces.append((left, left + 1, left + columns + 2, left + columns + 1))
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.data.materials.append(make_material("WalkableTemplateMaterial", (0.1, 0.65, 0.25, 1.0), 0.22))
    obj.display_type = "WIRE"
    obj["annotation_status"] = "TEMPLATE - trace walkable ground, delete blocked cells, then rename/return"
    obj["source_axis"] = "Blender X/Y ground plane; Blender Z is up"
    return obj


def make_marker(name: str, location: Vector, collection: bpy.types.Collection,
                display_type: str = "PLAIN_AXES", size: float = 0.08) -> bpy.types.Object:
    obj = bpy.data.objects.new(name, None)
    collection.objects.link(obj)
    obj.empty_display_type = display_type
    obj.empty_display_size = size
    obj.location = location
    obj.show_name = True
    return obj


def make_player_proxy(ground_z: float, location: Vector, collection: bpy.types.Collection,
                      player_height: float) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(location.x, location.y, ground_z + player_height / 2))
    proxy = bpy.context.object
    proxy.name = "PLAYER_REFERENCE"
    proxy.dimensions = (player_height * 0.34, player_height * 0.34, player_height)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move_to_collection(proxy, collection)
    proxy.display_type = "WIRE"
    # The proxy is a viewport calibration aid.  Keep the walker sprite as the
    # visible render reference, but never let the solid proxy occlude the
    # church in a camera preview.
    proxy.hide_render = True
    proxy["player_height_world"] = 1.75
    proxy["source_unit_height"] = player_height
    proxy["annotation_status"] = "REFERENCE - resize only if the owner wants a different player proportion"
    return proxy


def make_sprite_plane(path: Path, ground_z: float, location: Vector,
                      collection: bpy.types.Collection, height: float) -> bpy.types.Object:
    image = bpy.data.images.load(str(path), check_existing=True)
    image.pack()
    width, height_px = image.size
    frame_width = width / 6.0
    aspect = frame_width / max(height_px, 1.0)
    width_world = height * aspect
    vertices = [
        (-width_world / 2, 0, 0),
        (width_world / 2, 0, 0),
        (width_world / 2, 0, height),
        (-width_world / 2, 0, height),
    ]
    faces = [(0, 1, 2, 3)]
    mesh = bpy.data.meshes.new("WALKER_SPRITE_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.uv_layers.new(name="UVMap")
    # First 24x48 frame from the six-frame horizontal walker sheet.
    uv = [(0.0, 0.0), (1.0 / 6.0, 0.0), (1.0 / 6.0, 1.0), (0.0, 1.0)]
    for loop, coord in zip(mesh.loops, uv):
        mesh.uv_layers.active.data[loop.index].uv = coord
    mesh.update()
    obj = bpy.data.objects.new("WALKER_SPRITE", mesh)
    collection.objects.link(obj)
    obj.location = (location.x, location.y - 0.006, ground_z)
    obj["sprite_asset"] = str(path)
    obj["frame_index"] = 0
    material = bpy.data.materials.new("WalkerSpriteMaterial")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    principled = nodes.get("Principled BSDF")
    texture = nodes.new("ShaderNodeTexImage")
    texture.image = image
    texture.interpolation = "Closest"
    links.new(texture.outputs["Color"], principled.inputs["Base Color"])
    links.new(texture.outputs["Alpha"], principled.inputs["Alpha"])
    principled.inputs["Roughness"].default_value = 1.0
    try:
        material.surface_render_method = "DITHERED"
    except AttributeError:
        material.blend_method = "BLEND"
    obj.data.materials.append(material)
    return obj


def make_reference_image(path: Path, collection: bpy.types.Collection) -> bpy.types.Object:
    image = bpy.data.images.load(str(path), check_existing=True)
    image.pack()
    obj = bpy.data.objects.new("REFERENCE_TARGET_PHOTO", None)
    collection.objects.link(obj)
    obj.empty_display_type = "IMAGE"
    obj.data = image
    obj.empty_display_size = 0.75
    obj.color[3] = 0.9
    obj.location = (1.35, 0.1, 0.0)
    obj.rotation_euler = (math.pi / 2, 0.0, 0.0)
    obj["annotation_status"] = "REFERENCE ONLY - supplied church-town visual target"
    obj.hide_render = True
    return obj


def import_source(path: Path, collection: bpy.types.Collection) -> list[bpy.types.Object]:
    before = set(bpy.data.objects)
    try:
        bpy.ops.wm.obj_import(filepath=str(path), validate_meshes=False)
    except AttributeError:
        bpy.ops.import_scene.obj(filepath=str(path), axis_forward="-Z", axis_up="Y")
    imported = [obj for obj in bpy.data.objects if obj not in before]
    for obj in imported:
        move_to_collection(obj, collection)
        obj.name = "Meshy_Village_Source" if len(imported) == 1 else "Meshy_Village_Source_" + obj.name
        obj["source_asset"] = str(path)
    return imported


def bind_source_texture(source_obj: Path, imported: list[bpy.types.Object]) -> None:
    texture_path = source_obj.with_suffix(".png")
    if not texture_path.exists():
        candidates = sorted(source_obj.parent.glob("*.png"))
        if not candidates:
            raise FileNotFoundError(f"No source texture found beside {source_obj}")
        texture_path = candidates[0]
    image = bpy.data.images.load(str(texture_path.resolve()), check_existing=True)
    image.pack()
    materials = {
        material
        for obj in imported
        for material in obj.data.materials
        if material is not None
    }
    for material in materials:
        if not material.use_nodes:
            continue
        for node in material.node_tree.nodes:
            if node.type == "TEX_IMAGE":
                node.image = image


def build(args: argparse.Namespace) -> None:
    clear_scene()
    scene = bpy.context.scene
    scene["second_gate_annotation_scene"] = 1
    scene["authoring_note"] = "Edit named objects in SecondGate_Annotations, then return the .blend for extraction."
    scene["source_model_yaw_degrees_runtime"] = 270.0

    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.world.color = (0.12, 0.12, 0.12)
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
        scene.render.resolution_x = 512
        scene.render.resolution_y = 512
        scene.render.resolution_percentage = 100
        scene.view_settings.look = "AgX - Medium High Contrast"
    except (AttributeError, TypeError):
        pass

    source_collection = ensure_collection("Meshy_Village_Source")
    annotations = ensure_collection("SecondGate_Annotations")
    reference_collection = ensure_collection("Reference_Target")
    imported = import_source(args.source_obj.resolve(), source_collection)
    if not imported:
        raise RuntimeError("OBJ import produced no objects")
    bind_source_texture(args.source_obj.resolve(), imported)

    bounds_min = Vector((math.inf, math.inf, math.inf))
    bounds_max = Vector((-math.inf, -math.inf, -math.inf))
    for obj in imported:
        for corner in obj.bound_box:
            world_corner = obj.matrix_world @ Vector(corner)
            bounds_min = Vector((min(bounds_min.x, world_corner.x), min(bounds_min.y, world_corner.y), min(bounds_min.z, world_corner.z)))
            bounds_max = Vector((max(bounds_max.x, world_corner.x), max(bounds_max.y, world_corner.y), max(bounds_max.z, world_corner.z)))
    # Blender's OBJ importer converts the supplied Y-up OBJ to Blender's
    # conventional Z-up scene: X/Y are ground, Z is height.
    ground_z = bounds_min.z
    source_height = bounds_max.z - bounds_min.z
    environment_offset_z = -0.1
    for obj in imported:
        obj.location.z += environment_offset_z
    player_height = source_height * (1.75 / 6.4) * 0.5
    center = Vector(((bounds_min.x + bounds_max.x) / 2, (bounds_min.y + bounds_max.y) / 2, ground_z))
    player_location = Vector((center.x, bounds_min.y + (bounds_max.y - bounds_min.y) * 0.12, ground_z))

    proxy = make_player_proxy(ground_z, player_location, annotations, player_height)
    sprite = make_sprite_plane(args.walker.resolve(), ground_z, player_location, annotations, player_height)
    sprite.parent = proxy
    sprite.matrix_parent_inverse = proxy.matrix_world.inverted()
    marker_specs = {
        "SPAWN_PLAYER": player_location,
        "CHURCH_CENTER": center,
        "CHURCH_ENTRANCE": Vector((center.x, bounds_min.y + (bounds_max.y - bounds_min.y) * 0.30, ground_z)),
        "ORIENTATION_FORWARD": Vector((player_location.x, player_location.y + player_height * 1.5, ground_z)),
    }
    for name, location in marker_specs.items():
        marker = make_marker(name, location, annotations, "SINGLE_ARROW" if name == "ORIENTATION_FORWARD" else "SPHERE", player_height * 0.45)
        marker["edit_me"] = True
    walkable = make_grid_template("WALKABLE_MAIN", bounds_min, bounds_max, ground_z + environment_offset_z, annotations)
    walkable["environment_offset_z"] = environment_offset_z
    reference = make_reference_image(args.reference.resolve(), reference_collection)
    reference["reference_for"] = "church-square viewport composition"

    camera_data = bpy.data.cameras.new("CAMERA_PLAYER_VIEW_Data")
    camera = bpy.data.objects.new("CAMERA_PLAYER_VIEW", camera_data)
    annotations.objects.link(camera)
    camera.location = (player_location.x, bounds_min.y - (bounds_max.y - bounds_min.y) * 0.35, ground_z + player_height * 0.78)
    look_at(camera, Vector((center.x, center.y, ground_z + environment_offset_z + source_height * 0.38)))
    camera_data.lens = 42
    camera_data.sensor_width = 36
    scene.camera = camera
    try:
        background = camera_data.background_images.new()
        background.image = bpy.data.images.get(reference.data.name)
        background.alpha = 0.22
        background.display_depth = "BACK"
        background.frame_method = "FIT"
    except (AttributeError, RuntimeError):
        pass

    top_data = bpy.data.cameras.new("CAMERA_TOP_VIEW_Data")
    top = bpy.data.objects.new("CAMERA_TOP_VIEW", top_data)
    annotations.objects.link(top)
    top.location = (center.x, center.y, bounds_max.z + (bounds_max.x - bounds_min.x) * 1.25)
    top.rotation_euler = (0.0, 0.0, 0.0)
    top.rotation_euler = (0.0, 0.0, 0.0)
    look_at(top, Vector((center.x, center.y, ground_z + environment_offset_z)))
    top_data.type = "ORTHO"
    top_data.ortho_scale = max(bounds_max.x - bounds_min.x, bounds_max.z - bounds_min.z) * 1.25

    for name, location, energy, size in [
        ("Key_Light", (center.x - 0.8, center.y - 1.0, ground_z + 1.2), 24, 1.5),
        ("Fill_Light", (center.x + 0.8, center.y + 0.5, ground_z + 0.7), 8, 2.0),
    ]:
        data = bpy.data.lights.new(name + "_Data", "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        light = bpy.data.objects.new(name, data)
        annotations.objects.link(light)
        light.location = location
        look_at(light, Vector((center.x, center.y, ground_z)))

    scene["annotation_objects"] = "WALKABLE_MAIN, PLAYER_REFERENCE, WALKER_SPRITE, SPAWN_PLAYER, CHURCH_CENTER, CHURCH_ENTRANCE, ORIENTATION_FORWARD"
    scene["walkable_template_note"] = "WALKABLE_MAIN is a full-grid template. Delete blocked cells and return this file."
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()))
    print(f"ANNOTATION BLEND OK: {args.output.resolve()}")


if __name__ == "__main__":
    build(parse_args())
