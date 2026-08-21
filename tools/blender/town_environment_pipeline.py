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


def run_pipeline_in_blender(blend_path: Path, output_dir: Path, atlas_size: int = 512,
                            bake_samples: int = 16, allocation: str = "area",
                            window_offsets=(-96, 0, 96), supersample: float = 1.0,
                            cull_invisible: bool = True):
    import bpy
    from mathutils import Vector, Matrix

    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    scene = bpy.context.scene

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

    # Screen-space allocation (optional). The camera is fixed and the pan
    # range is bounded, so every face's screen footprint is known ahead of the
    # bake. Uniform area-based packing was measured spending 69.5% of the
    # atlas on faces the camera can never see, with a ~100x spread in texel
    # density across the faces it can. See cleanroom/atlaspack.py.
    allocation_report = None
    if allocation == "screen":
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).resolve().parent))
        from cleanroom import atlaspack
        cam = scene.camera or bpy.data.objects.get("TH_CAMERA_PREVIEW")
        if cam is None:
            raise RuntimeError("screen-space allocation needs the calibrated camera")
        allocation_report = atlaspack.allocate(
            scene, cam, target_obj, offsets=tuple(window_offsets),
            atlas_size=atlas_size, supersample=supersample, cull=cull_invisible)
        print("[pipeline] screen-space allocation: %s" % json.dumps(allocation_report))

    # Give the target non-overlapping atlas UVs.
    # A selected-to-active bake writes into the ACTIVE object's UV layer. The
    # runtime mesh is built as plain boxes and may carry no UV layer at all, or
    # carry world-scale tiling UVs shared between objects -- in either case the
    # bake lands on top of itself and the atlas is unusable. Unwrapping here is
    # part of what "produce a bake target" means, so it belongs to the pipeline
    # rather than to each scene.
    if allocation != "screen":
        if not target_obj.data.uv_layers:
            target_obj.data.uv_layers.new(name="UVMap")
        bpy.ops.object.select_all(action='DESELECT')
        target_obj.select_set(True)
        scene.view_layers[0].objects.active = target_obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=0.012)
        bpy.ops.object.mode_set(mode='OBJECT')
        print("[pipeline] Atlas-unwrapped bake target %s" % target_obj.name)

    # Create baked atlas image
    image_name = "environment_atlas"
    if image_name in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[image_name])
    # float_buffer=True is load-bearing, not a quality nicety. The bake result
    # is scene-referred LINEAR radiance. On an 8-bit image the buffer already
    # holds bytes, so `save_render` has no transform left to apply and writes
    # linear values into a PNG that every consumer samples as sRGB -- the atlas
    # then renders about half as bright as its source. With a float buffer the
    # display transform is applied on export and the file means what its
    # consumers assume it means.
    bake_image = bpy.data.images.new(image_name, width=atlas_size, height=atlas_size,
                                     alpha=True, float_buffer=True)

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
    scene.render.engine = 'CYCLES'
    try:
        scene.cycles.device = 'CPU'
    except Exception:
        pass
    scene.cycles.samples = bake_samples
    scene.cycles.bake_type = 'COMBINED'
    scene.render.bake.use_selected_to_active = True
    scene.render.bake.cage_extrusion = 0.15
    # Rays are cast from the cage along the target normal; anything further
    # from the runtime surface than this is simply never seen by the bake.
    # 1.0 m silently drops detail that sits a little way off its proxy, so the
    # budget is stated generously and the proxies are kept close instead.
    scene.render.bake.max_ray_distance = 2.5
    scene.render.bake.margin = 4

    # Select all source objects as Selected, target_obj as Active
    bpy.ops.object.select_all(action='DESELECT')
    for obj in col_source.objects:
        if obj.type in {'MESH', 'CURVE', 'SURFACE'}:
            obj.select_set(True)
    target_obj.select_set(True)
    scene.view_layers[0].objects.active = target_obj

    print(f"[pipeline] Baking beauty atlas ({atlas_size}x{atlas_size}, {bake_samples} samples)...")
    bpy.ops.object.bake(type='COMBINED')

    # Save baked texture.
    #
    # The bake result is scene-referred LINEAR radiance, and every consumer of
    # this package -- LOVE, a browser, Blender's own default for a colour
    # texture -- samples a PNG as sRGB. Written through unchanged the atlas
    # renders roughly half as bright as its source and reads as "mechanically
    # valid but almost black".
    #
    # Neither `save()` nor `save_render()` reliably applies the transfer here
    # (both were measured writing linear bytes, on 8-bit and float buffers
    # alike), so the encode is done explicitly on the pixel data. Deterministic
    # and independent of Blender's colour-management path.
    texture_path = output_dir / "environment.png"
    bake_image.file_format = 'PNG'
    try:
        import numpy as _np
        px = _np.array(bake_image.pixels[:], dtype=_np.float32)
        px = px.reshape(-1, 4)
        rgb = _np.clip(px[:, :3], 0.0, 1.0)
        encoded = _np.where(rgb <= 0.0031308,
                            rgb * 12.92,
                            1.055 * _np.power(rgb, 1.0 / 2.4) - 0.055)
        px[:, :3] = encoded
        bake_image.pixels[:] = px.reshape(-1).tolist()
        # A float bake buffer otherwise writes a 16-bit PNG; at a 426x240
        # render target that is ~5x the bytes for no visible gain.
        scene.render.image_settings.file_format = 'PNG'
        scene.render.image_settings.color_mode = 'RGBA'
        scene.render.image_settings.color_depth = '8'
        bake_image.filepath_raw = str(texture_path)
        bake_image.save()
        print("[pipeline] Saved beauty texture atlas to %s (sRGB-encoded)" % texture_path)
    except Exception as exc:
        bake_image.filepath_raw = str(texture_path)
        bake_image.save()
        print("[pipeline] WARNING atlas saved WITHOUT sRGB encoding (%s)" % exc)

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
            "pngSizeBytes": png_size,
            "renderMeshSizeBytes": obj_size,
            "packageSizeBytes": package_size,
        },
        "anchors": anchors,
        "allocation": allocation_report or {"mode": "area"},
        "provenance": {
            "generator": "town_environment_pipeline.py",
            "sourceBlend": str(blend_path.name),
        }
    }

    manifest_path = output_dir / "environment.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[pipeline] Manifest written to {manifest_path}")
    print(f"[pipeline] PACKAGE STATS: {tri_count} tris, {vert_count} verts, atlas: {atlas_size}x{atlas_size} ({png_size} bytes), package: {package_size} bytes")


def export_environment_package(blend_path: Path, output_dir: Path, atlas_size: int = 512,
                               bake_samples: int = 16, allocation: str = "area",
                               window_offsets=(-96, 0, 96), supersample: float = 1.0,
                               cull_invisible: bool = True):
    blender = blender_executable()
    blend_path = Path(blend_path).resolve()
    output_dir = Path(output_dir).resolve()

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
f"atlas_size={atlas_size}, bake_samples={bake_samples}, allocation={repr(allocation)}, "
f"window_offsets={tuple(window_offsets)}, supersample={supersample}, cull_invisible={cull_invisible})\n"
        f"sys.exit(0)\n"
    )
    temp_runner.close()

    try:
        cmd = [blender, "--background", str(blend_path), "--python", temp_runner.name]
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
    parser.add_argument("--samples", type=int, default=16, help="Cycles bake samples")
    parser.add_argument("--allocation", choices=("area", "screen"), default="area",
                        help="atlas texel allocation: uniform by surface area, "
                             "or proportional to fixed-camera screen footprint")
    parser.add_argument("--window-offsets", default="-96,0,96",
                        help="projection-window offsets in px that the allocation must cover")
    parser.add_argument("--supersample", type=float, default=1.0,
                        help="texels per screen pixel for the screen allocation")
    parser.add_argument("--keep-invisible", action="store_true",
                        help="do not cull faces that are never visible")
    args = parser.parse_args()

    export_environment_package(
        Path(args.blend), Path(args.output), atlas_size=args.atlas_size,
        bake_samples=args.samples, allocation=args.allocation,
        window_offsets=tuple(int(v) for v in args.window_offsets.split(",")),
        supersample=args.supersample, cull_invisible=not args.keep_invisible)


if __name__ == "__main__":
    if "bpy" in sys.modules:
        pass
    else:
        main()
