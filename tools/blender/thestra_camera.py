"""Blender preview adapter for an authoritative Thestra camera record.

The record is produced by runtime camera calibration tooling.  This module is
deliberately one-way: Blender consumes the record and never writes camera facts
back to runtime authoring data.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

try:
    import bpy
    from bpy_extras.object_utils import world_to_camera_view
    from mathutils import Matrix, Vector
except ImportError:  # ordinary-Python protocol checks do not need Blender
    bpy = None
    world_to_camera_view = None
    Matrix = None
    Vector = None


CONTRACT = "thestra.world-camera-calibration"
VERSION = 1
SENSOR_WIDTH_MM = 36.0


def validate_calibration(record: dict) -> dict:
    if not isinstance(record, dict):
        raise ValueError("camera calibration must be an object")
    if record.get("contract") != CONTRACT or record.get("version") != VERSION:
        raise ValueError("unsupported Thestra camera calibration contract/version")
    if record.get("projection") != "perspective":
        raise ValueError("this authoring adapter requires a perspective calibration")
    for key in (
        "targetWidth", "targetHeight", "baseViewportWidth", "baseViewportHeight",
        "nearPlane", "farPlane", "fovHalfX", "fovHalfY",
    ):
        value = float(record[key])
        if not math.isfinite(value) or value <= 0.0:
            raise ValueError(f"camera calibration {key} must be positive and finite")
    for key in (
        "viewportCenterX", "viewportCenterY", "projectionWindowOffsetX",
        "projectionWindowOffsetY",
    ):
        if not math.isfinite(float(record[key])):
            raise ValueError(f"camera calibration {key} must be finite")
    expected = {
        "handedness": "right-handed", "worldUp": "+Z", "worldHorizontal": "XY",
        "cameraForward": "+depth", "cameraRight": "+right",
        "screenOrigin": "top-left", "screenY": "+down",
        "blenderCameraForward": "-Z", "blenderCameraUp": "+Y",
    }
    if record.get("coordinateSystem") != expected:
        raise ValueError("unsupported Thestra/Blender coordinate-system declaration")
    return record


def load_calibration(path: Path) -> dict:
    return validate_calibration(json.loads(Path(path).read_text(encoding="utf-8")))


def _require_blender() -> None:
    if bpy is None:
        raise RuntimeError("thestra_camera.py requires Blender for scene operations")


def _basis(record: dict):
    orientation = record["orientation"]
    dx, dy = float(orientation["forwardX"]), float(orientation["forwardY"])
    pitch = float(orientation["pitchRadians"])
    right = Vector((float(orientation["rightX"]), float(orientation["rightY"]), 0.0))
    cp, sp = math.cos(pitch), math.sin(pitch)
    up = Vector((dx * sp, dy * sp, cp))
    forward = Vector((dx * cp, dy * cp, -sp))
    return right, up, forward


def _projection_coefficients(record: dict):
    scale = record["projectionScale"]
    base_width = float(record["baseViewportWidth"])
    base_height = float(record["baseViewportHeight"])
    target_width = float(record["targetWidth"])
    target_height = float(record["targetHeight"])
    return (
        float(scale["x"]) / float(record["fovHalfX"]) * base_width / target_width,
        float(scale["y"]) / float(record["fovHalfY"]) * base_height / target_height,
    )


def _set_transform(camera, record):
    eye = Vector(tuple(float(record["eye"][key]) for key in ("x", "y", "z")))
    right, up, forward = _basis(record)
    rotation = Matrix((right, up, -forward)).transposed()
    camera.matrix_world = Matrix.Translation(eye) @ rotation.to_4x4()


def _solve_principal_point(scene, camera, record):
    _, _, forward = _basis(record)
    probe_point = camera.location + forward * max(1.0, float(record["nearPlane"]) * 4.0)
    desired_x = float(record["viewportCenterX"]) / float(record["targetWidth"])
    desired_y = 1.0 - float(record["viewportCenterY"]) / float(record["targetHeight"])
    camera.data.shift_x = 0.0
    camera.data.shift_y = 0.0
    base = world_to_camera_view(scene, camera, probe_point)
    camera.data.shift_x = 1.0
    shifted_x = world_to_camera_view(scene, camera, probe_point)
    dx = shifted_x.x - base.x
    camera.data.shift_x = (desired_x - base.x) / dx
    camera.data.shift_y = 0.0
    base = world_to_camera_view(scene, camera, probe_point)
    camera.data.shift_y = 1.0
    shifted_y = world_to_camera_view(scene, camera, probe_point)
    dy = shifted_y.y - base.y
    camera.data.shift_y = (desired_y - base.y) / dy
    solved = world_to_camera_view(scene, camera, probe_point)
    if abs(solved.x - desired_x) > 1e-5 or abs(solved.y - desired_y) > 1e-5:
        raise RuntimeError("calibrated principal point did not reproduce the record")


def create_or_update_camera(record: dict, *, scene=None, name="TH_CAMERA_CALIBRATED"):
    """Instantiate the calibrated camera and return the Blender object."""

    _require_blender()
    validate_calibration(record)
    scene = scene or bpy.context.scene
    scene.render.resolution_x = int(record["targetWidth"])
    scene.render.resolution_y = int(record["targetHeight"])
    scene.render.resolution_percentage = 100
    obj = bpy.data.objects.get(name)
    if obj is None:
        data = bpy.data.cameras.new(name)
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
    if obj.type != "CAMERA":
        raise ValueError(f"{name!r} exists but is not a camera")
    ax, _ay = _projection_coefficients(record)
    data = obj.data
    data.type = "PERSP"
    data.sensor_fit = "HORIZONTAL"
    data.sensor_width = SENSOR_WIDTH_MM
    data.lens = SENSOR_WIDTH_MM * ax * 0.5
    data.clip_start = float(record["nearPlane"])
    data.clip_end = float(record["farPlane"])
    _set_transform(obj, record)
    _solve_principal_point(scene, obj, record)
    obj["thestra_calibration_contract"] = CONTRACT
    obj["thestra_calibration_version"] = VERSION
    obj["thestra_preview_only"] = True
    scene.camera = obj
    return obj


def project_world_point(scene, camera, point):
    _require_blender()
    result = world_to_camera_view(scene, camera, Vector(point))
    return (
        result.x * float(scene.render.resolution_x),
        (1.0 - result.y) * float(scene.render.resolution_y),
    )


def create_actor_preview(image_path: Path, camera, *, anchor=(0.0, 0.0, 0.0),
                         frame_width=24, frame_height=48, frame_index=0,
                         world_height=1.75, name="TH_WALKER_PREVIEW"):
    """Create a nearest-filtered, hard-alpha Walker preview at a feet anchor."""

    _require_blender()
    image = bpy.data.images.load(str(Path(image_path).resolve()), check_existing=True)
    width, height = map(int, image.size)
    if frame_width <= 0 or frame_height <= 0 or width % frame_width or height % frame_height:
        raise ValueError("Walker image dimensions are incompatible with the supplied frame grid")
    frames = (width // frame_width) * (height // frame_height)
    if not 0 <= int(frame_index) < frames:
        raise ValueError("Walker frame index is outside the image grid")
    old = bpy.data.objects.get(name)
    if old is not None:
        bpy.data.objects.remove(old, do_unlink=True)
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    aspect = float(frame_width) / float(frame_height)
    world_width = float(world_height) * aspect
    mesh.from_pydata([
        (-world_width / 2, 0, 0), (world_width / 2, 0, 0),
        (world_width / 2, 0, world_height), (-world_width / 2, 0, world_height),
    ], [], [(0, 1, 2, 3)])
    mesh.update()
    uv = mesh.uv_layers.new(name="UVMap")
    column = int(frame_index) % (width // frame_width)
    row = int(frame_index) // (width // frame_width)
    u0, u1 = column * frame_width / width, (column + 1) * frame_width / width
    v1, v0 = 1.0 - row * frame_height / height, 1.0 - (row + 1) * frame_height / height
    coords = ((u0, v0), (u1, v0), (u1, v1), (u0, v1))
    for loop in mesh.loops:
        uv.data[loop.index].uv = coords[loop.vertex_index]
    material = bpy.data.materials.new(name + "_MAT")
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    transparent = nodes.new("ShaderNodeBsdfTransparent")
    emission = nodes.new("ShaderNodeEmission")
    texture = nodes.new("ShaderNodeTexImage")
    cutoff = nodes.new("ShaderNodeMath")
    mix = nodes.new("ShaderNodeMixShader")
    texture.image = image
    texture.interpolation = "Closest"
    cutoff.operation = "GREATER_THAN"
    cutoff.inputs[1].default_value = 0.5
    links.new(texture.outputs["Color"], emission.inputs["Color"])
    links.new(texture.outputs["Alpha"], cutoff.inputs[0])
    links.new(cutoff.outputs[0], mix.inputs[0])
    links.new(transparent.outputs[0], mix.inputs[1])
    links.new(emission.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], output.inputs["Surface"])
    mesh.materials.append(material)
    obj.location = Vector(anchor)
    camera_forward = camera.matrix_world.to_3x3() @ Vector((0.0, 0.0, -1.0))
    obj.rotation_euler[2] = math.atan2(camera_forward.x, -camera_forward.y)
    obj["thestra_preview_only"] = True
    obj["thestra_feet_anchor"] = True
    return obj
