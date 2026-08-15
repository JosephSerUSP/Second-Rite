"""Thin-solid and planar primitives for authored item models.

This module deliberately attacks a different design space from ``parts.py``.
``parts.py`` starts from surfaces of revolution and composes semantic forms;
this file starts from 2D drawings and fabricates them into low-poly solids.
That makes it a better fit for blades, glasses, masks, feathers, armour plates,
insignia and other objects whose identity lives in an outline rather than a
turned profile.

All functions return ``lathe.LatheMesh`` only because that is the repository's
shared mesh value and OBJ writer contract. No geometry here is produced by a
lathe.
"""

from __future__ import annotations

import math

from lathe import LatheMesh, LatheError, merge


def _signed_area(points: list[tuple[float, float]]) -> float:
    return 0.5 * sum(
        x0 * y1 - x1 * y0
        for (x0, y0), (x1, y1) in zip(points, points[1:] + points[:1])
    )


def extrude_polygon(
    points: list[tuple[float, float]],
    depth: float,
    *,
    material: str = "old_limestone",
    name: str = "polygon",
) -> LatheMesh:
    """Extrude a convex XY polygon through Z, with planar UVs.

    The polygon is the authority.  It must be convex and non-self-intersecting;
    recipes in this module intentionally use several simple plates instead of
    asking one complicated concave outline to hide its construction.
    """
    if len(points) < 3:
        raise LatheError(f"{name}: polygon needs at least 3 points")
    if not math.isfinite(depth) or depth <= 0.0:
        raise LatheError(f"{name}: depth must be positive, got {depth!r}")
    if any(not (math.isfinite(x) and math.isfinite(y)) for x, y in points):
        raise LatheError(f"{name}: polygon contains a non-finite point")
    if any(a == b for a, b in zip(points, points[1:] + points[:1])):
        raise LatheError(f"{name}: polygon contains a zero-length edge")

    area = _signed_area(points)
    if abs(area) <= 1e-9:
        raise LatheError(f"{name}: polygon encloses no area")
    if area < 0.0:
        points = list(reversed(points))

    min_x = min(x for x, _ in points)
    max_x = max(x for x, _ in points)
    min_y = min(y for _, y in points)
    max_y = max(y for _, y in points)
    span_x = max(max_x - min_x, 1e-9)
    span_y = max(max_y - min_y, 1e-9)

    mesh = LatheMesh(name=name)
    half = depth / 2.0
    for z in (half, -half):
        for x, y in points:
            mesh.vertices.append((x, y, z))
            mesh.uvs.append(((x - min_x) / span_x, (y - min_y) / span_y))

    n = len(points)
    # front/back caps: fan triangulation is valid because this primitive is
    # intentionally convex.  Caps stay flat-shaded.
    for i in range(1, n - 1):
        mesh.faces.append((material, [(0, 0), (i, i), (i + 1, i + 1)]))
        mesh.smooth_groups.append(0)
        mesh.faces.append((material, [
            (n, n), (n + i + 1, n + i + 1), (n + i, n + i),
        ]))
        mesh.smooth_groups.append(0)

    # side walls.  With a CCW front polygon this winding points outwards.
    for i in range(n):
        j = (i + 1) % n
        mesh.faces.append((material, [
            (i, i), (n + i, n + i), (n + j, n + j), (j, j),
        ]))
        mesh.smooth_groups.append(0)
    return mesh


def bar_between(
    a: tuple[float, float],
    b: tuple[float, float],
    width: float,
    depth: float,
    *,
    material: str = "wrought_iron",
    name: str = "bar",
) -> LatheMesh:
    """A rectangular solid connecting two XY points."""
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    length = math.hypot(dx, dy)
    if length <= 1e-9:
        raise LatheError(f"{name}: bar endpoints are identical")
    if width <= 0.0:
        raise LatheError(f"{name}: width must be positive")
    px, py = -dy / length * width / 2.0, dx / length * width / 2.0
    return extrude_polygon(
        [(ax + px, ay + py), (ax - px, ay - py),
         (bx - px, by - py), (bx + px, by + py)],
        depth,
        material=material,
        name=name,
    )


def regular_plate(
    centre: tuple[float, float],
    radius: float,
    sides: int,
    depth: float,
    *,
    rotation: float = 0.0,
    material: str = "old_limestone",
    name: str = "regular_plate",
) -> LatheMesh:
    """A regular polygonal plate/cylinder facing the item viewer."""
    if sides < 3:
        raise LatheError(f"{name}: sides must be >= 3")
    if radius <= 0.0:
        raise LatheError(f"{name}: radius must be positive")
    cx, cy = centre
    phase = math.radians(rotation)
    points = [
        (cx + radius * math.cos(phase + i / sides * math.tau),
         cy + radius * math.sin(phase + i / sides * math.tau))
        for i in range(sides)
    ]
    return extrude_polygon(points, depth, material=material, name=name)


def ring_segments(
    centre: tuple[float, float],
    radius: float,
    sides: int,
    width: float,
    depth: float,
    *,
    rotation: float = 0.0,
    material: str = "wrought_iron",
    name: str = "ring_segments",
) -> LatheMesh:
    """A true open polygonal frame, assembled from bars rather than a filled disc."""
    if sides < 3:
        raise LatheError(f"{name}: sides must be >= 3")
    cx, cy = centre
    phase = math.radians(rotation)
    points = [
        (cx + radius * math.cos(phase + i / sides * math.tau),
         cy + radius * math.sin(phase + i / sides * math.tau))
        for i in range(sides)
    ]
    return merge(name, [
        bar_between(points[i], points[(i + 1) % sides], width, depth,
                    material=material, name=f"{name}_{i}")
        for i in range(sides)
    ])


def polyline(
    points: list[tuple[float, float]],
    width: float,
    depth: float,
    *,
    material: str = "wrought_iron",
    name: str = "polyline",
) -> LatheMesh:
    """Fabricate a bent strip from straight bar segments."""
    if len(points) < 2:
        raise LatheError(f"{name}: polyline needs at least 2 points")
    return merge(name, [
        bar_between(a, b, width, depth, material=material, name=f"{name}_{i}")
        for i, (a, b) in enumerate(zip(points, points[1:]))
    ])


def arc_bars(
    centre: tuple[float, float],
    radius: float,
    start_degrees: float,
    end_degrees: float,
    segments: int,
    width: float,
    depth: float,
    *,
    material: str = "wrought_iron",
    name: str = "arc",
) -> LatheMesh:
    """A deliberately faceted arc, useful for sickles, frames and ribs."""
    if segments < 1:
        raise LatheError(f"{name}: arc needs at least one segment")
    cx, cy = centre
    points = []
    for i in range(segments + 1):
        t = i / segments
        angle = math.radians(start_degrees + (end_degrees - start_degrees) * t)
        points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return polyline(points, width, depth, material=material, name=name)
