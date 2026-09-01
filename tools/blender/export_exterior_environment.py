"""Bake an authored modelled exterior into its runtime environment package."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "blender"))

import town_environment_pipeline as pipeline  # noqa: E402


def rebuild_render_mesh() -> None:
    print("[exterior] preparing render mesh", flush=True)
    source = bpy.data.collections["TH_SOURCE"]
    render = bpy.data.collections["TH_RENDER"]
    render.hide_viewport = False
    render.hide_render = False
    def reveal(layer):
        if layer.collection == render:
            layer.exclude = False
            layer.hide_viewport = False
            return True
        return any(reveal(child) for child in layer.children)
    if not reveal(bpy.context.view_layer.layer_collection):
        raise RuntimeError("TH_RENDER is not linked into the active view layer")
    bpy.ops.object.mode_set(mode="OBJECT") if bpy.context.object and bpy.context.object.mode != "OBJECT" else None
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = None
    for obj in list(render.all_objects):
        print(f"[exterior] removing {obj.name}", flush=True)
        bpy.data.objects.remove(obj, do_unlink=True)

    seed_mesh = bpy.data.meshes.new("st_maria_praca_TH_RENDER_seed")
    seed = bpy.data.objects.new("st_maria_praca_TH_RENDER_seed", seed_mesh)
    render.objects.link(seed)
    copies = [seed]
    source_objects = list(source.all_objects)
    for obj in source_objects:
        if obj.type != "MESH" or obj.hide_render:
            continue
        if not (obj.name.startswith("STUDY_") or
                obj.name in {"ARCH_square_ground", "ARCH_low_curb"} or
                obj.name.startswith("FG_")):
            continue
        print(f"[exterior] copying {obj.name}", flush=True)
        copy = obj.copy()
        copy.name = f"R_{obj.name}"
        copy.hide_viewport = False
        copy.hide_render = False
        render.objects.link(copy)
        copy.hide_set(False)
        copies.append(copy)
    if not copies:
        raise RuntimeError("TH_SOURCE contains no renderable meshes")

    bpy.ops.object.select_all(action="DESELECT")
    print(f"[exterior] selecting {len(copies)} copies", flush=True)
    for obj in copies:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = seed
    if len(bpy.context.selected_objects) != len(copies):
        raise RuntimeError(
            f"render join selection incomplete: {len(bpy.context.selected_objects)} "
            f"selected of {len(copies)}")
    if len(copies) > 1:
        bpy.ops.object.join()
    target = bpy.context.view_layer.objects.active
    if target is None or target.type != "MESH":
        raise RuntimeError("render join produced no active mesh")
    target.name = "st_maria_praca_TH_RENDER"
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=0.001)
    bpy.ops.mesh.dissolve_degenerate(threshold=0.001)
    bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=0.0)
    bpy.ops.object.mode_set(mode="OBJECT")
    target.data.calc_loop_triangles()
    if len(target.data.loop_triangles) < 100:
        raise RuntimeError(
            f"render join is implausibly small: {len(target.data.loop_triangles)} triangles")
    print(f"[exterior] joined {len(copies)} source meshes into "
          f"{len(target.data.loop_triangles)} runtime triangles")


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1:]
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--span", type=float, default=23.699)
    parser.add_argument("--atlas-size", type=int, default=1024)
    parser.add_argument("--samples", type=int, default=24)
    args = parser.parse_args(argv)

    opened = Path(bpy.data.filepath).resolve() if bpy.data.filepath else None
    if opened != args.blend.resolve():
        bpy.ops.wm.open_mainfile(filepath=str(args.blend.resolve()))
    rebuild_render_mesh()
    output = args.output.resolve()
    pipeline.run_pipeline_in_blender(args.blend.resolve(), output,
                                     atlas_size=args.atlas_size,
                                     bake_samples=args.samples)
    print("EXTERIOR 3D EXPORT OK")


if __name__ == "__main__":
    main()
