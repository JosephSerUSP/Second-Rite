"""Photograph a baked room package the way the game draws it: unlit, nearest-sampled, native size.

    blender -b --factory-startup -P tools/blender/photograph_room_package.py -- \
        --package projects/.../st_maria_town/alicias_padaria_3d --out out/look/padaria_new --lane-y 2.0 5.5

Imports `environment.obj` (the runtime's axis convention, which Blender's importer reproduces),
paints it with `environment.png` as an emission texture with Closest interpolation, and renders from
the town side-view camera at each `--lane-y` at 426 x 240 with no film filter, so what you see is
what one texel per pixel decisions look like in the game. Nothing is written but the PNGs.

Use it to compare a package before and after a rebake (`git show HEAD:path > ...` for the old one):
both go through the same camera, so the only thing that differs is the package.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import atlas_allocation  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--lane-y", type=float, nargs="+", default=[2.0, 3.8833, 5.5])
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new("black")
    package = args.package.resolve()
    bpy.ops.wm.obj_import(filepath=str(package / "environment.obj"))
    image = bpy.data.images.load(str(package / "environment.png"))
    image.colorspace_settings.name = "sRGB"
    material = bpy.data.materials.new("PACKAGE_UNLIT")
    material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()
    texture = tree.nodes.new("ShaderNodeTexImage")
    texture.image = image
    texture.interpolation = "Closest"
    emission = tree.nodes.new("ShaderNodeEmission")
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    tree.links.new(texture.outputs["Color"], emission.inputs["Color"])
    tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH":
            obj.data.materials.clear()
            obj.data.materials.append(material)

    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 64
    scene.render.filter_size = 0.0
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "Standard"
    args.out.mkdir(parents=True, exist_ok=True)
    for lane_y in args.lane_y:
        atlas_allocation.lane_camera(scene, float(lane_y), mirrored=False)   # the OBJ is in engine space
        scene.render.filepath = str((args.out / f"lane_{lane_y:g}.png").resolve())
        bpy.ops.render.render(write_still=True)
    print("PACKAGE PHOTOGRAPHED", args.out)


if __name__ == "__main__":
    main()
