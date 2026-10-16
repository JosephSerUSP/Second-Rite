"""Adversarial collection-instance export test for authoritative item sources."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import second_rite_asset_core as core


def parse_obj(path: Path):
    vertices = []
    faces = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.startswith("v "):
            vertices.append(tuple(float(v) for v in raw.split()[1:4]))
        elif raw.startswith("f "):
            faces.append(raw)
    return vertices, faces


def main():
    core.reset_scene(factory=True)

    # Deliberately keep the instanced kit outside the item hierarchy. This is
    # how ordinary Blender collection instances are authored: the Empty under
    # the item root references a reusable collection datablock.
    kit = bpy.data.collections.new("StressInstanceKit")
    mesh = bpy.data.meshes.new("StressInstanceCubeMesh")
    mesh.from_pydata(
        [(-0.5, -0.5, -0.5), (0.5, -0.5, -0.5), (0.5, 0.5, -0.5), (-0.5, 0.5, -0.5),
         (-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5)],
        [],
        [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2),
         (2, 6, 7, 3), (4, 0, 3, 7)],
    )
    cube = bpy.data.objects.new("StressInstanceCube", mesh)
    kit.objects.link(cube)
    core.assign_material(cube, core.make_material("StressInstanceGold", semantic_id="ritual_gold"))

    root = bpy.data.objects.new("StressInstanceRoot", None)
    bpy.context.scene.collection.objects.link(root)
    root.location = (8.0, -3.0, 2.0)
    root["item_export"] = True
    root["item_export_name"] = "instance_stress_fixture"
    root["sr_source_authority"] = "blend"
    core.tag_asset_target(
        root,
        asset_id="instance_stress_fixture",
        representation="full_model",
        role="item_display",
        authoring_space="item_display",
        placement_frame="item_viewport",
    )

    instance = bpy.data.objects.new("StressCollectionInstance", None)
    bpy.context.scene.collection.objects.link(instance)
    core.parent_local(instance, root, loc=(1.25, 0.0, 0.0), scale=(0.8, 1.1, 0.6))
    instance.instance_type = "COLLECTION"
    instance.instance_collection = kit

    # Establish an evaluated baseline before the exporter performs its own
    # defensive view-layer synchronization. A dependency-graph refresh is not
    # an authoritative transform mutation.
    bpy.context.view_layer.update()
    source_object_count = len(bpy.data.objects)
    source_collection_count = len(bpy.data.collections)
    original_collection = instance.instance_collection
    original_transform = instance.matrix_world.copy()

    with tempfile.TemporaryDirectory(prefix="item-instance-stress-") as directory:
        outputs = core.export_asset_root(bpy.context, root, Path(directory), center_mode="PIVOT")
        assert len(outputs) == 1
        output = Path(outputs[0])
        assert output.is_file()
        vertices, faces = parse_obj(output)
        assert len(vertices) >= 8, f"instance produced too few vertices: {len(vertices)}"
        assert len(faces) >= 6, f"instance produced too few faces: {len(faces)}"
        xs = [v[0] for v in vertices]
        # X is unchanged by the OBJ axis conversion. The root is recentered,
        # while the instance's +1.25 local offset and 0.8 X scale survive.
        assert min(xs) < 1.0 < max(xs), (min(xs), max(xs))
        assert 0.75 < min(xs) < 0.95, min(xs)
        assert 1.55 < max(xs) < 1.75, max(xs)

    # Realization belongs entirely to the temporary export graph.
    assert instance.instance_collection is original_collection
    assert instance.matrix_world == original_transform
    assert len(bpy.data.objects) == source_object_count, (source_object_count, len(bpy.data.objects))
    assert len(bpy.data.collections) == source_collection_count
    assert bpy.data.collections.get("__SECOND_RITE_ITEM_EXPORT_TEMP__") is None
    print("ITEM COLLECTION INSTANCE EXPORT STRESS OK")


if __name__ == "__main__":
    main()
