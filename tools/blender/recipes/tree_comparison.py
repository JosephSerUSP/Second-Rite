"""Render a fixed-camera comparison of the tree vocabulary.

This is disposable review evidence, not a shipping scene.  Every specimen
uses the same seed, preset, LOD, ground, actor scale and camera; only the
declared authoring controls differ.  It emits material and clay contact
views plus a second oblique angle so silhouette changes are inspectable.

Run with Blender:
    blender -b --factory-startup -P tools/blender/recipes/tree_comparison.py \
        -- --output-dir out/tree-comparison
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))
from tree_generator import generate, preset, reduce_lod, validate  # noqa: E402
import tree_material  # noqa: E402
import tree_mesh  # noqa: E402


VARIANTS = (
    ("baseline", {}),
    ("crown_bias_only", {
        "crown_bias": .65, "crown_bias_deg": 25,
    }),
    ("branch_sweep_only", {
        "branch_sweep_deg": 48,
    }),
    ("branch_twist_only", {
        "branch_twist_deg": 110,
    }),
    ("biased_twist", {
        "crown_bias": .65, "crown_bias_deg": 25, "branch_twist_deg": 110,
    }),
    ("rising_vase", {
        "branch_sweep_deg": 48, "apical_dominance": .85,
    }),
    ("guided_spread", {
        "crown_bias": .45, "crown_bias_deg": 145, "attraction_weight": 1.0,
        "influence_radius": 3.0, "kill_radius": .1, "stems": 3,
    }),
)
SEED = 17
def material(name, colour, roughness=.9):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*colour, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*colour, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def mesh_object(name, vertices, faces, material_data, uvs=None):
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata([list(v) for v in vertices], [], [list(f) for f in faces])
    mesh.update()
    if uvs:
        uv = mesh.uv_layers.new(name="UVMap")
        for loop, coord in enumerate(uvs):
            uv.data[loop].uv = coord
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    mesh.materials.append(material_data)
    return obj


def add_actor(x, actor_material, skin_material, y=-2.0):
    """Add a deliberately plain 1.75m scale reference figure."""
    for leg_x in (x - .11, x + .11):
        bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=.085, depth=.72,
                                            location=(leg_x, y, .36))
        bpy.context.object.name = "SCALE_ACTOR_LEG"
        bpy.context.object.data.materials.append(actor_material)
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=.22, depth=.85,
                                        location=(x, y, 1.0))
    body = bpy.context.object
    body.name = "SCALE_ACTOR_BODY"
    body.data.materials.append(actor_material)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6, radius=.23,
                                         location=(x, y, 1.52))
    head = bpy.context.object
    head.name = "SCALE_ACTOR_HEAD"
    head.data.materials.append(skin_material)
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=.10, depth=.72,
                                        location=(x - .28, y, .64),
                                        rotation=(0.0, math.pi / 2, 0.0))
    arm = bpy.context.object
    arm.name = "SCALE_ACTOR_ARM"
    arm.data.materials.append(actor_material)


def label(text, x, label_material):
    bpy.ops.object.text_add(location=(x, -2.0, .08), rotation=(math.pi / 2, 0, 0))
    obj = bpy.context.object
    obj.name = "LABEL_" + text
    obj.data.body = text.replace("_", " ")
    obj.data.align_x = "CENTER"
    obj.data.size = .22
    obj.data.extrude = .002
    obj.data.materials.append(label_material)
    return obj


def look_at(camera, target):
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()


def setup_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False

    world = bpy.data.worlds.new("TREE_COMPARISON_WORLD")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (.035, .05, .07, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = .45

    ground = material("comparison_ground", (.17, .20, .16))
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
    bpy.context.object.name = "COMPARISON_GROUND"
    bpy.context.object.data.materials.append(ground)
    bpy.ops.object.light_add(type="AREA", location=(-5, -8, 11))
    key = bpy.context.object
    key.name = "COMPARISON_KEY"
    key.data.energy = 1100
    key.data.size = 8
    look_at(key, (0, 0, 2.4))

    camera_data = bpy.data.cameras.new("COMPARISON_CAMERA")
    camera = bpy.data.objects.new("COMPARISON_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 11.5

    wood = material("comparison_wood", (.25, .12, .055))
    foliage = tree_material.foliage_material(name="comparison_foliage")
    clay = material("comparison_clay", (.42, .45, .48))
    actor = material("comparison_actor", (.12, .22, .46))
    skin = material("comparison_skin", (.62, .35, .20))
    ink = material("comparison_ink", (.82, .86, .88))
    add_actor(-3.0, actor, skin)

    tree_objects = {}
    manifest = {"seed": SEED, "lod": "low", "camera": "orthographic",
                "variants": [], "notes": [
                    "Review evidence only; not a shipping scene.",
                    "All variants share the same round_shade preset and seed.",
                    "The actor is a plain 1.75m scale reference.",
                ]}
    for name, overrides in VARIANTS:
        spec = preset("round_shade", seed=SEED, **overrides)
        full = generate(spec, "authoring")
        validate(full)
        skeleton = reduce_lod(full, "low")
        validate(skeleton, "low")
        branches = mesh_object(name + "_BRANCHES", *tree_mesh.branch_mesh(skeleton), wood)
        card_vertices, card_faces, card_uvs = tree_mesh.foliage_mesh(skeleton, lod="low")
        cards = mesh_object(name + "_CARDS", card_vertices, card_faces, foliage, card_uvs)
        for polygon in branches.data.polygons:
            polygon.use_smooth = True
        label_object = label(name, 0.0, ink)
        tree_objects[name] = (branches, cards, label_object)
        manifest["variants"].append({
            "name": name, "overrides": overrides, "segments": len(skeleton.segments),
            "carriers": len(skeleton.foliage_carriers),
        })

    return scene, camera, tree_objects, clay, manifest


def render(scene, camera, tree_objects, clay, output_dir, variant, mode, view):
    selected = set(tree_objects[variant])
    for objects in tree_objects.values():
        for obj in objects:
            obj.hide_render = obj not in selected
    for obj in selected:
        if mode == "clay":
            obj.data.materials.clear()
            obj.data.materials.append(clay)
    if view == "front":
        camera.location = (0, -22, 4.0)
        look_at(camera, (0, 0, 3.0))
    else:
        camera.location = (12.5, -24, 8.5)
        look_at(camera, (0, 0, 3.0))
    path = output_dir / f"tree-{variant}-{mode}-{view}.png"
    scene.render.filepath = str(path.resolve())
    bpy.ops.render.render(write_still=True)
    return path


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT / "out/tree-comparison")
    args = parser.parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    scene, camera, tree_objects, clay, manifest = setup_scene()
    paths = []
    for variant, _overrides in VARIANTS:
        for mode in ("material", "clay"):
            for view in ("front", "oblique"):
                paths.append(str(render(scene, camera, tree_objects, clay,
                                        args.output_dir, variant, mode, view).resolve()))
    manifest["renders"] = paths
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                                    encoding="utf-8")
    print("TREE COMPARISON OK")
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
