"""Phase 8 proof: rich TH_SOURCE vs the baked atlas on TH_RENDER.

Both frames are photographed at the identical calibrated framing. Preview
actors and preview-only lights are excluded from BOTH sides, so the difference
image measures the bake and nothing else -- if the actors were left in one
side they would dominate the difference and hide whatever the bake got wrong.

The baked side is shown unlit (emission), because a beauty bake already
contains its lighting; relighting it would double the shading and the
comparison would be meaningless.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

SNIPPET = '''
import bpy, sys, json
sys.path.insert(0, {tools!r})
from cleanroom import scene as cr_scene

scene = bpy.context.scene
mode = {mode!r}
src = bpy.data.collections.get("TH_SOURCE")
run = bpy.data.collections.get("TH_RENDER")
for name in ("TH_PREVIEW_ACTORS", "TH_PREVIEW_ONLY", "TH_COLLISION",
             "TH_ANCHORS", "TH_CAMERA_PREVIEW"):
    cr_scene.hide_render(bpy.data.collections.get(name), True)

if mode == "source":
    cr_scene.hide_render(src, False)
    cr_scene.hide_render(run, True)
    # the scene's own lights are preview-only; re-enable just the lights
    prev = bpy.data.collections.get("TH_PREVIEW_ONLY")
    if prev:
        prev.hide_render = False
        for obj in prev.objects:
            obj.hide_render = (obj.type != "LIGHT")
else:
    # Photograph the EXPORTED PACKAGE, not a re-dressed TH_RENDER in this file.
    # The atlas UVs are created inside the pipeline's own Blender process, so
    # the runtime boxes in this .blend carry no UVMap at all; assigning the
    # atlas to them samples UV (0,0) for every pixel and renders pure black.
    # Importing environment.obj proves the thing that actually ships.
    cr_scene.hide_render(src, True)
    cr_scene.hide_render(run, True)
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath={objpath!r})
    imported = [o for o in bpy.data.objects if o not in before]
    atlas = bpy.data.images.load({atlas!r}, check_existing=True)
    mat = bpy.data.materials.new("CR_BAKED_VIEW")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Strength"].default_value = 1.0
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = atlas
    tex.interpolation = "Closest"
    tex.extension = "CLIP"
    nt.links.new(tex.outputs["Color"], emit.inputs["Color"])
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    for obj in imported:
        obj.hide_render = False
        if obj.type == "MESH":
            obj.data.materials.clear()
            obj.data.materials.append(mat)
    bounds = []
    for obj in imported:
        if obj.type == "MESH":
            for c in obj.bound_box:
                v = obj.matrix_world @ __import__("mathutils").Vector(c)
                bounds.append(tuple(round(x, 3) for x in v))
    info = dict(objects=len(imported),
                uvLayers=[list(o.data.uv_layers.keys())
                          for o in imported if o.type == "MESH"],
                min=[round(min(b[i] for b in bounds), 3) for i in range(3)] if bounds else None,
                max=[round(max(b[i] for b in bounds), 3) for i in range(3)] if bounds else None)
    print("IMPORTED " + json.dumps(info))
    if scene.world and scene.world.node_tree:
        bg = scene.world.node_tree.nodes.get("Background")
        if bg:
            bg.inputs["Strength"].default_value = 0.0

bpy.context.view_layer.update()
cr_scene.render({png!r}, samples={samples}, exposure=0.0)
print("COMPARE_OK " + mode)
'''


def render_pair(blend, atlas, obj_path, out_dir, *, samples=96, blender=None):
    from town_environment_pipeline import blender_executable
    blender = blender or blender_executable()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    made = {}
    for mode in ("source", "baked"):
        png = out_dir / ("winner_%s.png" % mode)
        s = tempfile.NamedTemporaryFile(prefix="cr_cmp_", suffix=".py",
                                        delete=False, mode="w", encoding="utf-8")
        s.write(SNIPPET.format(tools=str(ROOT / "tools" / "blender"),
                               mode=mode, atlas=str(atlas), png=str(png),
                               objpath=str(obj_path), samples=samples))
        s.close()
        res = subprocess.run([blender, "--background", str(blend),
                              "--python", s.name], capture_output=True, text=True)
        Path(s.name).unlink(missing_ok=True)
        if res.returncode != 0 or "COMPARE_OK" not in res.stdout:
            raise SystemExit("compare render failed (%s)\n%s\n%s"
                             % (mode, res.stdout[-3000:], res.stderr[-2000:]))
        made[mode] = str(png)
        print("[compare] rendered %s" % mode)
    return made


def difference(source_png, baked_png, out_png, *, amplify=3.0):
    import numpy as np
    from PIL import Image
    a = np.asarray(Image.open(source_png).convert("RGB")).astype(np.float64)
    b = np.asarray(Image.open(baked_png).convert("RGB")).astype(np.float64)
    d = np.abs(a - b)
    stats = {
        "meanAbsDifference": round(float(d.mean()), 4),
        "meanAbsDifferencePercent": round(float(d.mean()) / 2.55, 3),
        "p95AbsDifference": round(float(np.percentile(d, 95)), 3),
        "maxAbsDifference": round(float(d.max()), 3),
    }
    Image.fromarray(np.clip(d * amplify, 0, 255).astype(np.uint8)).save(out_png)
    return stats


def atlas_coverage(atlas_path):
    """Fraction of the atlas that actually received bake data."""
    import numpy as np
    from PIL import Image
    im = Image.open(atlas_path).convert("RGBA")
    a = np.asarray(im).astype(np.float64)
    alpha = a[..., 3] / 255.0
    rgb = a[..., :3].max(axis=-1)
    used = (alpha > 0.02) | (rgb > 2.0)
    return {
        "atlasPixels": int(alpha.size),
        "coveredPixels": int(used.sum()),
        "coveragePercent": round(100.0 * float(used.mean()), 3),
        "dimensions": list(im.size),
    }
