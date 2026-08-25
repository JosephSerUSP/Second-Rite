"""Run inside Blender: compare Blender projection against the Lua-owned parity fixture."""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--fixture", required=True)
    return parser.parse_args(argv)


def transform_tuple(obj):
    matrix = obj.matrix_world
    return tuple(float(matrix[r][c]) for r in range(4) for c in range(4))


def max_transform_delta(a, b):
    return max(abs(x - y) for x, y in zip(a, b))


def record_for_offset(base, offset):
    record = copy.deepcopy(base)
    record["viewportCenterX"] = float(base["viewportCenterX"]) + float(offset)
    record["projectionWindowOffsetX"] = float(offset)
    return record


def main():
    args = parse_args()
    root = Path(args.root).resolve()
    sys.path.insert(0, str(root / "tools" / "blender"))
    import thestra_camera
    import bpy
    from mathutils import Vector

    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    scene = bpy.context.scene
    tolerance = float(fixture.get("pixelTolerance", 1e-4))
    base_transform = None
    maximum_error = 0.0

    for offset in fixture["offsets"]:
        record = record_for_offset(fixture["camera"], offset)
        camera = thestra_camera.create_or_update_camera(record, scene=scene)
        current_transform = transform_tuple(camera)
        if base_transform is None:
            base_transform = current_transform
        elif max_transform_delta(base_transform, current_transform) > 1e-10:
            raise AssertionError("projection-window offset moved TH_CAMERA_PREVIEW transform")
        for sample in fixture["samples"]:
            actual = thestra_camera.project_world_point(scene, camera, sample["world"])
            expected = (sample["screenAtZero"][0] + float(offset), sample["screenAtZero"][1])
            error = max(abs(actual[0] - expected[0]), abs(actual[1] - expected[1]))
            maximum_error = max(maximum_error, error)
            if error > tolerance:
                raise AssertionError(
                    f"offset {offset:+g} {sample['name']} error {error:.9g}px: "
                    f"actual={actual}, expected={expected}"
                )

    camera = thestra_camera.create_or_update_camera(fixture["camera"], scene=scene)
    sample = next(sample for sample in fixture["samples"] if sample["name"] == "mixed")
    expected = sample["screenAtZero"]

    original_shift = camera.data.shift_x
    camera.data.shift_x = original_shift + 0.02
    wrong_shift = thestra_camera.project_world_point(scene, camera, sample["world"])
    camera.data.shift_x = original_shift
    shift_error = max(abs(wrong_shift[0] - expected[0]), abs(wrong_shift[1] - expected[1]))
    if shift_error <= tolerance:
        raise AssertionError("negative control: deliberately wrong lens shift did not fail parity")

    original_location = camera.location.copy()
    camera.location.x += 0.25
    bpy.context.view_layer.update()
    wrong_translation = thestra_camera.project_world_point(scene, camera, sample["world"])
    camera.location = original_location
    bpy.context.view_layer.update()
    translation_error = max(abs(wrong_translation[0] - expected[0]),
                            abs(wrong_translation[1] - expected[1]))
    if translation_error <= tolerance:
        raise AssertionError("negative control: deliberately translated camera did not fail parity")

    # #927: the resolved camera basis exercised by this fixture includes a
    # reflection. Quaternions cannot represent that reflection, so a preview
    # actor must preserve the camera's 3x3 basis rather than round-tripping it
    # through matrix_world.to_quaternion().
    camera_basis_det = float(camera.matrix_world.to_3x3().determinant())
    if camera_basis_det >= -1e-6:
        raise AssertionError(
            "actor-orientation fixture no longer exercises a reflected camera basis"
        )

    walker = root / "projects" / "hichaukitoden-game" / "assets" / "character" / "walker.png"
    anchor = Vector(sample["world"])
    actor = thestra_camera.create_actor_preview(
        walker, camera, anchor=anchor, frame_width=24, frame_height=48,
        frame_index=0, world_height=1.0,
    )
    bpy.context.view_layer.update()

    feet_world = actor.matrix_world @ Vector((0.0, 0.0, 0.0))
    top_world = actor.matrix_world @ Vector((0.0, 1.0, 0.0))
    feet_screen = thestra_camera.project_world_point(scene, camera, feet_world)
    top_screen = thestra_camera.project_world_point(scene, camera, top_world)
    if top_screen[1] >= feet_screen[1]:
        raise AssertionError(
            "TH_ACTOR_PREVIEW local +Y does not project screen-up from its feet anchor"
        )

    actor_basis_det = float(actor.matrix_world.to_3x3().determinant())
    if actor_basis_det >= -1e-6:
        raise AssertionError("TH_ACTOR_PREVIEW dropped the reflected camera basis")

    # Regression negative control: reproduce the old quaternion-only transform
    # without mutating the actual actor. On this reflected fixture it maps local
    # +Y below the feet anchor; if it ever stops doing so, this fixture no longer
    # proves the bug that #927 guards.
    quaternion_up = camera.matrix_world.to_quaternion() @ Vector((0.0, 1.0, 0.0))
    quaternion_top_screen = thestra_camera.project_world_point(
        scene, camera, anchor + quaternion_up
    )
    if quaternion_top_screen[1] < feet_screen[1]:
        raise AssertionError(
            "negative control: quaternion-only actor transform unexpectedly projects screen-up"
        )

    print(json.dumps({
        "status": "passed",
        "offsetCases": len(fixture["offsets"]),
        "samplesPerCase": len(fixture["samples"]),
        "maxPixelError": maximum_error,
        "wrongShiftError": shift_error,
        "wrongTranslationError": translation_error,
        "transformInvariant": True,
        "actorScreenUp": True,
        "cameraBasisDeterminant": camera_basis_det,
        "actorBasisDeterminant": actor_basis_det,
        "quaternionNegativeControlDeltaY": quaternion_top_screen[1] - feet_screen[1],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
