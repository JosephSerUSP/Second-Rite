"""Render pre/post default-preset evidence for the tree generator.

The left specimen is an exact review-only reconstruction of the pre-e2fe5ada
defaults: the controls that were newly activated are set to their neutral
values, while the post specimen uses the authored preset unchanged.  This is
not a runtime compatibility path.  The two specimens share seed, mesh path,
materials, actor and camera in every frame.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))
sys.path.insert(0, str(ROOT / "tools/blender/recipes"))
from tree_comparison import add_actor, label, look_at, material, mesh_object  # noqa: E402
import tree_generator as trees  # noqa: E402
import tree_material  # noqa: E402
import tree_mesh  # noqa: E402

SEED = 31
NEUTRAL_NEW_CONTROLS = {
    "apical_dominance": 0.0,
    "attraction_weight": 0.0,
    "crown_bias": 0.0,
    "crown_bias_deg": 0.0,
    "branch_sweep_deg": 0.0,
    "branch_twist_deg": 0.0,
}


def scene_setup():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    world = bpy.data.worlds.new("TREE_DEFAULT_REGRESSION_WORLD")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (.035, .05, .07, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = .45
    ground = material("regression_ground", (.17, .20, .16))
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
    bpy.context.object.data.materials.append(ground)
    bpy.ops.object.light_add(type="AREA", location=(-5, -8, 11))
    key = bpy.context.object
    key.data.energy = 1100
    key.data.size = 8
    look_at(key, (0, 0, 2.4))
    camera_data = bpy.data.cameras.new("TREE_DEFAULT_REGRESSION_CAMERA")
    camera = bpy.data.objects.new("TREE_DEFAULT_REGRESSION_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 13.0
    wood = material("regression_wood", (.25, .12, .055))
    foliage = tree_material.foliage_material(name="regression_foliage")
    actor = material("regression_actor", (.12, .22, .46))
    skin = material("regression_skin", (.62, .35, .20))
    ink = material("regression_ink", (.82, .86, .88))
    add_actor(-5.0, actor, skin)
    return scene, camera, wood, foliage, ink


def build_pair(name, wood, foliage, ink):
    pair = []
    for side, overrides, x in (
        ("prechange", NEUTRAL_NEW_CONTROLS, -2.8),
        ("postchange", {}, 2.8),
    ):
        spec = trees.preset(name, seed=SEED, **overrides)
        full = trees.generate(spec, "authoring")
        trees.validate(full)
        skeleton = trees.reduce_lod(full, "low")
        trees.validate(skeleton, "low")
        branches = mesh_object(f"{name}_{side}_BRANCHES",
                               *tree_mesh.branch_mesh(skeleton), wood)
        card_vertices, card_faces, card_uvs = tree_mesh.foliage_mesh(skeleton, lod="low")
        cards = mesh_object(f"{name}_{side}_CARDS", card_vertices, card_faces,
                            foliage, card_uvs)
        branches.location.x = x
        cards.location.x = x
        for polygon in branches.data.polygons:
            polygon.use_smooth = True
        label_object = label(f"{side}_{name}", x, ink)
        label_object.data.body = side.upper()
        pair.extend((branches, cards))
    return pair


def render_pair(scene, camera, objects, output_dir, name, view):
    for obj in bpy.data.objects:
        obj.hide_render = obj not in objects and obj.name.startswith((
            name + "_prechange", name + "_postchange", "LABEL_" + "prechange_" + name,
            "LABEL_" + "postchange_" + name))
    if view == "front":
        camera.location = (0, -28, 3.6)
        look_at(camera, (0, 0, 3.0))
    else:
        camera.location = (12.5, -27, 8.5)
        look_at(camera, (0, 0, 3.0))
    path = output_dir / f"default-regression-{name}-{view}.png"
    scene.render.filepath = str(path.resolve())
    bpy.ops.render.render(write_still=True)
    return path


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path,
                        default=ROOT / "out/tree-default-regression")
    args = parser.parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    scene, camera, wood, foliage, ink = scene_setup()
    manifest = {"seed": SEED, "lod": "low", "camera": "orthographic",
                "neutralReviewControls": NEUTRAL_NEW_CONTROLS,
                "presets": [], "renders": [],
                "note": "prechange is a review reconstruction, not a runtime compatibility path"}
    for name in trees.PRESETS:
        pre = trees.generate(trees.preset(name, seed=SEED, **NEUTRAL_NEW_CONTROLS), "authoring")
        post = trees.generate(trees.preset(name, seed=SEED), "authoring")
        pair = build_pair(name, wood, foliage, ink)
        entry = {
            "name": name,
            "changed": pre.segments != post.segments or pre.foliage_indices != post.foliage_indices,
            "changedSegmentCount": sum(a != b for a, b in zip(pre.segments, post.segments)),
            "preSegments": len(pre.segments), "postSegments": len(post.segments),
            "preCarriers": len(pre.foliage_carriers), "postCarriers": len(post.foliage_carriers),
        }
        for view in ("front", "oblique"):
            manifest["renders"].append(str(render_pair(
                scene, camera, pair, args.output_dir, name, view).resolve()))
        manifest["presets"].append(entry)
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                                    encoding="utf-8")
    print("TREE DEFAULT REGRESSION OK")
    print(json.dumps(manifest["presets"], indent=2))


if __name__ == "__main__":
    main()
