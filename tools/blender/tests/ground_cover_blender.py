"""Blender-side probe for the Geometry Nodes ground cover (#1257).

Run by ``test_ground_cover.py`` through the pinned headless Blender: a node
tree only evaluates inside Blender, so the assertions live here as measurements
of the realised mesh.  Prints one JSON object per scenario; the runner asserts.

A tuft is realised as two crossed quads (8 vertices).  Its root is the mean of
the four lowest corners, which is where the card meets the ground.
"""
import json
import math
import sys
import traceback
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender"))

import ground_cover  # noqa: E402

VERTS_PER_TUFT = 8
LANE_CENTRE = (-3.0, 0.0)
LANE_HALF = 1.0
MARGIN = 0.5


def build_scene():
    """A 10x10 ground with a ridge along +x, a painted half and a lane object."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=20, y_subdivisions=20,
                                    size=10.0, location=(0.0, 0.0, 0.0))
    ground = bpy.context.object
    ground.name = "GROUND"
    for vertex in ground.data.vertices:
        vertex.co.z = max(0.0, vertex.co.x) * 0.6
    group = ground.vertex_groups.new(name="cover_density")
    for vertex in ground.data.vertices:
        # Painted for x < 1.75 (a vertex at exactly 2.0 must not round into it), bare beyond, so the ridge foot and
        # the ridge itself are both in play against the slope limit.
        group.add([vertex.index], 1.0 if vertex.co.x < 1.75 else 0.0, "REPLACE")
    bpy.ops.mesh.primitive_cube_add(size=2.0 * LANE_HALF,
                                    location=(LANE_CENTRE[0], LANE_CENTRE[1], 0.0))
    lane = bpy.context.object
    lane.name = "LANE"
    keep_out = bpy.data.collections.new(ground_cover.KEEP_OUT_COLLECTION)
    for owner in list(lane.users_collection):
        owner.objects.unlink(lane)
    keep_out.objects.link(lane)
    return ground, keep_out


def tufts(host):
    """Root positions of every realised tuft, and the raw vertex list."""
    mesh = ground_cover.evaluated_mesh(host)
    points = [tuple(v.co) for v in mesh.vertices]
    assert len(points) % VERTS_PER_TUFT == 0, len(points)
    roots = []
    for start in range(0, len(points), VERTS_PER_TUFT):
        corners = sorted(points[start:start + VERTS_PER_TUFT], key=lambda c: c[2])[:4]
        roots.append(tuple(sum(c[axis] for c in corners) / 4 for axis in range(3)))
    return roots, points


def ground_hit(ground, x, y):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = ground.evaluated_get(depsgraph)
    hit, location, normal, _face = evaluated.ray_cast(Vector((x, y, 50.0)),
                                                      Vector((0.0, 0.0, -1.0)))
    return (location.z, normal.z) if hit else (None, None)


def outside_lane_distance(x, y):
    """Distance from (x, y) to the lane footprint; 0 when inside it."""
    dx = max(abs(x - LANE_CENTRE[0]) - LANE_HALF, 0.0)
    dy = max(abs(y - LANE_CENTRE[1]) - LANE_HALF, 0.0)
    return math.hypot(dx, dy)


def main():
    result = {}
    try:
        ground, keep_out = build_scene()
        slope_limit = 25.0
        host = ground_cover.add(
            ground, keep_out=keep_out, density_group="cover_density",
            **{"Density": 8.0, "Slope Limit": slope_limit, "Max Tufts": 5000,
               "Keep Out Margin": MARGIN, "Lean": 0.0, "Seed": 4})
        roots, points = tufts(host)
        result["tufts"] = len(roots)
        result["vertices"] = len(points)

        floor = math.cos(math.radians(slope_limit))
        normals, errors = [], []
        for x, y, z in roots:
            height, normal_z = ground_hit(ground, x, y)
            normals.append(normal_z)
            errors.append(abs(z - height))
        result["min_normal_z"] = round(min(normals), 4)
        result["slope_floor"] = round(floor, 4)
        result["max_height_error"] = round(max(errors), 6)
        result["roots_inside_lane"] = sum(
            1 for x, y, _ in roots if outside_lane_distance(x, y) < MARGIN - 1e-3)
        result["roots_painted_side"] = sum(1 for x, _, _ in roots if x < 2.0)
        result["roots_bare_side"] = sum(1 for x, _, _ in roots if x > 2.0 + 1e-3)
        result["roots_on_ridge"] = sum(1 for x, _, _ in roots if x > 0.0)

        # Determinism: same document, same seed, identical realised geometry.
        again = tufts(host)[1]
        result["repeatable"] = again == points
        ground_cover.configure(host, **{"Seed": 5})
        result["seed_changes_layout"] = tufts(host)[1] != points
        ground_cover.configure(host, **{"Seed": 4})
        result["seed_restores_layout"] = tufts(host)[1] == points

        # Budget: the authored ceiling is honoured exactly.
        ground_cover.configure(host, **{"Max Tufts": 10})
        result["budgeted_vertices"] = len(tufts(host)[1])
        ground_cover.configure(host, **{"Max Tufts": 5000})

        # Controls: with the slope limit lifted the ridge roots, so the slope
        # limit -- not the density or the paint -- is what kept it bare above.
        ground_cover.configure(host, **{"Slope Limit": 89.0})
        lifted, _ = tufts(host)
        result["ridge_roots_without_limit"] = sum(1 for x, _, _ in lifted if x > 0.0)
        result["bare_side_with_paint_without_limit"] = sum(
            1 for x, _, _ in lifted if x > 2.0 + 1e-3)
        # No painted group: the flat density applies everywhere it may root.
        ground_cover.configure(host, **{"Density Group": ""})
        unpainted, _ = tufts(host)
        result["unpainted_bare_side"] = sum(1 for x, _, _ in unpainted if x > 2.0 + 1e-3)
        ground_cover.configure(host, **{"Slope Limit": slope_limit})

        # An empty keep-out culls nothing.
        ground_cover.configure(host, **{"Density Group": "cover_density"})
        with_lane = len(tufts(host)[0])
        empty = bpy.data.collections.new("EMPTY_KEEP_OUT")
        ground_cover.configure(host, **{"Keep Out": empty})
        result["empty_keep_out_gains"] = len(tufts(host)[0]) - with_lane
        result["ok"] = True
    except Exception:
        result["ok"] = False
        result["error"] = traceback.format_exc()
    print("GROUND_COVER_PROBE " + json.dumps(result))


main()
