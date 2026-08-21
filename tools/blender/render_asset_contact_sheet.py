"""Render a small 3D contact sheet of the sourced candidates used by the gauntlet."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = ROOT / "projects" / "hichaukitoden-game" / "assets" / "experimental" / "second-gate-human-assets"
KAY = OUT_ROOT / "sources" / "kaykit-medieval-hexagon" / "addons" / "kaykit_medieval_hexagon_pack" / "Assets" / "gltf"
PH = OUT_ROOT / "sources" / "polyhaven"


ASSETS = [
    ("KayKit / market", KAY / "buildings/blue/building_market_blue.gltf"),
    ("KayKit / tavern", KAY / "buildings/blue/building_tavern_blue.gltf"),
    ("KayKit / chapel", KAY / "buildings/blue/building_church_blue.gltf"),
    ("KayKit / stone gate", KAY / "buildings/neutral/fence_stone_straight_gate.gltf"),
    ("KayKit / bridge", KAY / "buildings/neutral/building_bridge_A.gltf"),
    ("KayKit / wheelbarrow", KAY / "decoration/props/wheelbarrow.gltf"),
    ("KayKit / crate", KAY / "decoration/props/crate_A_big.gltf"),
    ("Poly Haven / street lamp", PH / "street_lamp_01/street_lamp_01_1k.gltf"),
    ("Poly Haven / wine barrel", PH / "wine_barrel_01/wine_barrel_01_1k.gltf"),
    ("Poly Haven / lantern", PH / "wooden_lantern_01/wooden_lantern_01_1k.gltf"),
]


def link_only(obj, target):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    target.objects.link(obj)


def look_at(obj, point):
    obj.rotation_euler = (Vector(point) - obj.location).to_track_quat("-Z", "Y").to_euler()


def add_label(text, location, camera, collection):
    data = bpy.data.curves.new(f"Label_{text}", "FONT")
    data.body = text
    data.align_x = "CENTER"
    data.size = 0.34
    data.extrude = 0.008
    obj = bpy.data.objects.new(f"Label_{text}", data)
    collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector(camera.location) - obj.location).to_track_quat("Z", "Y").to_euler()
    mat = bpy.data.materials.new(f"LabelMat_{text}")
    mat.diffuse_color = (0.95, 0.8, 0.46, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.95, 0.52, 0.18, 1.0)
    bsdf.inputs["Emission Color"].default_value = (0.95, 0.23, 0.04, 1.0)
    bsdf.inputs["Emission Strength"].default_value = 0.7
    data.materials.append(mat)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]
    args = parser.parse_args(argv)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new("ContactWorld")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.025, 0.035, 0.055, 1.0)
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.35
    col = bpy.data.collections.new("SOURCED_CANDIDATES")
    scene.collection.children.link(col)
    ground_mat = bpy.data.materials.new("ContactGround")
    ground_mat.diffuse_color = (0.10, 0.08, 0.07, 1.0)
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, -0.05))
    ground = bpy.context.object
    ground.data.materials.append(ground_mat)
    link_only(ground, col)

    camera_data = bpy.data.cameras.new("ContactCamera")
    camera = bpy.data.objects.new("ContactCamera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = (13.5, -17.5, 13.0)
    look_at(camera, (0, 0, 1.2))
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 17.5
    scene.camera = camera

    for index, (label, path) in enumerate(ASSETS):
        if not path.is_file():
            raise FileNotFoundError(path)
        before = set(bpy.data.objects)
        bpy.ops.object.select_all(action="DESELECT")
        bpy.ops.import_scene.gltf(filepath=str(path))
        meshes = [o for o in bpy.context.selected_objects if o.type == "MESH" and o not in before]
        if not meshes:
            raise RuntimeError(f"no mesh imported from {path}")
        # Normalize each candidate to a comparable display height while
        # retaining the original sourced geometry and materials.
        bounds = []
        for obj in meshes:
            for corner in obj.bound_box:
                bounds.append(obj.matrix_world @ Vector(corner))
        min_z = min(v.z for v in bounds)
        max_z = max(v.z for v in bounds)
        height = max(0.01, max_z - min_z)
        scale = 2.25 / height
        col_idx = index % 5
        row_idx = index // 5
        location = Vector((-6.4 + col_idx * 3.2, 3.2 - row_idx * 5.3, 0.0))
        for obj in meshes:
            link_only(obj, col)
            obj.scale = Vector((scale, scale, scale))
            obj.location = location
        add_label(label, location + Vector((0.0, 0.0, 0.08)), camera, col)

    def add_area(name, location, energy, size, color):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        data.color = color
        light = bpy.data.objects.new(name, data)
        scene.collection.objects.link(light)
        light.location = location
        look_at(light, (0, 0, 0))

    add_area("Key", (-4, -8, 14), 1350, 8, (1.0, 0.62, 0.38))
    add_area("Fill", (8, 7, 11), 1150, 10, (0.35, 0.52, 1.0))
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 600
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(args.output.resolve())
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
