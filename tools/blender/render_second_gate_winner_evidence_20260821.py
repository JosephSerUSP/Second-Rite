"""Render matched source/runtime evidence for the selected town winner."""
from __future__ import annotations

import sys
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import second_gate_render  # noqa: E402


EVIDENCE = ROOT / "out" / "blender" / "second-gate-human-assets-20260821" / "evidence"
PACKAGE = EVIDENCE / "winner" / "runtime-package"


def visible_collection(name, value):
    col = bpy.data.collections.get(name)
    if not col:
        return
    col.hide_render = not value
    for obj in col.objects:
        obj.hide_render = not value


def render(path, profile="cycles-candidate"):
    scene = bpy.context.scene
    second_gate_render.apply(scene, profile)
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def source_extremes():
    scene = bpy.context.scene
    visible_collection("TH_SOURCE", True)
    visible_collection("TH_RENDER", False)
    visible_collection("TH_COLLISION", False)
    visible_collection("TH_PREVIEW_ACTORS", True)
    visible_collection("TH_PREVIEW_ONLY", False)
    cam = scene.camera
    base = float(cam.data.shift_x)
    rows = []
    for offset, label in ((-96.0, "source-left"), (0.0, "source-center"), (96.0, "source-right")):
        cam.data.shift_x = base - offset / 426.0
        path = EVIDENCE / "winner" / f"{label}.png"
        render(path, "cycles-candidate")
        rows.append({"label": label, "offset": offset, "path": path.name})
    cam.data.shift_x = base
    return rows


def runtime_render():
    scene = bpy.context.scene
    visible_collection("TH_SOURCE", False)
    visible_collection("TH_RENDER", False)
    visible_collection("TH_COLLISION", False)
    visible_collection("TH_PREVIEW_ACTORS", True)
    visible_collection("TH_PREVIEW_ONLY", False)
    runtime_col = bpy.data.collections.new("RUNTIME_BAKED")
    scene.collection.children.link(runtime_col)
    before = set(bpy.data.objects)
    if hasattr(bpy.ops.wm, "obj_import"):
        bpy.ops.wm.obj_import(filepath=str(PACKAGE / "environment.obj"))
    else:
        bpy.ops.import_scene.obj(filepath=str(PACKAGE / "environment.obj"))
    imported = [obj for obj in bpy.data.objects if obj not in before]
    image = bpy.data.images.load(str(PACKAGE / "environment.png"), check_existing=True)
    try:
        image.colorspace_settings.name = "sRGB"
    except (AttributeError, TypeError, ValueError):
        pass
    mat = bpy.data.materials.new("RUNTIME_BakedBeautyAtlas")
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image
    tex.interpolation = "Linear"
    links.new(tex.outputs["Color"], emission.inputs["Color"])
    emission.inputs["Strength"].default_value = 1.25
    links.new(emission.outputs[0], out.inputs["Surface"])
    for obj in imported:
        for col in list(obj.users_collection):
            col.objects.unlink(obj)
        runtime_col.objects.link(obj)
        if obj.type == "MESH":
            obj.data.materials.clear()
            obj.data.materials.append(mat)
    render(EVIDENCE / "winner" / "runtime-baked.png", "cycles-lookdev")


def main():
    rows = source_extremes()
    runtime_render()
    print(rows)


if __name__ == "__main__":
    main()
