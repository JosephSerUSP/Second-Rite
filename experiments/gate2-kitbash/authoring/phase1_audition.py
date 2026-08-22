"""Render downloaded human-made kitbash candidates through the #881 camera."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[3]
AUTH = Path(__file__).resolve().parent
SOURCE = ROOT / "experiments" / "gate2-kitbash" / "source-assets"
OUT = ROOT / "experiments" / "gate2-kitbash" / "evidence" / "phase1"
PIPELINE = Path(r"C:\Users\josep\.codex\worktrees\d2fb\Hichaukitoden\tools\blender")
WALKER = ROOT / "experiments" / "gate2-kitbash" / "authoring" / "walker.png"

sys.path.insert(0, str(PIPELINE))
import second_gate_render  # noqa: E402
import thestra_camera  # noqa: E402


def _material(name: str, color: tuple[float, float, float, float], roughness=0.78):
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = roughness
    return material


def _reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.film_transparent = False
    scene.world = bpy.data.worlds.new("AUDITION_WORLD")
    scene.world.color = (0.025, 0.035, 0.055)
    return scene


def _add_floor(scene):
    bpy.ops.mesh.primitive_plane_add(size=60.0, location=(0.0, 20.0, -0.02))
    floor = bpy.context.object
    floor.name = "AUDITION_GROUND"
    floor.data.materials.append(_material("AUDITION_GROUND_MAT", (0.09, 0.105, 0.12, 1.0)))
    bevel = floor.modifiers.new("small_edge_softening", "BEVEL")
    bevel.width = 0.015
    bevel.segments = 1


def _add_lighting(scene):
    world = scene.world or bpy.data.worlds.new("AUDITION_WORLD")
    scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputWorld")
    background = nodes.new("ShaderNodeBackground")
    background.inputs["Strength"].default_value = 0.35
    hdr = SOURCE / "polyhaven" / "courtyard_night_1k.hdr"
    image = bpy.data.images.load(str(hdr), check_existing=True)
    env = nodes.new("ShaderNodeTexEnvironment")
    env.image = image
    links.new(env.outputs["Color"], background.inputs["Color"])
    links.new(background.outputs["Background"], output.inputs["Surface"])

    data = bpy.data.lights.new("AUDITION_KEY", type="AREA")
    data.energy = 900.0
    data.shape = "RECTANGLE"
    data.size = 7.0
    data.color = (1.0, 0.75, 0.55)
    key = bpy.data.objects.new("AUDITION_KEY", data)
    scene.collection.objects.link(key)
    key.location = (5.0, 10.0, 14.0)
    key.rotation_euler = (math.radians(25.0), 0.0, math.radians(20.0))

    fill_data = bpy.data.lights.new("AUDITION_FILL", type="AREA")
    fill_data.energy = 500.0
    fill_data.size = 10.0
    fill_data.color = (0.35, 0.45, 1.0)
    fill = bpy.data.objects.new("AUDITION_FILL", fill_data)
    scene.collection.objects.link(fill)
    fill.location = (-8.0, 24.0, 8.0)
    fill.rotation_euler = (math.radians(65.0), 0.0, math.radians(180.0))


def _import_obj(path: Path):
    before = set(bpy.data.objects)
    if hasattr(bpy.ops.wm, "obj_import"):
        bpy.ops.wm.obj_import(filepath=str(path))
    else:
        bpy.ops.import_scene.obj(filepath=str(path))
    imported = [obj for obj in bpy.data.objects if obj not in before]
    if not imported:
        raise RuntimeError(f"OBJ import created no objects: {path}")
    return imported


def _bounds(objects):
    points = []
    for obj in objects:
        if obj.type != "MESH":
            continue
        points.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
    if not points:
        raise RuntimeError("candidate has no mesh bounds")
    lo = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    hi = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return lo, hi


def _place_candidate(path: Path, *, y: float, x: float, max_height=2.15):
    objects = _import_obj(path)
    lo, hi = _bounds(objects)
    height = max(hi.z - lo.z, 0.001)
    scale = max_height / height
    for obj in objects:
        obj.scale *= scale
    lo, hi = _bounds(objects)
    centre = (lo + hi) * 0.5
    for obj in objects:
        obj.location.x += x - centre.x
        obj.location.y += y - centre.y
        obj.location.z += -lo.z
    return objects


def _add_walker(scene, camera, y=16.0, x=0.0):
    return thestra_camera.create_actor_preview(
        WALKER,
        camera,
        anchor=(x, y, 0.0),
        frame_width=24,
        frame_height=48,
        frame_index=0,
        world_height=1.75,
        name="TH_WALKER_PREVIEW",
    )


def _write_manifest(groups):
    manifest = {
        "camera": "authoring/calibrated-camera.json",
        "profile": "cycles-draft",
        "native": [426, 240],
        "groups": groups,
        "pipeline": "PR #881 worktree d6de8558, read-only tooling path",
        "walker": "projects/hichaukitoden-game/assets/character/walker.png",
    }
    (OUT / "phase1-audition.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


GROUPS = [
    [
        ("city-builder-bits-1.0", "building_A.obj"),
        ("city-builder-bits-1.0", "building_C.obj"),
        ("city-builder-bits-1.0", "building_H.obj"),
        ("city-builder-bits-1.0", "watertower.obj"),
    ],
    [
        ("medieval-hexagon-pack-1.0", "building_destroyed.obj"),
        ("medieval-hexagon-pack-1.0", "building_tavern_red.obj"),
        ("medieval-hexagon-pack-1.0", "building_blacksmith_blue.obj"),
        ("medieval-hexagon-pack-1.0", "wall_straight_gate.obj"),
    ],
    [
        ("dungeon-remastered-1.0", "wall_doorway.obj"),
        ("dungeon-remastered-1.0", "wall_archedwindow_open.obj"),
        ("dungeon-remastered-1.0", "stairs_wide.obj"),
        ("dungeon-remastered-1.0", "barrel_large_decorated.obj"),
    ],
    [
        ("city-builder-bits-1.0", "streetlight.obj"),
        ("medieval-hexagon-pack-1.0", "wall_corner_A_gate.obj"),
        ("dungeon-remastered-1.0", "banner_patternA_red.obj"),
        ("dungeon-remastered-1.0", "crates_stacked.obj"),
    ],
]


def render_group(index: int, candidates):
    scene = _reset()
    camera_record = thestra_camera.load_calibration(AUTH / "calibrated-camera.json")
    camera = thestra_camera.create_or_update_camera(camera_record, scene=scene, name="TH_CAMERA_PREVIEW")
    _add_floor(scene)
    _add_lighting(scene)
    group_rows = []
    xs = (-4.0, -1.35, 1.35, 4.0)
    for (pack, filename), x in zip(candidates, xs):
        path = SOURCE / pack / filename
        if not path.exists():
            raise FileNotFoundError(path)
        _place_candidate(path, x=x, y=17.5)
        group_rows.append({"pack": pack, "file": filename, "local": str(path.relative_to(ROOT))})
    _add_walker(scene, camera, y=16.0, x=0.0)
    scene.render.filepath = str(OUT / f"candidate-group-{index:02d}.png")
    second_gate_render.apply(scene, "cycles-draft")
    scene.render.filepath = str(OUT / f"candidate-group-{index:02d}.png")
    bpy.ops.render.render(write_still=True)
    return group_rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for index, candidates in enumerate(GROUPS, 1):
        rows.extend(render_group(index, candidates))
    _write_manifest(rows)
    print("PHASE1 AUDITION OK")


if __name__ == "__main__":
    main()
