"""Render and inspect the first real-3D town spatial contract.

The fixture is intentionally asymmetric.  It is not a beauty scene and it is
not a replacement for a reviewed adopted .blend.  Its job is to make the
high-risk boundary visible:

* labelled +X/+Y axes and an off-centre anchor establish screen handedness;
* an anchor facing vector establishes orientation, not just position;
* a deliberately front-facing triangle proves that a reflected export must
  reverse winding;
* a near box and a far target prove depth occlusion with a real ray cast; and
* two elevations prove that the camera preview is not a flat placement map.

The only projection implementation used here is the canonical Blender helper
``thestra_camera.project_world_point``.  The adapter transform is deliberately
small and pure so it can be tested without Blender.  This proof does not alter
shipping maps, source blends, exporters, or goldens.

Run inside Blender:

    blender -b --factory-startup --python tools/blender/town_spatial_proof.py -- \
        --fixture tools/blender/fixtures/town_spatial_proof.json \
        --output out/town-spatial-proof
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CAMERA_MODULE = ROOT / "tools" / "blender" / "thestra_camera.py"


def lane_transform(point, lane_origin_y: float, reflected: bool):
    """Map one Blender source point to the explicit engine-space candidate."""
    x, y, z = (float(value) for value in point)
    return (x, lane_origin_y - y, z) if reflected else (x, y, z)


def transform_normal(normal, reflected: bool):
    x, y, z = (float(value) for value in normal)
    return (x, -y, z) if reflected else (x, y, z)


def reverse_winding(vertices, reflected: bool):
    values = [tuple(float(value) for value in point) for point in vertices]
    return list(reversed(values)) if reflected else values


def cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def subtract(a, b):
    return tuple(x - y for x, y in zip(a, b))


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def normal_for_triangle(vertices):
    return cross(subtract(vertices[1], vertices[0]), subtract(vertices[2], vertices[0]))


def length(value):
    return math.sqrt(dot(value, value))


def normalize(value):
    scale = length(value)
    if scale <= 1e-12:
        raise ValueError("cannot normalize a zero-length vector")
    return tuple(component / scale for component in value)


def _require_blender():
    try:
        import bpy  # noqa: F401
    except ImportError as error:
        raise RuntimeError("town_spatial_proof.py must run inside Blender") from error


def _material(bpy, name, color):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*color, 1.0)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (*color, 1.0)
    emission.inputs["Strength"].default_value = 1.0
    material.node_tree.links.new(emission.outputs[0], output.inputs["Surface"])
    return material


def _clear_scene(bpy):
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for material in list(bpy.data.materials):
        bpy.data.materials.remove(material)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)


def _cube(bpy, name, center, size, material):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    obj.data.materials.append(material)
    bpy.context.view_layer.update()
    return obj


def _line(bpy, name, start, end, thickness, material):
    midpoint = tuple((a + b) * 0.5 for a, b in zip(start, end))
    delta = subtract(end, start)
    obj = _cube(bpy, name, midpoint, (thickness, thickness, thickness), material)
    obj.dimensions = (max(abs(delta[0]), thickness), max(abs(delta[1]), thickness), max(abs(delta[2]), thickness))
    return obj


def _text(bpy, body, location, material, camera, size=0.32):
    from mathutils import Matrix, Vector

    bpy.ops.object.text_add(location=location)
    obj = bpy.context.object
    obj.name = f"LABEL_{body}"
    obj.data.body = body
    obj.data.align_x = "CENTER"
    obj.data.align_y = "CENTER"
    obj.data.size = size
    obj.data.extrude = 0.005
    obj.data.materials.append(material)
    # Text local +X/+Y are screen-right/screen-up.  Reuse the complete camera
    # basis instead of an Euler approximation, because this camera intentionally
    # carries the reflected basis that a quaternion cannot represent.
    basis = camera.matrix_world.to_3x3().copy()
    obj.matrix_world = Matrix.Translation(Vector(location)) @ basis.to_4x4()
    return obj


def _triangle(bpy, name, vertices, material):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], [(0, 1, 2)])
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def _build_variant(bpy, fixture, camera, reflected):
    source = fixture["source"]
    lane_origin = float(fixture["laneOriginY"])
    suffix = "REFLECTED" if reflected else "DIRECT"
    stone = _material(bpy, f"{suffix}_STONE", (0.28, 0.32, 0.38))
    red = _material(bpy, f"{suffix}_DEPTH_AXIS", (0.85, 0.15, 0.10))
    blue = _material(bpy, f"{suffix}_LANE_AXIS", (0.10, 0.35, 0.9))
    gold = _material(bpy, f"{suffix}_ANCHOR", (0.95, 0.68, 0.08))
    green = _material(bpy, f"{suffix}_ELEVATION", (0.18, 0.75, 0.28))
    magenta = _material(bpy, f"{suffix}_TRIANGLE", (0.85, 0.12, 0.75))
    white = _material(bpy, f"{suffix}_LABEL", (0.95, 0.95, 0.95))

    transform = lambda point: lane_transform(point, lane_origin, reflected)

    # The axis is geometry, not an annotation in the report.  +Y's rendered
    # horizontal direction is the handedness observation this fixture exists to
    # expose.
    _line(bpy, f"{suffix}_DEPTH_AXIS", transform((1.0, 0.0, 0.05)),
          transform((10.0, 0.0, 0.05)), 0.055, red)
    _line(bpy, f"{suffix}_LANE_AXIS", transform((3.0, -3.0, 0.05)),
          transform((3.0, 3.0, 0.05)), 0.055, blue)
    _text(bpy, "+X DEPTH", transform((5.0, -0.55, 0.16)), white, camera)
    _text(bpy, "+Y SOURCE", transform((3.0, 2.0, 0.16)), white, camera)

    anchor = transform(source["anchor"])
    _cube(bpy, f"{suffix}_OFF_CENTRE_ANCHOR", (anchor[0], anchor[1], 0.5),
          (0.35, 0.35, 1.0), gold)
    facing_tip = transform(tuple(source["anchor"][i] + source["facing"][i] * 1.0 for i in range(3)))
    _line(bpy, f"{suffix}_FACING", (anchor[0], anchor[1], 0.8),
          (facing_tip[0], facing_tip[1], 0.8), 0.09, gold)
    _text(bpy, "ANCHOR", (anchor[0] + 0.15, anchor[1], 1.15), white, camera, 0.26)

    elevated_ground = transform(source["elevationGround"])
    elevated_raised = transform(source["elevationRaised"])
    _cube(bpy, f"{suffix}_GROUND", (elevated_ground[0], elevated_ground[1], 0.08),
          (1.3, 1.0, 0.16), green)
    _cube(bpy, f"{suffix}_RAISED", (elevated_raised[0], elevated_raised[1], 0.375),
          (1.3, 1.0, 0.75), green)
    _text(bpy, "ELEVATION", (elevated_raised[0] + 0.15, elevated_raised[1], 1.0), white, camera, 0.25)

    occluder = source["occluder"]
    occluder_center = transform(occluder["center"])
    _cube(bpy, f"{suffix}_OCCLUDER", occluder_center, tuple(occluder["size"]), stone)
    _text(bpy, "OCCLUDER", (occluder_center[0] + 0.15, occluder_center[1], 2.1), white, camera, 0.24)

    triangle_source = source["triangle"]["vertices"]
    triangle_vertices = [transform(point) for point in triangle_source]
    triangle_vertices = reverse_winding(triangle_vertices, reflected)
    triangle = _triangle(bpy, f"{suffix}_WOUND_TRIANGLE", triangle_vertices, magenta)
    triangle.data.materials[0].use_nodes = True
    triangle.data.materials[0].use_backface_culling = True
    _text(bpy, "WINDING", (4.0, transform((-1.3, 0.0, 0.0))[1], 1.75), white, camera, 0.24)

    target = transform(source["occludedTarget"])
    _cube(bpy, f"{suffix}_OCCLUDED_TARGET", target, (0.28, 0.28, 0.28), red)

    # A ground surface gives the render a stable silhouette and makes the
    # foreground relation readable in the PNG without contributing to the
    # occlusion ray aimed at the elevated target.
    _cube(bpy, f"{suffix}_GROUND_PLANE", (5.0, 0.0, -0.08), (12.0, 8.0, 0.16),
          _material(bpy, f"{suffix}_GROUND_MAT", (0.055, 0.065, 0.08)))

    return {
        "anchor": anchor,
        "facingTip": facing_tip,
        "elevationGround": elevated_ground,
        "elevationRaised": elevated_raised,
        "occludedTarget": target,
        "triangle": triangle,
        "occluderName": f"{suffix}_OCCLUDER",
    }


def _configure_render(bpy, camera):
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = int(camera["targetWidth"])
    scene.render.resolution_y = int(camera["targetHeight"])
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.008, 0.008, 0.012)
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    if background:
        background.inputs["Color"].default_value = (0.025, 0.03, 0.045, 1.0)
        background.inputs["Strength"].default_value = 0.45
    scene.view_settings.look = "None"
    return scene


def _vector_list(value):
    return [round(float(component), 6) for component in value]


def _project(thestra_camera, scene, camera_obj, point):
    return _vector_list(thestra_camera.project_world_point(scene, camera_obj, point))


def _variant_evidence(bpy, thestra_camera, scene, camera_obj, fixture, state, reflected):
    source = fixture["source"]
    anchor = state["anchor"]
    facing_tip = state["facingTip"]
    ground = state["elevationGround"]
    raised = state["elevationRaised"]
    target = state["occludedTarget"]
    camera_eye = camera_obj.matrix_world.translation
    direction = normalize(subtract(target, camera_eye))
    hit, location, normal, face_index, hit_object, matrix = scene.ray_cast(
        bpy.context.evaluated_depsgraph_get(), camera_eye, direction)

    triangle_vertices = [tuple(vertex.co) for vertex in state["triangle"].data.vertices]
    triangle_normal = normalize(normal_for_triangle(triangle_vertices))
    to_eye = normalize(subtract(camera_eye, triangle_vertices[0]))
    expected_normal = normalize(transform_normal(source["triangle"]["frontFacingNormal"], reflected))
    return {
        "transform": "laneOriginY - sourceY" if reflected else "sourceY",
        "projection": {
            "anchor": _project(thestra_camera, scene, camera_obj, anchor),
            "facingTip": _project(thestra_camera, scene, camera_obj, facing_tip),
            "elevationGround": _project(thestra_camera, scene, camera_obj, ground),
            "elevationRaised": _project(thestra_camera, scene, camera_obj, raised),
            "occludedTarget": _project(thestra_camera, scene, camera_obj, target),
            "positiveSourceYScreenDelta": round(
                _project(thestra_camera, scene, camera_obj, lane_transform((4, 1, 0), fixture["laneOriginY"], reflected))[0]
                - _project(thestra_camera, scene, camera_obj, lane_transform((4, 0, 0), fixture["laneOriginY"], reflected))[0], 6),
            "facingScreenDelta": round(
                _project(thestra_camera, scene, camera_obj, facing_tip)[0]
                - _project(thestra_camera, scene, camera_obj, anchor)[0], 6),
            "elevationScreenDeltaY": round(
                _project(thestra_camera, scene, camera_obj, raised)[1]
                - _project(thestra_camera, scene, camera_obj, ground)[1], 6),
        },
        "occlusion": {
            "hit": bool(hit),
            "hitObject": hit_object.name if hit_object else None,
            "targetBlockedByExpectedOccluder": bool(hit and hit_object.name == state["occluderName"]),
            "hitPoint": _vector_list(location) if hit else None,
        },
        "triangle": {
            "normal": _vector_list(triangle_normal),
            "expectedFrontNormal": _vector_list(expected_normal),
            "frontFacing": dot(triangle_normal, to_eye) > 0.0,
            "normalMatchesExpected": dot(triangle_normal, expected_normal) > 0.999,
            "faceIndex": int(face_index),
        },
    }


def prove(fixture_path: Path, output_dir: Path):
    _require_blender()
    import bpy
    import importlib.util

    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    camera_record = json.loads((ROOT / fixture["camera"]).read_text(encoding="utf-8"))
    spec = importlib.util.spec_from_file_location("thestra_camera", CAMERA_MODULE)
    thestra_camera = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(thestra_camera)
    thestra_camera.validate_calibration(camera_record)

    output_dir.mkdir(parents=True, exist_ok=True)
    variants = {}
    for reflected, label in ((False, "direct"), (True, "reflected")):
        _clear_scene(bpy)
        scene = _configure_render(bpy, camera_record)
        camera = thestra_camera.create_or_update_camera(
            camera_record, scene=scene, make_active=True,
        )
        state = _build_variant(bpy, fixture, camera, reflected)
        bpy.context.view_layer.update()
        scene.render.filepath = str((output_dir / f"{label}.png").resolve())
        bpy.ops.render.render(write_still=True)
        variants[label] = _variant_evidence(
            bpy, thestra_camera, scene, camera, fixture, state, reflected)

    direct = variants["direct"]
    reflected = variants["reflected"]
    report = {
        "contract": fixture["contract"],
        "version": fixture["version"],
        "status": "passed",
        "fixture": str(fixture_path.resolve()),
        "camera": str((ROOT / fixture["camera"]).resolve()),
        "runtimeProjectionEvidence": fixture["runtimeProjectionEvidence"],
        "variants": variants,
        "checks": {
            "directPositiveSourceYMovesScreenLeft": direct["projection"]["positiveSourceYScreenDelta"] < 0,
            "reflectedPositiveSourceYMovesScreenRight": reflected["projection"]["positiveSourceYScreenDelta"] > 0,
            "directFacingMatchesScreenOrdering": direct["projection"]["facingScreenDelta"] < 0,
            "reflectedFacingMatchesScreenOrdering": reflected["projection"]["facingScreenDelta"] > 0,
            "directElevationProjectsUp": direct["projection"]["elevationScreenDeltaY"] < 0,
            "reflectedElevationProjectsUp": reflected["projection"]["elevationScreenDeltaY"] < 0,
            "directOcclusion": direct["occlusion"]["targetBlockedByExpectedOccluder"],
            "reflectedOcclusion": reflected["occlusion"]["targetBlockedByExpectedOccluder"],
            "directTriangleFrontFacing": direct["triangle"]["frontFacing"],
            "reflectedTriangleFrontFacingAfterWindingRepair": reflected["triangle"]["frontFacing"],
            "reflectedTriangleWindingMatchesExpected": reflected["triangle"]["normalMatchesExpected"],
            "runtimeTownSideviewUsesPositiveRightY": (
                fixture["runtimeProjectionEvidence"]["townSideviewRightY"] == 1.0
            ),
            "interiorMirrorReversesRuntimeSourceOrdering": (
                fixture["adapterEvidence"]["interiorCurrent"]["reversesFaceWinding"]
                and fixture["adapterEvidence"]["interiorCurrent"]["transform"]
                == "engine_y = 3.8833 - blender_y"
            ),
            "exteriorLeavesRuntimeSourceOrderingUnchanged": (
                not fixture["adapterEvidence"]["exteriorCurrent"]["reversesFaceWinding"]
                and fixture["adapterEvidence"]["exteriorCurrent"]["transform"]
                == "engine_y = blender_y"
            ),
        },
        "adapterConclusion": (
            "The current interior and exterior exporters disagree only after the "
            "Blender source reaches engine OBJ space: interior applies the explicit "
            "lane reflection and winding reversal, exterior does neither. The "
            "common adapter must require an explicit laneOriginY/source-space binding "
            "and apply the reflection plus winding reversal as one operation."
        ),
    }
    failed = [name for name, value in report["checks"].items() if not value]
    if failed:
        report["status"] = "failed"
        report["failedChecks"] = failed
    report_path = output_dir / "town-spatial-proof.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "report": str(report_path), "checks": report["checks"]}, sort_keys=True))
    if failed:
        raise SystemExit("spatial proof failed: " + ", ".join(failed))


def parse_args(argv=None):
    parser = argparse.ArgumentParser(prog="town_spatial_proof")
    parser.add_argument("--fixture", type=Path, default=ROOT / "tools/blender/fixtures/town_spatial_proof.json")
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else None)
    prove(args.fixture.resolve(), args.output.resolve())
