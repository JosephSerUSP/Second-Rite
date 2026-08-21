"""Render the baked TH_RENDER package through the authored fixed-eye camera."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path


def set_socket(node, name, value):
    socket = node.inputs.get(name)
    if socket is not None:
        socket.default_value = value


def configure_baked_material(image_path: Path):
    import bpy
    mat = bpy.data.materials.get("RUNTIME_BakedAtlas") or bpy.data.materials.new("RUNTIME_BakedAtlas")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(image_path), check_existing=True)
    tex.interpolation = "Linear"
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    set_socket(bsdf, "Roughness", 0.92)
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def add_runtime_proof_lights():
    import bpy
    scene = bpy.context.scene
    world = scene.world or bpy.data.worlds.new("RuntimeProofWorld")
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    set_socket(background, "Color", (0.07, 0.09, 0.12, 1.0))
    set_socket(background, "Strength", 0.65)
    for name, loc, energy, color, size in [
        ("RUNTIME_ProofWarm", (-7.0, -7.0, 9.0), 900.0, (1.0, 0.72, 0.48), 7.0),
        ("RUNTIME_ProofCool", (10.0, 4.0, 8.0), 1000.0, (0.48, 0.65, 0.82), 8.0),
        ("RUNTIME_ProofFill", (0.0, -2.0, 3.0), 520.0, (0.78, 0.84, 0.9), 5.0),
    ]:
        bpy.ops.object.light_add(type="AREA", location=loc)
        light = bpy.context.active_object
        light.name = name
        light.data.energy = energy
        light.data.color = color
        light.data.shape = "DISK"
        light.data.size = size
        light.rotation_euler = (math.pi / 2, 0.0, 0.0)


def render_proof(blend_path: Path, atlas_path: Path, out_dir: Path):
    import bpy
    bpy.ops.wm.open_mainfile(filepath=str(blend_path))
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 426
    scene.render.resolution_y = 240
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"
    try:
        scene.view_settings.look = "Medium High Contrast"
    except Exception:
        pass
    out_dir.mkdir(parents=True, exist_ok=True)

    cols = {col.name: col for col in bpy.data.collections}
    render_col = cols["TH_RENDER"]
    source_col = cols["TH_SOURCE"]
    camera_col = cols["TH_CAMERA_PREVIEW"]
    target_mat = configure_baked_material(atlas_path)
    add_runtime_proof_lights()
    for obj in render_col.objects:
        if obj.type == "MESH":
            obj.data.materials.clear()
            obj.data.materials.append(target_mat)
            obj.hide_render = False
    source_col.hide_render = True
    for obj in source_col.objects:
        obj.hide_render = True
    for name in ("TH_COLLISION", "TH_PREVIEW_ONLY", "TH_ANCHORS"):
        collection = cols.get(name)
        if collection:
            collection.hide_render = True
            for obj in collection.objects:
                obj.hide_render = True
    camera = next(obj for obj in camera_col.objects if obj.type == "CAMERA")
    scene.camera = camera
    # Width at the fixed camera target from the authored 43.27mm lens.
    hfov = 2.0 * math.atan(camera.data.sensor_width / (2.0 * camera.data.lens))
    width_at_target = 2.0 * 18.0 * math.tan(hfov * 0.5)
    offset_world = width_at_target / 426.0
    tracking = []
    actors = cols["TH_PREVIEW_ACTORS"]
    for with_actors in (False, True):
        actors.hide_render = not with_actors
        for actor in actors.objects:
            actor.hide_render = not with_actors
        prefix = "runtime_actors" if with_actors else "runtime_mesh"
        for px in (-96, 0, 96):
            camera.location.x = px * offset_world
            path = out_dir / f"{prefix}_{'m96' if px < 0 else 'p96' if px > 0 else 'zero'}.png"
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            tracking.append({"actors": with_actors, "offsetPx": px, "worldOffset": round(px * offset_world, 6), "path": path.name})
    camera.location.x = 0.0
    (out_dir / "runtime_tracking.json").write_text(json.dumps({
        "nativeResolution": [426, 240],
        "lensMm": 43.27,
        "cameraLocation": [0.0, -18.0, 3.55],
        "offsetsPx": [-96, 0, 96],
        "worldUnitsPerPixelAtTarget": round(offset_world, 8),
        "frames": tracking,
        "nearestWalker": True,
        "walkerSource": "projects/hichaukitoden-game/assets/character/walker.png",
    }, indent=2), encoding="utf-8")
    print(json.dumps({"outDir": str(out_dir), "frames": len(tracking)}, sort_keys=True))


def main():
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", type=Path, required=True)
    parser.add_argument("--atlas", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(values)
    render_proof(args.blend.resolve(), args.atlas.resolve(), args.out_dir.resolve())


if __name__ == "__main__":
    main()
