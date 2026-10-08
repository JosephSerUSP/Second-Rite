import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[1] / "semantics" / "environment_walk_surface.py"
SPEC = importlib.util.spec_from_file_location("environment_walk_surface", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_compile_polygons_preserves_order_and_plane():
    faces = [
        [(0, 0, 1.25), (3, 0, 1.25), (3, 2, 1.25), (0, 2, 1.25)],
        [(4, 0, 1.25), (5, 0, 1.25), (4.5, 1, 1.25)],
    ]
    polygons, ground_z = MODULE.compile_polygons(faces, "walk")
    assert ground_z == pytest.approx(1.25)
    assert polygons == [
        {"points": [[0.0, 0.0], [3.0, 0.0], [3.0, 2.0], [0.0, 2.0]]},
        {"points": [[4.0, 0.0], [5.0, 0.0], [4.5, 1.0]]},
    ]


def test_compile_polygons_rejects_nonplanar_walk_geometry():
    with pytest.raises(ValueError, match="must be planar"):
        MODULE.compile_polygons(
            [[(0, 0, 0), (1, 0, 0), (0, 1, 0.2)]],
            "walk",
        )


def test_obstacles_must_share_walk_plane():
    with pytest.raises(ValueError, match="must be planar"):
        MODULE.compile_polygons(
            [[(0, 0, 0.1), (1, 0, 0.1), (0, 1, 0.1)]],
            "obstacles",
            plane_z=0,
        )


def test_compile_polygons_rejects_short_faces():
    with pytest.raises(ValueError, match="at least 3 vertices"):
        MODULE.compile_polygons([[(0, 0, 0), (1, 0, 0)]], "walk")
