#!/usr/bin/env python3
"""Render matched source and baked-runtime checks for the Ashwater town."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]


def args():
    parser = argparse.ArgumentParser()
    parser.add_argument("blend")
    parser.add_argument("camera_record")
    parser.add_argument("atlas")
    parser.add_argument("--output", required=True)
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(argv)


def set_collection(name, visible):
    col = bpy.data.collections.get(name)
    if not col:
        return
    col.hide_render = not visible
    for obj in col.objects:
        obj.hide_render = not visible


def atlas_material(atlas_path):
    mat = bpy.data.materials.get("EnvironmentBakedAtlasPreview") or bpy.data.materials.new("EnvironmentBakedAtlasPreview")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(Path(atlas_path).resolve()), check_existing=True)
    tex.interpolation = "Closest"
    links.new(tex.outputs["Color"], emission.inputs["Color"])
    emission.inputs["Strength"].default_value = 1.0
    links.new(emission.outputs["Emission"], out.inputs["Surface"])
    return mat


def apply_mode(mode, atlas_path=None):
    # Source lights remain visible only for the source beauty check.  The
    # baked runtime is intentionally self-lit by the atlas, not relit by the
    # rich source scene.
    if mode == "source":
        set_collection("TH_SOURCE", True)
        set_collection("TH_RENDER", False)
    elif mode == "baked":
        set_collection("TH_SOURCE", False)
        set_collection("TH_RENDER", True)
        if atlas_path:
            mat = atlas_material(atlas_path)
            target = bpy.data.objects.get("RND_Environment_Mesh")
            if target:
                target.data.materials.clear()
                target.data.materials.append(mat)
    set_collection("TH_COLLISION", False)
    set_collection("TH_ANCHORS", False)
    set_collection("TH_PREVIEW_ONLY", False)
    set_collection("TH_CAMERA_PREVIEW", False)
    set_collection("TH_PREVIEW_ACTORS", True)
    if mode == "baked":
        # Source lights are excluded with the source collection; all colour is
        # already present in the atlas.
        for obj in bpy.data.objects:
            if obj.type == "LIGHT":
                obj.hide_render = True


def render(scene, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def main():
    parsed = args()
    scene = bpy.context.scene
    record = json.loads(Path(parsed.camera_record).read_text(encoding="utf-8"))
    sys.path.insert(0, str(ROOT / "tools" / "blender"))
    from thestra_camera import create_or_update_camera

    out = Path(parsed.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    base_record = dict(record)

    apply_mode("source")
    source_path = out / "th_source_rich_matched.png"
    create_or_update_camera(base_record, scene=scene, name="TH_CAMERA_PREVIEW", make_active=True)
    render(scene, source_path)

    apply_mode("baked", parsed.atlas)
    offsets = (-96, 0, 96)
    for offset in offsets:
        current = dict(base_record)
        current["viewportCenterX"] = float(base_record["viewportCenterX"]) + offset
        current["projectionWindowOffsetX"] = float(offset)
        create_or_update_camera(current, scene=scene, name="TH_CAMERA_PREVIEW", make_active=True)
        suffix = f"{offset:+d}"
        render(scene, out / f"projection_window_{suffix}.png")
    print(f"SECOND_GATE_RENDER_OK {out}")


if __name__ == "__main__":
    main()
