"""Geometry-conditioned facade projection proof for Blender authoring.

This module deliberately stops at the Blender authoring boundary.  It accepts
an already-produced image and optional height image; it never calls an image
provider, stores credentials, or promotes the result into runtime assets.

The Blender-facing functions are imported lazily so the protocol and
self-checks remain runnable with standard Python.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple


PROTOCOL_VERSION = 1
CONTROL_PACKET_VERSION = 1
DEFAULT_NATIVE_WIDTH = 426
DEFAULT_NATIVE_HEIGHT = 240
DEFAULT_PROJECTED_UV = "TH_FACADE_PROJECTED"
DEFAULT_TARGET_UV = "UVMap"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_relative_name(path: Path) -> str:
    """Return a manifest-safe basename rather than a machine-specific path."""

    return path.name


def _validate_provider_text(value: str, field_name: str) -> str:
    value = str(value or "")
    if "\x00" in value or "\n" in value or "\r" in value:
        raise ValueError(f"{field_name} contains a forbidden control character")
    if len(value) > 4096:
        raise ValueError(f"{field_name} is unexpectedly long")
    return value


@dataclass(frozen=True)
class GeneratedFacadeInput:
    """A provider result supplied from outside Blender.

    ``provider`` is provenance only.  The projection core treats every input
    as an ordinary local image and has no provider-specific branch.
    """

    image: Path
    provider: str = "external"
    model: str = "unrecorded"
    prompt: str = ""
    negative_prompt: str = ""
    seed: Optional[int] = None
    height_image: Optional[Path] = None
    source_reference: str = ""

    def validate(self) -> None:
        if not self.image.is_file():
            raise FileNotFoundError(f"facade image not found: {self.image}")
        if self.height_image is not None and not self.height_image.is_file():
            raise FileNotFoundError(f"height image not found: {self.height_image}")
        _validate_provider_text(self.provider, "provider")
        _validate_provider_text(self.model, "model")
        _validate_provider_text(self.prompt, "prompt")
        _validate_provider_text(self.negative_prompt, "negative_prompt")
        _validate_provider_text(self.source_reference, "source_reference")
        if self.seed is not None and not isinstance(self.seed, int):
            raise TypeError("seed must be an integer or None")

    def to_record(self) -> Dict[str, Any]:
        self.validate()
        return {
            "image": _safe_relative_name(self.image),
            "imageSha256": _sha256(self.image),
            "provider": _validate_provider_text(self.provider, "provider"),
            "model": _validate_provider_text(self.model, "model"),
            "prompt": _validate_provider_text(self.prompt, "prompt"),
            "negativePrompt": _validate_provider_text(
                self.negative_prompt, "negative_prompt"
            ),
            "seed": self.seed,
            "heightImage": (
                _safe_relative_name(self.height_image)
                if self.height_image is not None
                else None
            ),
            "heightImageSha256": (
                _sha256(self.height_image) if self.height_image is not None else None
            ),
            "sourceReference": _validate_provider_text(
                self.source_reference, "source_reference"
            ),
        }


@dataclass(frozen=True)
class ProjectionSpec:
    """The explicit, camera-calibrated projection request.

    Face indices are optional per object.  Omitting them means all faces in
    that named object, while still requiring the caller to name the target
    object and its authoritative collection.
    """

    target_objects: Tuple[str, ...]
    face_indices: Mapping[str, Optional[Tuple[int, ...]]] = field(default_factory=dict)
    projected_uv_map: str = DEFAULT_PROJECTED_UV
    target_uv_map: str = DEFAULT_TARGET_UV
    height_scale: float = 0.08
    allow_outside_camera: bool = False
    bake_width: Optional[int] = None
    bake_height: Optional[int] = None

    def validate(self) -> None:
        if not self.target_objects:
            raise ValueError("at least one explicit TH_SOURCE target object is required")
        if len(set(self.target_objects)) != len(self.target_objects):
            raise ValueError("target object names must be unique")
        unknown_face_targets = set(self.face_indices).difference(self.target_objects)
        if unknown_face_targets:
            raise ValueError(
                "face selections name non-target objects: "
                + ", ".join(sorted(unknown_face_targets))
            )
        for name in self.target_objects:
            if not name or "\x00" in name:
                raise ValueError("target object names must be non-empty and safe")
            indices = self.face_indices.get(name)
            if indices is not None:
                if any(not isinstance(index, int) or index < 0 for index in indices):
                    raise ValueError(f"invalid face index selection for {name!r}")
        if not self.projected_uv_map or not self.target_uv_map:
            raise ValueError("both projected and ordinary target UV map names are required")
        if not math.isfinite(float(self.height_scale)) or self.height_scale < 0:
            raise ValueError("height_scale must be finite and non-negative")
        if (self.bake_width is None) != (self.bake_height is None):
            raise ValueError("bake_width and bake_height must be supplied together")
        if self.bake_width is not None and (
            int(self.bake_width) <= 0 or int(self.bake_height) <= 0
        ):
            raise ValueError("bake dimensions must be positive")

    def faces_for(self, object_name: str, polygon_count: int) -> Tuple[int, ...]:
        self.validate()
        if object_name not in self.target_objects:
            raise KeyError(object_name)
        indices = self.face_indices.get(object_name)
        if indices is None:
            return tuple(range(polygon_count))
        if any(index >= polygon_count for index in indices):
            raise ValueError(f"face selection exceeds polygon count for {object_name!r}")
        return tuple(indices)

    def to_record(self) -> Dict[str, Any]:
        self.validate()
        return {
            "targetObjects": list(self.target_objects),
            "faceIndices": {
                name: (list(indices) if indices is not None else None)
                for name, indices in self.face_indices.items()
            },
            "projectedUvMap": self.projected_uv_map,
            "targetUvMap": self.target_uv_map,
            "heightScale": float(self.height_scale),
            "allowOutsideCamera": bool(self.allow_outside_camera),
            "bakeSize": (
                [int(self.bake_width), int(self.bake_height)]
                if self.bake_width is not None
                else None
            ),
        }


def validate_source_only_collection(collection_names: Iterable[str]) -> None:
    """Fail if a displacement target can affect runtime/render proxy layers."""

    names = set(collection_names)
    if "TH_SOURCE" not in names:
        raise RuntimeError("facade projection targets must belong to TH_SOURCE")
    forbidden = names.intersection(
        {"TH_RENDER", "TH_COLLISION", "TH_ANCHORS", "TH_PREVIEW_ACTORS"}
    )
    if forbidden:
        raise RuntimeError(
            "facade projection may not displace runtime/proxy collections: "
            + ", ".join(sorted(forbidden))
        )


def validate_control_packet(packet: Mapping[str, Any]) -> None:
    if packet.get("protocolVersion") != PROTOCOL_VERSION:
        raise ValueError("unsupported facade projection protocol version")
    if packet.get("controlPacketVersion") != CONTROL_PACKET_VERSION:
        raise ValueError("unsupported control packet version")
    camera = packet.get("camera")
    if not isinstance(camera, Mapping) or not camera.get("name"):
        raise ValueError("control packet has no calibrated camera record")
    images = packet.get("images")
    if not isinstance(images, Mapping) or not images.get("beauty"):
        raise ValueError("control packet must contain a beauty/clay image")


def write_control_packet(path: Path, packet: Mapping[str, Any]) -> None:
    validate_control_packet(packet)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_control_packet(path: Path) -> Dict[str, Any]:
    packet = json.loads(path.read_text(encoding="utf-8"))
    validate_control_packet(packet)
    return packet


def _camera_record(scene: Any, camera: Any) -> Dict[str, Any]:
    data = camera.data
    return {
        "name": camera.name,
        "type": data.type,
        "lens": float(getattr(data, "lens", 0.0)),
        "sensorWidth": float(getattr(data, "sensor_width", 0.0)),
        "sensorHeight": float(getattr(data, "sensor_height", 0.0)),
        "orthoScale": float(getattr(data, "ortho_scale", 0.0)),
        "shift": [float(data.shift_x), float(data.shift_y)],
        "clip": [float(data.clip_start), float(data.clip_end)],
        "worldMatrix": [
            [round(float(value), 10) for value in row] for row in camera.matrix_world
        ],
        "resolution": [int(scene.render.resolution_x), int(scene.render.resolution_y)],
    }


def _camera_calibration(record: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        key: record.get(key)
        for key in (
            "name",
            "type",
            "lens",
            "sensorWidth",
            "sensorHeight",
            "orthoScale",
            "shift",
            "clip",
            "worldMatrix",
        )
    }


def _collection_objects(collection: Any) -> Sequence[Any]:
    return sorted(collection.objects, key=lambda obj: obj.name)


def _hide_non_source_for_preview(scene: Any) -> Dict[Any, bool]:
    hidden: Dict[Any, bool] = {}
    for name in (
        "TH_RENDER",
        "TH_COLLISION",
        "TH_ANCHORS",
        "TH_PREVIEW_ACTORS",
        "TH_PREVIEW_ONLY",
        "TH_CAMERA_PREVIEW",
    ):
        collection = getattr(sys.modules.get("bpy"), "data", None)
        collection = collection.collections.get(name) if collection else None
        if collection is None:
            continue
        hidden[collection] = bool(collection.hide_render)
        collection.hide_render = True
    source = getattr(sys.modules.get("bpy"), "data", None)
    source = source.collections.get("TH_SOURCE") if source else None
    if source is not None:
        hidden[source] = bool(source.hide_render)
        source.hide_render = False
    return hidden


def _restore_collection_visibility(hidden: Mapping[Any, bool]) -> None:
    for collection, value in hidden.items():
        collection.hide_render = value


def _render_preview(scene: Any, output_path: Path, profile: str = "clay") -> None:
    import second_gate_render

    second_gate_render.apply(scene, profile)
    scene.render.filepath = str(output_path)
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    import bpy

    bpy.ops.render.render(write_still=True)


def _find_compositor_output(output_dir: Path, prefix: str, suffix: str) -> Path:
    candidates = sorted(output_dir.glob(f"{prefix}*{suffix}"))
    if len(candidates) != 1:
        raise RuntimeError(
            f"expected one compositor output for {prefix!r}, found "
            f"{[candidate.name for candidate in candidates]}"
        )
    desired = output_dir / f"{prefix.rstrip('_')}{suffix}"
    if candidates[0] != desired:
        candidates[0].replace(desired)
    return desired


def export_control_packet(
    scene: Any,
    camera: Any,
    output_dir: Path,
    *,
    profile: str = "clay",
    native_width: int = DEFAULT_NATIVE_WIDTH,
    native_height: int = DEFAULT_NATIVE_HEIGHT,
) -> Dict[str, Any]:
    """Render beauty/clay, depth, normals and object-index control products."""

    import bpy

    if camera is None or camera.type != "CAMERA":
        raise RuntimeError("an active calibrated camera is required")
    output_dir.mkdir(parents=True, exist_ok=True)
    scene.camera = camera
    hidden = _hide_non_source_for_preview(scene)
    try:
        import second_gate_render

        applied = second_gate_render.apply(scene, profile)
        scene.render.resolution_x = int(native_width * (applied["width"] / native_width))
        scene.render.resolution_y = int(native_height * (applied["height"] / native_height))
        scene.render.resolution_percentage = 100

        view_layer = scene.view_layers[0]
        for attribute in ("use_pass_z", "use_pass_normal", "use_pass_object_index"):
            if hasattr(view_layer, attribute):
                setattr(view_layer, attribute, True)

        source = bpy.data.collections.get("TH_SOURCE")
        mask_objects: Dict[str, int] = {}
        if source is not None:
            for pass_index, obj in enumerate(_collection_objects(source), start=1):
                if hasattr(obj, "pass_index"):
                    obj.pass_index = pass_index
                    mask_objects[obj.name] = pass_index

        scene.render.filepath = str(output_dir / "beauty.png")
        scene.render.image_settings.file_format = "PNG"
        scene.render.image_settings.color_mode = "RGBA"

        scene.use_nodes = True
        # Blender 5.1 stores compositor nodes in a scene-owned node group;
        # older Blender builds expose the same tree as scene.node_tree.
        if hasattr(scene, "compositing_node_group"):
            tree = scene.compositing_node_group
            if tree is None:
                tree = bpy.data.node_groups.new(
                    "TH_Facade_Control_Compositor", "CompositorNodeTree"
                )
                scene.compositing_node_group = tree
        else:
            tree = scene.node_tree
        tree.nodes.clear()
        layers = tree.nodes.new("CompositorNodeRLayers")

        def add_output(
            name: str, socket_name: str, file_format: str, socket_type: str
        ) -> None:
            node = tree.nodes.new("CompositorNodeOutputFile")
            node.name = f"TH_CONTROL_{name}"
            if hasattr(node, "file_output_items"):
                node.file_output_items.new(socket_type, name)
                node.directory = str(output_dir)
                node.file_name = f"{name}_"
                input_socket = node.inputs[name]
            else:
                node.base_path = str(output_dir)
                node.file_slots[0].path = f"{name}_"
                input_socket = node.inputs[0]
            try:
                node.format.file_format = file_format
            except (TypeError, ValueError):
                # Blender 5.1's compositor exposes the multilayer EXR enum
                # here even for a single pass output.
                node.format.file_format = "OPEN_EXR_MULTILAYER"
            if file_format == "OPEN_EXR":
                node.format.color_depth = "32"
            tree.links.new(layers.outputs[socket_name], input_socket)

        add_output("depth", "Depth", "OPEN_EXR", "FLOAT")
        add_output("normal", "Normal", "OPEN_EXR", "RGBA")
        mask_available = "IndexOB" in layers.outputs
        if mask_available:
            add_output("mask", "IndexOB", "OPEN_EXR", "FLOAT")
        bpy.ops.render.render(write_still=True)

        depth = _find_compositor_output(output_dir, "depth_", ".exr")
        normal = _find_compositor_output(output_dir, "normal_", ".exr")
        mask = (
            _find_compositor_output(output_dir, "mask_", ".exr")
            if mask_available
            else None
        )
        packet = {
            "protocolVersion": PROTOCOL_VERSION,
            "controlPacketVersion": CONTROL_PACKET_VERSION,
            "camera": _camera_record(scene, camera),
            "profile": applied,
            "images": {
                "beauty": "beauty.png",
                "depth": depth.name,
                "normal": normal.name,
                "objectMask": mask.name if mask is not None else None,
            },
            "maskObjects": mask_objects,
            "maskStatus": "object-index" if mask_available else "unavailable-in-compositor",
            "authority": "authoring-control-only",
        }
        write_control_packet(output_dir / "control.json", packet)
        return packet
    finally:
        _restore_collection_visibility(hidden)


def _object_collection_names(obj: Any) -> Tuple[str, ...]:
    return tuple(sorted(collection.name for collection in obj.users_collection))


def _require_source_target(obj: Any) -> None:
    validate_source_only_collection(_object_collection_names(obj))
    if obj.type != "MESH":
        raise RuntimeError(f"facade target {obj.name!r} is not a mesh")


def _project_object_uvs(scene: Any, camera: Any, obj: Any, spec: ProjectionSpec) -> Tuple[int, ...]:
    from bpy_extras.object_utils import world_to_camera_view

    _require_source_target(obj)
    mesh = obj.data
    target_faces = spec.faces_for(obj.name, len(mesh.polygons))
    if not target_faces:
        raise ValueError(f"facade target {obj.name!r} selected no faces")
    if mesh.uv_layers.get(spec.target_uv_map) is None:
        raise RuntimeError(
            f"facade target {obj.name!r} has no ordinary UV map {spec.target_uv_map!r}; "
            "unwrap it in Blender before projection"
        )
    projected = mesh.uv_layers.get(spec.projected_uv_map)
    if projected is None:
        projected = mesh.uv_layers.new(name=spec.projected_uv_map)

    selected = set(target_faces)
    for polygon in mesh.polygons:
        polygon.select = polygon.index in selected
        if not polygon.select:
            continue
        for loop_index in polygon.loop_indices:
            vertex = mesh.vertices[mesh.loops[loop_index].vertex_index]
            view = world_to_camera_view(scene, camera, obj.matrix_world @ vertex.co)
            x, y, depth = float(view.x), float(view.y), float(view.z)
            if depth <= 0.0:
                raise RuntimeError(
                    f"facade target {obj.name!r} has a face behind the calibrated camera"
                )
            if not spec.allow_outside_camera and not (
                -1e-6 <= x <= 1.000001 and -1e-6 <= y <= 1.000001
            ):
                raise RuntimeError(
                    f"facade target {obj.name!r} projects outside the control frame at "
                    f"UV ({x:.4f}, {y:.4f}); calibrate the camera or opt into outside projection"
                )
            projected.data[loop_index].uv = (x, y)
    return tuple(sorted(selected))


def _new_projection_material(
    name: str,
    source_image: Any,
    projected_uv_map: str,
    *,
    target_image: Any = None,
    target_uv_map: str = DEFAULT_TARGET_UV,
) -> Tuple[Any, Any]:
    import bpy

    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    def connect_uv(texture_node: Any, uv_map: str) -> None:
        if hasattr(texture_node, "uv_map"):
            texture_node.uv_map = uv_map
            return
        uv_node = nodes.new("ShaderNodeUVMap")
        uv_node.name = f"TH_UV_{uv_map}"
        uv_node.uv_map = uv_map
        links.new(uv_node.outputs["UV"], texture_node.inputs["Vector"])

    source = nodes.new("ShaderNodeTexImage")
    source.name = "TH_Facade_Source"
    source.image = source_image
    connect_uv(source, projected_uv_map)
    source.interpolation = "Linear"
    if target_image is not None:
        target = nodes.new("ShaderNodeTexImage")
        target.name = "TH_Facade_Bake_Target"
        target.image = target_image
        connect_uv(target, target_uv_map)
        target.select = True
        nodes.active = target
    else:
        target = None
    emission = nodes.new("ShaderNodeEmission")
    output = nodes.new("ShaderNodeOutputMaterial")
    links.new(source.outputs["Color"], emission.inputs["Color"])
    if "Alpha" in source.outputs and "Strength" in emission.inputs:
        emission.inputs["Strength"].default_value = 1.0
    links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return material, target


def _assign_material_to_faces(obj: Any, material: Any, face_indices: Iterable[int]) -> None:
    mesh = obj.data
    slot = next(
        (index for index, existing in enumerate(obj.data.materials) if existing == material),
        None,
    )
    if slot is None:
        obj.data.materials.append(material)
        slot = len(obj.data.materials) - 1
    for index in face_indices:
        mesh.polygons[index].material_index = slot


def _apply_source_height(
    obj: Any,
    height_image: Any,
    spec: ProjectionSpec,
    face_indices: Iterable[int],
) -> Dict[str, Any]:
    import bpy

    _require_source_target(obj)
    texture_name = f"TH_Facade_Height_{obj.name}"
    texture = bpy.data.textures.get(texture_name) or bpy.data.textures.new(
        texture_name, type="IMAGE"
    )
    texture.image = height_image
    modifier = obj.modifiers.get(texture_name) or obj.modifiers.new(texture_name, "DISPLACE")
    modifier.texture = texture
    modifier.texture_coords = "UV"
    modifier.uv_layer = spec.target_uv_map
    modifier.strength = float(spec.height_scale)
    modifier.mid_level = 0.5
    vertex_group_name = f"{texture_name}_Faces"
    vertex_group = obj.vertex_groups.get(vertex_group_name) or obj.vertex_groups.new(
        name=vertex_group_name
    )
    vertices = {
        vertex_index
        for face_index in face_indices
        for vertex_index in obj.data.polygons[face_index].vertices
    }
    vertex_group.add(sorted(vertices), 1.0, "REPLACE")
    modifier.vertex_group = vertex_group.name
    obj["th_facade_displacement_scope"] = "TH_SOURCE"
    obj["th_facade_height_image"] = height_image.name
    return {
        "object": obj.name,
        "modifier": modifier.name,
        "uvMap": spec.target_uv_map,
        "vertexGroup": vertex_group.name,
        "strength": float(spec.height_scale),
        "scope": "TH_SOURCE",
    }


def _new_baked_render_material(name: str, image: Any, target_uv_map: str) -> Any:
    import bpy

    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    texture = nodes.new("ShaderNodeTexImage")
    texture.image = image
    if hasattr(texture, "uv_map"):
        texture.uv_map = target_uv_map
    else:
        uv_node = nodes.new("ShaderNodeUVMap")
        uv_node.name = f"TH_UV_{target_uv_map}"
        uv_node.uv_map = target_uv_map
        links.new(uv_node.outputs["UV"], texture.inputs["Vector"])
    texture.interpolation = "Linear"
    emission = nodes.new("ShaderNodeEmission")
    output = nodes.new("ShaderNodeOutputMaterial")
    links.new(texture.outputs["Color"], emission.inputs["Color"])
    links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return material


def project_generated_facade(
    scene: Any,
    camera: Any,
    generated: GeneratedFacadeInput,
    spec: ProjectionSpec,
    output_dir: Path,
    *,
    control_packet: Optional[Mapping[str, Any]] = None,
    source_blend_name: str = "inspection-input.blend",
) -> Dict[str, Any]:
    """Project an external image, bake it to ordinary UVs, and render the A/B."""

    import bpy

    generated.validate()
    spec.validate()
    if control_packet is not None:
        validate_control_packet(control_packet)
        expected_camera = control_packet["camera"]["name"]
        if camera.name != expected_camera:
            raise RuntimeError(
                f"projection camera {camera.name!r} does not match control camera {expected_camera!r}"
            )
        current_camera = _camera_record(scene, camera)
        if _camera_calibration(current_camera) != _camera_calibration(
            control_packet["camera"]
        ):
            raise RuntimeError(
                "projection camera calibration differs from the control packet; "
                "re-export controls after changing the camera"
            )
    output_dir.mkdir(parents=True, exist_ok=True)
    scene.camera = camera
    hidden = _hide_non_source_for_preview(scene)
    try:
        _render_preview(scene, output_dir / "source_blockout.png", "clay")
        source_image = bpy.data.images.load(str(generated.image), check_existing=True)
        if source_image.size[0] <= 0 or source_image.size[1] <= 0:
            raise RuntimeError("generated facade image has no pixels")

        targets = []
        for object_name in spec.target_objects:
            obj = bpy.data.objects.get(object_name)
            if obj is None:
                raise KeyError(f"facade target object not found: {object_name!r}")
            faces = _project_object_uvs(scene, camera, obj, spec)
            projected_material, _ = _new_projection_material(
                f"TH_Facade_Projected_{object_name}",
                source_image,
                spec.projected_uv_map,
            )
            _assign_material_to_faces(obj, projected_material, faces)
            targets.append((obj, faces, projected_material))

        _render_preview(scene, output_dir / "generated_projection.png", "clay")

        baked_records = []
        for obj, faces, projected_material in targets:
            width = int(spec.bake_width or source_image.size[0])
            height = int(spec.bake_height or source_image.size[1])
            baked = bpy.data.images.new(
                f"TH_Facade_Baked_{obj.name}", width=width, height=height, alpha=True
            )
            baked.file_format = "PNG"
            baked_material, target_node = _new_projection_material(
                f"TH_Facade_Bake_{obj.name}",
                source_image,
                spec.projected_uv_map,
                target_image=baked,
                target_uv_map=spec.target_uv_map,
            )
            _assign_material_to_faces(obj, baked_material, faces)
            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            mesh = obj.data
            target_layer = mesh.uv_layers.get(spec.target_uv_map)
            mesh.uv_layers.active = target_layer
            mesh.uv_layers.active_index = list(mesh.uv_layers).index(target_layer)
            if target_node is None:
                raise RuntimeError("bake target image node was not created")
            for node in baked_material.node_tree.nodes:
                node.select = node == target_node
            baked_material.node_tree.nodes.active = target_node
            saved_materials = list(obj.data.materials)
            saved_material_indices = [
                polygon.material_index for polygon in obj.data.polygons
            ]
            # Blender validates every material slot during a bake. Temporarily
            # making the active target material the only slot keeps unrelated
            # source materials from producing a false "no active image node"
            # warning; unselected faces are restored immediately afterward.
            obj.data.materials.clear()
            obj.data.materials.append(baked_material)
            for polygon in obj.data.polygons:
                polygon.material_index = 0
            import second_gate_render

            second_gate_render.apply(scene, "cycles-draft")
            scene.render.bake.margin = 4
            bpy.ops.object.bake(type="EMIT", use_clear=True)
            obj.data.materials.clear()
            for material in saved_materials:
                obj.data.materials.append(material)
            for polygon, material_index in zip(obj.data.polygons, saved_material_indices):
                polygon.material_index = material_index
            baked_path = output_dir / f"{obj.name}_facade_baked.png"
            baked.filepath_raw = str(baked_path)
            baked.save()
            baked_render_material = _new_baked_render_material(
                f"TH_Facade_Baked_Render_{obj.name}", baked, spec.target_uv_map
            )
            _assign_material_to_faces(obj, baked_render_material, faces)
            baked_records.append(
                {
                    "object": obj.name,
                    "faces": list(faces),
                    "image": baked_path.name,
                    "size": [width, height],
                }
            )

        height_records = []
        if generated.height_image is not None:
            height_image = bpy.data.images.load(
                str(generated.height_image), check_existing=True
            )
            for obj, faces, _material in targets:
                height_records.append(
                    _apply_source_height(obj, height_image, spec, faces)
                )

        _render_preview(scene, output_dir / "baked_result.png", "clay")
        manifest = {
            "protocolVersion": PROTOCOL_VERSION,
            "sourceBlend": Path(source_blend_name).name,
            "camera": camera.name,
            "controlPacket": "control.json" if control_packet is not None else None,
            "providerInput": generated.to_record(),
            "projection": spec.to_record(),
            "targets": [
                {
                    "object": obj.name,
                    "collections": list(_object_collection_names(obj)),
                    "faces": list(faces),
                }
                for obj, faces, _material in targets
            ],
            "outputs": {
                "sourceBlockout": "source_blockout.png",
                "generatedProjection": "generated_projection.png",
                "bakedResult": "baked_result.png",
                "bakedFacades": baked_records,
            },
            "comparison": {
                "sameCamera": True,
                "frames": [
                    {
                        "name": "sourceBlockout",
                        "image": "source_blockout.png",
                        "sha256": _sha256(output_dir / "source_blockout.png"),
                    },
                    {
                        "name": "generatedProjection",
                        "image": "generated_projection.png",
                        "sha256": _sha256(output_dir / "generated_projection.png"),
                    },
                    {
                        "name": "bakedResult",
                        "image": "baked_result.png",
                        "sha256": _sha256(output_dir / "baked_result.png"),
                    },
                ],
            },
            "heightDisplacement": height_records,
            "authority": {
                "runtime": False,
                "generatedImage": "external-input",
                "geometryAuthority": "Blender TH_SOURCE",
                "openingAndSilhouetteAuthority": "real-geometry",
            },
        }
        (output_dir / "projection.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return manifest
    finally:
        _restore_collection_visibility(hidden)


def _camera_from_scene(scene: Any, camera_name: Optional[str]) -> Any:
    import bpy

    camera = bpy.data.objects.get(camera_name) if camera_name else scene.camera
    if camera is None:
        raise RuntimeError("scene has no active camera; pass a calibrated camera explicitly")
    if camera.type != "CAMERA":
        raise RuntimeError(f"object {camera.name!r} is not a camera")
    return camera


def _run_blender_runner(args: Sequence[str]) -> int:
    """Execute a command inside Blender when this file is used as a script."""

    import bpy

    command = args[0]
    scene = bpy.context.scene
    if command == "control":
        output_dir = Path(args[1]).resolve()
        camera_name = args[2] if len(args) > 2 and args[2] else None
        export_control_packet(scene, _camera_from_scene(scene, camera_name), output_dir)
        return 0
    if command == "project":
        output_dir = Path(args[1]).resolve()
        image = Path(args[2]).resolve()
        height = Path(args[3]).resolve() if len(args) > 3 and args[3] else None
        camera_name = args[4] if len(args) > 4 and args[4] else None
        control_path = Path(args[5]).resolve() if len(args) > 5 and args[5] else None
        objects = tuple(name for name in args[6].split(",") if name)
        generated = GeneratedFacadeInput(image=image, height_image=height)
        spec = ProjectionSpec(target_objects=objects)
        control = read_control_packet(control_path) if control_path else None
        manifest = project_generated_facade(
            scene,
            _camera_from_scene(scene, camera_name),
            generated,
            spec,
            output_dir,
            control_packet=control,
        )
        print(json.dumps(manifest, indent=2, sort_keys=True))
        return 0
    raise SystemExit(f"unknown Blender facade command: {command}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    if "bpy" in sys.modules:
        return _run_blender_runner(argv)
    raise SystemExit(
        "facade_projection.py is a Blender module; use the host wrapper "
        "tools/blender/run_facade_projection.py"
    )


if __name__ == "__main__":
    raise SystemExit(main())
