"""Spatial sweep and loft primitives for gesture-authored low-poly objects.

Unlike ``lathe.py`` (a 2D profile revolved around an axis) and ``poly_parts.py``
(a 2D silhouette extruded to thickness), this module starts from an authored
*3D path*. A cross-section is parallel-transported along that path, so bend,
taper, twist, branching, and closed loops are first-class rather than assembled
from many rotational solids or flattened plates.

The intended authoring unit is a gesture::

    fang = sweep(
        [(0, 0, 0), (0.08, 0.5, 0.04), (0.18, 0.9, 0.18)],
        scales=[0.22, 0.15, 0.03],
        sides=7,
        material="bone",
    )

Everything returns the repository's ordinary ``LatheMesh`` so transform,
merge, OBJ output, normals, and material validation remain shared contracts.
The name is historical; these meshes are not lathed.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import lathe

EPSILON = 1e-8


class SweepError(ValueError):
    """Raised when an authored spatial gesture cannot make a sane surface."""


def _add(a, b):
    return tuple(a[i] + b[i] for i in range(3))


def _sub(a, b):
    return tuple(a[i] - b[i] for i in range(3))


def _mul(v, s):
    return tuple(q * s for q in v)


def _dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _length(v):
    return math.sqrt(_dot(v, v))


def _unit(v, label="vector"):
    length = _length(v)
    if length <= EPSILON:
        raise SweepError(f"{label} has zero length")
    return _mul(v, 1.0 / length)


def regular_section(sides: int = 8, phase: float = 0.5) -> list[tuple[float, float]]:
    """Unit-radius regular polygon in local section coordinates.

    ``phase`` is a fraction of one side step. The default half-step keeps a
    face rather than a vertex pointing along the first local axis, which tends
    to read better on deliberately low-sided tubes.
    """
    if sides < 3:
        raise SweepError(f"section needs at least 3 sides, got {sides}")
    offset = math.tau / sides * phase
    return [
        (math.cos(offset + math.tau * i / sides), math.sin(offset + math.tau * i / sides))
        for i in range(sides)
    ]


def rectangle_section(width: float = 1.0, thickness: float = 1.0) -> list[tuple[float, float]]:
    if width <= 0 or thickness <= 0:
        raise SweepError("rectangle width and thickness must be positive")
    return [
        (-0.5 * width, -0.5 * thickness),
        (0.5 * width, -0.5 * thickness),
        (0.5 * width, 0.5 * thickness),
        (-0.5 * width, 0.5 * thickness),
    ]


def _validate_path(path, *, closed_path=False):
    minimum = 3 if closed_path else 2
    if len(path) < minimum:
        raise SweepError(f"path needs at least {minimum} points, got {len(path)}")
    clean = []
    for i, p in enumerate(path):
        if len(p) != 3 or not all(math.isfinite(float(q)) for q in p):
            raise SweepError(f"path point {i} is not a finite xyz triple: {p!r}")
        clean.append(tuple(float(q) for q in p))
    for i, (a, b) in enumerate(zip(clean, clean[1:])):
        if _length(_sub(b, a)) <= EPSILON:
            raise SweepError(f"path points {i} and {i + 1} coincide")
    if closed_path and _length(_sub(clean[0], clean[-1])) <= EPSILON:
        raise SweepError("closed_path expects unique loop points; do not repeat the first point")
    return clean


def _tangents(path, closed_path):
    n = len(path)
    tangents = []
    for i in range(n):
        if closed_path:
            delta = _sub(path[(i + 1) % n], path[(i - 1) % n])
        elif i == 0:
            delta = _sub(path[1], path[0])
        elif i == n - 1:
            delta = _sub(path[-1], path[-2])
        else:
            delta = _sub(path[i + 1], path[i - 1])
        tangents.append(_unit(delta, f"path tangent {i}"))
    return tangents


def _initial_normal(tangent):
    # Choose the cardinal direction least aligned with the tangent, then
    # project it into the tangent plane. This avoids a vertical path getting an
    # unstable almost-zero frame.
    candidates = [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)]
    ref = min(candidates, key=lambda axis: abs(_dot(axis, tangent)))
    projected = _sub(ref, _mul(tangent, _dot(ref, tangent)))
    return _unit(projected, "initial sweep normal")


def _frames(path, closed_path, rolls):
    tangents = _tangents(path, closed_path)
    normals = [_initial_normal(tangents[0])]
    for i in range(1, len(path)):
        tangent = tangents[i]
        previous = normals[-1]
        projected = _sub(previous, _mul(tangent, _dot(previous, tangent)))
        if _length(projected) <= EPSILON:
            projected = _initial_normal(tangent)
        normals.append(_unit(projected, f"transported normal {i}"))

    result = []
    for tangent, normal, roll in zip(tangents, normals, rolls):
        binormal = _unit(_cross(tangent, normal), "sweep binormal")
        angle = math.radians(float(roll))
        c, s = math.cos(angle), math.sin(angle)
        rolled_normal = _add(_mul(normal, c), _mul(binormal, s))
        rolled_binormal = _add(_mul(binormal, c), _mul(normal, -s))
        result.append((tangent, rolled_normal, rolled_binormal))
    return result


def _expand(value, count, *, label, pair=False):
    """Expand a scalar/pair or per-path sequence to one value per path point."""
    if pair:
        if isinstance(value, Sequence) and len(value) == 2 and all(isinstance(q, (int, float)) for q in value):
            values = [tuple(map(float, value))] * count
        else:
            values = [tuple(map(float, q)) if isinstance(q, Sequence) else (float(q), float(q)) for q in value]
    else:
        if isinstance(value, (int, float)):
            values = [float(value)] * count
        else:
            values = [float(q) for q in value]
    if len(values) != count:
        raise SweepError(f"{label} needs {count} values, got {len(values)}")
    return values


def sweep_sections(
    path: list[tuple[float, float, float]],
    sections: list[list[tuple[float, float]]],
    *,
    material: str = "old_limestone",
    rolls: float | list[float] = 0.0,
    closed_path: bool = False,
    cap_start: bool = True,
    cap_end: bool = True,
    smooth: bool = True,
    name: str = "sweep",
) -> lathe.LatheMesh:
    """Transport one authored 2D cross-section per path point through 3D space."""
    path = _validate_path(path, closed_path=closed_path)
    if len(sections) != len(path):
        raise SweepError(f"sections needs {len(path)} loops, got {len(sections)}")
    side_count = len(sections[0])
    if side_count < 3:
        raise SweepError("cross-section needs at least 3 points")
    for i, section in enumerate(sections):
        if len(section) != side_count:
            raise SweepError(f"section {i} has {len(section)} points; expected {side_count}")
        if any(len(p) != 2 or not all(math.isfinite(float(q)) for q in p) for p in section):
            raise SweepError(f"section {i} contains a non-finite uv-plane point")

    roll_values = _expand(rolls, len(path), label="rolls")
    frames = _frames(path, closed_path, roll_values)
    mesh = lathe.LatheMesh(name=name)

    # UV v follows path arc length. On a closed loop it intentionally leaves a
    # seam on the closing band; current item materials are not tiled albedo,
    # but authored UVs remain deterministic and inspectable.
    lengths = [0.0]
    for a, b in zip(path, path[1:]):
        lengths.append(lengths[-1] + _length(_sub(b, a)))
    total_length = lengths[-1]
    if closed_path:
        total_length += _length(_sub(path[0], path[-1]))
    if total_length <= EPSILON:
        raise SweepError("path has zero arc length")

    rings = []
    for i, (point, section, frame) in enumerate(zip(path, sections, frames)):
        _, normal, binormal = frame
        ring = []
        v_coord = lengths[i] / total_length
        for j, (u_local, v_local) in enumerate(section):
            position = _add(point, _add(_mul(normal, float(u_local)), _mul(binormal, float(v_local))))
            mesh.vertices.append(position)
            mesh.uvs.append((j / side_count, v_coord))
            ring.append((len(mesh.vertices) - 1, len(mesh.uvs) - 1))
        rings.append(ring)

    band_count = len(path) if closed_path else len(path) - 1
    for i in range(band_count):
        a = rings[i]
        b = rings[(i + 1) % len(rings)]
        for j in range(side_count):
            j2 = (j + 1) % side_count
            mesh.faces.append((material, [a[j], a[j2], b[j2], b[j]]))
            mesh.smooth_groups.append(1 if smooth else 0)

    def cap(ring, reverse):
        centre = tuple(sum(mesh.vertices[vi][axis] for vi, _ in ring) / side_count for axis in range(3))
        mesh.vertices.append(centre)
        mesh.uvs.append((0.5, 0.5))
        c = (len(mesh.vertices) - 1, len(mesh.uvs) - 1)
        for j in range(side_count):
            j2 = (j + 1) % side_count
            corners = [c, ring[j], ring[j2]]
            if reverse:
                corners = [c, ring[j2], ring[j]]
            mesh.faces.append((material, corners))
            mesh.smooth_groups.append(0)

    if not closed_path:
        if cap_start:
            cap(rings[0], True)
        if cap_end:
            cap(rings[-1], False)
    return mesh


def sweep(
    path,
    *,
    scales=1.0,
    aspect=(1.0, 1.0),
    sides=8,
    phase=0.5,
    material="old_limestone",
    rolls=0.0,
    closed_path=False,
    cap_start=True,
    cap_end=True,
    smooth=True,
    name="sweep",
):
    """Sweep a regular polygon, with authored per-point scale/aspect and roll."""
    clean = _validate_path(path, closed_path=closed_path)
    scale_values = _expand(scales, len(clean), label="scales")
    aspect_values = _expand(aspect, len(clean), label="aspect", pair=True)
    base = regular_section(sides=sides, phase=phase)
    sections = []
    for radius, (sx, sy) in zip(scale_values, aspect_values):
        if radius <= 0 or sx <= 0 or sy <= 0:
            raise SweepError("sweep scale/aspect values must stay positive; taper to a small value, not zero")
        sections.append([(u * radius * sx, v * radius * sy) for u, v in base])
    return sweep_sections(
        clean,
        sections,
        material=material,
        rolls=rolls,
        closed_path=closed_path,
        cap_start=cap_start,
        cap_end=cap_end,
        smooth=smooth,
        name=name,
    )


def ribbon(
    path,
    *,
    widths=0.2,
    thickness=0.05,
    rolls=0.0,
    material="aged_cloth",
    closed_path=False,
    name="ribbon",
):
    """A rectangular sweep: useful for tongues, straps, feathers and drips."""
    clean = _validate_path(path, closed_path=closed_path)
    width_values = _expand(widths, len(clean), label="widths")
    thick_values = _expand(thickness, len(clean), label="thickness")
    sections = []
    for width, thick in zip(width_values, thick_values):
        if width <= 0 or thick <= 0:
            raise SweepError("ribbon width/thickness must stay positive")
        sections.append(rectangle_section(width, thick))
    return sweep_sections(
        clean,
        sections,
        material=material,
        rolls=rolls,
        closed_path=closed_path,
        cap_start=not closed_path,
        cap_end=not closed_path,
        smooth=False,
        name=name,
    )


def loop(points, *, radius=0.06, sides=6, material="wrought_iron", rolls=0.0, name="loop"):
    """Convenience closed spatial tube with no privileged axis."""
    return sweep(
        points,
        scales=radius,
        sides=sides,
        material=material,
        rolls=rolls,
        closed_path=True,
        cap_start=False,
        cap_end=False,
        name=name,
    )
