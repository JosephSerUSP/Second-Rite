"""Render isolated source geometry from the production map-26 camera pose.

The adopted Blender source uses the lane-mirrored authoring Y axis. This
diagnostic resolves the actual runtime camera position, pitch, and proof-lane
Y values, then renders all geometry plus isolated near/background passes. It
does not save or modify the source blend.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import bpy


LANE_CENTRE = 12.031
PROOF_LANES = (("west", -300.0 / 256.0), ("centre", 0.0),
               ("east", 300.0 / 256.0))
# The adopted source stores the production eye directly.  Map 26's authored
# eye-height correction belongs to the runtime projection-window contract; it
# is not a reason to invent a second Blender eye for this source diagnostic.
CAMERA_X = -18.66666603088379
CAMERA_Z = 2.2604167461395264


def debug_material(name, color):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.diffuse_color = (*color, 1.0)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Emission Color"].default_value = (*color, 1.0)
        bsdf.inputs["Emission Strength"].default_value = 1.0
        bsdf.inputs["Roughness"].default_value = 1.0
    return material


def replace_material(obj, material):
    if obj.type != "MESH":
        return
    obj.data.materials.clear()
    obj.data.materials.append(material)


def render(blend: Path, output: Path) -> None:
    bpy.ops.wm.open_mainfile(filepath=str(blend.resolve()))
    scene = bpy.context.scene
    camera = bpy.data.objects.get("TH_CAMERA_PREVIEW")
    if camera is None:
        raise RuntimeError("adopted source is missing TH_CAMERA_PREVIEW")
    scene.camera = camera
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 426
    scene.render.resolution_y = 240
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    camera.data.lens = 72.0
    camera.data.shift_y = -0.2109375

    # Keep the adopted camera's authored orientation intact. It is the source
    # authority for the canonical -17.5 degree pitch; this diagnostic changes
    # only the mirrored lane position so it cannot accidentally invent a
    # second pitch or eye-height contract.

    output.mkdir(parents=True, exist_ok=True)
    all_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    near = [obj for obj in all_objects if obj.name.startswith("CORTICO_AUTHORED_NEAR_")]
    background = [obj for obj in all_objects
                  if obj.name.startswith("CORTICO_AUTHORED_BACKGROUND_")]
    near_mat = debug_material("CORTICO_DEBUG_NEAR", (0.95, 0.24, 0.08))
    background_mat = debug_material("CORTICO_DEBUG_BACKGROUND", (0.12, 0.85, 0.95))

    passes = (("all", None, None), ("near", near, near_mat),
              ("background", background, background_mat))
    original = {obj.name: obj.hide_render for obj in all_objects}
    try:
        for label, selected, material in passes:
            selected_names = {obj.name for obj in selected or []}
            for obj in all_objects:
                obj.hide_render = selected is not None and obj.name not in selected_names
                if selected is not None and obj.name in selected_names:
                    replace_material(obj, material)
            for view, shift_x in PROOF_LANES:
                camera.location = (CAMERA_X, 0.0, CAMERA_Z)
                camera.data.shift_x = shift_x
                scene.render.filepath = str((output / f"{label}-{view}.png").resolve())
                bpy.ops.render.render(write_still=True)
    finally:
        for obj in all_objects:
            obj.hide_render = original[obj.name]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:]
                             if "--" in sys.argv else [])
    if not args.blend.is_file():
        raise SystemExit(f"source blend not found: {args.blend}")
    render(args.blend, args.output)
    print("CORTICO RUNTIME DEBUG OK", args.output.resolve())


if __name__ == "__main__":
    main()
