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

The pipeline records candidate bake evidence and provenance; it does not become
the scene-contract preflight validator. An independent preflight can consume
``environment.json`` (especially ``provenance.bake.appearance`` and ``stats``)
at the candidate boundary before any owner-controlled promotion.
"""

from __future__ import annotations

import json
import hashlib
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIPELINE_VERSION = "town-environment-pipeline-v2"
WARNING_PATTERN = re.compile(r"\b(?:warning|warn|error|circular dependency|unsupported)\b", re.IGNORECASE)
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


def sha256_file(path: Path) -> str:
    """Return the SHA-256 of a file without loading it all into memory."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_record(path: Path, display_name: str | None = None):
    path = Path(path)
    if not path.is_file():
        return None
    return {
        "path": display_name or path.name,
        "sha256": sha256_file(path),
        "sizeBytes": path.stat().st_size,
    }


def _warning_evidence(result):
    evidence = []
    for stream_name, text in (("stdout", result.stdout or ""), ("stderr", result.stderr or "")):
        for line in text.splitlines():
            if WARNING_PATTERN.search(line):
                evidence.append({"stream": stream_name, "line": line.strip()})
    return evidence


def _display_dependency_path(path: Path, blend_path: Path):
    try:
        return path.resolve().relative_to(blend_path.parent.resolve()).as_posix()
    except ValueError:
        return path.name


def _finalize_manifest_provenance(manifest_path: Path, blend_path: Path, output_dir: Path,
                                  script_path: Path, blender: str, atlas_size: int,
                                  bake_samples: int, flat_bake: bool, result):
    """Add host-owned provenance after a successful isolated Blender run."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    provenance = manifest.setdefault("provenance", {})
    source = provenance.setdefault("source", {})
    source["blend"] = _file_record(blend_path, blend_path.name)
    provenance["pipelineVersion"] = PIPELINE_VERSION
    provenance["pipelineScript"] = _file_record(script_path, script_path.name)
    provenance["options"] = {
        "atlasSize": atlas_size,
        "bakeSamples": bake_samples,
        "flatBake": bool(flat_bake),
    }
    tool = provenance.setdefault("tool", {})
    tool["blenderExecutable"] = Path(blender).name
    tool.setdefault("blenderVersion", None)
    provenance["warningEvidence"] = _warning_evidence(result)
    bake_provenance = provenance.get("bake")
    if isinstance(bake_provenance, dict):
        bake_provenance["warningEvidence"] = provenance["warningEvidence"]

    outputs = []
    for name in ("environment.obj", "environment.mtl", "environment.png", "collision.obj"):
        record = _file_record(output_dir / name)
        if record:
            outputs.append(record)
    provenance["outputs"] = outputs
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def _material_base_color(material):
    """Read a constant Principled base colour when one is actually authored."""
    if not material or not getattr(material, "use_nodes", False):
        return None
    nodes = material.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if not bsdf or not bsdf.inputs.get("Base Color"):
        return None
    socket = bsdf.inputs["Base Color"]
    if socket.is_linked:
        return None
    value = socket.default_value
    return [round(float(value[index]), 4) for index in range(3)]


def _bake_appearance_metrics(image, source_objects):
    """Measure the bake result, keeping appearance evidence separate from mesh stats."""
    pixels = list(image.pixels)
    pixel_count = len(pixels) // 4
    non_black = 0
    channel_min = [1.0, 1.0, 1.0]
    channel_max = [0.0, 0.0, 0.0]
    channel_sum = [0.0, 0.0, 0.0]
    bins = set()
    for offset in range(0, len(pixels), 4):
        rgb = pixels[offset:offset + 3]
        if max(rgb) > 0.02:
            non_black += 1
        for index, value in enumerate(rgb):
            channel_min[index] = min(channel_min[index], float(value))
            channel_max[index] = max(channel_max[index], float(value))
            channel_sum[index] += float(value)
        if max(rgb) > 0.02:
            bins.add(tuple(max(0, min(7, int(value * 8))) for value in rgb))

    source_colors = []
    source_materials = set()
    for obj in source_objects:
        for material in getattr(getattr(obj, "data", None), "materials", []):
            if material:
                source_materials.add(material.name)
                color = _material_base_color(material)
                if color and color not in source_colors:
                    source_colors.append(color)

    palette_coverage = []
    for color in source_colors:
        dominant = max(range(3), key=lambda index: color[index])
        saturation = max(color) - min(color)
        if saturation < 0.2:
            continue
        matching_pixels = 0
        for offset in range(0, len(pixels), 4):
            rgb = pixels[offset:offset + 3]
            other_channels = [rgb[index] for index in range(3) if index != dominant]
            if rgb[dominant] - max(other_channels) > 0.04:
                matching_pixels += 1
        palette_coverage.append({
            "sourceColor": color,
            "dominantChannel": ["red", "green", "blue"][dominant],
            "matchedPixelCount": matching_pixels,
            "matched": matching_pixels > 0,
        })

    mean = [round(total / pixel_count, 6) if pixel_count else 0.0 for total in channel_sum]
    ranges = [round(channel_max[i] - channel_min[i], 6) for i in range(3)]
    distinct_source_colors = len(source_colors)
    transfer_proof = {
        "sourceMaterialCount": len(source_materials),
        "distinctSourceColorCount": distinct_source_colors,
        "sourceBaseColors": source_colors,
        "nonBlackFraction": round(non_black / pixel_count, 6) if pixel_count else 0.0,
        "uniqueColorBinCount": len(bins),
        "channelMean": mean,
        "channelRange": ranges,
        "paletteCoverage": palette_coverage,
        "passed": bool(
            non_black
            and (distinct_source_colors < 2 or len(bins) >= 2)
            and all(entry["matched"] for entry in palette_coverage)
        ),
    }
    if not transfer_proof["passed"]:
        raise RuntimeError(
            "Bake integrity failure: atlas is blank or did not preserve the "
            "source material colour asymmetry: " + json.dumps(transfer_proof)
        )
    return transfer_proof


def run_pipeline_in_blender(blend_path: Path, output_dir: Path, atlas_size: int = 512,
                            bake_samples: int = 16, flat_bake: bool = False):
    """Bake an authored .blend into a runtime environment package.

    ``flat_bake`` selects the exterior profile: one sample, no light bounces
    and no bake margin, for a street whose atlas already carries its lighting.
    It defaults off so the interior rooms keep the multi-sample, bounced,
    margin-4 bake their shipped atlases were made with -- the exterior pipeline
    on PR #998 hardcoded the flat values, which would silently have re-baked
    the Padaria and the smith at one sample.
    """
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

    render_mesh_objects = [obj for obj in col_render.all_objects if obj and obj.type == 'MESH']
    if not render_mesh_objects:
        raise RuntimeError("TH_RENDER contains no mesh objects")
    source_objects = [obj for obj in col_source.all_objects if obj]

    # 2. Exclude preview and non-render collections from bake
    for col in (col_preview_actors, col_preview_only, col_collision, col_anchors, col_camera):
        if col:
            col.hide_render = True
            for obj in col.all_objects:
                if obj:
                    obj.hide_render = True

    # Ensure source and render are visible in render for baking
    col_source.hide_render = False
    for obj in col_source.all_objects:
        if obj:
            obj.hide_render = False

    col_render.hide_render = False
    for obj in col_render.all_objects:
        if obj:
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

    # Create baked atlas image
    image_name = "environment_atlas"
    if image_name in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[image_name])
    bake_image = bpy.data.images.new(image_name, width=atlas_size, height=atlas_size, alpha=True)
    # Start the atlas OPAQUE black, not transparent black.
    #
    # The alpha channel was doing two unrelated jobs at once: material
    # transparency (a gap between leaves on an alpha-cut foliage card) and
    # "was this texel ever baked". A new image is transparent everywhere, so
    # any texel the bake did not reach came out alpha 0 and was
    # indistinguishable from a leaf gap. Honouring alpha then tore holes in the
    # facades; ignoring it turned every foliage card into an opaque rectangle.
    # There was no setting that was right for both.
    #
    # Filling with alpha 1 first means alpha 0 can only come from the bake
    # itself -- that is, from real material transparency. Unreached texels stay
    # opaque and stop pretending to be holes. Gutter is never sampled anyway:
    # the runtime samples nearest with no mipmaps.
    bake_image.generated_color = (0.0, 0.0, 0.0, 1.0)

    # Ensure target object has a material with active image node
    mat_name = "EnvironmentBakedAtlas"
    mat = bpy.data.materials.get(mat_name)
    if not mat:
        mat = bpy.data.materials.new(mat_name)
        mat.use_nodes = True
    else:
        mat.use_nodes = True

    # Setup shader nodes for bake receiving.
    # Keep img_node UNLINKED from BSDF during the bake to avoid Cycles circular
    # image dependency warnings (#1023). Link it only after bake completion.
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    target_image_was_linked = bool(
        bsdf and bsdf.inputs.get("Base Color") and bsdf.inputs["Base Color"].is_linked
    )
    if bsdf and bsdf.inputs.get("Base Color") and bsdf.inputs["Base Color"].links:
        for link in list(bsdf.inputs["Base Color"].links):
            links.remove(link)

    img_node = nodes.get("BakeTargetImg")
    if not img_node:
        img_node = nodes.new("ShaderNodeTexImage")
        img_node.name = "BakeTargetImg"
    img_node.image = bake_image
    nodes.active = img_node
    img_node.select = True

    target_obj.data.materials.clear()
    target_obj.data.materials.append(mat)

    # 4. Perform Selected-To-Active Beauty Bake (Combined: materials, lights, shadows, AO)
    scene.render.engine = 'CYCLES'
    try:
        scene.cycles.device = 'CPU'
    except Exception:
        pass
    if flat_bake:
        scene.cycles.samples = 1
        scene.cycles.max_bounces = 0
        scene.cycles.diffuse_bounces = 0
        scene.cycles.glossy_bounces = 0
        scene.cycles.transparent_max_bounces = 0
    else:
        scene.cycles.samples = bake_samples
    scene.cycles.bake_type = 'COMBINED'
    scene.render.bake.use_selected_to_active = True
    # Keep the opaque fill above; clearing would restore transparent black and
    # reintroduce the ambiguity this pass exists to remove.
    scene.render.bake.use_clear = False
    scene.render.bake.cage_extrusion = 0.15
    scene.render.bake.max_ray_distance = 1.0
    # One texel of dilation for the exterior, and only one.
    #
    # Zero was tried and is wrong, for a reason unrelated to filtering. The
    # runtime samples nearest, so there is no filtering bleed to defend
    # against -- but the baker RASTERISES a texel only when its centre falls
    # inside the triangle, while the geometry SAMPLES whatever texel its UV
    # coordinate lands on. At an island edge those two disagree, so a face can
    # sample a texel the bake never filled. With margin 0 that showed as seams
    # tracing every visible edge of the culled facades; margin 1 removed them
    # completely, for one texel per island boundary.
    scene.render.bake.margin = 1 if flat_bake else 4

    # Select all source objects as Selected, target_obj as Active.
    # target_obj must NOT be in the selected set during selected-to-active bake,
    # or Cycles attempts to bake target_obj onto itself, triggering self-occlusion
    # and circular dependency warnings (#1023).
    bpy.ops.object.select_all(action='DESELECT')
    for obj in col_source.all_objects:
        if obj and obj.type in {'MESH', 'CURVE', 'SURFACE'}:
            obj.select_set(True)
    target_obj.select_set(False)
    scene.view_layers[0].objects.active = target_obj
    target_selected_during_bake = target_obj.select_get()
    pre_bake_pixels = list(bake_image.pixels)
    pre_bake_non_black = sum(
        1 for offset in range(0, len(pre_bake_pixels), 4)
        if max(pre_bake_pixels[offset:offset + 3]) > 0.02
    )

    print(f"[pipeline] Baking beauty atlas ({atlas_size}x{atlas_size}, {bake_samples} samples)...")
    bpy.ops.object.bake(type='COMBINED')

    appearance = _bake_appearance_metrics(bake_image, source_objects)

    # Connect baked texture to BSDF Base Color for material export and display
    if bsdf:
        links.new(img_node.outputs["Color"], bsdf.inputs["Base Color"])

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
    if col_collision and len(col_collision.all_objects) > 0:
        col_mesh_objects = [o for o in col_collision.all_objects if o and o.type == 'MESH']
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
    for obj in col_anchors.all_objects:
        if not obj:
            continue
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

    known_dependencies = []
    for image in bpy.data.images:
        if image == bake_image or not image.filepath or image.packed_file:
            continue
        dependency = Path(bpy.path.abspath(image.filepath))
        record = _file_record(dependency, _display_dependency_path(dependency, blend_path))
        if record:
            record["name"] = image.name
            known_dependencies.append(record)

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
        "provenance": {
            "generator": "town_environment_pipeline.py",
            "pipelineVersion": PIPELINE_VERSION,
            "sourceBlend": str(blend_path.name),
            "source": {
                "blend": _file_record(blend_path, blend_path.name),
                "dependencies": known_dependencies,
            },
            "tool": {
                "blenderVersion": getattr(bpy.app, "version_string", None),
                "blenderExecutable": None,
                "pipelineScript": _file_record(Path(__file__).resolve(), Path(__file__).name),
            },
            "options": {
                "atlasSize": atlas_size,
                "bakeSamples": bake_samples,
                "flatBake": bool(flat_bake),
            },
            "bake": {
                "receiver": {
                    "targetObject": target_obj.name,
                    "targetSelectedDuringBake": target_selected_during_bake,
                    "targetImageLinkedDuringBake": target_image_was_linked,
                    "preBakeNonBlackFraction": round(
                        pre_bake_non_black / (len(pre_bake_pixels) // 4), 6
                    ) if pre_bake_pixels else 0.0,
                },
                "appearance": appearance,
                "warningEvidence": [],
            },
            "outputs": [
                record for record in (
                    _file_record(texture_path),
                    _file_record(obj_path),
                    _file_record(mtl_path),
                    _file_record(output_dir / "collision.obj"),
                ) if record
            ],
            "warningEvidence": [],
        }
    }

    manifest_path = output_dir / "environment.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[pipeline] Manifest written to {manifest_path}")
    print(f"[pipeline] PACKAGE STATS: {tri_count} tris, {vert_count} verts, atlas: {atlas_size}x{atlas_size} ({png_size} bytes), package: {package_size} bytes")


def export_environment_package(blend_path: Path, output_dir: Path, atlas_size: int = 512,
                               bake_samples: int = 16, flat_bake: bool = False):
    """Build a candidate package and promote it only after the bake succeeds.

    An existing output directory is deliberately not replaced. Callers that
    need a new candidate must choose a new path; promotion into shipping asset
    locations remains an explicit owner action outside this exporter.
    """
    blender = blender_executable()
    blend_path = Path(blend_path).resolve()
    output_dir = Path(output_dir).resolve()

    if not blend_path.is_file():
        raise FileNotFoundError(f"Source blend file not found: {blend_path}")
    if output_dir.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing environment package: {output_dir}; "
            "export to a new candidate directory"
        )
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    candidate_dir = Path(tempfile.mkdtemp(
        prefix=f".{output_dir.name}.candidate-", dir=str(output_dir.parent)
    ))

    script_path = Path(__file__).resolve()
    temp_runner = tempfile.NamedTemporaryFile(prefix="run_env_pipe_", suffix=".py", delete=False, mode="w", encoding="utf-8")
    temp_runner.write(
        f"import sys\n"
        f"sys.path.insert(0, {repr(str(script_path.parent))})\n"
        f"from town_environment_pipeline import run_pipeline_in_blender\n"
        f"from pathlib import Path\n"
        f"run_pipeline_in_blender(Path({repr(str(blend_path))}), Path({repr(str(candidate_dir))}), atlas_size={atlas_size}, bake_samples={bake_samples}, flat_bake={flat_bake})\n"
    )
    temp_runner.close()

    try:
        cmd = [blender, "--background", str(blend_path), "--python", temp_runner.name]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(res.stdout)
            print(res.stderr, file=sys.stderr)
            raise SystemExit(f"Pipeline execution failed in Blender (code {res.returncode})")
        manifest_path = candidate_dir / "environment.json"
        if not manifest_path.is_file():
            print(res.stdout)
            print(res.stderr, file=sys.stderr)
            raise RuntimeError("Pipeline completed without environment.json")
        _finalize_manifest_provenance(
            manifest_path, blend_path, candidate_dir, script_path, blender,
            atlas_size, bake_samples, flat_bake, res
        )
        candidate_dir.rename(output_dir)
        print(res.stdout)
        return res
    except BaseException:
        if candidate_dir.exists():
            shutil.rmtree(candidate_dir, ignore_errors=True)
        raise
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
    args = parser.parse_args()

    export_environment_package(Path(args.blend), Path(args.output), atlas_size=args.atlas_size, bake_samples=args.samples)


if __name__ == "__main__":
    if "bpy" in sys.modules:
        pass
    else:
        main()
