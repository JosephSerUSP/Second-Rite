"""Blender-side importer for Thestra's authoritative renderable-bundle JSON.

Invoke through Blender, not ordinary Python::

    blender --background --factory-startup --python tools/blender/import_map_bundle.py -- \
        bundle.json output.blend <project-root>
"""

from __future__ import annotations

import base64
import json
import os
import sys
import tempfile
from pathlib import Path

import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from map_bundle_scene import BundleError, build_scene_plan  # noqa: E402


def _after_double_dash(argv):
    if "--" not in argv:
        return []
    return argv[argv.index("--") + 1:]


def _clear_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)
    for material in list(bpy.data.materials):
        bpy.data.materials.remove(material)


def _rgba(value):
    values = list(value or [1, 1, 1, 1])
    while len(values) < 4:
        values.append(1)
    return tuple(float(v) for v in values[:4])


def _load_image(payload, project_root: Path, temp_paths):
    if not payload:
        return None
    kind = payload.get("kind")
    if kind == "project-asset":
        relative = payload.get("path")
        if not relative:
            return None
        image_path = (project_root / Path(relative)).resolve()
        if not image_path.is_file():
            raise BundleError(f"project texture does not exist: {relative}")
        image = bpy.data.images.load(str(image_path), check_existing=True)
        image.pack()
        return image
    if kind == "embedded-png":
        encoded = payload.get("base64")
        if not encoded:
            return None
        handle = tempfile.NamedTemporaryFile(prefix="thestra-map-", suffix=".png", delete=False)
        handle.write(base64.b64decode(encoded))
        handle.close()
        temp_paths.append(handle.name)
        image = bpy.data.images.load(handle.name, check_existing=False)
        image.pack()
        return image
    raise BundleError(f"unsupported image payload kind: {kind!r}")


def _payload_metadata(payload):
    if not payload:
        return None
    return {
        key: payload.get(key)
        for key in ("kind", "path", "mime", "width", "height")
        if payload.get(key) is not None
    }


def _material_metadata(spec):
    return {
        "id": spec.get("id"),
        "color": spec.get("color"),
        "albedo": _payload_metadata(spec.get("albedo")),
        "emission": _payload_metadata(spec.get("emission")),
    }


def _material_from_spec(spec, project_root: Path, temp_paths):
    material = bpy.data.materials.new(name=str(spec.get("id") or "ThestraMaterial"))
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    principled = nodes.new("ShaderNodeBsdfPrincipled")
    links.new(principled.outputs["BSDF"], output.inputs["Surface"])

    tint = _rgba(spec.get("color"))
    base_input = principled.inputs.get("Base Color")
    alpha_input = principled.inputs.get("Alpha")
    if base_input:
        base_input.default_value = tint
    if alpha_input:
        alpha_input.default_value = tint[3]

    albedo = _load_image(spec.get("albedo"), project_root, temp_paths)
    if albedo:
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = albedo
        mix = nodes.new("ShaderNodeMixRGB")
        mix.blend_type = "MULTIPLY"
        mix.inputs[0].default_value = 1.0
        mix.inputs[2].default_value = tint
        links.new(tex.outputs["Color"], mix.inputs[1])
        if base_input:
            links.new(mix.outputs["Color"], base_input)
        if alpha_input and "Alpha" in tex.outputs:
            links.new(tex.outputs["Alpha"], alpha_input)

    emission = _load_image(spec.get("emission"), project_root, temp_paths)
    if emission:
        emission_input = principled.inputs.get("Emission Color") or principled.inputs.get("Emission")
        strength_input = principled.inputs.get("Emission Strength")
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = emission
        if emission_input:
            links.new(tex.outputs["Color"], emission_input)
        if strength_input:
            strength_input.default_value = 1.0

    material["thestra_material_id"] = str(spec.get("id") or "")
    material["thestra_material_json"] = json.dumps(
        _material_metadata(spec), sort_keys=True, separators=(",", ":")
    )
    return material


def _assign_loop_data(mesh, obj_plan):
    uvs = obj_plan.get("uvs") or []
    if uvs:
        layer = mesh.uv_layers.new(name="Thestra UV")
        for loop in mesh.loops:
            if loop.vertex_index < len(uvs):
                layer.data[loop.index].uv = uvs[loop.vertex_index]

    normals = obj_plan.get("normals") or []
    if normals and hasattr(mesh, "normals_split_custom_set"):
        mesh.normals_split_custom_set([normals[loop.vertex_index] for loop in mesh.loops])

    colors = obj_plan.get("colors") or []
    if colors:
        layer = mesh.color_attributes.new(name="Thestra Light", type="FLOAT_COLOR", domain="CORNER")
        for loop in mesh.loops:
            if loop.vertex_index < len(colors):
                layer.data[loop.index].color = colors[loop.vertex_index]


def _link_object(collections, entities, obj_plan, material):
    mesh = bpy.data.meshes.new(obj_plan["name"] + "_mesh")
    mesh.from_pydata(obj_plan["vertices"], [], obj_plan["faces"])
    mesh.update()
    _assign_loop_data(mesh, obj_plan)
    if material:
        mesh.materials.append(material)

    obj = bpy.data.objects.new(obj_plan["name"], mesh)
    collection = collections[obj_plan["collection"]]
    collection.objects.link(obj)
    entity = entities[obj_plan["entity_key"]]
    obj.parent = entity
    for key, value in obj_plan["properties"].items():
        if value is not None:
            obj[key] = value
    return obj


def import_bundle(bundle_path: Path, output_path: Path, project_root: Path):
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    plan = build_scene_plan(bundle)
    _clear_scene()

    scene_collection = bpy.context.scene.collection
    root = bpy.data.collections.new(plan["root_collection"])
    scene_collection.children.link(root)

    collections = {}
    for name in plan["collections"]:
        collection = bpy.data.collections.new("Thestra_" + name)
        root.children.link(collection)
        collections[name] = collection

    temp_paths = []
    try:
        materials = {
            spec["id"]: _material_from_spec(spec, project_root, temp_paths)
            for spec in plan["materials"]
        }
        entities = {}
        for obj_plan in plan["objects"]:
            key = obj_plan["entity_key"]
            if key not in entities:
                empty = bpy.data.objects.new(obj_plan["entity_name"], None)
                empty.empty_display_type = "PLAIN_AXES"
                collections[obj_plan["collection"]].objects.link(empty)
                for prop_key, value in obj_plan["properties"].items():
                    if prop_key.startswith("thestra_source_") and value is not None:
                        empty[prop_key] = value
                entities[key] = empty
            _link_object(collections, entities, obj_plan, materials.get(obj_plan["material"]))

        root["thestra_bundle_version"] = plan["version"]
        root["thestra_map_id"] = str(plan["map"].get("id", ""))
        root["thestra_map_name"] = str(plan["map"].get("name", ""))
        root["thestra_object_count"] = plan["stats"]["object_count"]
        root["thestra_triangle_count"] = plan["stats"]["triangle_count"]

        output_path.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(output_path.resolve()))
    finally:
        for temp_path in temp_paths:
            try:
                os.unlink(temp_path)
            except OSError:
                pass


def main():
    args = _after_double_dash(sys.argv)
    if len(args) != 3:
        raise SystemExit(
            "usage: blender --background --python import_map_bundle.py -- "
            "<bundle.json> <output.blend> <project-root>"
        )
    import_bundle(Path(args[0]), Path(args[1]), Path(args[2]))


if __name__ == "__main__":
    main()
