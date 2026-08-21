"""Render an exported Second Gate environment package in the source scene."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
TOOL_ROOT = ROOT / "tools" / "blender"
sys.path.insert(0, str(TOOL_ROOT))
import second_gate_render  # noqa: E402
import thestra_camera  # noqa: E402


def link_only(obj, collection):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    collection.objects.link(obj)


def make_camera(calibration_path: Path, offset_x=0.0, offset_y=0.0):
    record = json.loads(calibration_path.read_text(encoding="utf-8"))
    record = copy.deepcopy(record)
    record["viewportCenterX"] += float(offset_x)
    record["viewportCenterY"] += float(offset_y)
    record["projectionWindowOffsetX"] = float(offset_x)
    record["projectionWindowOffsetY"] = float(offset_y)
    return thestra_camera.create_or_update_camera(record)


def render_package(package: Path, output: Path, calibration: Path, walker: bool):
    output.mkdir(parents=True, exist_ok=True)
    render_col = bpy.data.collections.get("TH_RENDER")
    if render_col is None:
        render_col = bpy.data.collections.new("TH_RENDER")
        bpy.context.scene.collection.children.link(render_col)
    before = set(bpy.data.objects)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.wm.obj_import(filepath=str(package / "environment.obj"))
    imported = [obj for obj in bpy.context.selected_objects if obj.type == "MESH"]
    if not imported:
        raise RuntimeError("environment.obj imported no mesh")
    for obj in imported:
        link_only(obj, render_col)

    scene = bpy.context.scene
    source_col = bpy.data.collections.get("TH_SOURCE")
    if source_col:
        source_col.hide_render = True
    collision_col = bpy.data.collections.get("TH_COLLISION")
    if collision_col:
        collision_col.hide_render = True
    actors_col = bpy.data.collections.get("TH_PREVIEW_ACTORS")
    if actors_col:
        actors_col.hide_render = not walker
        for obj in actors_col.objects:
            obj.hide_render = not walker
    render_col.hide_render = False

    for offset, label in [(-96, "left_96"), (0, "nominal"), (96, "right_96")]:
        make_camera(calibration, offset)
        second_gate_render.apply(scene, "cycles-candidate")
        scene.render.filepath = str(output / f"runtime_baked_{label}_426.png")
        bpy.ops.render.render(write_still=True)

    if actors_col:
        actors_col.hide_render = False
        for obj in actors_col.objects:
            obj.hide_render = False
    make_camera(calibration, 0)
    second_gate_render.apply(scene, "cycles-candidate")
    scene.render.filepath = str(output / "runtime_baked_with_walker_426.png")
    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "baked_runtime.blend"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--walker", action="store_true")
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]
    args = parser.parse_args(argv)
    render_package(args.package.resolve(), args.output.resolve(), args.calibration.resolve(), args.walker)


if __name__ == "__main__":
    main()
