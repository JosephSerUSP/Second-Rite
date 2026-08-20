#!/usr/bin/env python3
"""Thestra WorldCamera Blender Calibration Tool.

Instantiates and synchronizes a Blender camera object (TH_CAMERA_PREVIEW) that is
numerically equivalent to an authoritative resolved Thestra WorldCamera.

Authority direction:
  Thestra WorldCamera -> calibration record -> Blender camera (TH_CAMERA_PREVIEW)
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

try:
    import bpy
    import bpy_extras
    import mathutils
    IN_BLENDER = True
except ImportError:
    IN_BLENDER = False

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WALKER_PATH = REPO_ROOT / "projects" / "hichaukitoden-game" / "assets" / "character" / "walker.png"


def project_world_point_thestra(record: dict, point: tuple[float, float, float] | list[float]) -> tuple[float, float, float]:
    """Authoritative mathematical projection of a 3D world point to Thestra screen coordinates."""
    wx, wy, wz = point[0], point[1], point[2]
    eye = record["eye"]
    rel_x = wx - eye[0]
    rel_y = wy - eye[1]
    rel_z = wz - eye[2]

    f = record["forward"]
    r = record["right"]
    u = record["up"]

    depth = rel_x * f[0] + rel_y * f[1] + rel_z * f[2]
    horizontal = rel_x * r[0] + rel_y * r[1] + rel_z * r[2]
    vertical = rel_x * u[0] + rel_y * u[1] + rel_z * u[2]

    viewport_center_x = record["viewportCenterX"]
    viewport_center_y = record["viewportCenterY"]
    base_w = record["baseViewportWidth"]
    base_h = record["baseViewportHeight"]
    proj_scale_x = record.get("projectionScaleX", 1.0)
    proj_scale_y = record.get("projectionScaleY", 1.0)

    if record["projection"] == "orthographic":
        ortho_half_x = record["orthoHalfX"]
        ortho_half_y = record["orthoHalfY"]
        screen_x = viewport_center_x + (horizontal / ortho_half_x) * proj_scale_x * (base_w * 0.5)
        screen_y = viewport_center_y - (vertical / ortho_half_y) * proj_scale_y * (base_h * 0.5)
    else:
        fov_half_x = record["fovHalfX"]
        fov_half_y = record["fovHalfY"]
        screen_x = viewport_center_x + (horizontal / (fov_half_x * depth)) * proj_scale_x * (base_w * 0.5)
        screen_y = viewport_center_y - (vertical / (fov_half_y * depth)) * proj_scale_y * (base_h * 0.5)

    return screen_x, screen_y, depth


if IN_BLENDER:
    def project_world_point_blender(scene: bpy.types.Scene, camera_obj: bpy.types.Object, point: tuple[float, float, float] | list[float]) -> tuple[float, float, float]:
        """Project a 3D point using Blender's camera model and return screen pixel coordinates."""
        pw = mathutils.Vector((point[0], point[1], point[2]))
        ndc = bpy_extras.object_utils.world_to_camera_view(scene, camera_obj, pw)
        target_w = scene.render.resolution_x
        target_h = scene.render.resolution_y
        screen_x = ndc.x * target_w
        screen_y = (1.0 - ndc.y) * target_h
        return screen_x, screen_y, ndc.z


    def get_or_create_collection(name: str, parent: bpy.types.Collection | None = None) -> bpy.types.Collection:
        if name in bpy.data.collections:
            return bpy.data.collections[name]
        col = bpy.data.collections.new(name)
        if parent:
            parent.children.link(col)
        else:
            bpy.context.scene.collection.children.link(col)
        return col


    def apply_thestra_camera(
        record: dict,
        scene: bpy.types.Scene | None = None,
        name: str = "TH_CAMERA_PREVIEW",
        create_guides: bool = True,
    ) -> bpy.types.Object:
        """Instantiate or update the preview camera object in Blender."""
        scene = scene or bpy.context.scene

        cam_obj = bpy.data.objects.get(name)
        if cam_obj and cam_obj.type == 'CAMERA':
            cam_data = cam_obj.data
        else:
            cam_data = bpy.data.cameras.new(name)
            cam_obj = bpy.data.objects.new(name, cam_data)
            scene.collection.objects.link(cam_obj)

        scene.camera = cam_obj

        target_w = int(record.get("targetWidth", 426))
        target_h = int(record.get("targetHeight", 240))
        base_w = float(record.get("baseViewportWidth", 256))
        base_h = float(record.get("baseViewportHeight", 144))
        proj_scale_x = float(record.get("projectionScaleX", 1.0))
        proj_scale_y = float(record.get("projectionScaleY", 1.0))

        # 1. Output framing
        scene.render.resolution_x = target_w
        scene.render.resolution_y = target_h
        scene.render.pixel_aspect_x = 1.0
        scene.render.pixel_aspect_y = 1.0

        # 2. Camera Projection & Lens
        cam_data.sensor_fit = 'HORIZONTAL'
        sensor_width_mm = 36.0
        cam_data.sensor_width = sensor_width_mm

        is_ortho = record.get("projection") == "orthographic"
        if is_ortho:
            cam_data.type = 'ORTHO'
            ortho_half_x = float(record.get("orthoHalfX", 6.0))
            ortho_width = (2.0 * ortho_half_x * target_w) / (proj_scale_x * base_w)
            cam_data.ortho_scale = ortho_width
        else:
            cam_data.type = 'PERSP'
            fov_half_x = float(record.get("fovHalfX", 0.75))
            tan_half_fov_x = (fov_half_x * target_w) / (proj_scale_x * base_w)
            cam_data.lens = (sensor_width_mm * 0.5) / tan_half_fov_x

        # 3. Off-axis Principal Point Shift
        viewport_center_x = float(record.get("viewportCenterX", target_w * 0.5))
        viewport_center_y = float(record.get("viewportCenterY", 70.0))

        cam_data.shift_x = -(viewport_center_x - target_w * 0.5) / target_w
        cam_data.shift_y = -(target_h * 0.5 - viewport_center_y) / target_w

        # 4. Clipping
        cam_data.clip_start = float(record.get("nearPlane", 0.05))
        cam_data.clip_end = float(record.get("farPlane", 64.0))

        # 5. Transform Matrix
        eye = record["eye"]
        r = record["right"]
        u = record["up"]
        f = record["forward"]

        R = mathutils.Vector((r[0], r[1], r[2]))
        U = mathutils.Vector((u[0], u[1], u[2]))
        F = mathutils.Vector((f[0], f[1], f[2]))
        T = mathutils.Vector((eye[0], eye[1], eye[2]))

        cam_obj.matrix_world = mathutils.Matrix((
            (R.x, U.x, -F.x, T.x),
            (R.y, U.y, -F.y, T.y),
            (R.z, U.z, -F.z, T.z),
            (0.0, 0.0,  0.0, 1.0),
        ))

        bpy.context.view_layer.update()

        if create_guides:
            create_composition_guides(cam_obj, record, scene)

        return cam_obj


    def create_composition_guides(camera_obj: bpy.types.Object, record: dict, scene: bpy.types.Scene) -> bpy.types.Collection:
        """Create composition guides visualizing native frame, base frame, and panning envelope."""
        guides_col = get_or_create_collection("TH_CAMERA_GUIDES")

        # Clean existing guide objects
        for obj in list(guides_col.objects):
            bpy.data.objects.remove(obj, do_unlink=True)

        target_w = float(record.get("targetWidth", 426))
        target_h = float(record.get("targetHeight", 240))
        base_w = float(record.get("baseViewportWidth", 256))
        base_h = float(record.get("baseViewportHeight", 144))

        # Reference plane at focus/guide distance (e.g. depth = 4.0 units)
        guide_depth = 4.0
        tan_half_fov_x = (record.get("fovHalfX", 0.75) * target_w) / (record.get("projectionScaleX", 1.0) * base_w)
        tan_half_fov_y = tan_half_fov_x * (target_h / target_w)

        world_w = 2.0 * guide_depth * tan_half_fov_x
        world_h = 2.0 * guide_depth * tan_half_fov_y

        def make_wire_rect(name: str, x0: float, y0: float, x1: float, y1: float) -> bpy.types.Object:
            # Map normalized screen [-1..1] to camera local plane at -guide_depth
            local_x0 = x0 * (world_w * 0.5)
            local_x1 = x1 * (world_w * 0.5)
            local_y0 = y0 * (world_h * 0.5)
            local_y1 = y1 * (world_h * 0.5)

            mesh = bpy.data.meshes.new(name)
            verts = [
                (local_x0, local_y0, -guide_depth),
                (local_x1, local_y0, -guide_depth),
                (local_x1, local_y1, -guide_depth),
                (local_x0, local_y1, -guide_depth),
            ]
            edges = [(0, 1), (1, 2), (2, 3), (3, 0)]
            mesh.from_pydata(verts, edges, [])
            mesh.update()

            obj = bpy.data.objects.new(name, mesh)
            obj.parent = camera_obj
            guides_col.objects.link(obj)
            return obj

        # 1. Base 256x144 framing guide (centered)
        b_x0 = -(base_w / target_w)
        b_x1 = (base_w / target_w)
        b_y0 = -(base_h / target_h)
        b_y1 = (base_h / target_h)
        make_wire_rect("GUIDE_BASE_256x144", b_x0, b_y0, b_x1, b_y1)

        # 2. Panning envelope (+/- 96 px travel)
        max_travel_px = 96.0
        env_x0 = -((base_w + 2 * max_travel_px) / target_w)
        env_x1 = ((base_w + 2 * max_travel_px) / target_w)
        make_wire_rect("GUIDE_PAN_ENVELOPE_96PX", env_x0, b_y0, env_x1, b_y1)

        return guides_col


    def create_actor_preview(
        image_path: str | Path | None = None,
        frame_index: int = 0,
        width_units: float = 1.0,
        height_units: float = 2.0,
        name: str = "TH_ACTOR_PREVIEW",
        location: tuple[float, float, float] = (0.0, 0.0, 0.0),
        face_camera: bool = True,
        scene: bpy.types.Scene | None = None,
    ) -> bpy.types.Object:
        """Create a 24x48 character reference plane with feet anchored at the origin."""
        scene = scene or bpy.context.scene
        image_path = Path(image_path or DEFAULT_WALKER_PATH)

        if not image_path.is_file():
            raise FileNotFoundError(f"Actor sprite image not found: {image_path}")

        # Load or locate image in Blender
        img = bpy.data.images.get(image_path.name) or bpy.data.images.load(str(image_path))
        img_w, img_h = img.size[0], img.size[1]

        # Slicing evidence: 144x48 consists of 6 columns of 24x48
        frame_w = 24
        frame_h = 48
        total_frames = max(1, img_w // frame_w)
        frame_index = max(0, min(frame_index, total_frames - 1))

        u0 = frame_index / float(total_frames)
        u1 = (frame_index + 1) / float(total_frames)
        v0 = 0.0
        v1 = 1.0

        # Build Mesh Plane anchored at feet (Z=0, centered in X)
        half_w = width_units * 0.5
        verts = [
            (-half_w, 0.0, 0.0),          # 0: bottom-left
            (half_w, 0.0, 0.0),           # 1: bottom-right
            (half_w, 0.0, height_units),  # 2: top-right
            (-half_w, 0.0, height_units), # 3: top-left
        ]
        faces = [(0, 1, 2, 3)]

        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(verts, [], faces)
        mesh.update()

        # UV Layer
        uv_layer = mesh.uv_layers.new(name="UVMap")
        uv_layer.data[0].uv = (u0, v0)
        uv_layer.data[1].uv = (u1, v0)
        uv_layer.data[2].uv = (u1, v1)
        uv_layer.data[3].uv = (u0, v1)

        obj = bpy.data.objects.get(name)
        if obj:
            obj.data = mesh
        else:
            obj = bpy.data.objects.new(name, mesh)
            scene.collection.objects.link(obj)

        obj.location = location

        # Material Setup: Unlit Emission, Closest filtering, Chroma-Key (#0050FF) / Alpha Clip
        mat_name = f"{name}_Material"
        mat = bpy.data.materials.get(mat_name) or bpy.data.materials.new(mat_name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        nodes.clear()

        output = nodes.new('ShaderNodeOutputMaterial')
        emission = nodes.new('ShaderNodeEmission')
        transparent = nodes.new('ShaderNodeBsdfTransparent')
        mix = nodes.new('ShaderNodeMixShader')

        tex = nodes.new('ShaderNodeTexImage')
        tex.image = img
        tex.interpolation = 'Closest'

        # Chroma key detection: distance to (0, 80/255, 255/255)
        dist = nodes.new('ShaderNodeVectorMath')
        dist.operation = 'DISTANCE'
        dist.inputs[1].default_value = (0.0, 80.0 / 255.0, 1.0)

        greater = nodes.new('ShaderNodeMath')
        greater.operation = 'GREATER_THAN'
        greater.inputs[1].default_value = 0.05

        links = mat.node_tree.links
        links.new(dist.inputs[0], tex.outputs['Color'])
        links.new(greater.inputs[0], dist.outputs['Value'])

        links.new(emission.inputs['Color'], tex.outputs['Color'])
        links.new(mix.inputs['Fac'], greater.outputs['Value'])
        links.new(mix.inputs[1], transparent.outputs['BSDF'])
        links.new(mix.inputs[2], emission.outputs['Emission'])
        links.new(output.inputs['Surface'], mix.outputs['Shader'])

        if hasattr(mat, 'blend_method'):
            mat.blend_method = 'CLIP'
        if hasattr(mat, 'shadow_method'):
            mat.shadow_method = 'NONE'

        if len(obj.data.materials) == 0:
            obj.data.materials.append(mat)
        else:
            obj.data.materials[0] = mat

        # Face camera orientation
        if face_camera:
            cam = bpy.data.objects.get("TH_CAMERA_PREVIEW") or scene.camera
            if cam:
                # Align plane normal with camera forward in ground XY
                cam_fwd = cam.matrix_world.to_3x3() @ mathutils.Vector((0, 0, -1))
                yaw = math.atan2(cam_fwd.y, cam_fwd.x) + math.pi / 2
                obj.rotation_euler = (0, 0, yaw)

        return obj


def main():
    if not IN_BLENDER:
        print("This script is designed to be executed inside Blender (`blender --python thestra_camera.py`).")
        sys.exit(1)

    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    parser = argparse.ArgumentParser(description="Thestra WorldCamera Blender Tool")
    parser.add_argument("--record", type=str, help="Path to JSON camera calibration record")
    parser.add_argument("--actor", action="store_true", help="Instantiate 24x48 actor preview plane")
    parser.add_argument("--actor-frame", type=int, default=0, help="Actor frame index (0..5)")
    parser.add_argument("--out-blend", type=str, help="Save resulting .blend file")
    args = parser.parse_args(argv)

    if args.record:
        record_path = Path(args.record)
        if not record_path.is_file():
            print(f"ERROR: Record file not found: {record_path}", file=sys.stderr)
            sys.exit(1)
        record = json.loads(record_path.read_text(encoding="utf-8"))
        cam = apply_thestra_camera(record)
        print(f"TH_CAMERA_PREVIEW applied successfully from {record_path}")

    if args.actor:
        actor = create_actor_preview(frame_index=args.actor_frame)
        print(f"TH_ACTOR_PREVIEW instantiated (frame={args.actor_frame})")

    if args.out_blend:
        bpy.ops.wm.save_as_mainfile(filepath=args.out_blend)
        print(f"Saved .blend file to {args.out_blend}")


if __name__ == "__main__":
    if IN_BLENDER:
        main()
