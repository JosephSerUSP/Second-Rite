#!/usr/bin/env python3
"""tests/test_blender_camera_parity.py.

Numerical parity test suite proving exact equivalence between Thestra WorldCamera
and Blender camera preview (TH_CAMERA_PREVIEW), plus 24x48 actor preview calibration.

Can be run via:
  blender --background --factory-startup --python tests/test_blender_camera_parity.py
"""

from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "blender"))

import bpy
import mathutils
import thestra_camera


def generate_first_person_record(
    shift_x: float = 0.0,
    target_w: int = 426,
    target_h: int = 240,
    base_w: int = 256,
    base_h: int = 144,
    fov_scale: float = 1.0,
) -> dict:
    """Generate a first-person calibration record matching Thestra world_camera.resolveFirstPerson."""
    eye = [5.0, 5.0, 0.5]
    # Direction North: dirX=0, dirY=-1, rightX=1, rightY=0, pitch=0
    return {
        "coordinateSystem": "thestra_world_z_up",
        "projection": "perspective",
        "profile": "first_person",
        "eye": eye,
        "forward": [0.0, -1.0, 0.0],
        "right": [1.0, 0.0, 0.0],
        "up": [0.0, 0.0, 1.0],
        "yaw": -math.pi * 0.5,
        "pitch": 0.0,
        "dirX": 0.0,
        "dirY": -1.0,
        "rightX": 1.0,
        "rightY": 0.0,
        "fovHalfX": 0.75 * fov_scale,
        "fovHalfY": (144.0 / 256.0 * 0.75) * fov_scale,
        "fovDegrees": math.degrees(2.0 * math.atan(0.75 * fov_scale)),
        "orthoHalfX": 1.0,
        "orthoHalfY": 1.0,
        "projectionScaleX": 1.0,
        "projectionScaleY": 1.0,
        "nearPlane": 0.05,
        "farPlane": 32.0,
        "targetWidth": target_w,
        "targetHeight": target_h,
        "baseViewportWidth": base_w,
        "baseViewportHeight": base_h,
        "viewportCenterX": (target_w * 0.5) + shift_x,
        "viewportCenterY": 70.0,
        "projectionWindowOffsetX": shift_x,
        "projectionWindowOffsetY": 0.0,
    }


def generate_overhead_perspective_record(
    shift_x: float = 0.0,
    pitch_deg: float = 45.0,
    fov_deg: float = 26.0,
    target_w: int = 426,
    target_h: int = 240,
    base_w: int = 256,
    base_h: int = 144,
) -> dict:
    """Generate an overhead perspective calibration record matching Thestra world_camera.resolveOverhead."""
    pitch = math.radians(pitch_deg)
    yaw = -math.pi * 0.5  # North
    dir_x, dir_y = math.cos(yaw), math.sin(yaw)
    right_x, right_y = -dir_y, dir_x

    cos_p = math.cos(pitch)
    sin_p = math.sin(pitch)

    forward = [dir_x * cos_p, dir_y * cos_p, -sin_p]
    right = [right_x, right_y, 0.0]
    up = [dir_x * sin_p, dir_y * sin_p, cos_p]

    height = 6.0
    ground_dist = height / math.tan(pitch)
    target = [5.0, 5.0, 0.0]
    eye = [target[0] - dir_x * ground_dist, target[1] - dir_y * ground_dist, target[2] + height]

    fov_half_x = math.tan(math.radians(fov_deg) * 0.5)
    fov_half_y = fov_half_x * (base_h / base_w)

    return {
        "coordinateSystem": "thestra_world_z_up",
        "projection": "perspective",
        "profile": "perspective_oblique",
        "eye": eye,
        "target": target,
        "forward": forward,
        "right": right,
        "up": up,
        "yaw": yaw,
        "pitch": pitch,
        "dirX": dir_x,
        "dirY": dir_y,
        "rightX": right_x,
        "rightY": right_y,
        "fovHalfX": fov_half_x,
        "fovHalfY": fov_half_y,
        "fovDegrees": fov_deg,
        "orthoHalfX": 6.0,
        "orthoHalfY": 6.0 * (base_h / base_w),
        "projectionScaleX": 1.0,
        "projectionScaleY": 1.0,
        "nearPlane": 0.05,
        "farPlane": 64.0,
        "targetWidth": target_w,
        "targetHeight": target_h,
        "baseViewportWidth": base_w,
        "baseViewportHeight": base_h,
        "viewportCenterX": (target_w * 0.5) + shift_x,
        "viewportCenterY": 70.0,
        "projectionWindowOffsetX": shift_x,
        "projectionWindowOffsetY": 0.0,
    }


def generate_overhead_orthographic_record(
    shift_x: float = 0.0,
    pitch_deg: float = 45.0,
    target_w: int = 426,
    target_h: int = 240,
    base_w: int = 256,
    base_h: int = 144,
) -> dict:
    """Generate an overhead orthographic calibration record matching Thestra world_camera.resolveOverhead."""
    pitch = math.radians(pitch_deg)
    yaw = -math.pi * 0.5  # North
    dir_x, dir_y = math.cos(yaw), math.sin(yaw)
    right_x, right_y = -dir_y, dir_x

    cos_p = math.cos(pitch)
    sin_p = math.sin(pitch)

    forward = [dir_x * cos_p, dir_y * cos_p, -sin_p]
    right = [right_x, right_y, 0.0]
    up = [dir_x * sin_p, dir_y * sin_p, cos_p]

    height = 6.0
    ground_dist = height / math.tan(pitch)
    target = [5.0, 5.0, 0.0]
    eye = [target[0] - dir_x * ground_dist, target[1] - dir_y * ground_dist, target[2] + height]

    ortho_half_x = 6.0
    ortho_half_y = 6.0 * (base_h / base_w)

    return {
        "coordinateSystem": "thestra_world_z_up",
        "projection": "orthographic",
        "profile": "ortho_oblique",
        "eye": eye,
        "target": target,
        "forward": forward,
        "right": right,
        "up": up,
        "yaw": yaw,
        "pitch": pitch,
        "dirX": dir_x,
        "dirY": dir_y,
        "rightX": right_x,
        "rightY": right_y,
        "fovHalfX": 0.75,
        "fovHalfY": 0.421875,
        "fovDegrees": 73.74,
        "orthoHalfX": ortho_half_x,
        "orthoHalfY": ortho_half_y,
        "projectionScaleX": 1.0,
        "projectionScaleY": 1.0,
        "nearPlane": 0.05,
        "farPlane": 32.0,
        "targetWidth": target_w,
        "targetHeight": target_h,
        "baseViewportWidth": base_w,
        "baseViewportHeight": base_h,
        "viewportCenterX": (target_w * 0.5) + shift_x,
        "viewportCenterY": 70.0,
        "projectionWindowOffsetX": shift_x,
        "projectionWindowOffsetY": 0.0,
    }


class BlenderCameraParityTests(unittest.TestCase):
    def setUp(self):
        # Reset scene to clean state
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.scene = bpy.context.scene

    def test_first_person_numerical_parity_and_shifts(self):
        """Test optical-center, lateral points, near/far, and heights across shifts (-96, -48, 0, 48, 96)."""
        shifts = [-96, -48, 0, 48, 96]
        depths = [0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0]
        laterals = [-3.0, -1.5, -0.5, 0.0, 0.5, 1.5, 3.0]
        heights = [0.0, 0.5, 1.0, 2.5]

        for shift in shifts:
            record = generate_first_person_record(shift_x=shift)
            cam_obj = thestra_camera.apply_thestra_camera(record, scene=self.scene)

            # 1. Optical Center Point at depth 4.0
            opt_pt = (record["eye"][0], record["eye"][1] - 4.0, record["eye"][2])
            b_x, b_y, _ = thestra_camera.project_world_point_blender(self.scene, cam_obj, opt_pt)
            t_x, t_y, _ = thestra_camera.project_world_point_thestra(record, opt_pt)

            self.assertAlmostEqual(b_x, t_x, delta=1e-3, msg=f"Optical center X mismatch at shift {shift}")
            self.assertAlmostEqual(b_y, t_y, delta=1e-3, msg=f"Optical center Y mismatch at shift {shift}")

            # 2. Comprehensive grid of spatial points
            for d in depths:
                for lat in laterals:
                    for h in heights:
                        pw = (record["eye"][0] + lat, record["eye"][1] - d, h)
                        b_sx, b_sy, _ = thestra_camera.project_world_point_blender(self.scene, cam_obj, pw)
                        t_sx, t_sy, _ = thestra_camera.project_world_point_thestra(record, pw)

                        self.assertAlmostEqual(
                            b_sx, t_sx, delta=1e-3,
                            msg=f"Screen X mismatch at shift={shift}, depth={d}, lateral={lat}, height={h}"
                        )
                        self.assertAlmostEqual(
                            b_sy, t_sy, delta=1e-3,
                            msg=f"Screen Y mismatch at shift={shift}, depth={d}, lateral={lat}, height={h}"
                        )

    def test_overhead_perspective_numerical_parity(self):
        """Test pitched overhead perspective camera across multiple FOVs and offsets."""
        fovs = [26.0, 50.0, 75.0]
        shifts = [-96, -48, 0, 48, 96]
        pitches = [30.0, 45.0, 60.0]

        for fov in fovs:
            for pitch in pitches:
                for shift in shifts:
                    record = generate_overhead_perspective_record(shift_x=shift, pitch_deg=pitch, fov_deg=fov)
                    cam_obj = thestra_camera.apply_thestra_camera(record, scene=self.scene)

                    # Target point
                    tgt = record["target"]
                    b_sx, b_sy, _ = thestra_camera.project_world_point_blender(self.scene, cam_obj, tgt)
                    t_sx, t_sy, _ = thestra_camera.project_world_point_thestra(record, tgt)

                    self.assertAlmostEqual(b_sx, t_sx, delta=1e-3, msg=f"Target X mismatch fov={fov} pitch={pitch} shift={shift}")
                    self.assertAlmostEqual(b_sy, t_sy, delta=1e-3, msg=f"Target Y mismatch fov={fov} pitch={pitch} shift={shift}")

                    # Offset ground and height points
                    test_pts = [
                        (tgt[0] + 2.0, tgt[1], tgt[2]),
                        (tgt[0] - 2.0, tgt[1], tgt[2]),
                        (tgt[0], tgt[1] + 2.0, tgt[2] + 1.0),
                        (tgt[0] + 1.0, tgt[1] - 3.0, tgt[2] + 2.0),
                    ]
                    for pt in test_pts:
                        bs_x, bs_y, _ = thestra_camera.project_world_point_blender(self.scene, cam_obj, pt)
                        ts_x, ts_y, _ = thestra_camera.project_world_point_thestra(record, pt)
                        self.assertAlmostEqual(bs_x, ts_x, delta=1e-3, msg=f"Point {pt} mismatch fov={fov} shift={shift}")
                        self.assertAlmostEqual(bs_y, ts_y, delta=1e-3, msg=f"Point {pt} mismatch fov={fov} shift={shift}")

    def test_overhead_orthographic_numerical_parity(self):
        """Test orthographic camera numerical parity."""
        shifts = [-96, -48, 0, 48, 96]
        for shift in shifts:
            record = generate_overhead_orthographic_record(shift_x=shift)
            cam_obj = thestra_camera.apply_thestra_camera(record, scene=self.scene)

            tgt = record["target"]
            test_pts = [
                (tgt[0], tgt[1], tgt[2]),
                (tgt[0] + 3.0, tgt[1], tgt[2]),
                (tgt[0] - 3.0, tgt[1], tgt[2]),
                (tgt[0], tgt[1] + 2.0, tgt[2] + 1.5),
            ]
            for pt in test_pts:
                bs_x, bs_y, _ = thestra_camera.project_world_point_blender(self.scene, cam_obj, pt)
                ts_x, ts_y, _ = thestra_camera.project_world_point_thestra(record, pt)
                self.assertAlmostEqual(bs_x, ts_x, delta=1e-3, msg=f"Ortho point {pt} mismatch at shift={shift}")
                self.assertAlmostEqual(bs_y, ts_y, delta=1e-3, msg=f"Ortho point {pt} mismatch at shift={shift}")

    def test_changing_offset_does_not_move_camera_transform(self):
        """Prove changing projection-window offset leaves Blender camera matrix_world strictly invariant."""
        base_record = generate_first_person_record(shift_x=0)
        base_cam = thestra_camera.apply_thestra_camera(base_record, scene=self.scene)
        base_mat = [list(row) for row in base_cam.matrix_world]

        for shift in [-96, -48, -16, 16, 48, 96]:
            shifted_record = generate_first_person_record(shift_x=shift)
            shifted_cam = thestra_camera.apply_thestra_camera(shifted_record, scene=self.scene)
            shifted_mat = [list(row) for row in shifted_cam.matrix_world]

            for r in range(4):
                for c in range(4):
                    self.assertAlmostEqual(
                        base_mat[r][c], shifted_mat[r][c], places=7,
                        msg=f"Camera transform matrix row {r} col {c} changed under offset {shift}"
                    )

    def test_negative_controls(self):
        """Deliberately wrong lens shift, translation, or FOV must fail parity checks loudly."""
        record = generate_first_person_record(shift_x=48)
        cam_obj = thestra_camera.apply_thestra_camera(record, scene=self.scene)
        test_pt = (record["eye"][0] + 2.0, record["eye"][1] - 4.0, 0.5)

        # 1. Deliberately wrong lens shift
        cam_obj.data.shift_x += 0.05
        bpy.context.view_layer.update()
        b_x, _, _ = thestra_camera.project_world_point_blender(self.scene, cam_obj, test_pt)
        t_x, _, _ = thestra_camera.project_world_point_thestra(record, test_pt)
        self.assertGreater(abs(b_x - t_x), 10.0, "Corrupted shift_x must fail parity test")

        # Restore
        thestra_camera.apply_thestra_camera(record, scene=self.scene)

        # 2. Deliberately wrong camera translation
        cam_obj.location.x += 1.0
        bpy.context.view_layer.update()
        b_x, _, _ = thestra_camera.project_world_point_blender(self.scene, cam_obj, test_pt)
        t_x, _, _ = thestra_camera.project_world_point_thestra(record, test_pt)
        self.assertGreater(abs(b_x - t_x), 20.0, "Corrupted camera location must fail parity test")

        # Restore
        thestra_camera.apply_thestra_camera(record, scene=self.scene)

        # 3. Deliberately wrong focal length / lens
        cam_obj.data.lens += 5.0
        bpy.context.view_layer.update()
        b_x, _, _ = thestra_camera.project_world_point_blender(self.scene, cam_obj, test_pt)
        t_x, _, _ = thestra_camera.project_world_point_thestra(record, test_pt)
        self.assertGreater(abs(b_x - t_x), 10.0, "Corrupted lens/FOV must fail parity test")

    def test_24x48_actor_calibration_helper(self):
        """Validate 24x48 actor preview creation, layout derivation, feet anchoring, and material properties."""
        walker_path = ROOT / "projects" / "hichaukitoden-game" / "assets" / "character" / "walker.png"
        self.assertTrue(walker_path.is_file(), f"walker.png missing at {walker_path}")

        actor_obj = thestra_camera.create_actor_preview(
            image_path=walker_path, frame_index=2, width_units=1.0, height_units=2.0, scene=self.scene
        )
        self.assertIsNotNone(actor_obj)
        self.assertEqual(actor_obj.name, "TH_ACTOR_PREVIEW")

        # Vertices and feet anchor at Z=0
        mesh = actor_obj.data
        self.assertEqual(len(mesh.vertices), 4)
        z_coords = [v.co.z for v in mesh.vertices]
        min_z = min(z_coords)
        max_z = max(z_coords)
        self.assertAlmostEqual(min_z, 0.0, places=6, msg="Actor plane feet must be at world anchor Z=0")
        self.assertAlmostEqual(max_z, 2.0, places=6, msg="Actor plane top must be at Z=2.0")

        # UV coordinates for frame 2 (of 6): u in [2/6, 3/6]
        uv_data = mesh.uv_layers["UVMap"].data
        u_coords = [d.uv[0] for d in uv_data]
        self.assertAlmostEqual(min(u_coords), 2.0 / 6.0, places=5)
        self.assertAlmostEqual(max(u_coords), 3.0 / 6.0, places=5)

        # Material setup
        self.assertEqual(len(actor_obj.data.materials), 1)
        mat = actor_obj.data.materials[0]
        self.assertTrue(mat.use_nodes)
        tex_nodes = [n for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE']
        self.assertEqual(len(tex_nodes), 1)
        self.assertEqual(tex_nodes[0].interpolation, 'Closest')

        emission_nodes = [n for n in mat.node_tree.nodes if n.type == 'EMISSION']
        self.assertEqual(len(emission_nodes), 1, "Actor material must have unlit Emission shader")


def run_tests():
    suite = unittest.TestLoader().loadTestsFromTestCase(BlenderCameraParityTests)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    run_tests()
