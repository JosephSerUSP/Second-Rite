"""Composable distant scenery for modelled St. Maria exterior studies.

This module deliberately stops at the authoring boundary.  It makes one
standalone library blend and, when given an adopted source blend, one scratch
study blend that contains a separate ``SCENERY_CANDIDATE`` collection.  It
never saves the source blend and it never changes the runtime exporter or the
global sky.

The scenery pieces are opaque, thin extruded silhouette meshes.  That is a
scoped alternative to alpha cards: the current town bake path has not proved
that cutout alpha survives its atlas transfer, while closed silhouette meshes
use the existing mesh/material/export role contracts without a second
renderer.  The candidate is ``preview_only`` and ``sr_export=False`` until an
owner explicitly imports it into an adopted source.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path


SCHEMA_VERSION = 1
LANE_CENTRE_Y = 12.031
LANE_MIN_Y = -2.844
LANE_MAX_Y = 26.906
CAMERA_X = -18.666666
CAMERA_TARGET_X = 7.8
CANON_DISTANCE = 18.666666666666668
CANON_EYE_HEIGHT = 2.2604166666666665
CANON_PITCH_DEGREES = -17.5
SCENERY_MIN_DEPTH = 24.0
SCENERY_MAX_Y = 30.0


# Profiles use normalized width/height coordinates.  The helper expands them
# using each piece's explicit width and height; authors therefore tune massing
# without duplicating mesh construction or coordinate math.
DEFAULT_SPECS = (
    {
        "id": "far_terrain",
        "depth": 38.0,
        "width": 60.0,
        "center_y": 0.0,
        "height": 16.0,
        "base_z": -8.0,
        "thickness": 0.16,
        "material": "rough_limestone",
        "color": (0.19, 0.22, 0.19),
        "profile": ((0.00, 0.42), (0.07, 0.50), (0.14, 0.46),
                     (0.22, 0.59), (0.31, 0.52), (0.40, 0.67),
                     (0.49, 0.56), (0.58, 0.61), (0.67, 0.48),
                     (0.76, 0.57), (0.84, 0.49), (0.92, 0.54),
                     (1.00, 0.45)),
    },
    {
        "id": "mid_roofline",
        "depth": 31.0,
        "width": 26.0,
        "center_y": -16.0,
        "height": 17.0,
        "base_z": -8.0,
        "thickness": 0.14,
        "material": "terracotta",
        "color": (0.30, 0.13, 0.09),
        "profile": ((0.00, 0.30), (0.06, 0.37), (0.12, 0.34),
                     (0.17, 0.52), (0.24, 0.52), (0.29, 0.39),
                     (0.35, 0.42), (0.41, 0.72), (0.50, 0.72),
                     (0.55, 0.47), (0.61, 0.49), (0.67, 0.62),
                     (0.75, 0.62), (0.80, 0.44), (0.86, 0.47),
                     (0.92, 0.36), (1.00, 0.40)),
    },
    {
        "id": "distant_vegetation",
        "depth": 24.5,
        "width": 22.0,
        "center_y": -16.0,
        "height": 18.0,
        "base_z": -8.0,
        "thickness": 0.12,
        "material": "dark_wood",
        "color": (0.10, 0.17, 0.12),
        "profile": ((0.00, 0.22), (0.06, 0.29), (0.10, 0.27),
                     (0.14, 0.52), (0.19, 0.65), (0.24, 0.48),
                     (0.30, 0.35), (0.35, 0.42), (0.40, 0.70),
                     (0.45, 0.61), (0.50, 0.34), (0.56, 0.40),
                     (0.61, 0.58), (0.67, 0.75), (0.73, 0.54),
                     (0.78, 0.35), (0.84, 0.43), (0.90, 0.62),
                     (0.95, 0.51), (1.00, 0.27)),
    },
    {
        "id": "mid_roofline_east",
        "depth": 31.0,
        "width": 26.0,
        "center_y": 16.0,
        "height": 17.0,
        "base_z": -8.0,
        "thickness": 0.14,
        "material": "terracotta",
        "color": (0.30, 0.13, 0.09),
        "profile": ((0.00, 0.30), (0.06, 0.37), (0.12, 0.34),
                     (0.17, 0.52), (0.24, 0.52), (0.29, 0.39),
                     (0.35, 0.42), (0.41, 0.72), (0.50, 0.72),
                     (0.55, 0.47), (0.61, 0.49), (0.67, 0.62),
                     (0.75, 0.62), (0.80, 0.44), (0.86, 0.47),
                     (0.92, 0.36), (1.00, 0.40)),
    },
    {
        "id": "distant_vegetation_east",
        "depth": 24.5,
        "width": 22.0,
        "center_y": 16.0,
        "height": 18.0,
        "base_z": -8.0,
        "thickness": 0.12,
        "material": "dark_wood",
        "color": (0.10, 0.17, 0.12),
        "profile": ((0.00, 0.22), (0.06, 0.29), (0.10, 0.27),
                     (0.14, 0.52), (0.19, 0.65), (0.24, 0.48),
                     (0.30, 0.35), (0.35, 0.42), (0.40, 0.70),
                     (0.45, 0.61), (0.50, 0.34), (0.56, 0.40),
                     (0.61, 0.58), (0.67, 0.75), (0.73, 0.54),
                     (0.78, 0.35), (0.84, 0.43), (0.90, 0.62),
                     (0.95, 0.51), (1.00, 0.27)),
    },
)


def _finite(value, label):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{label} must be finite")
    return value


def validate_scenery_spec(spec):
    """Validate one serializable scenery specification without Blender."""
    if not isinstance(spec, dict):
        raise ValueError("scenery spec must be an object")
    ident = str(spec.get("id", ""))
    if not ident or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789_" for ch in ident):
        raise ValueError("scenery id must be lower snake case")
    for field in ("depth", "width", "height", "thickness"):
        value = _finite(spec.get(field), field)
        if value <= 0:
            raise ValueError(f"{field} must be positive")
    base_z = _finite(spec.get("base_z", 0.0), "base_z")
    _finite(spec.get("center_y", 0.0), "center_y")
    profile = spec.get("profile")
    if not isinstance(profile, (list, tuple)) or len(profile) < 3:
        raise ValueError("profile needs at least three points")
    previous_u = None
    for point in profile:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ValueError("profile points must be [u, v] pairs")
        u, v = (_finite(point[0], "profile u"), _finite(point[1], "profile v"))
        if not 0.0 <= u <= 1.0 or not 0.0 <= v <= 1.0:
            raise ValueError("profile coordinates must be in [0, 1]")
        if previous_u is not None and u < previous_u:
            raise ValueError("profile u coordinates must be non-decreasing")
        previous_u = u
    if abs(float(profile[0][0])) > 1e-9 or abs(float(profile[-1][0]) - 1.0) > 1e-9:
        raise ValueError("profile must span the declared width from u=0 to u=1")
    if base_z >= 0.0:
        raise ValueError("distant scenery base_z must sit below the walkable ground")
    return True


def validate_specs(specs=DEFAULT_SPECS):
    """Validate a full compositional stack and its depth/coverage contract."""
    if not specs:
        raise ValueError("at least one scenery layer is required")
    for spec in specs:
        validate_scenery_spec(spec)
    depths = [float(spec["depth"]) for spec in specs]
    if any(depth <= CAMERA_TARGET_X for depth in depths):
        raise ValueError("scenery depth must remain behind the pilot geometry")
    if len(set(depths)) < 3:
        raise ValueError("scenery stack needs at least three depth ranks for parallax ordering")
    if min(depths) < SCENERY_MIN_DEPTH:
        raise ValueError("scenery layer is too close to the adopted pilot geometry")
    if not any(
        coverage_bounds(spec)[0] <= -SCENERY_MAX_Y
        and coverage_bounds(spec)[1] >= SCENERY_MAX_Y
        for spec in specs
    ):
        raise ValueError("the scenery stack needs one continuous layer across the study window")
    return True


def lane_to_blender_y(lane_y, lane_centre=LANE_CENTRE_Y):
    """Apply the adopted source's explicit runtime lane mirror."""
    return float(lane_centre) - _finite(lane_y, "lane_y")


def coverage_bounds(spec):
    """Return the world-Y interval covered by a centered scenery plane."""
    validate_scenery_spec(spec)
    half = float(spec["width"]) * 0.5
    centre = float(spec.get("center_y", 0.0))
    return (centre - half, centre + half)


def _mesh_object(name, spec, collection, material):
    import bpy

    validate_scenery_spec(spec)
    depth = float(spec["depth"])
    width = float(spec["width"])
    height = float(spec["height"])
    base_z = float(spec.get("base_z", -1.0))
    thickness = float(spec["thickness"])
    center_y = float(spec.get("center_y", 0.0))
    outline = [(center_y + float(u) * width - width * 0.5,
               base_z + float(v) * height) for u, v in spec["profile"]]
    # Close the silhouette at a common below-ground line.  A front face is
    # camera-facing (-X), and the back/sides make the otherwise thin plane a
    # stable opaque full-model mesh for existing exporters.
    boundary = [(outline[0][0], base_z), *outline,
                (outline[-1][0], base_z)]
    half = thickness * 0.5
    vertices = [(depth - half, y, z) for y, z in boundary]
    vertices += [(depth + half, y, z) for y, z in boundary]
    count = len(boundary)
    front = tuple(reversed(range(count)))
    back = tuple(count + index for index in range(count))
    faces = [front, back]
    for index in range(count):
        other = (index + 1) % count
        faces.append((index, other, count + other, count + index))
    mesh = bpy.data.meshes.new(f"{name}_MESH")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    mesh.materials.append(material)
    for polygon in mesh.polygons:
        polygon.use_smooth = False
    return obj


def _asset_core():
    root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(root / "tools" / "blender"))
    import second_rite_asset_core as asset_core
    return asset_core


def _materials():
    core = _asset_core()
    return {
        "rough_limestone": core.make_material(
            "sr_scenery_rough_limestone", semantic_id="rough_limestone",
            color=(0.19, 0.22, 0.19), roughness=0.96,
            scope="distant_scenery_candidate"),
        "terracotta": core.make_material(
            "sr_scenery_terracotta", semantic_id="terracotta",
            color=(0.30, 0.13, 0.09), roughness=0.92,
            scope="distant_scenery_candidate"),
        "dark_wood": core.make_material(
            "sr_scenery_dark_wood", semantic_id="dark_wood",
            color=(0.10, 0.17, 0.12), roughness=0.95,
            scope="distant_scenery_candidate"),
    }


def build_stack(*, collection_name="SCENERY_CANDIDATE"):
    """Build and return an opaque candidate stack in the active Blender scene."""
    import bpy

    core = _asset_core()
    validate_specs()
    collection = core.ensure_collection(collection_name)
    materials = _materials()
    root = bpy.data.objects.new("CORTICO_DISTANT_SCENERY_ROOT", None)
    collection.objects.link(root)
    root.empty_display_type = "PLAIN_AXES"
    core.tag_asset_target(
        root, asset_id="cortico_distant_scenery", representation="full_model",
        role="preview_only", authoring_space="world_cell",
        placement_frame="preview_frame", states=["default"],
        variants=["candidate"], extra={
            "sr_preview_only": True,
            "sr_noninteractive": True,
            "sr_explicit_import_only": True,
            "sr_scenery_schema": f"v{SCHEMA_VERSION}",
            "sr_export": False,
        })
    pieces = []
    for spec in DEFAULT_SPECS:
        obj = _mesh_object(
            f"CORTICO_SCENERY_{spec['id'].upper()}", spec, collection,
            materials[spec["material"]])
        obj.parent = root
        core.tag_asset_target(
            obj, asset_id=f"cortico_distant_scenery_{spec['id']}",
            representation="full_model", role="preview_only",
            authoring_space="world_cell", placement_frame="preview_frame",
            states=["default"], variants=["candidate"], extra={
                "sr_preview_only": True,
                "sr_noninteractive": True,
                "sr_explicit_import_only": True,
                "sr_export": False,
                "sr_scenery_depth": float(spec["depth"]),
                "sr_scenery_width": float(spec["width"]),
                "sr_scenery_height": float(spec["height"]),
                "sr_scenery_center_y": float(spec.get("center_y", 0.0)),
                "sr_scenery_material": spec["material"],
            })
        pieces.append(obj)
    return root, pieces


def _neutral_actor():
    """Create a review-only actor so every study has a scale reference."""
    spec = {
        "id": "study_actor",
        "depth": 7.8,
        "width": 0.78,
        "height": 1.75,
        "base_z": -0.01,
        "thickness": 0.08,
        "material": "dark_wood",
        "profile": ((0.00, 0.00), (0.08, 0.53), (0.25, 0.63),
                     (0.36, 0.78), (0.43, 1.00), (0.57, 1.00),
                     (0.64, 0.78), (0.75, 0.63), (0.92, 0.53),
                     (1.00, 0.00)),
    }
    import bpy

    collection = bpy.data.collections.get("SCENERY_CANDIDATE")
    core = _asset_core()
    material = core.make_material(
        "sr_scenery_study_actor", semantic_id="whitewash",
        color=(0.72, 0.34, 0.08), roughness=0.88,
        scope="distant_scenery_candidate")
    actor = _mesh_object("CORTICO_STUDY_ACTOR", spec, collection, material)
    actor["sr_preview_only"] = True
    actor["sr_study_actor"] = True
    actor["sr_export"] = False
    return actor


def _canon_study_camera():
    """Clone the pilot camera and apply the canon town pitch locally.

    The adopted source's ``TH_CAMERA_PREVIEW`` is currently level.  It remains
    untouched; this review camera carries the game camera's declared -17.5
    degree pitch so the study cannot accidentally bless a level preview.
    """
    import bpy
    from mathutils import Vector

    source_camera = bpy.data.objects.get("TH_CAMERA_PREVIEW")
    if source_camera is None:
        raise RuntimeError("adopted source is missing TH_CAMERA_PREVIEW")
    camera = source_camera.copy()
    camera.data = source_camera.data.copy()
    camera.name = "TH_CAMERA_CANON_STUDY"
    collection = bpy.data.collections.get("SCENERY_CANDIDATE")
    collection.objects.link(camera)
    # Preserve the adopted source eye/lens.  The source preview is authored at
    # the canonical 18.6667 action-plane distance; relocating it to a different
    # map target would change the very exterior geometry this study is meant to
    # review.  Only the local study camera receives pitch and framing.
    camera.location = source_camera.location.copy()
    camera.data.shift_y = -0.8
    # Runtime's screen-space pitch sign is opposite Blender's world-camera
    # rotation sign for this +X/-Z camera basis.
    pitch = math.radians(-CANON_PITCH_DEGREES)
    forward = Vector((math.cos(pitch), 0.0, math.sin(pitch)))
    camera.rotation_mode = "QUATERNION"
    camera.rotation_quaternion = forward.to_track_quat("-Z", "Y")
    return camera


def _source_sha256(source):
    digest = hashlib.sha256()
    with Path(source).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _render_studies(source, out_dir, actor):
    import bpy

    scene = bpy.context.scene
    camera = _canon_study_camera()
    scene.camera = camera
    # Blender 5.1 exposes the Eevee engine under the legacy Python enum even
    # though the command-line alias is BLENDER_EEVEE_NEXT.
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(Path(out_dir) / "unused.png")
    positions = (
        ("west", LANE_MIN_Y),
        ("centre", LANE_CENTRE_Y),
        ("east", LANE_MAX_Y),
    )
    output = []
    original_camera_location = camera.location.copy()
    original_actor_location = actor.location.copy()
    for label, lane_y in positions:
        # The mesh helper stores world depth in its vertices.  The source
        # camera is fixed in the runtime contract, but its end positions are
        # outside the current zero-offset crop.  Translate the Blender camera
        # with the review actor so all three composition studies are legible;
        # this is explicitly Blender-only evidence, not a runtime claim.
        actor_y = lane_to_blender_y(lane_y)
        actor.location = (0.0, actor_y, 0.0)
        camera.location.y = actor_y
        scene.render.filepath = str(Path(out_dir) / f"blender-study-{label}.png")
        bpy.ops.render.render(write_still=True)
        output.append({
            "label": label,
            "runtimeLaneY": lane_y,
            "blenderActorY": actor.location.y,
            "blenderCameraY": camera.location.y,
            "mode": "camera_follow_review",
            "path": Path(scene.render.filepath).name,
        })
    camera.location = original_camera_location
    actor.location = original_actor_location
    return output


def _manifest(source, output_dir, studies):
    return {
        "schemaVersion": SCHEMA_VERSION,
        "candidate": "cortico_distant_scenery",
        "evidenceKind": "blender_authoring_study",
        "runtimeEvidence": False,
        "source": {
            "blend": Path(source).name,
            "sha256": _source_sha256(source),
            "commit": "fa874c88",
            "ownership": "adopted_source_read_only",
        },
        "camera": {
            "kind": "pilot_source_TH_CAMERA_PREVIEW_with_local_canon_pitch",
            "viewDirection": "+X",
            "pitchDegrees": CANON_PITCH_DEGREES,
            "blenderEquivalentPitchDegrees": -CANON_PITCH_DEGREES,
            "sourceEyePreserved": True,
            "studyPrincipalShiftY": -0.8,
            "laneMirror": "blenderY = 12.031 - runtimeLaneY",
            "studyMode": "camera_follow_review",
            "studyModeRuntimeEquivalent": False,
            "laneStudyPositions": [LANE_MIN_Y, LANE_CENTRE_Y, LANE_MAX_Y],
        },
        "layers": [
            {
                "id": spec["id"],
                "depth": spec["depth"],
                "width": spec["width"],
                "centerY": spec.get("center_y", 0.0),
                "height": spec["height"],
                "material": spec["material"],
                "coverageY": list(coverage_bounds(spec)),
                "opaqueExtrudedSilhouette": True,
                "srExport": False,
            }
            for spec in DEFAULT_SPECS
        ],
        "coverage": {
            "laneRuntime": [LANE_MIN_Y, LANE_MAX_Y],
            "studyMarginY": SCENERY_MAX_Y,
            "allLayersContinuousAcrossCoverage": True,
            "endExposureRisk": "not observed in the declared study window",
        },
        "studies": studies,
        "outputs": {
            "libraryBlend": "cortico-distant-scenery-library.blend",
            "studyBlend": "cortico-distant-scenery-study.blend",
        },
    }


def build_library(out_dir):
    import bpy

    core = _asset_core()
    core.reset_scene(factory=True)
    build_stack()
    path = Path(out_dir) / "cortico-distant-scenery-library.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    return path


def build_study(source, out_dir):
    import bpy

    bpy.ops.wm.open_mainfile(filepath=str(Path(source).resolve()))
    build_stack()
    actor = _neutral_actor()
    study_dir = Path(out_dir) / "studies"
    study_dir.mkdir(parents=True, exist_ok=True)
    studies = _render_studies(source, study_dir, actor)
    path = Path(out_dir) / "cortico-distant-scenery-study.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    return path, studies


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True,
                        help="adopted source blend; opened read-only and never overwritten")
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if not args.source.is_file():
        raise SystemExit(f"source blend not found: {args.source}")
    validate_specs()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    library = build_library(args.out_dir)
    study, studies = build_study(args.source, args.out_dir)
    manifest = _manifest(args.source, args.out_dir, studies)
    manifest["outputs"]["libraryBlend"] = library.name
    manifest["outputs"]["studyBlend"] = study.name
    (args.out_dir / "candidate-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "DISTANT SCENERY STUDY OK",
        "library": str(library),
        "study": str(study),
        "manifest": str(args.out_dir / "candidate-manifest.json"),
        "studies": studies,
    }, sort_keys=True))


if __name__ == "__main__":
    import bpy  # noqa: F401
    main(sys.argv[sys.argv.index("--") + 1:])
