"""Blender-side probe for the terrain-sampling adapter.

Run by ``test_terrain_surface.py`` through a headless Blender, because the
adapter exists to read real scene geometry and cannot be exercised any other
way.  Prints one JSON object; the runner asserts on it.
"""
import json
import sys
import traceback
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender"))

import grass  # noqa: E402
import terrain_surface  # noqa: E402


def build_ramp():
    """A 10x10 ground plane tilted so height and slope both vary."""
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=10, y_subdivisions=10,
                                    size=10.0, location=(0.0, 0.0, 0.0))
    ground = bpy.context.object
    ground.name = "GROUND"
    for vertex in ground.data.vertices:
        # A ridge along +x: flat at x<0, climbing steeply after.
        vertex.co.z = max(0.0, vertex.co.x) * 0.6
    return ground


def main():
    result = {}
    try:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        ground = build_ramp()

        surface = terrain_surface.mesh_surface(ground)
        flat_z, flat_n = surface(-3.0, 0.0)
        ramp_z, ramp_n = surface(3.0, 0.0)
        miss_z, _miss_n = surface(400.0, 400.0)
        result["flat_height"] = round(flat_z, 4)
        result["ramp_height"] = round(ramp_z, 4)
        result["flat_normal_z"] = round(flat_n[2], 4)
        result["ramp_normal_z"] = round(ramp_n[2], 4)
        result["miss_height"] = round(miss_z, 4)

        # Paint the flat half only, so density has a visible boundary.
        group = ground.vertex_groups.new(name="grass_density")
        for vertex in ground.data.vertices:
            group.add([vertex.index], 1.0 if vertex.co.x < 0.0 else 0.0, "REPLACE")
        mask = terrain_surface.weight_mask(ground, "grass_density")
        result["weight_painted"] = round(mask(-4.0, 0.0), 3)
        result["weight_bare"] = round(mask(4.0, 0.0), 3)

        bpy.ops.mesh.primitive_cube_add(size=2.0, location=(-3.0, 0.0, 0.0))
        lane = bpy.context.object
        lane.name = "LANE"
        keep_out = terrain_surface.keep_out_mask([lane], margin=0.5)
        result["mask_on_lane"] = keep_out(-3.0, 0.0)
        result["mask_off_lane"] = keep_out(-3.0, 4.0)

        centre_x, centre_y, width, depth = terrain_surface.patch_bounds(ground)
        result["patch"] = [round(centre_x, 3), round(centre_y, 3),
                           round(width, 3), round(depth, 3)]

        # The scatter, driven by the real ground.
        spec = grass.GrassSpec(density=8.0, seed=4, slope_limit_deg=25.0)
        verts, faces, _uvs = grass.scatter(
            spec, width, depth, origin=(centre_x, centre_y, 0.0),
            surface=surface, mask=terrain_surface.keep_out_mask([lane], margin=0.5,
                                                                inner=mask))
        result["tufts"] = len(faces) // spec.crossings
        # One root per TUFT: the crossed pair shares a base, so stepping by
        # crossings avoids counting every plant twice.
        roots = []
        for index in range(0, len(faces), spec.crossings):
            corners = [verts[i] for i in faces[index]]
            roots.append((sum(c[0] for c in corners) / 4,
                          sum(c[1] for c in corners) / 4,
                          min(c[2] for c in corners)))
        result["roots_on_painted_side"] = sum(1 for r in roots if r[0] < 0.0)
        result["roots_on_bare_side"] = sum(1 for r in roots if r[0] > 0.0)
        result["roots_inside_lane"] = sum(
            1 for r in roots if -4.0 <= r[0] <= -2.0 and -1.5 <= r[1] <= 1.5)
        # Every tuft must sit ON the ground, not at z=0 regardless of terrain.
        # Measured with no lean: a leaning card's lowest corner is displaced
        # horizontally, so on a ramp it legitimately differs from the height
        # under the card's centre, and that is measurement error, not drift.
        upright = grass.GrassSpec(density=8.0, seed=4, slope_limit_deg=25.0,
                                  lean_deg=0.0)
        uv_verts, uv_faces, _ = grass.scatter(
            upright, width, depth, origin=(centre_x, centre_y, 0.0),
            surface=surface, mask=mask)
        errors = []
        for index in range(0, len(uv_faces), upright.crossings):
            corners = [uv_verts[i] for i in uv_faces[index]]
            x = sum(c[0] for c in corners) / 4
            y = sum(c[1] for c in corners) / 4
            errors.append(abs(min(c[2] for c in corners) - surface(x, y)[0]))
        result["max_height_error"] = round(max(errors), 6)
        result["ok"] = True
    except Exception:
        result["ok"] = False
        result["error"] = traceback.format_exc()
    print("TERRAIN_PROBE " + json.dumps(result))


main()
