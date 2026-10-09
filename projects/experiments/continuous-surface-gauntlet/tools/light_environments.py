"""Create new sources once, then bake adopted documents through the shared pipeline.

Run with tools/blender/run.py. --create-sources refuses existing documents.
Normal export never writes the source. Geometry uses the standard OBJ adapter;
walk surfaces and anchors are explicit Blender collections, not inferred meshes.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parents[2]
sys.path.insert(0, str(ROOT / "tools/blender"))
import export_room_environment as room
import town_environment_pipeline as pipeline


def material(name, color):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = (*color, 1)
    mat.node_tree.nodes.get("Principled BSDF").inputs["Roughness"].default_value = 0.85
    return mat


def import_mesh(path, collection):
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.wm.obj_import(filepath=str(path), forward_axis="NEGATIVE_Z", up_axis="Y")
    objects = list(bpy.context.selected_objects)
    for obj in objects:
        room.move(obj, collection)
    return objects


def polygon(collection, name, points, z):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([(x, y, z) for x, y in points], [], [list(range(len(points)))])
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)


def area(name, position, target, color, watts, size, collection):
    data = bpy.data.lights.new(name, "AREA")
    data.energy, data.color, data.shape, data.size = watts, color, "DISK", size
    obj = bpy.data.objects.new(name, data)
    collection.objects.link(obj)
    obj.location = position
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def create_source(name, source):
    if source.exists():
        raise RuntimeError(f"Source already exists; edit it directly: {source}")
    package = PROJECT / "assets/environments" / name
    manifest = json.loads((package / "environment.json").read_text())
    bpy.ops.wm.read_factory_settings(use_empty=True)
    beauty = room.collection("TH_SOURCE")
    meshes = import_mesh(package / "environment.obj", beauty)
    floor = material("Floor neutral warm", (0.32, 0.30, 0.26))
    wall = material("Walls neutral cool", (0.25, 0.30, 0.34))
    top = material("Obstacle tops", (0.40, 0.43, 0.42))
    for obj in meshes:
        obj.data.materials.clear()
        for mat in (floor, wall, top):
            obj.data.materials.append(mat)
        for face in obj.data.polygons:
            face.material_index = (0 if face.center.z < 0.05 else 2) if face.normal.z > 0.5 else 1
    import_mesh(package / "collision.obj", room.collection("TH_COLLISION"))
    for name_, anchor in manifest["anchors"].items():
        obj = bpy.data.objects.new(name_, None)
        obj.location = anchor["position"]
        room.collection("TH_ANCHORS").objects.link(obj)
    walk = manifest["walkSurface"]
    for kind, collection in (("regions", "TH_WALKABLE"), ("obstacles", "TH_OBSTACLES")):
        for i, shape in enumerate(walk[kind]):
            polygon(room.collection(collection), f"{kind}_{i}", shape["points"], walk["groundZ"])
    lights = room.collection("TH_LIGHTS")
    area("Warm key", (1.8, -1.5, 3.0), (0.2, -0.7, 0), (1.0, 0.78, 0.51), 420, 1.1, lights)
    area("Cool fill", (-1.5, 1.8, 2.8), (1.1, 0.7, 0), (0.48, 0.69, 1.0), 240, 2.0, lights)
    world = bpy.data.worlds.new("Low ambient")
    bpy.context.scene.world = world
    world.use_nodes = True
    world.node_tree.nodes.get("Background").inputs[0].default_value = (0.18, 0.22, 0.28, 1)
    world.node_tree.nodes.get("Background").inputs[1].default_value = 0.22
    bpy.context.scene.view_settings.view_transform = "Standard"
    bpy.context.scene.view_settings.look = "None"
    room.build_render_mesh(beauty, name + "_TH_RENDER", 1, atlas_size=512)
    source.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(source))


def main():
    global PROJECT
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=PROJECT)
    parser.add_argument("--create-sources", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    PROJECT = args.project.resolve()
    for name in ("archive_antechamber", "service_annex"):
        source = PROJECT / "assets/authoring/environments" / (name + ".blend")
        if args.create_sources:
            create_source(name, source)
        before = hashlib.sha256(source.read_bytes()).hexdigest()
        bpy.ops.wm.open_mainfile(filepath=str(source))
        pipeline.run_pipeline_in_blender(source, args.output / name, atlas_size=512,
                                         bake_samples=32, backend="cycles", cycles_device="CPU")
        assert hashlib.sha256(source.read_bytes()).hexdigest() == before, "Export changed source"
        path = args.output / name / "environment.json"
        manifest = json.loads(path.read_text())
        manifest["provenance"]["sourceSha256"] = before
        manifest["provenance"]["productsSha256"] = {
            name_: hashlib.sha256((path.parent / name_).read_bytes()).hexdigest()
            for name_ in ("environment.obj", "environment.mtl", "environment.png", "collision.obj")
        }
        path.write_text(json.dumps(manifest, indent=2) + "\n")
    print("GAUNTLET LIT ENVIRONMENTS OK")


if __name__ == "__main__":
    main()
