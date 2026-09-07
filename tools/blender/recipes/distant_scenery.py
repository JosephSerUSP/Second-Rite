"""Render source-derived Cortico background topology onto world-space planes.

This is deliberately not a silhouette generator or a runtime row of houses.
The pilot source already contains authored lodging, padaria, shrine and facade
modules. This recipe duplicates those complete modules into a deeper,
coherent town row, renders that topology from the canon pitched camera, and
puts the result on a world-space billboard. The plane reacts to pitch like
background geometry; actor/event billboards remain the separate camera-up,
non-keystoning presentation path in the runtime.

The floor is not painted into a floating card. A grounded bridge extends from
the action plane to the billboard's base so the visible floor reaches the
background instead of stopping at a depth seam.

The adopted source is opened read-only and is never saved by this script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import sys
from pathlib import Path


SCHEMA_VERSION = 3
LANE_MIN_Y = -2.844
LANE_CENTRE_Y = 12.031
LANE_MAX_Y = 26.906
STUDY_MARGIN_Y = 20.0
BACKGROUND_MIN_X = 22.0
BACKGROUND_MAX_X = 34.0
MAX_OPENING_Y = 5.0
PLATE_WIDTH = 866
PLATE_HEIGHT = 240
BILLBOARD_X = 36.0
# The canon pitched camera sees the floor's bottom frame intersection around
# X=-12.0. Starting there keeps the world filled under the translucent menu as
# well as across the action plane and into the background card.
FLOOR_NEAR_X = -13.0


# Each span is the measured visible Y footprint of the source module. The
# layout is intentionally legible as a row of real places, with small gaps for
# alleys/openings rather than a random collection of disconnected shapes.
DEFAULT_MODULES = (
    {
        "id": "east_end_facade",
        "selectors": ("CORTICO_east_facade",),
        "anchor": (17.0, -12.875, 0.0),
        "target": (28.0, 17.5, 0.0),
        "span": 5.12,
    },
    {
        "id": "padaria_west",
        "selectors": ("CORTICO_padaria_house_",),
        "anchor": (15.3, -2.964, 0.0),
        "target": (25.5, 11.0, 0.0),
        "span": 6.2,
    },
    {
        "id": "lodging_west",
        "selectors": ("CORTICO_lodging_house_",),
        "anchor": (16.0, -0.233, 0.0),
        "target": (24.5, 5.5, 0.0),
        "span": 8.6,
    },
    {
        "id": "shrine_west",
        "selectors": ("CORTICO_shrine_facade", "CORTICO_shrine_door_"),
        "anchor": (16.7, 6.531, 0.0),
        "target": (26.5, 0.0, 0.0),
        "span": 4.35,
    },
    {
        "id": "shrine_east",
        "selectors": ("CORTICO_shrine_facade", "CORTICO_shrine_door_"),
        "anchor": (16.7, 6.531, 0.0),
        "target": (26.5, -3.0, 0.0),
        "span": 4.35,
    },
    {
        "id": "lodging_east",
        "selectors": ("CORTICO_lodging_house_",),
        "anchor": (16.0, -0.233, 0.0),
        "target": (24.5, -8.0, 0.0),
        "span": 8.6,
    },
    {
        "id": "padaria_east",
        "selectors": ("CORTICO_padaria_house_",),
        "anchor": (15.3, -2.964, 0.0),
        "target": (25.5, -13.0, 0.0),
        "span": 6.2,
    },
    {
        "id": "west_end_facade",
        "selectors": ("CORTICO_west_facade",),
        "anchor": (16.9, 13.175, 0.0),
        "target": (28.0, -19.5, 0.0),
        "span": 4.95,
    },
)


def lane_to_blender_y(lane_y, lane_centre=LANE_CENTRE_Y):
    """Apply the adopted source's explicit runtime lane mirror."""
    value = float(lane_y)
    if not math.isfinite(value):
        raise ValueError("lane_y must be finite")
    return float(lane_centre) - value


def coverage_bounds(module):
    """Return the authored world-Y footprint of one background module."""
    centre = float(module["target"][1])
    span = float(module["span"])
    return centre - span * 0.5, centre + span * 0.5


def validate_module(module):
    if not isinstance(module, dict):
        raise ValueError("background module must be an object")
    ident = str(module.get("id", ""))
    if not ident or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789_"
                        for ch in ident):
        raise ValueError("background module id must be lower snake case")
    selectors = module.get("selectors")
    if not selectors or not all(isinstance(item, str) and item for item in selectors):
        raise ValueError(f"{ident}: selectors are required")
    for field in ("anchor", "target"):
        point = module.get(field)
        if not isinstance(point, (tuple, list)) or len(point) != 3:
            raise ValueError(f"{ident}: {field} must be an xyz point")
        if not all(math.isfinite(float(value)) for value in point):
            raise ValueError(f"{ident}: {field} must be finite")
    if float(module.get("span", 0.0)) <= 0.0:
        raise ValueError(f"{ident}: span must be positive")
    x = float(module["target"][0])
    if x < BACKGROUND_MIN_X or x > BACKGROUND_MAX_X:
        raise ValueError(f"{ident}: target X is outside background depth")
    return True


def validate_modules(modules=DEFAULT_MODULES):
    if len(modules) < 5:
        raise ValueError("background needs a complete multi-building topology")
    for module in modules:
        validate_module(module)
    bounds = sorted(coverage_bounds(module) for module in modules)
    if bounds[0][0] > -STUDY_MARGIN_Y or bounds[-1][1] < STUDY_MARGIN_Y:
        raise ValueError("background topology does not overscan the study window")
    for left, right in zip(bounds, bounds[1:]):
        if right[0] - left[1] > MAX_OPENING_Y:
            raise ValueError("background row contains an unreasonably large opening")
    return True


def _candidate_collection():
    import bpy

    collection = bpy.data.collections.get("BACKGROUND_TOPOLOGY_CANDIDATE")
    if collection is None:
        collection = bpy.data.collections.new("BACKGROUND_TOPOLOGY_CANDIDATE")
    if collection.name not in {child.name for child in bpy.context.scene.collection.children}:
        bpy.context.scene.collection.children.link(collection)
    return collection


def _source_meshes(selectors):
    import bpy

    return sorted(
        [obj for obj in bpy.context.scene.objects
         if obj.type == "MESH"
         and any(obj.name.startswith(selector) for selector in selectors)],
        key=lambda obj: obj.name,
    )


def _copy_module(module, collection, index):
    import bpy
    from mathutils import Matrix, Vector

    source_objects = _source_meshes(module["selectors"])
    if not source_objects:
        selectors = ", ".join(module["selectors"])
        raise RuntimeError(f"source module {module['id']} has no mesh objects: {selectors}")
    anchor = Matrix.Translation(Vector(module["anchor"]))
    target = Matrix.Translation(Vector(module["target"]))
    root = bpy.data.objects.new(
        f"CORTICO_BG_{index:02d}_{module['id'].upper()}_ROOT", None)
    collection.objects.link(root)
    root.empty_display_type = "PLAIN_AXES"
    root.location = tuple(float(value) for value in module["target"])
    root["sr_export"] = False
    root["sr_preview_only"] = True
    root["sr_noninteractive"] = True
    root["sr_background_topology"] = True
    root["sr_flatten_via_exterior_exporter"] = True
    root["sr_source_module"] = module["id"]
    for source in source_objects:
        copy = source.copy()
        copy.data = source.data.copy()
        copy.name = f"CORTICO_BG_{index:02d}_{source.name}"
        collection.objects.link(copy)
        copy.parent = root
        relative = anchor.inverted() @ source.matrix_world
        copy.matrix_world = target @ relative
        copy.hide_render = False
        copy.hide_viewport = False
        copy["sr_export"] = False
        copy["sr_preview_only"] = True
        copy["sr_noninteractive"] = True
        copy["sr_background_topology"] = True
        copy["sr_flatten_via_exterior_exporter"] = True
        copy["sr_source_module"] = module["id"]
        copy["sr_source_object"] = source.name
        copy["sr_representation"] = "authoring_topology"
    return root, source_objects


def _copy_ground(collection):
    """Extend the actual source ground with one grounded 3D slab."""
    import bpy

    source = bpy.data.objects.get("CORTICO_ground")
    if source is None or source.type != "MESH":
        raise RuntimeError("adopted source is missing CORTICO_ground")
    x0, x1 = 21.0, 38.0
    y0, y1 = -32.0, 32.0
    z0, z1 = -0.6, 0.0
    vertices = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    faces = ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5),
             (2, 3, 7, 6), (3, 0, 4, 7))
    mesh = bpy.data.meshes.new("CORTICO_BACKGROUND_GROUND_MESH")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new("CORTICO_BACKGROUND_GROUND", mesh)
    collection.objects.link(obj)
    for material in source.data.materials:
        mesh.materials.append(material)
    obj["sr_export"] = False
    obj["sr_preview_only"] = True
    obj["sr_noninteractive"] = True
    obj["sr_background_topology"] = True
    obj["sr_flatten_via_exterior_exporter"] = True
    obj["sr_source_object"] = source.name
    obj["sr_ground"] = True
    obj["sr_representation"] = "authoring_topology"
    return obj


def _source_material(names):
    import bpy

    for name in names:
        material = bpy.data.materials.get(name)
        if material is not None:
            return material
    raise RuntimeError(f"adopted source is missing material family: {names}")


def _topology_tag(obj, source_name):
    obj["sr_export"] = False
    obj["sr_preview_only"] = True
    obj["sr_noninteractive"] = True
    obj["sr_background_topology"] = True
    obj["sr_flatten_via_exterior_exporter"] = True
    obj["sr_source_object"] = source_name
    obj["sr_representation"] = "authoring_topology"


def _connector_wall(collection, index, y0, y1):
    import bpy

    x0, x1 = 27.25, 31.0
    z0, z1 = 0.0, 4.65
    vertices = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    faces = ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5),
             (2, 3, 7, 6), (3, 0, 4, 7))
    mesh = bpy.data.meshes.new(f"CORTICO_BACKGROUND_CONNECTOR_{index:02d}_MESH")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(f"CORTICO_BACKGROUND_CONNECTOR_{index:02d}", mesh)
    collection.objects.link(obj)
    mesh.materials.append(_source_material(("sr_old_limestone", "sr_rough_limestone")))
    _topology_tag(obj, "source_derived_party_wall")
    obj["sr_connector_y"] = (float(y0), float(y1))
    return obj


def _connector_roof(collection, index, y0, y1):
    import bpy

    x0, x1 = 27.1, 31.15
    base, ridge = 4.65, 5.55
    centre = (y0 + y1) * 0.5
    half = max(0.55, (y1 - y0) * 0.5)
    vertices = [
        (x0, centre - half, base), (x0, centre, ridge),
        (x0, centre + half, base), (x1, centre - half, base),
        (x1, centre, ridge), (x1, centre + half, base),
    ]
    faces = ((0, 3, 4, 1), (1, 4, 5, 2), (0, 1, 2), (3, 5, 4),
             (0, 2, 5, 3))
    mesh = bpy.data.meshes.new(f"CORTICO_BACKGROUND_CONNECTOR_{index:02d}_ROOF_MESH")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(f"CORTICO_BACKGROUND_CONNECTOR_{index:02d}_ROOF", mesh)
    collection.objects.link(obj)
    mesh.materials.append(_source_material(("sr_roof_tile", "sr_terracotta")))
    _topology_tag(obj, "source_derived_party_wall_roof")
    return obj


def _add_connectors(collection, root, module_records):
    bounds = sorted((item["coverageY"], item["id"]) for item in module_records)
    connectors = []
    for index, (left, right) in enumerate(zip(bounds, bounds[1:]), 1):
        gap = right[0][0] - left[0][1]
        if gap <= 0.25:
            continue
        y0 = left[0][1] - 0.12
        y1 = right[0][0] + 0.12
        wall = _connector_wall(collection, index, y0, y1)
        roof = _connector_roof(collection, index, y0, y1)
        wall.parent = root
        roof.parent = root
        connectors.append({"id": f"connector_{index:02d}",
                           "coverageY": [y0, y1],
                           "gapY": gap,
                           "objects": [wall.name, roof.name]})
    return connectors


def build_topology():
    import bpy

    validate_modules()
    collection = _candidate_collection()
    root = bpy.data.objects.new("CORTICO_BACKGROUND_TOPOLOGY_ROOT", None)
    collection.objects.link(root)
    root.empty_display_type = "PLAIN_AXES"
    root["sr_export"] = False
    root["sr_preview_only"] = True
    root["sr_noninteractive"] = True
    root["sr_background_topology"] = True
    root["sr_representation"] = "authoring_topology"
    root["sr_flatten_via_exterior_exporter"] = True
    root["sr_schema_version"] = SCHEMA_VERSION
    modules = []
    for index, module in enumerate(DEFAULT_MODULES, 1):
        module_root, source_objects = _copy_module(module, collection, index)
        module_root.parent = root
        modules.append({
            "id": module["id"],
            "root": module_root,
            "sourceObjects": [obj.name for obj in source_objects],
            "coverageY": list(coverage_bounds(module)),
        })
    connector_records = _add_connectors(collection, root, modules)
    ground = _copy_ground(collection)
    ground.parent = root
    return root, modules, connector_records, ground


def _canon_camera(collection):
    import bpy
    from mathutils import Vector

    source_camera = bpy.data.objects.get("TH_CAMERA_PREVIEW")
    if source_camera is None:
        raise RuntimeError("adopted source is missing TH_CAMERA_PREVIEW")
    camera = source_camera.copy()
    camera.data = source_camera.data.copy()
    camera.name = "TH_CAMERA_CANON_STUDY"
    collection.objects.link(camera)
    camera.location = source_camera.location.copy()
    camera.data.shift_y = -0.8
    forward = Vector((math.cos(math.radians(17.5)), 0.0,
                      math.sin(math.radians(17.5))))
    camera.rotation_mode = "QUATERNION"
    camera.rotation_quaternion = forward.to_track_quat("-Z", "Y")
    return camera


def _study_actor(collection):
    import bpy

    source = bpy.data.objects.get("TH_ACTOR_PREVIEW_npc_scholar")
    if source is None:
        raise RuntimeError("adopted source is missing the scholar preview actor")
    actor = source.copy()
    actor.data = source.data.copy()
    actor.name = "CORTICO_BACKGROUND_STUDY_ACTOR"
    collection.objects.link(actor)
    actor.hide_render = False
    actor.hide_viewport = False
    actor["sr_export"] = False
    actor["sr_preview_only"] = True
    actor["sr_study_actor"] = True
    return actor


def _hide_original_scene_meshes():
    """Leave only the duplicated review topology visible for the plate render."""
    import bpy

    candidate = bpy.data.collections["BACKGROUND_TOPOLOGY_CANDIDATE"]
    candidate_objects = {obj.name for obj in candidate.all_objects}
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH" and obj.name not in candidate_objects:
            obj.hide_render = True


def _project(scene, camera, point):
    from bpy_extras.object_utils import world_to_camera_view
    from mathutils import Vector

    coord = world_to_camera_view(scene, camera, Vector(point))
    return coord.x * scene.render.resolution_x, (1.0 - coord.y) * scene.render.resolution_y


def _bisect_for_screen_y(scene, camera, x, y, target_y, low=-16.0, high=16.0):
    """Find the Z on a constant-X plane that projects to one image row."""
    for _ in range(64):
        mid = (low + high) * 0.5
        value = _project(scene, camera, (x, y, mid))[1]
        if value > target_y:
            low = mid
        else:
            high = mid
    return (low + high) * 0.5


def _bisect_for_screen_x(scene, camera, x, z, target_x, low=-64.0, high=64.0):
    """Find the Y on a constant-X plane that projects to one image column."""
    for _ in range(64):
        mid = (low + high) * 0.5
        value = _project(scene, camera, (x, mid, z))[0]
        # The adopted camera has screen-right = -Y.
        if value > target_x:
            low = mid
        else:
            high = mid
    return (low + high) * 0.5


def _render_background_plate(out_dir, camera):
    """Render the real distant topology once, as the billboard's texture."""
    import bpy

    scene = bpy.context.scene
    scene.camera = camera
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = PLATE_WIDTH
    scene.render.resolution_y = PLATE_HEIGHT
    scene.render.resolution_percentage = 100
    # Keep the canon vertical framing while the texture widens to cover the
    # whole lane. Blender's horizontal-fit camera would widen the vertical
    # FOV at this 866x240 aspect and shrink the buildings to a thin strip.
    camera.data.sensor_fit = "VERTICAL"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    # Keep the topology pass transparent. The painted sky is a separate
    # world-space plane behind the card, so it can remain an independently
    # pitched background layer instead of becoming part of the architecture
    # texture or the floor.
    scene.render.film_transparent = True
    scene.render.filepath = str(Path(out_dir) / "cortico-background-billboard.png")

    # The floor is deliberately separate. It is a world-space bridge in the
    # study, not a painted lower edge that can float above the action plane.
    for obj in bpy.data.collections["BACKGROUND_TOPOLOGY_CANDIDATE"].all_objects:
        if obj.get("sr_ground"):
            obj.hide_render = True
        if obj.get("sr_study_actor"):
            obj.hide_render = True
        if obj.get("sr_sky_backdrop"):
            obj.hide_render = True
    bpy.ops.render.render(write_still=True)
    camera.data.sensor_fit = "HORIZONTAL"
    return Path(scene.render.filepath)


def _billboard_material(image):
    import bpy

    material = bpy.data.materials.get("CORTICO_BACKGROUND_BILLBOARD_MATERIAL")
    if material is None:
        material = bpy.data.materials.new("CORTICO_BACKGROUND_BILLBOARD_MATERIAL")
    material.use_nodes = True
    material.use_backface_culling = False
    nodes, links = material.node_tree.nodes, material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    transparent = nodes.new("ShaderNodeBsdfTransparent")
    emission = nodes.new("ShaderNodeEmission")
    texture = nodes.new("ShaderNodeTexImage")
    mix = nodes.new("ShaderNodeMixShader")
    texture.image = image
    texture.interpolation = "Closest"
    texture.extension = "CLIP"
    links.new(texture.outputs["Color"], emission.inputs["Color"])
    links.new(texture.outputs["Alpha"], mix.inputs[0])
    links.new(transparent.outputs[0], mix.inputs[1])
    links.new(emission.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], output.inputs["Surface"])
    return material


def _make_sky_backdrop(collection):
    """Provide a restrained painted fill behind the topology render."""
    import bpy

    material = bpy.data.materials.get("CORTICO_BACKGROUND_SKY_MATERIAL")
    if material is None:
        material = bpy.data.materials.new("CORTICO_BACKGROUND_SKY_MATERIAL")
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (0.055, 0.075, 0.11, 1.0)
    emission.inputs["Strength"].default_value = 0.35
    links.new(emission.outputs[0], output.inputs["Surface"])

    mesh = bpy.data.meshes.new("CORTICO_BACKGROUND_SKY_MESH")
    mesh.from_pydata([(40.0, -64.0, -8.0), (40.0, 64.0, -8.0),
                     (40.0, 64.0, 16.0), (40.0, -64.0, 16.0)], [], [(0, 1, 2, 3)])
    mesh.update()
    obj = bpy.data.objects.new("CORTICO_BACKGROUND_SKY", mesh)
    collection.objects.link(obj)
    mesh.materials.append(material)
    obj["sr_export"] = False
    obj["sr_preview_only"] = True
    obj["sr_noninteractive"] = True
    obj["sr_sky_backdrop"] = True
    return obj


def _make_world_billboard(collection, camera, image):
    """Create a constant-depth card whose corners match the pitched camera frame."""
    import bpy

    z_mid = 3.5
    left_y = _bisect_for_screen_x(bpy.context.scene, camera, BILLBOARD_X, z_mid, 0.0)
    right_y = _bisect_for_screen_x(bpy.context.scene, camera, BILLBOARD_X, z_mid, PLATE_WIDTH)
    # The rendered topology has no painted floor. Its lowest opaque pixels are
    # the building/foliage feet, so the billboard's lower edge belongs on the
    # authored ground plane at z=0. Keeping that contact explicit prevents the
    # card from floating above the bridge or being hidden below it.
    bottom_z = 0.0
    top_z = 8.0
    # Render-time source pixels were framed with a vertical-fit camera. Map
    # that source's z=0 row to the billboard's world z=0, otherwise the
    # buildings appear suspended above the real floor bridge. The temporary
    # fit switch affects only this calibration query; the study camera returns
    # to the normal horizontal-fit projection immediately afterwards.
    previous_fit = camera.data.sensor_fit
    camera.data.sensor_fit = "VERTICAL"
    contact_row = _project(bpy.context.scene, camera, (28.0, 0.0, 0.0))[1]
    camera.data.sensor_fit = previous_fit
    bottom_v = max(0.0, min(1.0, 1.0 - contact_row / PLATE_HEIGHT))

    mesh = bpy.data.meshes.new("CORTICO_BACKGROUND_BILLBOARD_MESH")
    # Image left is world +Y because the camera's screen-right is world -Y.
    mesh.from_pydata([
        (BILLBOARD_X, left_y, bottom_z),
        (BILLBOARD_X, right_y, bottom_z),
        (BILLBOARD_X, right_y, top_z),
        (BILLBOARD_X, left_y, top_z),
    ], [], [(0, 1, 2, 3)])
    mesh.update()
    uv = mesh.uv_layers.new(name="UVMap")
    for loop, coord in zip(mesh.loops, ((0.0, bottom_v), (1.0, bottom_v),
                                        (1.0, 1.0), (0.0, 1.0))):
        uv.data[loop.index].uv = coord
    obj = bpy.data.objects.new("CORTICO_BACKGROUND_BILLBOARD", mesh)
    collection.objects.link(obj)
    mesh.materials.append(_billboard_material(image))
    obj["sr_export"] = False
    obj["sr_preview_only"] = True
    obj["sr_noninteractive"] = True
    obj["sr_background_billboard"] = True
    obj["sr_render_role"] = "background_billboard"
    obj["sr_source_representation"] = "rendered_authoring_topology"
    obj["sr_reacts_to_pitch"] = True
    obj["sr_camera_space"] = False
    return obj, {
        "x": BILLBOARD_X,
        "y": [round(right_y, 4), round(left_y, 4)],
        "z": [round(bottom_z, 4), round(top_z, 4)],
        "sourceContactRow": round(contact_row, 4),
        "sourceBottomV": round(bottom_v, 6),
        "imageSize": [PLATE_WIDTH, PLATE_HEIGHT],
    }


def _make_floor_bridge(collection):
    """Carry the grounded floor from the action plane into the card's base."""
    import bpy

    source = bpy.data.objects.get("CORTICO_ground")
    if source is None or source.type != "MESH":
        raise RuntimeError("adopted source is missing CORTICO_ground")
    mesh = bpy.data.meshes.new("CORTICO_BACKGROUND_FLOOR_BRIDGE_MESH")
    x0, x1 = FLOOR_NEAR_X, BILLBOARD_X + 0.05
    y0, y1 = -32.0, 32.0
    z0, z1 = -0.12, 0.0
    mesh.from_pydata([
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
    ], [], [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
            (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])
    mesh.update()
    obj = bpy.data.objects.new("CORTICO_BACKGROUND_FLOOR_BRIDGE", mesh)
    collection.objects.link(obj)
    for material in source.data.materials:
        mesh.materials.append(material)
    obj["sr_export"] = False
    obj["sr_preview_only"] = True
    obj["sr_noninteractive"] = False
    obj["sr_floor_bridge"] = True
    obj["sr_render_role"] = "walkable_floor"
    obj["sr_ground_z"] = 0.0
    return obj


def _render_studies(out_dir, camera, actor, billboard, floor):
    import bpy

    scene = bpy.context.scene
    scene.camera = camera
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 426
    scene.render.resolution_y = 240
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    for obj in bpy.data.collections["BACKGROUND_TOPOLOGY_CANDIDATE"].all_objects:
        if obj.get("sr_ground") or obj.get("sr_background_topology"):
            obj.hide_render = True
        if obj.get("sr_study_actor"):
            obj.hide_render = False
    billboard.hide_render = False
    floor.hide_render = False
    original_camera_y = camera.location.y
    original_actor_location = actor.location.copy()
    studies = []
    for label, lane_y in (("west", LANE_MIN_Y), ("centre", LANE_CENTRE_Y),
                          ("east", LANE_MAX_Y)):
        y = lane_to_blender_y(lane_y)
        actor.location = (7.8, y, 0.0)
        camera.location.y = y
        path = Path(out_dir) / f"background-billboard-{label}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        studies.append({"label": label, "runtimeLaneY": lane_y,
                        "blenderY": y, "path": path.name})
    camera.location.y = original_camera_y
    actor.location = original_actor_location
    return studies


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_runtime_layer(out_dir, billboard_geometry, image_path):
    """Emit the reusable depth-tested runtime card beside the study output.

    Blender's card uses world coordinates. The runtime OBJ convention is the
    inverse of obj_model.objToWorld: OBJ (x, z, -y) restores engine (x, y, z).
    The image is already rendered through the canonical pitched camera once;
    the runtime card must never render it through that camera a second time.
    """
    out_dir = Path(out_dir)
    left_y = float(billboard_geometry["y"][1])
    right_y = float(billboard_geometry["y"][0])
    bottom_z = float(billboard_geometry["z"][0])
    top_z = float(billboard_geometry["z"][1])
    bottom_v = float(billboard_geometry["sourceBottomV"])
    obj = out_dir / "background.obj"
    obj.write_text(
        "mtllib background.mtl\n"
        "o distant_scenery_world_card\n"
        "# Engine coordinates are authored as OBJ x,z,-y for obj_model.\n"
        f"v 36.000000 {bottom_z:.6f} {-left_y:.6f}\n"
        f"v 36.000000 {bottom_z:.6f} {-right_y:.6f}\n"
        f"v 36.000000 {top_z:.6f} {-right_y:.6f}\n"
        f"v 36.000000 {top_z:.6f} {-left_y:.6f}\n"
        f"vt 0.000000 {bottom_v:.6f}\n"
        f"vt 1.000000 {bottom_v:.6f}\n"
        "vt 1.000000 1.000000\n"
        "vt 0.000000 1.000000\n"
        "usemtl DistantSceneryCard\n"
        "f 1/1 2/2 3/3 4/4\n",
        encoding="utf-8",
    )
    mtl = out_dir / "background.mtl"
    mtl.write_text(
        "# Source-derived world-space distant scenery card.\n"
        "newmtl DistantSceneryCard\n"
        "Ka 1.000 1.000 1.000\n"
        "Kd 1.000 1.000 1.000\n"
        "map_Kd cortico_background.png\n",
        encoding="utf-8",
    )
    texture = out_dir / "cortico_background.png"
    shutil.copyfile(image_path, texture)
    return {
        "renderMesh": obj.name,
        "materialLibrary": mtl.name,
        "texture": texture.name,
        "sha256": {
            "renderMesh": _sha256(obj),
            "materialLibrary": _sha256(mtl),
            "texture": _sha256(texture),
        },
        "cameraSpace": False,
        "reactsToPitch": True,
        "depthRangeX": [36.0, 36.0],
        "floorBridge": False,
    }


def _manifest(source, studies, modules):
    return {
        "schemaVersion": SCHEMA_VERSION,
        "candidate": "cortico_background_billboard",
        "evidenceKind": "blender_source_derived_billboard_study",
        "runtimeEvidence": False,
        "source": {"blend": Path(source).name, "sha256": _sha256(source),
                   "ownership": "adopted_source_read_only"},
        "camera": {"pitchDegrees": -17.5,
                   "blenderEquivalentPitchDegrees": 17.5,
                   "sourceEyePreserved": True, "studyPrincipalShiftY": -0.8,
                   "studyMode": "camera_follow_review",
                   "studyModeRuntimeEquivalent": False},
        "topology": {"representation": "authoring_topology_only",
                     "opaqueSilhouettes": False,
                     "cameraSpaceBackdrop": False,
                     "flattenPath": "source topology -> pitched camera render -> world-space billboard",
                     "backgroundDepthX": [BACKGROUND_MIN_X, BACKGROUND_MAX_X],
                     "modules": modules["modules"],
                     "connectors": modules["connectors"],
                     "groundCoverageY": [-32.0, 32.0]},
        "runtimeRepresentation": {
            "background": "world_space_textured_billboard",
            "reactsToPitch": True,
            "cameraSpaceActorBillboard": False,
            "floorBridge": modules["floorBridge"],
            "assets": modules.get("runtimeAssets"),
        },
        "studies": studies,
        "outputs": {"libraryBlend": "cortico-background-topology-authoring.blend",
                    "studyBlend": "cortico-background-billboard-study.blend",
                    "billboardTexture": "cortico-background-billboard.png"},
    }


def build_study(source, out_dir):
    import bpy

    bpy.ops.wm.open_mainfile(filepath=str(Path(source).resolve()))
    root, modules, connectors, ground = build_topology()
    del root
    _hide_original_scene_meshes()
    collection = bpy.data.collections["BACKGROUND_TOPOLOGY_CANDIDATE"]
    camera = _canon_camera(collection)
    actor = _study_actor(collection)
    sky = _make_sky_backdrop(collection)
    plate_path = _render_background_plate(out_dir, camera)
    plate_image = bpy.data.images.load(str(plate_path.resolve()), check_existing=True)
    billboard, billboard_geometry = _make_world_billboard(collection, camera, plate_image)
    floor = _make_floor_bridge(collection)
    runtime_assets = _write_runtime_layer(out_dir, billboard_geometry, plate_path)
    sky.hide_render = False
    study_dir = Path(out_dir) / "studies"
    study_dir.mkdir(parents=True, exist_ok=True)
    studies = _render_studies(study_dir, camera, actor, billboard, floor)
    study_path = Path(out_dir) / "cortico-background-billboard-study.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(study_path))
    manifest_modules = [{"id": item["id"], "coverageY": item["coverageY"],
                         "sourceObjects": item["sourceObjects"]}
                        for item in modules]
    return study_path, studies, {"modules": manifest_modules,
                                 "connectors": connectors,
                                 "billboard": billboard_geometry,
                                 "runtimeAssets": runtime_assets,
                                 "floorBridge": {"nearX": FLOOR_NEAR_X,
                                                  "farX": BILLBOARD_X + 0.05,
                                                  "groundZ": 0.0}}


def build_library(source, out_dir):
    """Save a source-derived library with the candidate collection isolated."""
    import bpy

    bpy.ops.wm.open_mainfile(filepath=str(Path(source).resolve()))
    build_topology()
    candidate = bpy.data.collections["BACKGROUND_TOPOLOGY_CANDIDATE"]
    for obj in candidate.all_objects:
        if obj.type == "MESH":
            obj["sr_export"] = False
    path = Path(out_dir) / "cortico-background-topology-authoring.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    return path


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if not args.source.is_file():
        raise SystemExit(f"source blend not found: {args.source}")
    validate_modules()
    args.out_dir = args.out_dir.resolve()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    library = build_library(args.source, args.out_dir)
    study, studies, modules = build_study(args.source, args.out_dir)
    manifest = _manifest(args.source, studies, modules)
    manifest["outputs"]["libraryBlend"] = library.name
    manifest["outputs"]["studyBlend"] = study.name
    manifest_path = args.out_dir / "candidate-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n",
                             encoding="utf-8")
    print(json.dumps({"status": "BACKGROUND BILLBOARD STUDY OK",
                      "library": str(library), "study": str(study),
                      "manifest": str(manifest_path), "studies": studies},
                     sort_keys=True))


if __name__ == "__main__":
    import bpy  # noqa: F401
    main(sys.argv[sys.argv.index("--") + 1:])
