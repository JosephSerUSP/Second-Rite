"""Disposable, bridge-driven tree laboratory.

This file is deliberately not an exterior source recipe.  It builds a marked
study document that can be regenerated safely while the owner orbits around
the trees in a separate Blender window.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/blender"))
sys.path.insert(0, str(ROOT / "tools/blender/recipes"))
from exterior import Exterior  # noqa: E402
import thestra_camera  # noqa: E402
from tree_generator import PRESETS, generate, preset, reduce_lod, validate  # noqa: E402
import tree_material  # noqa: E402
import tree_mesh  # noqa: E402


def _branch_mesh(name, skeleton, origin, material, collection):
    """Build one genuinely connected branch graph.

    The former builder emitted a capped cone for every segment.  Coincident
    endpoints are not topology, so the caps and unrelated ring orientations
    made the result read as a pile of funnels.  Blender's Skin modifier is a
    good fit here: skeleton nodes become shared vertices, parent links become
    edges, and forks receive one manifold junction before conversion.
    """
    verts, edges = [], []
    ox, oy, oz = origin
    node_for_segment = {}
    root_node = None
    for segment in skeleton.segments:
        if segment.parent is None:
            root_node = len(verts)
            verts.append((segment.start[0] + ox, segment.start[1] + oy, segment.start[2] + oz))
            start_node = root_node
        else:
            start_node = node_for_segment[segment.parent]
        end_node = len(verts)
        verts.append((segment.end[0] + ox, segment.end[1] + oy, segment.end[2] + oz))
        edges.append((start_node, end_node)); node_for_segment[segment.index] = end_node
    mesh = bpy.data.meshes.new(name + "_mesh"); mesh.from_pydata(verts, edges, []); mesh.update()
    obj = bpy.data.objects.new(name, mesh); collection.objects.link(obj); obj.data.materials.append(material)
    skin = obj.modifiers.new("Connected branch skin", "SKIN")
    bpy.context.view_layer.objects.active = obj; obj.select_set(True)
    bpy.context.view_layer.update()
    radii = mesh.skin_vertices[0].data
    if root_node is not None:
        root_radius = skeleton.segments[0].radius
        radii[root_node].radius = (root_radius, root_radius)
    for segment in skeleton.segments:
        radius = max(.018, segment.radius * (.78 if segment.foliage else .9))
        radii[node_for_segment[segment.index]].radius = (radius, radius)
    bpy.ops.object.modifier_apply(modifier=skin.name)
    # Keep Skin's compact, graph-derived topology.  Whole-object remeshing is
    # deliberately forbidden here: it spends polygons on every straight run
    # and erases the authored relationship between skeleton and surface.
    # Junction improvements must remain local and topology-aware.
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    obj.select_set(False)
    return obj


def _foliage_material():
    return tree_material.foliage_material()


def _foliage_mesh(name, skeleton, origin, material, collection, lod):
    """Build the lab's cards from the shared mesher.

    The lab previously carried its own copy of this maths.  A lab that meshes
    foliage differently from the placement path approves specimens nobody can
    place, so the geometry now has exactly one definition.
    """
    verts, faces, uvs = tree_mesh.foliage_mesh(skeleton, lod=lod, origin=origin)
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata([list(v) for v in verts], [], [list(f) for f in faces])
    mesh.update()
    uv = mesh.uv_layers.new(name="UVMap")
    for loop, coord in enumerate(uvs):
        uv.data[loop].uv = coord
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def build_generation(exterior, collection, generation=0, preset_names=None,
                     seed_offset=0, overrides=None):
    """Append one disposable generation to an existing marked lab scene."""
    # Static lab dressing must survive generation toggles.  Early lab files
    # placed the ground in generation zero, so repair that layout in place.
    scene = bpy.context.scene
    epochs = bpy.data.collections.get("TREE_LAB_EPOCHS")
    if epochs is None:
        epochs = bpy.data.collections.new("TREE_LAB_EPOCHS")
        scene.collection.children.link(epochs)
    # Retrofit earlier flat lab files into one obvious hierarchy.
    for epoch in [c for c in bpy.data.collections if re.fullmatch(r"TREE_LAB_GEN_\d{3}", c.name)]:
        if epochs.children.get(epoch.name) is None:
            epochs.children.link(epoch)
        if scene.collection.children.get(epoch.name) is not None:
            scene.collection.children.unlink(epoch)
    for child in [c for c in bpy.data.collections
                  if re.fullmatch(r"TREE_LAB_GEN_\d{3}_(AUTHORING|LOW)", c.name)]:
        if epochs.children.get(child.name) is not None:
            epochs.children.unlink(child)
    ground = bpy.data.objects.get("TREE_LAB_GROUND")
    if ground is not None:
        static = bpy.data.collections.get("TREE_LAB_STATIC")
        if static is None:
            static = bpy.data.collections.new("TREE_LAB_STATIC")
            scene.collection.children.link(static)
        for old in list(ground.users_collection):
            old.objects.unlink(ground)
        static.objects.link(ground); static.hide_viewport = False; static.hide_render = False
    names = list(preset_names or PRESETS)
    unknown = [name for name in names if name not in PRESETS]
    if unknown: raise ValueError("unknown tree preset(s): " + ", ".join(unknown))
    overrides = overrides or {}; foliage = _foliage_material(); stats = []
    # Visual approval now targets the low LOD.  The full skeleton is still
    # generated as the semantic source, but building a second near-identical
    # mesh crowds each bay and makes the disposable lab unnecessarily heavy.
    low_collection = bpy.data.collections.get(collection.name + "_LOW")
    if low_collection is None:
        low_collection = bpy.data.collections.new(collection.name + "_LOW")
        collection.children.link(low_collection)
    specs = []
    for name in names:
        spec_overrides = {key: value for key, value in overrides.items() if key == name or key.startswith(name + ".")}
        spec_overrides = {key.split(".", 1)[1] if "." in key else key: value for key, value in spec_overrides.items()}
        specs.append(preset(name, seed_offset=seed_offset, **spec_overrides))
    # Preset bays are separated by their authored crown envelopes, not by an
    # arbitrary lane interval.  Adjacent silhouettes therefore cannot invade
    # one another even when broad and narrow morphologies alternate.
    centres = [0.0]
    for previous, current in zip(specs, specs[1:]):
        centres.append(centres[-1] - previous.crown_radius - current.crown_radius - 1.25)
    midpoint = (centres[0] + centres[-1]) * .5
    centres = [value - midpoint for value in centres]
    ground = bpy.data.objects.get("TREE_LAB_GROUND")
    if ground is not None:
        ground.scale.y = max(ground.scale.y, 1.35)
    for centre_y, spec in zip(centres, specs):
        name = spec.name
        full = generate(spec, "authoring"); validate(full)
        lod = "low"; skeleton = reduce_lod(full, lod); validate(skeleton, lod)
        origin = (4.6, centre_y, 0.0)
        root = bpy.data.objects.new("TREE_LAB_G%03d_%s_%s_ROOT" % (generation, name, lod), None)
        low_collection.objects.link(root); root.location = origin
        root["treePreset"] = name; root["treeLOD"] = lod; root["treeSegments"] = len(skeleton.segments); root["treeCards"] = len(skeleton.foliage_indices)
        branch = _branch_mesh("TREE_LAB_G%03d_%s_%s_BRANCHES" % (generation, name, lod), skeleton, (0,0,0), exterior.wood, low_collection); branch.parent = root
        cards = _foliage_mesh("TREE_LAB_G%03d_%s_%s_CARDS" % (generation, name, lod), skeleton, (0,0,0), foliage, low_collection, lod); cards.parent = root
        stats.append({"preset": name, "lod": lod, "segments": len(skeleton.segments), "cards": len(skeleton.foliage_indices)})
    return stats


def build(output: Path, render: Path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    exterior = Exterior("TREE_LAB", 12.0, back_x=8.0, near_x=-4.0)
    scene = bpy.context.scene; scene["thestra_tree_lab"] = 1; scene["tree_lab_generation"] = 0
    epochs = bpy.data.collections.new("TREE_LAB_EPOCHS"); scene.collection.children.link(epochs)
    lab = bpy.data.collections.new("TREE_LAB_GEN_000"); epochs.children.link(lab)
    bpy.ops.mesh.primitive_plane_add(size=32.0, location=(4.0, 6.0, 0.0))
    ground = bpy.context.object; ground.name = "TREE_LAB_GROUND"
    for old in list(ground.users_collection): old.objects.unlink(ground)
    static = bpy.data.collections.new("TREE_LAB_STATIC"); scene.collection.children.link(static)
    static.objects.link(ground); ground.data.materials.append(exterior.paving)
    build_generation(exterior, lab, generation=0)
    record = json.loads((ROOT / "tools/blender/fixtures/town_sideview_camera.json").read_text())
    camera = thestra_camera.create_or_update_camera(record, make_active=True)
    actor = thestra_camera.create_actor_preview(ROOT / "projects/hichaukitoden-game/assets/character/npc_alicia.png", camera, anchor=(0, exterior.y(6.0), 0), world_height=1.75, name="TREE_LAB_WALKER"); actor.hide_render = False
    world = bpy.data.worlds.new("Tree lab world"); scene.world = world; world.use_nodes = True; world.node_tree.nodes["Background"].inputs["Color"].default_value = (.07,.09,.12,1); world.node_tree.nodes["Background"].inputs["Strength"].default_value = .5
    bpy.ops.object.light_add(type="AREA", location=(-8, 0, 9)); key = bpy.context.object; key.name = "TREE_LAB_SKY"; key.data.energy = 1500; key.data.size = 14
    key.rotation_euler = (Vector((3, 0, 2)) - key.location).to_track_quat('-Z','Y').to_euler()
    scene.render.engine = "BLENDER_EEVEE"; scene.render.resolution_x = 512; scene.render.resolution_y = 320; scene.render.resolution_percentage = 100; scene.render.image_settings.file_format = "PNG"; scene.render.filepath = str(render.resolve())
    output.parent.mkdir(parents=True, exist_ok=True); render.parent.mkdir(parents=True, exist_ok=True); bpy.ops.wm.save_as_mainfile(filepath=str(output.resolve())); bpy.ops.render.render(write_still=True)
    print("TREE LAB OK", output, render)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, default=ROOT/"out/tree-lab/tree_lab.blend"); parser.add_argument("--render", type=Path, default=ROOT/"out/tree-lab/tree_lab.png"); args = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    build(args.output, args.render)


if __name__ == "__main__": main()
