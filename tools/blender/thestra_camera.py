"""Blender preview helpers for serialized Thestra WorldCamera calibration records.

Authority is one-way: Thestra WorldCamera -> calibration JSON -> Blender preview.
Nothing here writes Scene camera data back to Thestra.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

try:
    import bpy
    from bpy_extras.object_utils import world_to_camera_view
    from mathutils import Matrix, Vector
except ImportError:  # Allows ordinary Python syntax/import tests outside Blender.
    bpy = None
    world_to_camera_view = None
    Matrix = None
    Vector = None


CAMERA_NAME = "TH_CAMERA_PREVIEW"
ACTOR_NAME = "TH_ACTOR_PREVIEW"
CONTRACT = "thestra.world-camera-calibration"
VERSION = 1
SENSOR_WIDTH_MM = 36.0


def _require_blender():
    if bpy is None:
        raise RuntimeError("thestra_camera.py must run inside Blender")


def load_calibration(path):
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_calibration(record)
    return record


def validate_calibration(record):
    if not isinstance(record, dict):
        raise ValueError("camera calibration must be a JSON object")
    if record.get("contract") != CONTRACT or record.get("version") != VERSION:
        raise ValueError("unsupported Thestra camera calibration contract/version")
    if record.get("projection") not in {"perspective", "orthographic"}:
        raise ValueError("camera calibration projection must be perspective or orthographic")
    for key in ("targetWidth", "targetHeight", "baseViewportWidth", "baseViewportHeight",
                "nearPlane", "farPlane"):
        value = float(record[key])
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"camera calibration {key} must be positive and finite")
    for key in ("viewportCenterX", "viewportCenterY", "projectionWindowOffsetX",
                "projectionWindowOffsetY"):
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


def _camera_basis(record):
    o = record["orientation"]
    dx, dy = float(o["forwardX"]), float(o["forwardY"])
    rx, ry = float(o["rightX"]), float(o["rightY"])
    pitch = float(o["pitchRadians"])
    cp, sp = math.cos(pitch), math.sin(pitch)
    right = Vector((rx, ry, 0.0))
    up = Vector((dx * sp, dy * sp, cp))
    forward = Vector((dx * cp, dy * cp, -sp))
    return right, up, forward


def _projection_coefficients(record):
    sx = float(record["projectionScale"]["x"])
    sy = float(record["projectionScale"]["y"])
    bw, bh = float(record["baseViewportWidth"]), float(record["baseViewportHeight"])
    tw, th = float(record["targetWidth"]), float(record["targetHeight"])
    if record["projection"] == "perspective":
        ax = sx / float(record["fovHalfX"]) * (bw / tw)
        ay = sy / float(record["fovHalfY"]) * (bh / th)
    else:
        ax = sx / float(record["orthoHalfX"]) * (bw / tw)
        ay = sy / float(record["orthoHalfY"]) * (bh / th)
    return ax, ay


def _set_scene_framing(scene, record):
    scene.render.resolution_x = int(record["targetWidth"])
    scene.render.resolution_y = int(record["targetHeight"])
    scene.render.resolution_percentage = 100
    ax, ay = _projection_coefficients(record)
    # Blender's horizontal sensor fit yields vertical/horizontal NDC scale ratio
    # equal to display aspect. Adjust pixel aspect only when Thestra's resolved
    # projectionScale/fov pair deliberately asks for an anisotropic projection.
    desired_display_aspect = ay / ax
    scene.render.pixel_aspect_y = 1.0
    scene.render.pixel_aspect_x = desired_display_aspect * (
        float(record["targetHeight"]) / float(record["targetWidth"])
    )


def _set_transform(obj, record):
    eye = Vector((float(record["eye"]["x"]), float(record["eye"]["y"]),
                  float(record["eye"]["z"])))
    right, up, forward = _camera_basis(record)
    backward = -forward
    rotation = Matrix((right, up, backward)).transposed()
    obj.matrix_world = Matrix.Translation(eye) @ rotation.to_4x4()


def _optical_axis_world_point(obj, record):
    _, _, forward = _camera_basis(record)
    depth = max(1.0, float(record["nearPlane"]) * 4.0)
    return obj.location + forward * depth


def _solve_lens_shift(scene, obj, record):
    axis_point = _optical_axis_world_point(obj, record)
    desired_x = float(record["viewportCenterX"]) / float(record["targetWidth"])
    desired_y = 1.0 - float(record["viewportCenterY"]) / float(record["targetHeight"])

    obj.data.shift_x = 0.0
    obj.data.shift_y = 0.0
    base = world_to_camera_view(scene, obj, axis_point)

    obj.data.shift_x = 1.0
    probe_x = world_to_camera_view(scene, obj, axis_point)
    dx = probe_x.x - base.x
    if abs(dx) < 1e-12:
        raise RuntimeError("Blender camera shift_x probe produced no principal-point movement")
    obj.data.shift_x = (desired_x - base.x) / dx

    obj.data.shift_y = 1.0
    probe_y = world_to_camera_view(scene, obj, axis_point)
    obj.data.shift_y = 0.0
    base_y = world_to_camera_view(scene, obj, axis_point)
    dy = probe_y.y - base_y.y
    if abs(dy) < 1e-12:
        raise RuntimeError("Blender camera shift_y probe produced no principal-point movement")
    obj.data.shift_y = (desired_y - base_y.y) / dy

    solved = world_to_camera_view(scene, obj, axis_point)
    if abs(solved.x - desired_x) > 1e-5 or abs(solved.y - desired_y) > 1e-5:
        raise RuntimeError("Blender lens-shift calibration failed to reproduce Thestra principal point")


def create_or_update_camera(record, *, scene=None, name=CAMERA_NAME, make_active=False):
    """Create/update the preview camera without making Blender authoritative."""
    _require_blender()
    validate_calibration(record)
    scene = scene or bpy.context.scene
    _set_scene_framing(scene, record)

    obj = bpy.data.objects.get(name)
    if obj is None:
        data = bpy.data.cameras.new(name)
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
    elif obj.type != "CAMERA":
        raise ValueError(f"{name} exists but is not a camera")

    camera = obj.data
    ax, ay = _projection_coefficients(record)
    camera.sensor_fit = "HORIZONTAL"
    camera.sensor_width = SENSOR_WIDTH_MM
    camera.clip_start = float(record["nearPlane"])
    camera.clip_end = float(record["farPlane"])
    camera.shift_x = 0.0
    camera.shift_y = 0.0

    if record["projection"] == "perspective":
        camera.type = "PERSP"
        # Runtime NDC X coefficient is ax. Blender horizontal sensor fit uses
        # 2*lens/sensorWidth, so this is an exact derived lens, not an authored
        # millimetre guess.
        camera.lens = SENSOR_WIDTH_MM * ax * 0.5
    else:
        camera.type = "ORTHO"
        # Blender ortho_scale is the full vertical span. ay is Thestra's NDC
        # coefficient per world unit, hence full span = 2/ay.
        camera.ortho_scale = 2.0 / ay

    _set_transform(obj, record)
    _solve_lens_shift(scene, obj, record)

    obj["thestra_preview_only"] = True
    obj["thestra_calibration_contract"] = CONTRACT
    obj["thestra_calibration_version"] = VERSION
    obj["thestra_projection_window_offset_x"] = float(record["projectionWindowOffsetX"])
    obj["thestra_projection_window_offset_y"] = float(record["projectionWindowOffsetY"])
    if make_active:
        scene.camera = obj
    return obj


def project_world_point(scene, camera_obj, point):
    _require_blender()
    coord = world_to_camera_view(scene, camera_obj, Vector(point))
    return (
        coord.x * float(scene.render.resolution_x),
        (1.0 - coord.y) * float(scene.render.resolution_y),
    )


def inspect_sprite_sheet(image_path, frame_width, frame_height):
    """Validate a caller-supplied frame size; never infer a sheet convention."""
    _require_blender()
    image = bpy.data.images.load(str(Path(image_path).resolve()), check_existing=True)
    width, height = int(image.size[0]), int(image.size[1])
    fw, fh = int(frame_width), int(frame_height)
    if fw <= 0 or fh <= 0 or width % fw or height % fh:
        raise ValueError(f"{image_path} is {width}x{height}; it is not a {fw}x{fh} frame grid")
    return {
        "image": image,
        "width": width,
        "height": height,
        "frameWidth": fw,
        "frameHeight": fh,
        "columns": width // fw,
        "rows": height // fh,
        "frames": (width // fw) * (height // fh),
    }


def _actor_material(image, name, alpha_cutoff):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    transparent = nodes.new("ShaderNodeBsdfTransparent")
    emission = nodes.new("ShaderNodeEmission")
    texture = nodes.new("ShaderNodeTexImage")
    mix = nodes.new("ShaderNodeMixShader")
    texture.image = image
    texture.interpolation = "Closest"
    texture.extension = "CLIP"

    sep = nodes.new("ShaderNodeSeparateColor")
    less = nodes.new("ShaderNodeMath")
    less.operation = "LESS_THAN"
    less.inputs[1].default_value = 0.6

    alpha_math = nodes.new("ShaderNodeMath")
    alpha_math.operation = "GREATER_THAN"
    alpha_math.inputs[1].default_value = float(alpha_cutoff)

    combine = nodes.new("ShaderNodeMath")
    combine.operation = "MINIMUM"

    links.new(texture.outputs["Color"], sep.inputs["Color"])
    links.new(sep.outputs["Blue"], less.inputs[0])
    links.new(texture.outputs["Alpha"], alpha_math.inputs[0])
    links.new(less.outputs[0], combine.inputs[0])
    links.new(alpha_math.outputs[0], combine.inputs[1])

    links.new(texture.outputs["Color"], emission.inputs["Color"])
    links.new(combine.outputs[0], mix.inputs[0])
    links.new(transparent.outputs[0], mix.inputs[1])
    links.new(emission.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], output.inputs["Surface"])
    if hasattr(material, "blend_method"):
        material.blend_method = "CLIP"
        material.alpha_threshold = float(alpha_cutoff)
    material.use_backface_culling = False
    return material


def create_actor_preview(image_path, camera_obj, *, anchor=(0.0, 0.0, 0.0),
                         frame_width=24, frame_height=48, frame_index=0,
                         world_height=1.0, alpha_cutoff=0.5, name=ACTOR_NAME):
    """Create a nearest-filtered, alpha-clipped, unlit preview plane.

    The object origin is the actor's feet/world anchor. The caller supplies the
    frame dimensions; the helper validates the real image grid before slicing.
    """
    _require_blender()
    info = inspect_sprite_sheet(image_path, frame_width, frame_height)
    if frame_index < 0 or frame_index >= info["frames"]:
        raise ValueError(f"frame_index {frame_index} outside 0..{info['frames'] - 1}")
    frame_index = int(frame_index)
    col = frame_index % info["columns"]
    row = frame_index // info["columns"]
    aspect = float(frame_width) / float(frame_height)
    height = float(world_height)
    width = height * aspect

    obj = bpy.data.objects.get(name)
    if obj is not None:
        bpy.data.objects.remove(obj, do_unlink=True)
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    # Camera-local XY plane: +Y is screen-up and local +Z faces back toward the eye.
    mesh.from_pydata([
        (-width * 0.5, 0.0, 0.0),
        ( width * 0.5, 0.0, 0.0),
        ( width * 0.5, height, 0.0),
        (-width * 0.5, height, 0.0),
    ], [], [(0, 1, 2, 3)])
    mesh.update()

    uv_layer = mesh.uv_layers.new(name="UVMap")
    u0 = (col * frame_width) / info["width"]
    u1 = ((col + 1) * frame_width) / info["width"]
    v1 = 1.0 - (row * frame_height) / info["height"]
    v0 = 1.0 - ((row + 1) * frame_height) / info["height"]
    uv_by_vertex = ((u0, v0), (u1, v0), (u1, v1), (u0, v1))
    for loop in mesh.loops:
        uv_layer.data[loop.index].uv = uv_by_vertex[loop.vertex_index]

    material = _actor_material(info["image"], name + "_MAT", alpha_cutoff)
    mesh.materials.append(material)
    obj.location = Vector(anchor)
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = camera_obj.matrix_world.to_quaternion()
    obj["thestra_preview_only"] = True
    obj["thestra_feet_anchor"] = True
    obj["thestra_frame_width"] = int(frame_width)
    obj["thestra_frame_height"] = int(frame_height)
    obj["thestra_frame_index"] = frame_index
    return obj
