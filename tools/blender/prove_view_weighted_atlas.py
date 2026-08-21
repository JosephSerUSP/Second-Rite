"""One disposable Blender A/B proof for camera-aware atlas allocation.

The fixture is generated in this process and is never an authored town asset.
Both allocations are baked from the same saved source scene, then rendered at
426x240 across the same bounded camera envelope.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

LABELS = [
    "hero-front",
    "projection-extreme",
    "top-reveal",
    "occluded-front",
    "strongly-rear",
    "internal-unreachable",
]


def blender_executable() -> str:
    candidates = [
        os.environ.get("BLENDER_PATH"), os.environ.get("BLENDER"),
        r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
        shutil.which("blender"),
    ]
    for candidate in candidates:
        if candidate and (candidate == "blender" or Path(candidate).is_file()):
            return str(candidate)
    raise SystemExit("Blender not found; set BLENDER_PATH or BLENDER")


def calibration_record() -> dict:
    # tan(14 degrees) gives a 28 degree horizontal FOV.  The derived lens is
    # approximately 43 mm with the 36 mm reference sensor used by the adapter.
    half_x = math.tan(math.radians(14.0))
    half_y = math.tan(math.atan(half_x) * 240.0 / 426.0)
    return {
        "contract": "thestra.world-camera-calibration",
        "version": 1,
        "projection": "perspective",
        "eye": {"x": 0.0, "y": -8.0, "z": 3.4},
        "orientation": {
            "forwardX": 0.0, "forwardY": 1.0,
            "rightX": 1.0, "rightY": 0.0,
            "pitchRadians": 0.10,
        },
        "projectionScale": {"x": 1.0, "y": 1.0},
        "fovHalfX": half_x,
        "fovHalfY": half_y,
        "nearPlane": 0.1,
        "farPlane": 50.0,
        "targetWidth": 426,
        "targetHeight": 240,
        "baseViewportWidth": 256,
        "baseViewportHeight": 144,
        "viewportCenterX": 213,
        "viewportCenterY": 120,
        "projectionWindowOffsetX": 0,
        "projectionWindowOffsetY": 0,
        "coordinateSystem": {
            "handedness": "right-handed", "worldUp": "+Z", "worldHorizontal": "XY",
            "cameraForward": "+depth", "cameraRight": "+right",
            "screenOrigin": "top-left", "screenY": "+down",
            "blenderCameraForward": "-Z", "blenderCameraUp": "+Y",
        },
    }


def _move_to(obj, collection) -> None:
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    collection.objects.link(obj)


def _material(name, color, emission=0.0):
    import bpy

    material = bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.72
        if emission and "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = (*color, 1.0)
            bsdf.inputs["Emission Strength"].default_value = emission
    return material


def _mesh_object(name, faces, collection, materials):
    import bpy

    vertices = [vertex for face in faces for vertex in face]
    polygons = []
    for index in range(len(faces)):
        start = index * 4
        polygons.append((start, start + 1, start + 2, start + 3))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], polygons)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    for material in materials:
        mesh.materials.append(material)
    for polygon, index in zip(mesh.polygons, range(len(materials))):
        polygon.material_index = index
    return obj


def _cube(name, location, scale, collection, material):
    import bpy

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    _move_to(obj, collection)
    obj.data.materials.append(material)
    return obj


def build_fixture(path: Path) -> dict:
    import bpy
    import thestra_camera

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    root = scene.collection
    collections = {}
    for name in ("TH_SOURCE", "TH_RENDER", "TH_COLLISION", "TH_ANCHORS", "TH_CAMERA_PREVIEW"):
        collection = bpy.data.collections.new(name)
        root.children.link(collection)
        collections[name] = collection

    colors = (
        (0.72, 0.28, 0.18), (0.18, 0.48, 0.78), (0.72, 0.64, 0.18),
        (0.68, 0.22, 0.52), (0.20, 0.25, 0.30), (0.12, 0.52, 0.34),
    )
    target_mats = [_material("Surface_" + label, color) for label, color in zip(LABELS, colors)]
    source_mats = [_material("Source_" + label, color) for label, color in zip(LABELS, colors)]
    occluder_mat = _material("Source_Occluder", (0.08, 0.08, 0.08))

    # The camera looks along +Y from a fixed eye.  The first four surfaces are
    # deliberately separated so their envelope behavior is independently
    # measurable; the last face is retained only by explicit declaration.
    target_faces = [
        [(-2.6, 4.0, 0.0), (2.6, 4.0, 0.0), (2.6, 4.0, 3.0), (-2.6, 4.0, 3.0)],
        [(5.40, 4.0, 0.2), (6.30, 4.0, 0.2), (6.30, 4.0, 2.2), (5.40, 4.0, 2.2)],
        [(-1.1, 5.2, 3.60), (1.1, 5.2, 3.60), (1.1, 6.7, 3.60), (-1.1, 6.7, 3.60)],
        [(-2.1, 5.0, 0.45), (-1.1, 5.0, 0.45), (-1.1, 5.0, 1.65), (-2.1, 5.0, 1.65)],
        [(1.0, 6.0, 0.5), (1.0, 6.0, 1.7), (2.0, 6.0, 1.7), (2.0, 6.0, 0.5)],
        [(-0.35, 2.6, 1.05), (0.35, 2.6, 1.05), (0.35, 2.6, 1.75), (-0.35, 2.6, 1.75)],
    ]
    # Source faces sit just behind the render faces along their outward normal.
    source_faces = []
    for index, face in enumerate(target_faces):
        dz = 0.025 if index == 2 else 0.0
        dy = 0.035 if index != 2 else 0.0
        source_faces.append([(x, y + dy, z + dz) for x, y, z in face])
    target = _mesh_object("RND_Synthetic_Envelope", target_faces, collections["TH_RENDER"], target_mats)
    source = _mesh_object("SRC_Synthetic_Envelope", source_faces, collections["TH_SOURCE"], source_mats)
    bpy.ops.object.select_all(action="DESELECT")
    source.select_set(True)
    bpy.context.view_layer.objects.active = source
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=66.0, island_margin=0.04)
    bpy.ops.object.mode_set(mode="OBJECT")
    # The small pillar makes the fourth target face front-facing but occluded.
    _cube("SRC_Occluder", (-1.6, 1.5, 1.1), (1.25, 0.5, 2.2), collections["TH_SOURCE"], occluder_mat)

    anchor = bpy.data.objects.new("proof_anchor", None)
    collections["TH_ANCHORS"].objects.link(anchor)

    record = calibration_record()
    camera = thestra_camera.create_or_update_camera(record, scene=scene)
    _move_to(camera, collections["TH_CAMERA_PREVIEW"])
    if abs(float(camera.data.lens) - 43.0) > 1.5:
        raise AssertionError(f"proof camera lens is {camera.data.lens}, expected approximately 43mm")

    bpy.ops.object.light_add(type="AREA", location=(0.0, 0.0, 8.0))
    light = bpy.context.active_object
    light.data.energy = 900.0
    light.data.shape = "DISK"
    light.data.size = 8.0
    _move_to(light, collections["TH_SOURCE"])
    scene.world = bpy.data.worlds.new("ProofWorld")
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    if background:
        background.inputs["Color"].default_value = (0.015, 0.015, 0.02, 1.0)
        background.inputs["Strength"].default_value = 0.15
    scene.render.film_transparent = False
    scene.render.resolution_x = 426
    scene.render.resolution_y = 240
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene["proof_surface_labels"] = json.dumps(LABELS)
    scene["proof_camera_contract"] = "thestra.world-camera-calibration"
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    return {"target": target.name, "source": source.name, "camera": camera.name, "record": record}


def envelope():
    from view_weighted_atlas import ViewSample

    return [
        ViewSample("center", weight=1.0, cost=0.0),
        ViewSample("window-left", weight=0.7, cost=0.55, projection_window_offset_x=-96.0),
        ViewSample("window-right", weight=0.7, cost=0.55, projection_window_offset_x=96.0),
        ViewSample("eye-up", weight=0.65, cost=0.60, eye_offset=(0.0, 0.0, 0.45)),
        ViewSample("pitch-up", weight=0.45, cost=0.70, pitch_deg=-3.0),
    ]


def _set_collection_visibility(collection, visible):
    collection.hide_render = not visible
    for obj in collection.objects:
        obj.hide_render = not visible


def _render(scene, camera, sample, output_path, *, source, target):
    import bpy
    import second_gate_render
    import view_weighted_atlas

    source_collection = bpy.data.collections["TH_SOURCE"]
    render_collection = bpy.data.collections["TH_RENDER"]
    # Keep the source lights active for both matched renders; only source mesh
    # and runtime target geometry change.  This makes the A/B a material/UV
    # comparison instead of accidentally comparing lit source to unlit runtime.
    source_collection.hide_render = False
    for obj in source_collection.objects:
        obj.hide_render = (obj.type == "MESH" and not source)
    render_collection.hide_render = False
    target.hide_render = source
    second_gate_render.apply(scene, "clay")
    base_state = view_weighted_atlas._camera_state(camera)
    view_weighted_atlas._apply_view(scene, camera, sample, base_state)
    scene.render.filepath = str(output_path)
    bpy.ops.render.render(write_still=True)
    view_weighted_atlas._restore_camera(scene, camera, base_state)


def run_mode(base_path: Path, output: Path, mode: str) -> dict:
    import bpy
    import town_environment_pipeline
    import view_weighted_atlas

    bpy.ops.wm.open_mainfile(filepath=str(base_path))
    scene = bpy.context.scene
    samples = envelope()
    started = time.perf_counter()
    town_environment_pipeline.run_pipeline_in_blender(
        base_path,
        output,
        atlas_size=256,
        bake_samples=4,
        render_profile="cycles-draft",
        atlas_allocation=mode,
        camera_envelope=samples if mode == "view-weighted" else None,
        view_policy="bounded-camera",
        explicitly_unreachable=(5,),
        margin_px=4,
    )
    manifest = json.loads((output / "environment.json").read_text(encoding="utf-8"))
    allocation = manifest["allocation"]
    if allocation["packing"]["uvIslandCount"] != 6:
        raise AssertionError("proof fixture did not retain one atlas island per face")
    if manifest["stats"]["textureDimensions"] != [256, 256]:
        raise AssertionError("proof atlas is not the requested 256x256 size")
    if mode == "view-weighted":
        demands = {row["faceIndex"]: row for row in allocation["faceDemands"]}
        if {row["category"] for row in demands.values()} != {
            "visible-in-envelope", "occluded", "strongly-back-facing", "unreachable",
        }:
            raise AssertionError("view proof did not exercise every allocation category")
        by_name = {
            row["sample"]: row
            for row in demands[1]["observations"]
        }
        if not by_name["window-left"]["inFrame"] or any(
            by_name[name]["inFrame"] for name in ("center", "window-right")
        ):
            raise AssertionError("projection-extreme did not isolate the left window sample")
        by_name = {
            row["sample"]: row
            for row in demands[2]["observations"]
        }
        if not by_name["eye-up"]["inFrame"] or any(
            by_name[name]["inFrame"]
            for name in ("center", "window-left", "window-right", "pitch-up")
        ):
            raise AssertionError("top-reveal did not isolate the eye-up sample")
        if demands[3]["category"] != "occluded":
            raise AssertionError("occluded proof face lost its occlusion category")
        if demands[4]["category"] != "strongly-back-facing":
            raise AssertionError("rear proof face lost its orientation category")
        if demands[5]["category"] != "unreachable":
            raise AssertionError("explicit unreachable proof face was not retained as such")
    target = next(obj for obj in bpy.data.collections["TH_RENDER"].objects if obj.type == "MESH")
    camera = scene.camera
    frames = []
    for sample in samples:
        source_path = output / f"source_{sample.name}.png"
        runtime_path = output / f"runtime_{sample.name}.png"
        _render(scene, camera, sample, source_path, source=True, target=target)
        _render(scene, camera, sample, runtime_path, source=False, target=target)
        frames.append({"name": sample.name, "source": source_path.name, "runtime": runtime_path.name})
    measurement = {}
    source_collection = bpy.data.collections["TH_SOURCE"]
    for obj in source_collection.objects:
        obj.hide_set(True)
    try:
        areas, observations = view_weighted_atlas.measure_envelope(scene, camera, target, samples)
        sweep = {}
        for preset in ("free-camera", "bounded-camera", "fixed-camera"):
            policy = view_weighted_atlas.policy_from_preset(preset)
            demands = view_weighted_atlas.allocate_demands(areas, observations, policy, explicitly_unreachable=(5,))
            sweep[preset] = {
                "policy": policy.to_record(),
                "densityByFace": [d.density_multiplier for d in demands],
                "categoryByFace": [d.category for d in demands],
            }
        bounded = view_weighted_atlas.policy_from_preset("bounded-camera")
        parameter_sweep = {}
        for name, policy in {
            "bias-low": replace(bounded, view_bias=0.50),
            "bias-high": replace(bounded, view_bias=0.80),
            "floor-low": replace(bounded, min_density=0.05),
            "floor-high": replace(bounded, min_density=0.12),
            "expected-heavy": replace(bounded, peak_mix=0.15),
            "peak-heavy": replace(bounded, peak_mix=0.55),
            "movement-soft": replace(bounded, movement_falloff=1.0),
            "movement-hard": replace(bounded, movement_falloff=2.5),
        }.items():
            demands = view_weighted_atlas.allocate_demands(
                areas, observations, policy, explicitly_unreachable=(5,)
            )
            parameter_sweep[name] = {
                "policy": policy.to_record(),
                "densityByFace": [d.density_multiplier for d in demands],
            }
        measurement = {"sweep": sweep, "parameterSweep": parameter_sweep}
    finally:
        for obj in source_collection.objects:
            obj.hide_set(False)
    manifest["proof"] = {
        "mode": mode,
        "fixture": "disposable-synthetic-envelope",
        "surfaceLabels": LABELS,
        "frames": frames,
        "elapsedSeconds": round(time.perf_counter() - started, 4),
        **measurement,
    }
    (output / "manifest-with-proof.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def run_facade_proof(base_path: Path, output: Path) -> dict:
    """Run the external-image -> projection -> ordinary-UV bake seam."""

    import bpy
    import facade_projection

    bpy.ops.wm.open_mainfile(filepath=str(base_path))
    scene = bpy.context.scene
    output.mkdir(parents=True, exist_ok=True)
    generated_path = output / "external_generated_facade.png"
    generated = bpy.data.images.new("ExternalGeneratedFacade", width=64, height=64, alpha=True)
    pixels = []
    for y in range(64):
        for x in range(64):
            pixels.extend((0.15 + 0.65 * x / 63.0, 0.12 + 0.55 * y / 63.0, 0.28, 1.0))
    generated.pixels = pixels
    generated.filepath_raw = str(generated_path)
    generated.file_format = "PNG"
    generated.save()
    control = facade_projection.export_control_packet(
        scene, scene.camera, output / "control", profile="clay"
    )
    spec = facade_projection.ProjectionSpec(
        target_objects=("SRC_Synthetic_Envelope",),
        face_indices={"SRC_Synthetic_Envelope": (0,)},
        bake_width=64,
        bake_height=64,
    )
    manifest = facade_projection.project_generated_facade(
        scene,
        scene.camera,
        facade_projection.GeneratedFacadeInput(
            image=generated_path,
            provider="disposable-synthetic-provider",
            model="fixture-pattern",
            prompt="synthetic facade proof",
            seed=7,
        ),
        spec,
        output / "projection",
        control_packet=control,
        source_blend_name=base_path.name,
    )
    if not (output / "projection" / "projection_inspection.blend").is_file():
        raise AssertionError("facade projection did not write its derived inspection blend")
    return {
        "control": control,
        "projection": manifest,
    }


def _image_difference(left: Path, right: Path) -> dict:
    import bpy

    first = bpy.data.images.load(str(left), check_existing=False)
    second = bpy.data.images.load(str(right), check_existing=False)
    if tuple(first.size) != tuple(second.size):
        raise AssertionError(f"matched render size mismatch: {first.size} != {second.size}")
    image_size = list(first.size)
    first_pixels = list(first.pixels)
    second_pixels = list(second.pixels)
    deltas = [abs(a - b) for a, b in zip(first_pixels, second_pixels)]
    changed = sum(
        1
        for index in range(0, len(deltas), 4)
        if max(deltas[index:index + 4]) > 1.0 / 255.0
    )
    mean_delta = sum(deltas) / max(len(deltas), 1)
    bpy.data.images.remove(first)
    bpy.data.images.remove(second)
    return {
        "size": image_size,
        "meanAbsoluteChannelDelta": mean_delta,
        "changedPixels": changed,
    }


def run_inside_blender(output: Path) -> None:
    import bpy

    output.mkdir(parents=True, exist_ok=True)
    base_path = output / "synthetic_envelope.blend"
    build_fixture(base_path)
    area = run_mode(base_path, output / "area", "area")
    view = run_mode(base_path, output / "view-weighted", "view-weighted")
    facade = run_facade_proof(base_path, output / "facade")
    result = {
        "fixture": str(base_path),
        "atlas": {"area": area, "viewWeighted": view},
        "facade": facade,
        "comparison": [
            {
                "name": frame["name"],
                "area": _image_difference(output / "area" / frame["runtime"], output / "area" / frame["source"]),
                "viewWeighted": _image_difference(output / "view-weighted" / frame["runtime"], output / "view-weighted" / frame["source"]),
            }
            for frame in area["proof"]["frames"]
        ],
    }
    for row in result["comparison"]:
        row["allocatorAB"] = _image_difference(
            output / "area" / f"runtime_{row['name']}.png",
            output / "view-weighted" / f"runtime_{row['name']}.png",
        )
    (output / "proof.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("VIEW_WEIGHTED_ATLAS_BLENDER_PROOF OK")
    print(json.dumps(result, indent=2))


def main() -> None:
    try:
        import bpy  # noqa: F401
        in_blender = True
    except ImportError:
        in_blender = False
    output = ROOT / "out" / "blender" / "view-weighted-ab"
    if not in_blender:
        command = [
            blender_executable(), "--background", "--factory-startup",
            "--python", str(Path(__file__).resolve()), "--",
            "--output", str(output),
        ]
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
        print(result.stdout)
        if result.returncode:
            print(result.stderr, file=sys.stderr)
            raise SystemExit(result.returncode)
        return
    # Blender's argv after -- is intentionally not needed; the default output
    # is deterministic and disposable.  A later wrapper can add --output.
    run_inside_blender(output)


if __name__ == "__main__":
    main()
