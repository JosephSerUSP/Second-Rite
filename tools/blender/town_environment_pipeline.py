"""Blender-authored baked environment pipeline for Second Gate town slices.

Contract V0 collections:
- TH_SOURCE: Authoritative detailed source geometry, materials, and lighting.
- TH_RENDER: Lightweight coarse render/depth mesh (with unwrapped UVs for atlas baking).
- TH_COLLISION: Simplified collision volumes.
- TH_ANCHORS: Spatial markers/empties with orientation.
- TH_PREVIEW_ACTORS: Preview actors (MUST be excluded from bake, mesh, collision, anchors).
- TH_PREVIEW_ONLY: Visual guides/reference geometry.
- TH_CAMERA_PREVIEW: Preview camera(s).

Produces a self-contained runtime package usable without Blender:
- environment.obj
- environment.mtl
- environment.png
- collision.obj (optional)
- environment.json
"""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BLENDER_SEARCH = [
    os.environ.get("BLENDER"),
    r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
    "blender",
]


def blender_executable():
    for candidate in BLENDER_SEARCH:
        if candidate and (candidate == "blender" or Path(candidate).is_file()):
            return candidate
    raise SystemExit("Blender not found; set BLENDER or install Blender")


def _operator_kwargs(operator, candidate_dict):
    try:
        rna = operator.get_rna_type()
        props = {prop.identifier for prop in rna.properties}
        return {k: v for k, v in candidate_dict.items() if k in props}
    except Exception:
        return candidate_dict


def run_pipeline_in_blender(
    blend_path: Path,
    output_dir: Path,
    atlas_size: int = 512,
    bake_samples: int | None = None,
    render_profile: str = "cycles-candidate",
    atlas_allocation: str = "area",
    camera_envelope=None,
    view_policy="bounded-camera",
    explicitly_unreachable=(),
    margin_px: int = 4,
):
    import bpy
    from mathutils import Vector, Matrix
    import second_gate_render
    import view_weighted_atlas

    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    scene = bpy.context.scene

    if atlas_allocation not in {"area", "view-weighted"}:
        raise ValueError("atlas_allocation must be 'area' or 'view-weighted'")
    if int(atlas_size) <= 0:
        raise ValueError("atlas_size must be positive")
    if int(margin_px) < 0:
        raise ValueError("margin_px must be >= 0")
    if atlas_allocation == "view-weighted":
        if not camera_envelope:
            raise ValueError(
                "view-weighted atlas allocation requires an explicit camera_envelope"
            )
        camera_envelope = [
            sample if isinstance(sample, view_weighted_atlas.ViewSample)
            else view_weighted_atlas.ViewSample.from_record(sample)
            for sample in camera_envelope
        ]
        view_policy = view_weighted_atlas.policy_from_preset(view_policy)

    # The project wrapper owns Second Gate's review dimensions; the shared
    # module owns the render-cost policy. Baking may use an explicit lower
    # sample count for a fixture, but it must start from a named profile.
    applied_profile = second_gate_render.apply(scene, render_profile)

    # 1. Validate Collections
    collections = {col.name: col for col in bpy.data.collections}
    required = ["TH_RENDER", "TH_SOURCE", "TH_ANCHORS"]
    for req in required:
        if req not in collections:
            raise RuntimeError(f"V0 contract violation: missing required collection '{req}'")

    col_render = collections["TH_RENDER"]
    col_source = collections["TH_SOURCE"]
    col_anchors = collections["TH_ANCHORS"]
    col_collision = collections.get("TH_COLLISION")
    col_preview_actors = collections.get("TH_PREVIEW_ACTORS")
    col_preview_only = collections.get("TH_PREVIEW_ONLY")
    col_camera = collections.get("TH_CAMERA_PREVIEW")

    render_mesh_objects = [obj for obj in col_render.objects if obj.type == 'MESH']
    if not render_mesh_objects:
        raise RuntimeError("TH_RENDER contains no mesh objects")

    # 2. Exclude preview and non-render collections from bake
    for col in (col_preview_actors, col_preview_only, col_collision, col_anchors, col_camera):
        if col:
            col.hide_render = True
            for obj in col.objects:
                obj.hide_render = True

    # Ensure source and render are visible in render for baking
    col_source.hide_render = False
    for obj in col_source.objects:
        obj.hide_render = False

    col_render.hide_render = False
    for obj in col_render.objects:
        obj.hide_render = False

    # 3. Setup Bake Target Image & Material on TH_RENDER
    target_obj = render_mesh_objects[0]
    # If multiple render objects, join duplicates or bake to the primary
    bpy.ops.object.select_all(action='DESELECT')
    for obj in render_mesh_objects:
        obj.select_set(True)
    scene.view_layers[0].objects.active = target_obj
    if len(render_mesh_objects) > 1:
        bpy.ops.object.join()
        target_obj = bpy.context.active_object

    if atlas_allocation == "view-weighted":
        allocation_report = view_weighted_atlas.allocate_blender(
            scene,
            scene.camera,
            target_obj,
            camera_envelope,
            view_policy,
            atlas_size=atlas_size,
            margin_px=margin_px,
            explicitly_unreachable=explicitly_unreachable,
        )
    else:
        allocation_report = view_weighted_atlas.allocate_area_blender(
            target_obj, atlas_size=atlas_size, margin_px=margin_px
        )
    print(
        "[pipeline] Atlas allocation: "
        f"{atlas_allocation}, islands={allocation_report['packing']['uvIslandCount']}, "
        f"packed={allocation_report['packing']['packedFraction']:.3f}"
    )

    # Create baked atlas image
    image_name = "environment_atlas"
    if image_name in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[image_name])
    bake_image = bpy.data.images.new(image_name, width=atlas_size, height=atlas_size, alpha=True)
    try:
        bake_image.colorspace_settings.name = "sRGB"
    except (AttributeError, TypeError, ValueError):
        pass

    # Ensure target object has a material with active image node
    mat_name = "EnvironmentBakedAtlas"
    mat = bpy.data.materials.get(mat_name)
    if not mat:
        mat = bpy.data.materials.new(mat_name)
        mat.use_nodes = True
    else:
        mat.use_nodes = True

    # Setup shader nodes for bake receiving
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    img_node = nodes.get("BakeTargetImg")
    if not img_node:
        img_node = nodes.new("ShaderNodeTexImage")
        img_node.name = "BakeTargetImg"
    img_node.image = bake_image
    nodes.active = img_node
    img_node.select = True

    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        links.new(img_node.outputs["Color"], bsdf.inputs["Base Color"])

    target_obj.data.materials.clear()
    target_obj.data.materials.append(mat)

    # 4. Perform Selected-To-Active Beauty Bake (Combined: materials, lights, shadows, AO)
    try:
        scene.cycles.device = 'CPU'
    except Exception:
        pass
    if bake_samples is not None:
        if int(bake_samples) <= 0:
            raise ValueError("bake_samples must be positive when supplied")
        scene.cycles.samples = int(bake_samples)
    scene.cycles.bake_type = 'COMBINED'
    scene.render.bake.use_selected_to_active = True
    scene.render.bake.cage_extrusion = 0.15
    scene.render.bake.max_ray_distance = 1.0
    scene.render.bake.margin = 4

    # Select all source objects as Selected, target_obj as Active
    bpy.ops.object.select_all(action='DESELECT')
    for obj in col_source.objects:
        if obj.type in {'MESH', 'CURVE', 'SURFACE'}:
            obj.select_set(True)
    target_obj.select_set(True)
    scene.view_layers[0].objects.active = target_obj

    bake_started = time.perf_counter()
    print(
        f"[pipeline] Baking beauty atlas ({atlas_size}x{atlas_size}, "
        f"{scene.cycles.samples} samples)..."
    )
    bpy.ops.object.bake(type='COMBINED')
    bake_seconds = time.perf_counter() - bake_started

    # Save baked texture
    texture_path = output_dir / "environment.png"
    bake_image.filepath_raw = str(texture_path)
    bake_image.file_format = 'PNG'
    bake_image.save()
    print(f"[pipeline] Saved beauty texture atlas to {texture_path}")

    # 5. Export TH_RENDER to environment.obj
    obj_path = output_dir / "environment.obj"
    mtl_path = output_dir / "environment.mtl"

    bpy.ops.object.select_all(action='DESELECT')
    target_obj.select_set(True)
    scene.view_layers[0].objects.active = target_obj

    export_candidates = {
        "filepath": str(obj_path),
        "check_existing": False,
        "export_selected_objects": True,
        "export_uv": True,
        "export_normals": True,
        "export_colors": False,
        "export_materials": True,
        "export_pbr_extensions": False,
        "export_triangulated_mesh": True,
        "apply_modifiers": True,
        "path_mode": "RELATIVE",
        "export_object_groups": True,
        "export_material_groups": True,
        "export_vertex_groups": False,
        "export_smooth_groups": True,
        "export_smooth_groups_bitflags": False,
    }
    kwargs = _operator_kwargs(bpy.ops.wm.obj_export, export_candidates)
    bpy.ops.wm.obj_export(**kwargs)
    print(f"[pipeline] Exported render mesh to {obj_path}")

    # Ensure environment.mtl points cleanly to environment.png
    # Replace any material lib texture path to standard relative environment.png
    mtl_content = (
        "# Second Rite Environment Material\n"
        "newmtl EnvironmentBakedAtlas\n"
        "Ka 1.000 1.000 1.000\n"
        "Kd 1.000 1.000 1.000\n"
        "map_Kd environment.png\n"
    )
    mtl_path.write_text(mtl_content, encoding="utf-8")

    # 6. Export TH_COLLISION if present
    collision_filename = None
    if col_collision and len(col_collision.objects) > 0:
        col_mesh_objects = [o for o in col_collision.objects if o.type == 'MESH']
        if col_mesh_objects:
            bpy.ops.object.select_all(action='DESELECT')
            for o in col_mesh_objects:
                o.select_set(True)
            scene.view_layers[0].objects.active = col_mesh_objects[0]
            col_obj_path = output_dir / "collision.obj"
            col_candidates = {
                "filepath": str(col_obj_path),
                "check_existing": False,
                "export_selected_objects": True,
                "export_uv": False,
                "export_normals": True,
                "export_materials": False,
                "export_triangulated_mesh": True,
                "apply_modifiers": True,
            }
            col_kwargs = _operator_kwargs(bpy.ops.wm.obj_export, col_candidates)
            bpy.ops.wm.obj_export(**col_kwargs)
            collision_filename = "collision.obj"
            print(f"[pipeline] Exported collision mesh to {col_obj_path}")

    # 7. Extract Anchors from TH_ANCHORS
    # Thestra coordinates: +X East, +Y South, +Z Up.
    # In Blender: X East, Y North, Z Up -> Thestra (x, -y, z) or (x, y, z) depending on scene convention.
    # Standard mapping matching obj_model:
    # Blender (x, y, z) -> Thestra world (x, y, z) directly when authoring in Z-up.
    anchors = {}
    for obj in col_anchors.objects:
        # Ignore preview actors or non-empty objects
        if obj.type not in {'EMPTY', 'LOCATOR'}:
            continue
        # Check parentage: preview actors must never leak
        pos = obj.matrix_world.translation
        rot = obj.matrix_world.to_euler()
        forward = obj.matrix_world.to_3x3() @ Vector((0, 1, 0))
        forward.normalize()

        anchors[obj.name] = {
            "id": obj.name,
            "position": [round(pos.x, 4), round(pos.y, 4), round(pos.z, 4)],
            "rotation": [round(math.degrees(rot.x), 2), round(math.degrees(rot.y), 2), round(math.degrees(rot.z), 2)],
            "forward": [round(forward.x, 4), round(forward.y, 4), round(forward.z, 4)],
        }

    # 8. Compute Mesh Statistics and Bounds
    target_mesh = target_obj.data
    tri_count = len(target_mesh.polygons)
    # If not all triangles, count tessellated
    target_mesh.calc_loop_triangles()
    tri_count = len(target_mesh.loop_triangles)
    vert_count = len(target_mesh.vertices)

    # Calculate world-space bounds
    bbox_corners = [target_obj.matrix_world @ Vector(corner) for corner in target_obj.bound_box]
    min_x = min(c.x for c in bbox_corners)
    min_y = min(c.y for c in bbox_corners)
    min_z = min(c.z for c in bbox_corners)
    max_x = max(c.x for c in bbox_corners)
    max_y = max(c.y for c in bbox_corners)
    max_z = max(c.z for c in bbox_corners)

    png_size = texture_path.stat().st_size if texture_path.exists() else 0
    obj_size = obj_path.stat().st_size if obj_path.exists() else 0
    mtl_size = mtl_path.stat().st_size if mtl_path.exists() else 0
    col_size = (output_dir / "collision.obj").stat().st_size if (output_dir / "collision.obj").exists() else 0

    package_size = png_size + obj_size + mtl_size + col_size

    manifest = {
        "contractVersion": 1,
        "environmentId": blend_path.stem,
        "renderMesh": "environment.obj",
        "materialLibrary": "environment.mtl",
        "textureAtlas": "environment.png",
        "collisionMesh": collision_filename,
        "bounds": [round(min_x, 4), round(min_y, 4), round(min_z, 4),
                   round(max_x, 4), round(max_y, 4), round(max_z, 4)],
        "stats": {
            "triangleCount": tri_count,
            "vertexCount": vert_count,
            "materialGroupCount": 1,
            "textureDimensions": [atlas_size, atlas_size],
            "atlasColorSpace": "sRGB",
            "pngSizeBytes": png_size,
            "renderMeshSizeBytes": obj_size,
            "packageSizeBytes": package_size,
        },
        "anchors": anchors,
        "provenance": {
            "generator": "town_environment_pipeline.py",
            "sourceBlend": str(blend_path.name),
            "renderProfile": applied_profile["profile"],
            "renderProfileSamples": applied_profile["samples"],
            "atlasAllocation": atlas_allocation,
            "allocationPolicy": allocation_report["policy"],
            "cameraEnvelopeExplicit": bool(camera_envelope),
            "bakeSeconds": round(bake_seconds, 4),
        },
        "allocation": allocation_report,
    }

    manifest_path = output_dir / "environment.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[pipeline] Manifest written to {manifest_path}")
    print(f"[pipeline] PACKAGE STATS: {tri_count} tris, {vert_count} verts, atlas: {atlas_size}x{atlas_size} ({png_size} bytes), package: {package_size} bytes")


def export_environment_package(
    blend_path: Path,
    output_dir: Path,
    atlas_size: int = 512,
    bake_samples: int | None = None,
    render_profile: str = "cycles-candidate",
    atlas_allocation: str = "area",
    camera_envelope=None,
    view_policy="bounded-camera",
    explicitly_unreachable=(),
    margin_px: int = 4,
):
    blender = blender_executable()
    blend_path = Path(blend_path).resolve()
    output_dir = Path(output_dir).resolve()

    # The host wrapper serializes the public dataclass API before crossing the
    # process boundary.  Blender still performs the authoritative decode.
    if camera_envelope is not None:
        import view_weighted_atlas
        camera_envelope = [
            sample.to_record()
            if isinstance(sample, view_weighted_atlas.ViewSample)
            else sample
            for sample in camera_envelope
        ]
    if hasattr(view_policy, "to_record"):
        view_policy = view_policy.to_record()

    if not blend_path.is_file():
        raise FileNotFoundError(f"Source blend file not found: {blend_path}")

    script_path = Path(__file__).resolve()
    temp_runner = tempfile.NamedTemporaryFile(prefix="run_env_pipe_", suffix=".py", delete=False, mode="w", encoding="utf-8")
    temp_runner.write(
        f"import sys\n"
        f"sys.path.insert(0, {repr(str(script_path.parent))})\n"
        f"from town_environment_pipeline import run_pipeline_in_blender\n"
        f"from pathlib import Path\n"
        f"run_pipeline_in_blender(Path({repr(str(blend_path))}), Path({repr(str(output_dir))}), "
        f"atlas_size={atlas_size}, bake_samples={bake_samples!r}, "
        f"render_profile={render_profile!r}, atlas_allocation={atlas_allocation!r}, "
        f"camera_envelope={camera_envelope!r}, view_policy={view_policy!r}, "
        f"explicitly_unreachable={list(explicitly_unreachable)!r}, margin_px={margin_px})\n"
    )
    temp_runner.close()

    try:
        cmd = [blender, "--background", "--factory-startup", str(blend_path), "--python", temp_runner.name]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(res.stdout)
            print(res.stderr, file=sys.stderr)
            raise SystemExit(f"Pipeline execution failed in Blender (code {res.returncode})")
        print(res.stdout)
    finally:
        if os.path.exists(temp_runner.name):
            os.unlink(temp_runner.name)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Bake and export Blender environment to runtime package.")
    parser.add_argument("blend", help="Input .blend source path")
    parser.add_argument("--output", "-o", default="exports/environments/town_slice", help="Output directory")
    parser.add_argument("--atlas-size", type=int, default=512, help="Atlas texture dimension")
    parser.add_argument("--samples", type=int, default=None, help="Optional Cycles bake sample override")
    parser.add_argument("--profile", default="cycles-candidate", help="Named shared render profile")
    parser.add_argument(
        "--atlas-allocation", choices=("area", "view-weighted"), default="area",
        help="UV density policy; view-weighted requires --camera-envelope",
    )
    parser.add_argument("--camera-envelope", type=Path, help="JSON authored camera envelope")
    parser.add_argument("--view-policy", default="bounded-camera", help="View policy preset")
    parser.add_argument(
        "--unreachable-face", action="append", type=int, default=[],
        help="Explicit TH_RENDER polygon index to retain at the floor",
    )
    parser.add_argument("--margin-px", type=int, default=4, help="UV island margin in atlas pixels")
    args = parser.parse_args()

    camera_envelope = None
    if args.camera_envelope:
        payload = json.loads(args.camera_envelope.read_text(encoding="utf-8"))
        camera_envelope = payload.get("samples", payload) if isinstance(payload, dict) else payload

    export_environment_package(
        Path(args.blend),
        Path(args.output),
        atlas_size=args.atlas_size,
        bake_samples=args.samples,
        render_profile=args.profile,
        atlas_allocation=args.atlas_allocation,
        camera_envelope=camera_envelope,
        view_policy=args.view_policy,
        explicitly_unreachable=args.unreachable_face,
        margin_px=args.margin_px,
    )


if __name__ == "__main__":
    if "bpy" in sys.modules:
        pass
    else:
        main()
