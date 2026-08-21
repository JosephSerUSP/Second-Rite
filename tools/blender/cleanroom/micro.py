"""Phase 1 material test at true native pixel density.

Not a thirty-swatch ranking gauntlet. The only job is to eliminate material
sources that are obviously wrong *at the density the game actually renders*:
27.4286 px per world metre, measured from the calibrated camera.

Each swatch is therefore rendered through an orthographic camera covering
exactly 128 px / 27.4286 px-per-m = 4.6667 m of surface at 128x128. Anything
that reads as uniform noise, as a photograph of a wall, or at the wrong
physical scale is visible immediately.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

from . import geom, mats, scene as cr_scene, vocab

PX_PER_M = 48.0 / 1.75
SWATCH_PX = 128
SWATCH_M = SWATCH_PX / PX_PER_M


def _swatch_camera():
    data = bpy.data.cameras.new("MICRO_CAM")
    data.type = "ORTHO"
    data.ortho_scale = SWATCH_M
    obj = bpy.data.objects.new("MICRO_CAM", data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = Vector((-6.0, 0.0, 0.0))
    obj.rotation_euler = (math.radians(90), 0.0, math.radians(-90))
    bpy.context.scene.camera = obj
    return obj


def _swatch_lighting():
    world = bpy.data.worlds.new("MICRO_WORLD")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.34, 0.38, 0.44, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    data = bpy.data.lights.new("MICRO_SUN", type="SUN")
    data.energy = 3.2
    data.color = (1.0, 0.95, 0.87)
    data.angle = math.radians(4.0)
    sun = bpy.data.objects.new("MICRO_SUN", data)
    # raking light: grazing enough to reveal relief, not so low it silhouettes
    sun.rotation_euler = (math.radians(62), 0.0, math.radians(-38))
    bpy.context.scene.collection.objects.link(sun)
    return sun


def run(out_dir, *, samples=64):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cr_scene.reset()
    col = bpy.data.collections.new("MICRO")
    bpy.context.scene.collection.children.link(col)
    _swatch_camera()
    _swatch_lighting()

    registry = vocab.build_vocabulary()
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    try:
        scene.cycles.device = "CPU"
    except Exception:
        pass
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x = SWATCH_PX
    scene.render.resolution_y = SWATCH_PX
    scene.render.resolution_percentage = 100
    scene.render.pixel_aspect_x = 1.0
    scene.render.pixel_aspect_y = 1.0
    scene.render.image_settings.file_format = "PNG"
    try:
        scene.view_settings.view_transform = "Filmic"
        scene.view_settings.look = "None"
    except Exception:
        pass

    results = {}
    for mid, material in sorted(registry.items()):
        for obj in list(col.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        # a slightly relieved panel, not a flat card: bump and displacement
        # only prove themselves against a surface that can catch light
        slab = geom.panel("MICRO_SLAB", col, x=0.0,
                          y0=-SWATCH_M, y1=SWATCH_M,
                          z0=-SWATCH_M, z1=SWATCH_M,
                          cuts_y=96, cuts_z=96)
        mats.apply(slab, mid)
        if material.height_path:
            tex = mats.height_texture("MICRO_H_" + mid, material.height_path)
            geom.displace(slab, tex, strength=0.045, mid_level=0.5)
        cr_scene.shade_smooth(slab)
        path = out_dir / ("swatch_%s.png" % mid)
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        results[mid] = {
            "kind": material.kind,
            "tile_m": material.tile_m,
            "displaceable": bool(material.height_path),
            "swatch": str(path),
            "provenance": material.provenance,
        }
        print("[micro] %-20s %-10s tile=%.2fm" % (mid, material.kind, material.tile_m))

    (out_dir / "micro.json").write_text(json.dumps(results, indent=2),
                                        encoding="utf-8")
    print("[micro] MICRO_OK %d" % len(results))
    return results


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    run(Path(argv[0]) if argv else Path("micro"))
