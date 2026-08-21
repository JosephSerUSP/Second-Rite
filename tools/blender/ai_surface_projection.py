"""Geometry-conditioned image projection helpers for Blender authoring.

This module deliberately contains NO image-generation provider code. Blender
owns camera/geometry/UV facts; any API/local model may consume the exported
control packet and return an image for projection.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, List, Optional, Sequence


CONTROL_CONTRACT = "thestra.ai-surface-control"
CONTROL_VERSION = 1
PROJECTED_UV = "TH_AI_PROJECT"
BAKE_UV = "TH_AI_BAKE"


def _require_blender():
    try:
        import bpy
        from bpy_extras.object_utils import world_to_camera_view
    except ImportError as exc:
        raise RuntimeError("ai_surface_projection.py must run inside Blender") from exc
    return bpy, world_to_camera_view


def _mesh_objects(objects: Iterable[Any]) -> List[Any]:
    result = [obj for obj in objects if getattr(obj, "type", None) == "MESH"]
    if not result:
        raise RuntimeError("no mesh objects supplied")
    return result


def _matrix_rows(matrix: Any) -> List[List[float]]:
    return [[float(matrix[row][col]) for col in range(4)] for row in range(4)]


def capture_control_packet(
    output_dir: Path,
    *,
    scene: Optional[Any] = None,
    camera: Optional[Any] = None,
    objects: Optional[Sequence[Any]] = None,
    render_profile: str = "cycles-draft",
) -> Path:
    """Render one provider-neutral control packet without a second render.

    The packet contains a normal beauty PNG plus a multilayer EXR carrying the
    exact same render's Combined, Depth/Z, Normal and Object Index passes.
    Selected/supplied mesh objects receive Object Index 1 for an easy mask.
    """

    bpy, _ = _require_blender()
    import second_gate_render

    scene = scene or bpy.context.scene
    camera = camera or scene.camera
    if camera is None:
        raise RuntimeError("control capture requires an active camera")

    meshes = _mesh_objects(objects or bpy.context.selected_objects)
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    resolved_profile = second_gate_render.apply(scene, render_profile)
    scene.camera = camera

    view_layer = bpy.context.view_layer
    old_passes = (
        bool(view_layer.use_pass_z),
        bool(view_layer.use_pass_normal),
        bool(view_layer.use_pass_object_index),
    )
    old_indices = {obj.name: int(obj.pass_index) for obj in meshes}
    old_format = scene.render.image_settings.file_format
    old_depth = getattr(scene.render.image_settings, "color_depth", None)

    try:
        view_layer.use_pass_z = True
        view_layer.use_pass_normal = True
        view_layer.use_pass_object_index = True
        for obj in meshes:
            obj.pass_index = 1

        # One actual render; save the retained Render Result twice in different
        # encodings rather than paying for a second Cycles pass.
        bpy.ops.render.render()
        result = bpy.data.images.get("Render Result")
        if result is None:
            raise RuntimeError("Blender produced no Render Result")

        beauty_path = output_dir / "control-beauty.png"
        scene.render.image_settings.file_format = "PNG"
        result.save_render(filepath=str(beauty_path), scene=scene)

        passes_path = output_dir / "control-passes.exr"
        scene.render.image_settings.file_format = "OPEN_EXR_MULTILAYER"
        if hasattr(scene.render.image_settings, "color_depth"):
            scene.render.image_settings.color_depth = "32"
        result.save_render(filepath=str(passes_path), scene=scene)
    finally:
        view_layer.use_pass_z, view_layer.use_pass_normal, view_layer.use_pass_object_index = old_passes
        for obj in meshes:
            obj.pass_index = old_indices[obj.name]
        scene.render.image_settings.file_format = old_format
        if old_depth is not None and hasattr(scene.render.image_settings, "color_depth"):
            scene.render.image_settings.color_depth = old_depth

    manifest = {
        "contract": CONTROL_CONTRACT,
        "version": CONTROL_VERSION,
        "renderProfile": resolved_profile,
        "beauty": "control-beauty.png",
        "passes": {
            "file": "control-passes.exr",
            "combined": "Combined",
            "depth": "Depth/Z",
            "normal": "Normal",
            "objectIndex": {"pass": "IndexOB", "selectedValue": 1},
        },
        "camera": {
            "name": camera.name,
            "matrixWorld": _matrix_rows(camera.matrix_world),
            "lensMm": float(camera.data.lens),
            "sensorWidthMm": float(camera.data.sensor_width),
            "clipStart": float(camera.data.clip_start),
            "clipEnd": float(camera.data.clip_end),
        },
        "objects": [obj.name for obj in meshes],
        "providerBoundary": {
            "input": "this packet",
            "output": "one generated/projectable image matching the control camera",
            "apiOwnedByBlenderTool": False,
        },
    }
    manifest_path = output_dir / "control.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def project_image_to_objects(
    image_path: Path,
    *,
    scene: Optional[Any] = None,
    camera: Optional[Any] = None,
    objects: Optional[Sequence[Any]] = None,
    uv_name: str = PROJECTED_UV,
    material_name: str = "TH_AI_PROJECTED",
) -> Any:
    """Project a returned image through ``camera`` onto real mesh UV loops."""

    bpy, world_to_camera_view = _require_blender()
    scene = scene or bpy.context.scene
    camera = camera or scene.camera
    if camera is None:
        raise RuntimeError("projection requires an active camera")
    meshes = _mesh_objects(objects or bpy.context.selected_objects)

    image_path = Path(image_path).resolve()
    if not image_path.is_file():
        raise FileNotFoundError(image_path)
    image = bpy.data.images.load(str(image_path), check_existing=True)

    material = bpy.data.materials.get(material_name) or bpy.data.materials.new(material_name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    uv_node = nodes.new("ShaderNodeUVMap")
    uv_node.uv_map = uv_name
    texture = nodes.new("ShaderNodeTexImage")
    texture.image = image
    texture.interpolation = "Linear"
    texture.extension = "CLIP"
    links.new(uv_node.outputs["UV"], texture.inputs["Vector"])
    links.new(texture.outputs["Color"], shader.inputs["Base Color"])
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])

    for obj in meshes:
        mesh = obj.data
        uv_layer = mesh.uv_layers.get(uv_name) or mesh.uv_layers.new(name=uv_name)
        for poly in mesh.polygons:
            for loop_index in poly.loop_indices:
                vertex_index = mesh.loops[loop_index].vertex_index
                world = obj.matrix_world @ mesh.vertices[vertex_index].co
                ndc = world_to_camera_view(scene, camera, world)
                uv_layer.data[loop_index].uv = (float(ndc.x), float(ndc.y))

        slot_index = len(obj.data.materials)
        obj.data.materials.append(material)
        for poly in mesh.polygons:
            poly.material_index = slot_index
        obj["thestra_ai_projection_uv"] = uv_name
        obj["thestra_ai_projection_image"] = str(image_path)
        obj["thestra_ai_projection_camera"] = camera.name

    return material


def _smart_unwrap(obj: Any, uv_name: str) -> Any:
    bpy, _ = _require_blender()
    mesh = obj.data
    uv = mesh.uv_layers.get(uv_name) or mesh.uv_layers.new(name=uv_name)
    mesh.uv_layers.active = uv
    uv.active_render = True

    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    try:
        bpy.ops.uv.smart_project(island_margin=0.03)
    finally:
        bpy.ops.object.mode_set(mode="OBJECT")
    return uv


def bake_projection_to_uv(
    obj: Any,
    output_path: Path,
    *,
    atlas_size: int = 1024,
    source_uv: str = PROJECTED_UV,
    target_uv: str = BAKE_UV,
    samples: int = 4,
) -> Path:
    """Bake one camera-projected material into ordinary object UV space.

    The first spike intentionally handles one mesh at a time. Multi-view and
    multi-object atlas resolution belong to later iterations once this boundary
    is proven.
    """

    bpy, _ = _require_blender()
    if getattr(obj, "type", None) != "MESH":
        raise TypeError("bake target must be one mesh object")
    if obj.data.uv_layers.get(source_uv) is None:
        raise RuntimeError(f"object has no projected UV layer {source_uv!r}")
    if not obj.data.materials:
        raise RuntimeError("object has no projected material")
    if atlas_size <= 0:
        raise ValueError("atlas_size must be positive")

    target_layer = _smart_unwrap(obj, target_uv)
    target_layer.active_render = True

    material = obj.data.materials[obj.active_material_index]
    if material is None or not material.use_nodes:
        raise RuntimeError("active projected material is not node-based")
    nodes = material.node_tree.nodes

    target_image = bpy.data.images.new(
        "TH_AI_BAKED_ATLAS", width=atlas_size, height=atlas_size, alpha=True
    )
    target_node = nodes.new("ShaderNodeTexImage")
    target_node.name = "TH_AI_BAKE_TARGET"
    target_node.image = target_image
    nodes.active = target_node
    target_node.select = True

    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = int(samples)
    scene.render.bake.use_pass_direct = False
    scene.render.bake.use_pass_indirect = False
    scene.render.bake.use_pass_color = True
    scene.render.bake.margin = 8

    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.bake(type="DIFFUSE")

    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    target_image.filepath_raw = str(output_path)
    target_image.file_format = "PNG"
    target_image.save()
    obj["thestra_ai_baked_atlas"] = str(output_path)
    obj["thestra_ai_bake_uv"] = target_uv
    return output_path
