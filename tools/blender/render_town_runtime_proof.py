"""Render the exported town mesh with its baked atlas for a source/runtime proof."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy  # type: ignore


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", required=True)
    parser.add_argument("--package", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])


def make_baked_material(image_path: Path):
    material = bpy.data.materials.get("RuntimeProofBakedAtlas")
    if material is None:
        material = bpy.data.materials.new("RuntimeProofBakedAtlas")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    image = nodes.new("ShaderNodeTexImage")
    image.name = "RuntimeProofAtlas"
    image.image = bpy.data.images.load(str(image_path), check_existing=True)
    shader.inputs["Roughness"].default_value = 0.86
    if "Specular IOR Level" in shader.inputs:
        shader.inputs["Specular IOR Level"].default_value = 0.15
    if "Emission Color" in shader.inputs:
        links.new(image.outputs["Color"], shader.inputs["Emission Color"])
        shader.inputs["Emission Strength"].default_value = 0.08
    else:
        links.new(image.outputs["Color"], shader.inputs["Emission"])
        shader.inputs["Emission Strength"].default_value = 0.08
    links.new(image.outputs["Color"], shader.inputs["Base Color"])
    links.new(image.outputs["Alpha"], shader.inputs["Alpha"])
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    return material


def main():
    args = parse_args()
    blend_path = Path(args.blend).resolve()
    package_dir = Path(args.package).resolve()
    output_path = Path(args.output).resolve()
    atlas_path = package_dir / "environment.png"
    for path in (blend_path, atlas_path):
        if not path.is_file():
            raise FileNotFoundError(path)

    bpy.ops.wm.open_mainfile(filepath=str(blend_path))
    scene = bpy.context.scene
    render_collection = bpy.data.collections.get("TH_RENDER")
    if render_collection is None:
        raise RuntimeError("TH_RENDER is missing from the source blend")

    baked_material = make_baked_material(atlas_path)
    render_objects = [obj for obj in render_collection.objects if obj.type == "MESH"]
    if not render_objects:
        raise RuntimeError("TH_RENDER contains no mesh objects")
    for obj in render_objects:
        obj.hide_render = False
        obj.data.materials.clear()
        obj.data.materials.append(baked_material)

    # Keep only the exported render mesh visible. Source lights remain active so
    # the result reads like the runtime mesh under the authored lighting mood.
    for collection_name in ("TH_PREVIEW_ACTORS", "TH_PREVIEW_ONLY", "TH_COLLISION",
                            "TH_ANCHORS", "TH_CAMERA_PREVIEW"):
        collection = bpy.data.collections.get(collection_name)
        if collection:
            collection.hide_render = True
            for obj in collection.objects:
                obj.hide_render = True
    source = bpy.data.collections.get("TH_SOURCE")
    if source:
        source.hide_render = False
        for obj in source.objects:
            obj.hide_render = obj.type == "MESH"
    render_collection.hide_render = False

    camera = bpy.data.objects.get("TH_CAMERA_PREVIEW")
    if camera is None or camera.type != "CAMERA":
        raise RuntimeError("TH_CAMERA_PREVIEW camera is missing from the source blend")
    scene.camera = camera
    scene.render.resolution_x = 426
    scene.render.resolution_y = 240
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.filepath = str(output_path)
    bpy.ops.render.render(write_still=True)
    print(f"TOWN RUNTIME PROOF OK: {output_path}")


if __name__ == "__main__":
    main()
