"""Sample real Blender geometry as a surface and a density mask.

The grass scatter takes a ``surface`` and a ``mask`` callable and is otherwise
Blender-free.  This is the adapter that plugs authored scene geometry into
those sockets, which is what makes vegetation follow the actual ground instead
of an abstract flat rectangle:

- :func:`mesh_surface` raycasts straight down onto a mesh for world height and
  normal, so a patch drapes over a bank or a stair.
- :func:`weight_mask` reads a vertex group, so density is painted rather than
  argued about in parameters.
- :func:`keep_out_mask` clears vegetation from named objects' footprints,
  which is how grass stays out of a walkable lane.

Everything here is bpy-dependent by nature -- it exists to read a document --
so it is deliberately thin, and every decision it can defer to the scatter it
does defer.
"""
from __future__ import annotations

import bpy
from mathutils import Vector

#: How far above the patch a probe starts.  A ray must begin clear of the
#: tallest thing it may legitimately land on, or a hill samples its own far
#: side; 50 m is far above anything in a town scene.
PROBE_HEIGHT = 50.0


def _evaluated(obj):
    """The object as the depsgraph sees it, so modifiers are included."""
    return obj.evaluated_get(bpy.context.evaluated_depsgraph_get())


def mesh_surface(terrain, *, probe_height: float = PROBE_HEIGHT,
                 default=(0.0, (0.0, 0.0, 1.0))):
    """A ``surface`` callable that drapes a patch over ``terrain``.

    Returns world height and world normal at a world (x, y).  Points that miss
    the mesh return ``default`` rather than raising: a patch overhanging the
    edge of its ground should thin out, not fail the whole scatter.
    """
    if terrain is None or terrain.type != "MESH":
        raise ValueError("terrain must be a mesh object")
    evaluated = _evaluated(terrain)
    to_local = terrain.matrix_world.inverted()
    to_world = terrain.matrix_world
    # Normals transform by the inverse transpose, not the matrix; a scaled
    # terrain otherwise reports normals that are wrong exactly where slope
    # matters most.
    normal_matrix = terrain.matrix_world.to_3x3().inverted().transposed()

    def sample(x, y):
        start = to_local @ Vector((x, y, probe_height))
        direction = (to_local.to_3x3() @ Vector((0.0, 0.0, -1.0))).normalized()
        hit, location, normal, _index = evaluated.ray_cast(start, direction)
        if not hit:
            return default
        world = to_world @ location
        return world.z, tuple((normal_matrix @ normal).normalized())

    return sample


def weight_mask(terrain, group: str, *, gamma: float = 1.0,
                default: float = 0.0, probe_height: float = PROBE_HEIGHT):
    """A ``mask`` callable reading a painted vertex group as density.

    The weight is taken from the hit polygon's corners, inverse-distance
    weighted toward the hit point.  Nearest-vertex sampling would step in
    visible facets at exactly the polygon scale terrain is modelled at.

    ``gamma`` bends the painted ramp: above 1 concentrates growth in the
    strongly painted areas, below 1 spreads it out.
    """
    if terrain is None or terrain.type != "MESH":
        raise ValueError("terrain must be a mesh object")
    index = terrain.vertex_groups.find(group)
    if index < 0:
        raise ValueError(f"{terrain.name!r} has no vertex group {group!r}")
    evaluated = _evaluated(terrain)
    mesh = evaluated.to_mesh()
    to_local = terrain.matrix_world.inverted()

    weights = []
    for vertex in mesh.vertices:
        weight = 0.0
        for entry in vertex.groups:
            if entry.group == index:
                weight = entry.weight
                break
        weights.append(weight)
    polygons = [(tuple(p.vertices), [mesh.vertices[v].co.copy() for v in p.vertices])
                for p in mesh.polygons]
    evaluated.to_mesh_clear()

    def sample(x, y):
        start = to_local @ Vector((x, y, probe_height))
        direction = (to_local.to_3x3() @ Vector((0.0, 0.0, -1.0))).normalized()
        hit, location, _normal, face = evaluated.ray_cast(start, direction)
        if not hit or face < 0 or face >= len(polygons):
            return default
        indices, corners = polygons[face]
        total = 0.0
        weighted = 0.0
        for vertex_index, corner in zip(indices, corners):
            distance = (corner - location).length
            influence = 1.0 / max(1e-4, distance)
            weighted += weights[vertex_index] * influence
            total += influence
        value = weighted / total if total else default
        return max(0.0, min(1.0, value)) ** max(1e-6, gamma)

    return sample


def keep_out_mask(objects, *, margin: float = 0.0, inner=None):
    """A ``mask`` callable that clears vegetation from objects' footprints.

    Uses world-space XY bounds, which is the right shape for the boxes this
    project marks lanes and collision with, and cheap enough to call per tuft.
    ``margin`` widens the exclusion; ``inner`` is an optional mask consulted
    outside every footprint, so a keep-out can wrap a painted weight.
    """
    boxes = []
    for obj in objects:
        if obj is None:
            continue
        corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        xs = [c.x for c in corners]
        ys = [c.y for c in corners]
        boxes.append((min(xs) - margin, max(xs) + margin,
                      min(ys) - margin, max(ys) + margin))

    def sample(x, y):
        for x0, x1, y0, y1 in boxes:
            if x0 <= x <= x1 and y0 <= y <= y1:
                return 0.0
        return 1.0 if inner is None else max(0.0, min(1.0, inner(x, y)))

    return sample


def patch_bounds(terrain, *, margin: float = 0.0):
    """World-space (centre_x, centre_y, width, depth) covering ``terrain``.

    Saves callers hand-measuring a patch to match a ground object, which is
    the sort of number that silently rots when the ground is re-authored.
    """
    corners = [terrain.matrix_world @ Vector(corner) for corner in terrain.bound_box]
    xs = [c.x for c in corners]
    ys = [c.y for c in corners]
    width = (max(xs) - min(xs)) + margin * 2
    depth = (max(ys) - min(ys)) + margin * 2
    return ((min(xs) + max(xs)) * .5, (min(ys) + max(ys)) * .5, width, depth)
