"""Add the editable Cortico walkable grid to the adopted source blend.

This is a direct authoring operation, not a generator. It refuses an existing
floor grid and saves only the explicitly supplied source blend. The exporter
later reads the grid's vertex heights and world-unit spacing into floor.obj.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def _axis_values(start: float, end: float, spacing: float) -> list[float]:
    values = []
    value = start
    while value < end - 1e-6:
        values.append(value)
        value = min(value + spacing, end)
    if not values or values[-1] < end - 1e-6:
        values.append(end)
    return values


def author(blend: Path, spacing: float, texture_period: float) -> None:
    if spacing <= 0 or texture_period <= 0:
        raise SystemExit("spacing and texture period must be positive")
    if Path(bpy.data.filepath).resolve() != blend.resolve():
        bpy.ops.wm.open_mainfile(filepath=str(blend.resolve()))
    if bpy.data.objects.get("CORTICO_floor_grid") is not None:
        raise SystemExit("refusing to replace existing CORTICO_floor_grid")

    ground = bpy.data.objects.get("CORTICO_ground")
    if ground is None or ground.type != "MESH":
        raise SystemExit("CORTICO_ground mesh is required")
    # The walkable grid owns the floor runtime surface. Keep the old beauty
    # ground as an authoring reference, but do not spend facade-atlas UVs on a
    # duplicate giant plane.
    ground["sr_export"] = False
    corners = [ground.matrix_world @ Vector(corner) for corner in ground.bound_box]
    min_x, max_x = min(point.x for point in corners), max(point.x for point in corners)
    min_y, max_y = min(point.y for point in corners), max(point.y for point in corners)
    xs = _axis_values(min_x, max_x, spacing)
    ys = _axis_values(min_y, max_y, spacing)
    vertices = [(x, y, 0.0) for y in ys for x in xs]
    columns = len(xs)
    faces = [
        (row * columns + col, row * columns + col + 1,
         (row + 1) * columns + col + 1, (row + 1) * columns + col)
        for row in range(len(ys) - 1)
        for col in range(columns - 1)
    ]
    mesh = bpy.data.meshes.new("CORTICO_floor_grid_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    floor = bpy.data.objects.new("CORTICO_floor_grid", mesh)
    bpy.data.collections["21_FOREGROUND"].objects.link(floor)
    floor["sr_floor_mesh"] = True
    floor["sr_ground"] = True
    floor["sr_export"] = False
    floor["sr_floor_grid_spacing"] = spacing
    floor["sr_floor_texture_period"] = texture_period
    floor["sr_source_role"] = "walkable_world_unit_grid"
    if ground.data.materials:
        floor.data.materials.append(ground.data.materials[0])
    bpy.context.scene["sr_floor_grid_object"] = floor.name
    bpy.context.scene["sr_floor_grid_spacing"] = spacing
    bpy.ops.wm.save_as_mainfile(filepath=str(blend.resolve()))
    print("CORTICO FLOOR GRID OK", {
        "blend": str(blend.resolve()), "object": floor.name,
        "spacing": spacing, "texturePeriod": texture_period,
        "vertices": len(vertices), "faces": len(faces),
        "bounds": [min_x, min_y, max_x, max_y],
    })


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1:]
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", type=Path, required=True)
    parser.add_argument("--spacing", type=float, default=1.0)
    parser.add_argument("--texture-period", type=float, default=2.0)
    args = parser.parse_args(argv)
    author(args.blend, args.spacing, args.texture_period)


if __name__ == "__main__":
    main()
