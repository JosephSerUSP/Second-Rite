"""Compose a real, source-derived background topology for the Cortico pilot.

This is deliberately not a silhouette generator. The pilot source already
contains authored lodging, padaria, shrine and facade modules. This recipe
duplicates those complete modules into a deeper, coherent town row, preserving
their meshes, roofs, openings, materials and authored proportions. The result
is a Blender-only candidate until an owner explicitly imports it under
TH_SOURCE and enables sr_export; the normal exterior exporter can then flatten
the real topology into the runtime package.

The adopted source is opened read-only and is never saved by this script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path


SCHEMA_VERSION = 2
LANE_MIN_Y = -2.844
LANE_CENTRE_Y = 12.031
LANE_MAX_Y = 26.906
STUDY_MARGIN_Y = 30.0
BACKGROUND_MIN_X = 22.0
BACKGROUND_MAX_X = 34.0
MAX_OPENING_Y = 5.0


# Each span is the measured visible Y footprint of the source module. The
# layout is intentionally legible as a row of real places, with small gaps for
# alleys/openings rather than a random collection of disconnected shapes.
DEFAULT_MODULES = (
    {
        "id": "east_end_facade",
        "selectors": ("CORTICO_east_facade",),
        "anchor": (17.0, -12.875, 0.0),
        "target": (28.0, -28.0, 0.0),
        "span": 5.12,
    },
    {
        "id": "padaria_west",
        "selectors": ("CORTICO_padaria_house_",),
        "anchor": (15.3, -2.964, 0.0),
        "target": (25.5, -21.5, 0.0),
        "span": 6.2,
    },
    {
        "id": "lodging_west",
        "selectors": ("CORTICO_lodging_house_",),
        "anchor": (16.0, -0.233, 0.0),
        "target": (24.5, -12.7, 0.0),
        "span": 8.6,
    },
    {
        "id": "shrine_west",
        "selectors": ("CORTICO_shrine_facade", "CORTICO_shrine_door_"),
        "anchor": (16.7, 6.531, 0.0),
        "target": (26.5, -5.8, 0.0),
        "span": 4.35,
    },
    {
        "id": "shrine_east",
        "selectors": ("CORTICO_shrine_facade", "CORTICO_shrine_door_"),
        "anchor": (16.7, 6.531, 0.0),
        "target": (26.5, 1.0, 0.0),
        "span": 4.35,
    },
    {
        "id": "lodging_east",
        "selectors": ("CORTICO_lodging_house_",),
        "anchor": (16.0, -0.233, 0.0),
        "target": (24.5, 9.0, 0.0),
        "span": 8.6,
    },
    {
        "id": "padaria_east",
        "selectors": ("CORTICO_padaria_house_",),
        "anchor": (15.3, -2.964, 0.0),
        "target": (25.5, 18.0, 0.0),
        "span": 6.2,
    },
    {
        "id": "west_end_facade",
        "selectors": ("CORTICO_west_facade",),
        "anchor": (16.9, 13.175, 0.0),
        "target": (28.0, 28.0, 0.0),
        "span": 4.95,
    },
)


def lane_to_blender_y(lane_y, lane_centre=LANE_CENTRE_Y):
    """Apply the adopted source's explicit runtime lane mirror."""
    value = float(lane_y)
    if not math.isfinite(value):
        raise ValueError("lane_y must be finite")
    return float(lane_centre) - value


def coverage_bounds(module):
    """Return the authored world-Y footprint of one background module."""
    centre = float(module["target"][1])
    span = float(module["span"])
    return centre - span * 0.5, centre + span * 0.5


def validate_module(module):
    if not isinstance(module, dict):
        raise ValueError("background module must be an object")
    ident = str(module.get("id", ""))
    if not ident or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789_"
                        for ch in ident):
        raise ValueError("background module id must be lower snake case")
    selectors = module.get("selectors")
    if not selectors or not all(isinstance(item, str) and item for item in selectors):
        raise ValueError(f"{ident}: selectors are required")
    for field in ("anchor", "target"):
        point = module.get(field)
        if not isinstance(point, (tuple, list)) or len(point) != 3:
            raise ValueError(f"{ident}: {field} must be an xyz point")
        if not all(math.isfinite(float(value)) for value in point):
            raise ValueError(f"{ident}: {field} must be finite")
    if float(module.get("span", 0.0)) <= 0.0:
        raise ValueError(f"{ident}: span must be positive")
    x = float(module["target"][0])
    if x < BACKGROUND_MIN_X or x > BACKGROUND_MAX_X:
        raise ValueError(f"{ident}: target X is outside background depth")
    return True


def validate_modules(modules=DEFAULT_MODULES):
    if len(modules) < 5:
        raise ValueError("background needs a complete multi-building topology")
    for module in modules:
        validate_module(module)
    bounds = sorted(coverage_bounds(module) for module in modules)
    if bounds[0][0] > -STUDY_MARGIN_Y or bounds[-1][1] < STUDY_MARGIN_Y:
        raise ValueError("background topology does not overscan the study window")
    for left, right in zip(bounds, bounds[1:]):
        if right[0] - left[1] > MAX_OPENING_Y:
            raise ValueError("background row contains an unreasonably large opening")
    return True


def _candidate_collection():
    import bpy

    collection = bpy.data.collections.get("BACKGROUND_TOPOLOGY_CANDIDATE")
    if collection is None:
        collection = bpy.data.collections.new("BACKGROUND_TOPOLOGY_CANDIDATE")
    if collection.name not in {child.name for child in bpy.context.scene.collection.children}:
        bpy.context.scene.collection.children.link(collection)
    return collection


def _source_meshes(selectors):
    import bpy

    return sorted(
        [obj for obj in bpy.context.scene.objects
         if obj.type == "MESH"
         and any(obj.name.startswith(selector) for selector in selectors)],
        key=lambda obj: obj.name,
    )


def _copy_module(module, collection, index):
    import bpy
    from mathutils import Matrix, Vector

    source_objects = _source_meshes(module["selectors"])
    if not source_objects:
        selectors = ", ".join(module["selectors"])
        raise RuntimeError(f"source module {module['id']} has no mesh objects: {selectors}")
    anchor = Matrix.Translation(Vector(module["anchor"]))
    target = Matrix.Translation(Vector(module["target"]))
    root = bpy.data.objects.new(
        f"CORTICO_BG_{index:02d}_{module['id'].upper()}_ROOT", None)
    collection.objects.link(root)
    root.empty_display_type = "PLAIN_AXES"
    root.location = tuple(float(value) for value in module["target"])
    root["sr_export"] = False
    root["sr_preview_only"] = True
    root["sr_noninteractive"] = True
    root["sr_background_topology"] = True
    root["sr_flatten_via_exterior_exporter"] = True
    root["sr_source_module"] = module["id"]
    for source in source_objects:
        copy = source.copy()
        copy.data = source.data.copy()
        copy.name = f"CORTICO_BG_{index:02d}_{source.name}"
        collection.objects.link(copy)
        copy.parent = root
        relative = anchor.inverted() @ source.matrix_world
        copy.matrix_world = target @ relative
        copy.hide_render = False
        copy.hide_viewport = False
        copy["sr_export"] = False
        copy["sr_preview_only"] = True
        copy["sr_noninteractive"] = True
        copy["sr_background_topology"] = True
        copy["sr_flatten_via_exterior_exporter"] = True
        copy["sr_source_module"] = module["id"]
        copy["sr_source_object"] = source.name
        copy["sr_representation"] = "full_model"
    return root, source_objects


def _copy_ground(collection):
    """Extend the actual source ground with one grounded 3D slab."""
    import bpy

    source = bpy.data.objects.get("CORTICO_ground")
    if source is None or source.type != "MESH":
        raise RuntimeError("adopted source is missing CORTICO_ground")
    x0, x1 = 21.0, 38.0
    y0, y1 = -32.0, 32.0
    z0, z1 = -0.6, 0.0
    vertices = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    faces = ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5),
             (2, 3, 7, 6), (3, 0, 4, 7))
    mesh = bpy.data.meshes.new("CORTICO_BACKGROUND_GROUND_MESH")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new("CORTICO_BACKGROUND_GROUND", mesh)
    collection.objects.link(obj)
    for material in source.data.materials:
        mesh.materials.append(material)
    obj["sr_export"] = False
    obj["sr_preview_only"] = True
    obj["sr_noninteractive"] = True
    obj["sr_background_topology"] = True
    obj["sr_flatten_via_exterior_exporter"] = True
    obj["sr_source_object"] = source.name
    obj["sr_ground"] = True
    return obj


def _source_material(names):
    import bpy

    for name in names:
        material = bpy.data.materials.get(name)
        if material is not None:
            return material
    raise RuntimeError(f"adopted source is missing material family: {names}")


def _topology_tag(obj, source_name):
    obj["sr_export"] = False
    obj["sr_preview_only"] = True
    obj["sr_noninteractive"] = True
    obj["sr_background_topology"] = True
    obj["sr_flatten_via_exterior_exporter"] = True
    obj["sr_source_object"] = source_name
    obj["sr_representation"] = "full_model"


def _connector_wall(collection, index, y0, y1):
    import bpy

    x0, x1 = 27.25, 31.0
    z0, z1 = 0.0, 4.65
    vertices = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    faces = ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5),
             (2, 3, 7, 6), (3, 0, 4, 7))
    mesh = bpy.data.meshes.new(f"CORTICO_BACKGROUND_CONNECTOR_{index:02d}_MESH")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(f"CORTICO_BACKGROUND_CONNECTOR_{index:02d}", mesh)
    collection.objects.link(obj)
    mesh.materials.append(_source_material(("sr_old_limestone", "sr_rough_limestone")))
    _topology_tag(obj, "source_derived_party_wall")
    obj["sr_connector_y"] = (float(y0), float(y1))
    return obj


def _connector_roof(collection, index, y0, y1):
    import bpy

    x0, x1 = 27.1, 31.15
    base, ridge = 4.65, 5.55
    centre = (y0 + y1) * 0.5
    half = max(0.55, (y1 - y0) * 0.5)
    vertices = [
        (x0, centre - half, base), (x0, centre, ridge),
        (x0, centre + half, base), (x1, centre - half, base),
        (x1, centre, ridge), (x1, centre + half, base),
    ]
    faces = ((0, 3, 4, 1), (1, 4, 5, 2), (0, 1, 2), (3, 5, 4),
             (0, 2, 5, 3))
    mesh = bpy.data.meshes.new(f"CORTICO_BACKGROUND_CONNECTOR_{index:02d}_ROOF_MESH")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(f"CORTICO_BACKGROUND_CONNECTOR_{index:02d}_ROOF", mesh)
    collection.objects.link(obj)
    mesh.materials.append(_source_material(("sr_roof_tile", "sr_terracotta")))
    _topology_tag(obj, "source_derived_party_wall_roof")
    return obj


def _add_connectors(collection, root, module_records):
    bounds = sorted((item["coverageY"], item["id"]) for item in module_records)
    connectors = []
    for index, (left, right) in enumerate(zip(bounds, bounds[1:]), 1):
        gap = right[0][0] - left[0][1]
        if gap <= 0.25:
            continue
        y0 = left[0][1] - 0.12
        y1 = right[0][0] + 0.12
        wall = _connector_wall(collection, index, y0, y1)
        roof = _connector_roof(collection, index, y0, y1)
        wall.parent = root
        roof.parent = root
        connectors.append({"id": f"connector_{index:02d}",
                           "coverageY": [y0, y1],
                           "gapY": gap,
                           "objects": [wall.name, roof.name]})
    return connectors


def build_topology():
    import bpy

    validate_modules()
    collection = _candidate_collection()
    root = bpy.data.objects.new("CORTICO_BACKGROUND_TOPOLOGY_ROOT", None)
    collection.objects.link(root)
    root.empty_display_type = "PLAIN_AXES"
    root["sr_export"] = False
    root["sr_preview_only"] = True
    root["sr_noninteractive"] = True
    root["sr_background_topology"] = True
    root["sr_representation"] = "full_model"
    root["sr_flatten_via_exterior_exporter"] = True
    root["sr_schema_version"] = SCHEMA_VERSION
    modules = []
    for index, module in enumerate(DEFAULT_MODULES, 1):
        module_root, source_objects = _copy_module(module, collection, index)
        module_root.parent = root
        modules.append({
            "id": module["id"],
            "root": module_root,
            "sourceObjects": [obj.name for obj in source_objects],
            "coverageY": list(coverage_bounds(module)),
        })
    connector_records = _add_connectors(collection, root, modules)
    ground = _copy_ground(collection)
    ground.parent = root
    return root, modules, connector_records, ground


def _canon_camera(collection):
    import bpy
    from mathutils import Vector

    source_camera = bpy.data.objects.get("TH_CAMERA_PREVIEW")
    if source_camera is None:
        raise RuntimeError("adopted source is missing TH_CAMERA_PREVIEW")
    camera = source_camera.copy()
    camera.data = source_camera.data.copy()
    camera.name = "TH_CAMERA_CANON_STUDY"
    collection.objects.link(camera)
    camera.location = source_camera.location.copy()
    camera.data.shift_y = -0.8
    forward = Vector((math.cos(math.radians(17.5)), 0.0,
                      math.sin(math.radians(17.5))))
    camera.rotation_mode = "QUATERNION"
    camera.rotation_quaternion = forward.to_track_quat("-Z", "Y")
    return camera


def _study_actor(collection):
    import bpy

    source = bpy.data.objects.get("TH_ACTOR_PREVIEW_npc_scholar")
    if source is None:
        raise RuntimeError("adopted source is missing the scholar preview actor")
    actor = source.copy()
    actor.data = source.data.copy()
    actor.name = "CORTICO_BACKGROUND_STUDY_ACTOR"
    collection.objects.link(actor)
    actor.hide_render = False
    actor.hide_viewport = False
    actor["sr_export"] = False
    actor["sr_preview_only"] = True
    actor["sr_study_actor"] = True
    return actor


def _render_studies(out_dir):
    import bpy

    scene = bpy.context.scene
    collection = bpy.data.collections["BACKGROUND_TOPOLOGY_CANDIDATE"]
    camera = _canon_camera(collection)
    actor = _study_actor(collection)
    scene.camera = camera
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 426
    scene.render.resolution_y = 240
    scene.render.resolution_percentage = 100
    original_camera_y = camera.location.y
    original_actor_location = actor.location.copy()
    studies = []
    for label, lane_y in (("west", LANE_MIN_Y), ("centre", LANE_CENTRE_Y),
                          ("east", LANE_MAX_Y)):
        y = lane_to_blender_y(lane_y)
        actor.location = (7.8, y, 0.0)
        camera.location.y = y
        path = Path(out_dir) / f"background-topology-{label}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        studies.append({"label": label, "runtimeLaneY": lane_y,
                        "blenderY": y, "path": path.name})
    camera.location.y = original_camera_y
    actor.location = original_actor_location
    return studies


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _manifest(source, studies, modules):
    return {
        "schemaVersion": SCHEMA_VERSION,
        "candidate": "cortico_background_topology",
        "evidenceKind": "blender_source_derived_topology_study",
        "runtimeEvidence": False,
        "source": {"blend": Path(source).name, "sha256": _sha256(source),
                   "ownership": "adopted_source_read_only"},
        "camera": {"pitchDegrees": -17.5,
                   "blenderEquivalentPitchDegrees": 17.5,
                   "sourceEyePreserved": True, "studyPrincipalShiftY": -0.8,
                   "studyMode": "camera_follow_review",
                   "studyModeRuntimeEquivalent": False},
        "topology": {"representation": "full_model",
                     "opaqueSilhouettes": False,
                     "cameraSpaceBackdrop": False,
                     "flattenPath": "TH_SOURCE -> exterior exporter -> runtime atlas",
                     "backgroundDepthX": [BACKGROUND_MIN_X, BACKGROUND_MAX_X],
                     "modules": modules["modules"],
                     "connectors": modules["connectors"],
                     "groundCoverageY": [-32.0, 32.0]},
        "studies": studies,
        "outputs": {"libraryBlend": "cortico-background-topology-library.blend",
                    "studyBlend": "cortico-background-topology-study.blend"},
    }


def build_study(source, out_dir):
    import bpy

    bpy.ops.wm.open_mainfile(filepath=str(Path(source).resolve()))
    root, modules, connectors, ground = build_topology()
    del root, ground
    study_dir = Path(out_dir) / "studies"
    study_dir.mkdir(parents=True, exist_ok=True)
    studies = _render_studies(study_dir)
    study_path = Path(out_dir) / "cortico-background-topology-study.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(study_path))
    manifest_modules = [{"id": item["id"], "coverageY": item["coverageY"],
                         "sourceObjects": item["sourceObjects"]}
                        for item in modules]
    return study_path, studies, {"modules": manifest_modules,
                                 "connectors": connectors}


def build_library(source, out_dir):
    """Save a source-derived library with the candidate collection isolated."""
    import bpy

    bpy.ops.wm.open_mainfile(filepath=str(Path(source).resolve()))
    build_topology()
    candidate = bpy.data.collections["BACKGROUND_TOPOLOGY_CANDIDATE"]
    for obj in candidate.all_objects:
        if obj.type == "MESH":
            obj["sr_export"] = False
    path = Path(out_dir) / "cortico-background-topology-library.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    return path


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if not args.source.is_file():
        raise SystemExit(f"source blend not found: {args.source}")
    validate_modules()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    library = build_library(args.source, args.out_dir)
    study, studies, modules = build_study(args.source, args.out_dir)
    manifest = _manifest(args.source, studies, modules)
    manifest["outputs"]["libraryBlend"] = library.name
    manifest["outputs"]["studyBlend"] = study.name
    manifest_path = args.out_dir / "candidate-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n",
                             encoding="utf-8")
    print(json.dumps({"status": "BACKGROUND TOPOLOGY STUDY OK",
                      "library": str(library), "study": str(study),
                      "manifest": str(manifest_path), "studies": studies},
                     sort_keys=True))


if __name__ == "__main__":
    import bpy  # noqa: F401
    main(sys.argv[sys.argv.index("--") + 1:])
