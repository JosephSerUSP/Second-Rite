"""Surfaces of revolution from authored 2D profiles.

Most of this game's item catalogue is rotationally symmetric — bottles, rings,
bells, incense, coins, jars, bowls, eggs. Modelling each as an independent
solid produced the duplicate clusters the corpus gate now records. A profile
curve is the cheaper and more honest authority: the author draws a silhouette,
the lathe supplies the third dimension, and cylindrical UVs fall out of the
construction for free rather than needing a separate unwrap.

A profile is a list of ``(y, radius)`` points, ordered from the bottom of the
object upward. That convention matches the bottle tables the earlier batch
builders already used, so existing authored silhouettes can move over
unchanged.

    profile = [(-1.0, 0.00), (-1.0, 0.42), (0.6, 0.38), (0.9, 0.12)]
    mesh = lathe(profile, segments=24)
    write_obj(mesh, path, material="crystal")

Radius 0 at an end closes that end on the axis without a cap; a nonzero end
radius grows a flat cap so the solid is watertight. Everything here is pure
geometry with no Blender dependency, so it runs in a bare worktree and in CI.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MATERIALS_JSON = REPO_ROOT / "tools" / "asset-language" / "materials.json"

# Below this, a profile point sits on the axis: the ring of vertices collapses
# to a single pole and the quad band degenerates into a triangle fan.
AXIS_EPSILON = 1e-6


class LatheError(ValueError):
    """Raised for a profile that cannot produce a sane solid."""


@dataclass
class LatheMesh:
    """Geometry plus the per-face material assignment, ready for OBJ."""

    name: str
    vertices: list[tuple[float, float, float]] = field(default_factory=list)
    uvs: list[tuple[float, float]] = field(default_factory=list)
    # (material, [(vertex_index, uv_index), ...]) with 0-based indices
    faces: list[tuple[str, list[tuple[int, int]]]] = field(default_factory=list)

    def bounds(self) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        xs, ys, zs = zip(*self.vertices)
        return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def validate_profile(profile: list[tuple[float, float]], closed: bool = False) -> None:
    """Reject profiles that cannot describe a solid, loudly.

    A silently degenerate profile is how a batch produces 200 files and 100
    shapes, so every one of these is an error rather than a repair.
    """
    minimum = 3 if closed else 2
    if len(profile) < minimum:
        raise LatheError(f"profile needs at least {minimum} points, got {len(profile)}")

    for index, point in enumerate(profile):
        if len(point) != 2:
            raise LatheError(f"point {index} is not a (y, radius) pair: {point!r}")
        y, radius = point
        if not math.isfinite(y) or not math.isfinite(radius):
            raise LatheError(f"point {index} is not finite: {point!r}")
        if radius < 0.0:
            raise LatheError(f"point {index} has negative radius {radius}")

    heights = [y for y, _ in profile]
    radii = [radius for _, radius in profile]

    if closed:
        # A closed cross-section sweeps a tube (a ring, a bead, a torus). It
        # never touches the axis: a point at radius 0 would pinch the tube shut
        # and turn the solid inside out at the pole.
        if min(radii) <= AXIS_EPSILON:
            raise LatheError("a closed profile must not touch the axis")
        if max(heights) - min(heights) <= 0.0 or max(radii) - min(radii) <= 0.0:
            raise LatheError("closed profile encloses no area")
        return

    if heights != sorted(heights):
        raise LatheError(
            "profile points must run bottom-to-top by y "
            "(use closed_profile=True for a ring or bead cross-section)"
        )
    if heights[0] == heights[-1]:
        raise LatheError("profile has zero height")
    if all(radius <= AXIS_EPSILON for radius in radii):
        raise LatheError("profile is entirely on the axis: no surface to revolve")


def lathe(
    profile: list[tuple[float, float]],
    segments: int = 24,
    material: str = "old_limestone",
    materials: list[str] | None = None,
    name: str = "lathe",
    sweep: float = 1.0,
    closed_profile: bool = False,
) -> LatheMesh:
    """Revolve ``profile`` around the Y axis.

    ``materials`` optionally assigns one material per profile *band* (there are
    ``len(profile) - 1`` bands), which is how a bottle gets a glass body and a
    wax stopper without a second mesh. ``sweep`` below 1.0 produces a partial
    revolution, which is what makes an open ring or a broken vessel possible
    from the same primitive.

    ``closed_profile`` treats the profile as a loop rather than a bottom-to-top
    silhouette, sweeping a tube instead of a solid: that is what a ring, a bead
    or any torus actually is, and it is the shape an ordinary monotonic profile
    cannot express at all.
    """
    validate_profile(profile, closed=closed_profile)
    if segments < 3:
        raise LatheError(f"segments must be at least 3, got {segments}")
    if not 0.0 < sweep <= 1.0:
        raise LatheError(f"sweep must be in (0, 1], got {sweep}")

    if closed_profile and profile[0] != profile[-1]:
        # Close the loop explicitly so the band loop below stays uniform.
        profile = list(profile) + [profile[0]]

    band_count = len(profile) - 1
    if materials is None:
        band_materials = [material] * band_count
    elif len(materials) != band_count:
        raise LatheError(
            f"{len(materials)} materials for {band_count} bands "
            f"({len(profile)} profile points)"
        )
    else:
        band_materials = list(materials)

    closed = sweep >= 1.0
    # An open sweep needs a final column of vertices at the end angle; a closed
    # one wraps back onto column 0 for position but still needs a duplicate
    # column for UVs, or the texture mirrors across the seam.
    columns = segments if closed else segments + 1

    mesh = LatheMesh(name=name)

    # --- vertices and UVs -----------------------------------------------------
    # ``rings[i]`` holds one (vertex_index, uv_index) pair per column for
    # profile point i, or a single shared pole pair when the point is on axis.
    rings: list[list[tuple[int, int]]] = []

    # v runs along the profile by arc length rather than by height, so a steep
    # shoulder does not compress its texture and a closed loop — which has no
    # meaningful "height fraction" at all — still gets a monotonic coordinate.
    lengths = [0.0]
    for (y0, r0), (y1, r1) in zip(profile, profile[1:]):
        lengths.append(lengths[-1] + math.hypot(y1 - y0, r1 - r0))
    total_length = lengths[-1]
    if total_length <= 0.0:
        raise LatheError("profile has zero arc length")

    for point_index, (y, radius) in enumerate(profile):
        v_coord = lengths[point_index] / total_length
        on_axis = radius <= AXIS_EPSILON

        if on_axis:
            vertex_index = len(mesh.vertices)
            mesh.vertices.append((0.0, y, 0.0))
            ring = []
            for column in range(columns):
                # A pole is one position but many UVs, so the cap fan does not
                # collapse to a zero-area triangle in texture space.
                mesh.uvs.append((column / max(columns - 1, 1), v_coord))
                ring.append((vertex_index, len(mesh.uvs) - 1))
            rings.append(ring)
            continue


        ring = []
        for column in range(columns):
            fraction = column / segments * sweep
            angle = fraction * math.tau
            mesh.vertices.append((radius * math.cos(angle), y, radius * math.sin(angle)))
            mesh.uvs.append((fraction, v_coord))
            ring.append((len(mesh.vertices) - 1, len(mesh.uvs) - 1))
        rings.append(ring)

    def column_pair(ring: list[tuple[int, int]], column: int) -> tuple:
        """The (this, next) pair for a column, wrapping a closed sweep."""
        if closed:
            return ring[column], ring[(column + 1) % segments]
        return ring[column], ring[column + 1]

    # --- side bands -----------------------------------------------------------
    for band in range(band_count):
        lower, upper = rings[band], rings[band + 1]
        lower_on_axis = profile[band][1] <= AXIS_EPSILON
        upper_on_axis = profile[band + 1][1] <= AXIS_EPSILON
        if lower_on_axis and upper_on_axis:
            # Two consecutive axis points describe a line, not a surface.
            continue
        band_material = band_materials[band]

        for column in range(segments):
            (lo_a, lo_a_uv), (lo_b, lo_b_uv) = column_pair(lower, column)
            (up_a, up_a_uv), (up_b, up_b_uv) = column_pair(upper, column)

            if lower_on_axis:
                mesh.faces.append(
                    (band_material, [(lo_a, lo_a_uv), (up_b, up_b_uv), (up_a, up_a_uv)])
                )
            elif upper_on_axis:
                mesh.faces.append(
                    (band_material, [(lo_a, lo_a_uv), (lo_b, lo_b_uv), (up_a, up_a_uv)])
                )
            else:
                mesh.faces.append(
                    (
                        band_material,
                        [
                            (lo_a, lo_a_uv),
                            (lo_b, lo_b_uv),
                            (up_b, up_b_uv),
                            (up_a, up_a_uv),
                        ],
                    )
                )

    # --- end caps -------------------------------------------------------------
    # A closed profile is already a sealed tube; capping it would put a disc
    # through the middle of the ring.
    cap_ends = () if closed_profile else (("bottom", 0), ("top", len(profile) - 1))
    for end, ring_index in cap_ends:
        radius = profile[ring_index][1]
        if radius <= AXIS_EPSILON:
            continue  # already closed on the axis
        y = profile[ring_index][0]
        ring = rings[ring_index]
        centre_index = len(mesh.vertices)
        mesh.vertices.append((0.0, y, 0.0))
        mesh.uvs.append((0.5, 0.0 if end == "bottom" else 1.0))
        centre_uv = len(mesh.uvs) - 1
        cap_material = band_materials[0 if end == "bottom" else -1]

        for column in range(segments):
            (a, a_uv), (b, b_uv) = column_pair(ring, column)
            # Wind the bottom cap the other way so both caps face outward.
            corners = [(centre_index, centre_uv), (a, a_uv), (b, b_uv)]
            if end == "top":
                corners = [(centre_index, centre_uv), (b, b_uv), (a, a_uv)]
            mesh.faces.append((cap_material, corners))

    return mesh


def transform(
    mesh: LatheMesh,
    translate: tuple[float, float, float] = (0.0, 0.0, 0.0),
    rotate: tuple[float, float, float] = (0.0, 0.0, 0.0),
    scale: float | tuple[float, float, float] = 1.0,
    name: str | None = None,
) -> LatheMesh:
    """Scale, then rotate (X, then Y, then Z, in degrees), then translate.

    The order is fixed and stated because a part library is only reusable if
    two authors composing the same numbers get the same object.
    """
    if isinstance(scale, (int, float)):
        scale_vec = (float(scale), float(scale), float(scale))
    else:
        scale_vec = tuple(float(component) for component in scale)
    if len(scale_vec) != 3:
        raise LatheError(f"scale must be a number or 3 components, got {scale!r}")
    if any(component == 0.0 for component in scale_vec):
        raise LatheError("a zero scale component collapses the part to a plane")

    rx, ry, rz = (math.radians(angle) for angle in rotate)

    def rotate_point(x: float, y: float, z: float) -> tuple[float, float, float]:
        y, z = y * math.cos(rx) - z * math.sin(rx), y * math.sin(rx) + z * math.cos(rx)
        x, z = x * math.cos(ry) + z * math.sin(ry), -x * math.sin(ry) + z * math.cos(ry)
        x, y = x * math.cos(rz) - y * math.sin(rz), x * math.sin(rz) + y * math.cos(rz)
        return x, y, z

    moved = LatheMesh(name=name or mesh.name)
    for x, y, z in mesh.vertices:
        x, y, z = x * scale_vec[0], y * scale_vec[1], z * scale_vec[2]
        x, y, z = rotate_point(x, y, z)
        moved.vertices.append((x + translate[0], y + translate[1], z + translate[2]))
    moved.uvs = list(mesh.uvs)
    moved.faces = [(material, list(corners)) for material, corners in mesh.faces]
    return moved


def merge(name: str, parts: list[LatheMesh]) -> LatheMesh:
    """Combine lathed parts into one mesh, offsetting indices.

    This is what makes a ring more than a band: a ring is a band *plus* a
    setting *plus* a stone, and none of those is a surface of revolution about
    the same axis. Composition is a prerequisite for the lathe being useful on
    real objects, not a later refinement of it.
    """
    if not parts:
        raise LatheError("merge needs at least one part")

    combined = LatheMesh(name=name)
    for part in parts:
        vertex_offset = len(combined.vertices)
        uv_offset = len(combined.uvs)
        combined.vertices.extend(part.vertices)
        combined.uvs.extend(part.uvs)
        for material, corners in part.faces:
            combined.faces.append(
                (material, [(v + vertex_offset, t + uv_offset) for v, t in corners])
            )
    return combined


def canonical_materials() -> set[str]:
    """Material ids the shared registry defines, so a typo fails loudly."""
    import json

    data = json.loads(MATERIALS_JSON.read_text(encoding="utf-8"))
    return {material["id"] for material in data["materials"]}


def write_obj(mesh: LatheMesh, path: Path, mtllib: str, comment: str = "") -> None:
    """Write OBJ with UVs. Indices are 1-based per the format."""
    known = canonical_materials()
    used = {material for material, _ in mesh.faces}
    unknown = sorted(used - known)
    if unknown:
        raise LatheError(f"{mesh.name}: materials not in the canonical registry: {unknown}")

    lines: list[str] = []
    if comment:
        lines.append(f"# {comment}")
    lines.append("# generated by tools/asset-production/lathe.py")
    lines.append(f"mtllib {mtllib}")
    lines.append(f"o {mesh.name}")
    lines.append("s off")
    lines += [f"v {x:.6f} {y:.6f} {z:.6f}" for x, y, z in mesh.vertices]
    lines += [f"vt {u:.6f} {v:.6f}" for u, v in mesh.uvs]

    current = None
    for material, corners in mesh.faces:
        if material != current:
            lines.append(f"usemtl {material}")
            current = material
        lines.append("f " + " ".join(f"{v + 1}/{t + 1}" for v, t in corners))

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_mtl(path: Path, material_ids: list[str], comment: str = "") -> None:
    """Emit an MTL for the given canonical materials, colours from the registry."""
    import json

    data = json.loads(MATERIALS_JSON.read_text(encoding="utf-8"))
    registry = {m["id"]: m for m in data["materials"]}
    missing = [m for m in material_ids if m not in registry]
    if missing:
        raise LatheError(f"materials not in the canonical registry: {missing}")

    lines = [f"# {comment}"] if comment else []
    lines.append("# generated by tools/asset-production/lathe.py")
    for material_id in material_ids:
        r, g, b = registry[material_id]["legacyMtl"]["kd"]
        lines += [f"newmtl {material_id}", f"Kd {r:.3f} {g:.3f} {b:.3f}", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
