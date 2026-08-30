"""Blender-free grass scatter.

Grass is deliberately NOT a tree with small parameters.  A tree is a skeleton
that foliage hangs off; grass is a scatter of cards across a surface, governed
by density and slope.  Routing it through :mod:`tree_generator` would mean
growing a woody graph nobody renders in order to reach the cards.

What it does share is the card itself -- ``tree_mesh.card_corners`` and
``tree_mesh.atlas_uvs`` -- so a blade and a branch spray remain the same kind
of object, and a change to card construction cannot make the two diverge.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from tree_mesh import atlas_uvs, card_corners


@dataclass(frozen=True)
class GrassSpec:
    """One authored grass population."""
    #: Height of an average tuft, in metres.  Absolute, for the same reason
    #: spray_length is: a denser lawn must not grow taller blades.
    tuft_height: float = .34
    #: Width of a tuft card as a fraction of its height.
    tuft_aspect: float = .95
    #: Tufts per square metre of surface.
    density: float = 14.0
    #: Fractional spread either side of tuft_height.
    height_variation: float = .34
    #: Maximum lean from vertical, in degrees.  Grass is never perfectly
    #: upright, and a uniform field reads as a texture rather than as plants.
    lean_deg: float = 14.0
    #: Steepest surface a tuft will root on.  Beyond this the scatter thins to
    #: nothing rather than standing blades out of a cliff face.
    slope_limit_deg: float = 38.0
    #: Crossed pair, for the same reason foliage cards are crossed: a lone
    #: plane vanishes edge-on.
    crossings: int = 2
    atlas_columns: int = 4
    #: Which atlas columns tufts may draw from.  A field of one silhouette
    #: repeats visibly at these densities, so a tuft picks a cell per instance
    #: from the grass atlas built by tools/materials/make_grass_atlas.py.
    atlas_cells: tuple = (0, 1, 2, 3)
    #: Vertex ceiling, matching the live bridge's per-request limit so a patch
    #: stays placeable through any route.
    max_vertices: int = 1024
    seed: int = 1


def _rng(seed):
    """The same small LCG the tree generator uses, so scatters are reproducible."""
    state = [(int(seed) * 1103515245 + 12345) & 0x7fffffff]
    def next_value(lo=0.0, hi=1.0):
        state[0] = (state[0] * 1103515245 + 12345) & 0x7fffffff
        return lo + (hi - lo) * state[0] / 0x7fffffff
    return next_value


def flat_ground(_x, _y):
    """The default surface: z = 0 everywhere, facing straight up."""
    return 0.0, (0.0, 0.0, 1.0)


def tuft_capacity(spec: GrassSpec) -> int:
    """How many tufts fit inside the vertex ceiling."""
    return max(1, spec.max_vertices // (max(1, spec.crossings) * 4))


def scatter(spec: GrassSpec, width: float, depth: float, *,
            origin=(0.0, 0.0, 0.0), surface=flat_ground, mask=None):
    """Scatter tufts over a ``width`` x ``depth`` patch centred on ``origin``.

    ``surface`` maps a WORLD (x, y) to ``(z, normal)``, so the same scatter
    works on a lawn, a verge or a bank -- and so a terrain-backed sampler can
    tell where on the ground the patch actually sits.  ``mask`` maps the same
    world point to a 0..1 density, which is how a painted weight or a keep-out
    around a walkable lane thins or stops the scatter.  Returns
    ``(vertices, faces, uvs)`` in the same shape as the foliage mesher.

    Placement is a jittered grid rather than pure random sampling: uniform
    random leaves visible clumps and bald patches at these densities, which
    reads as a bug in the scatter rather than as natural variation.
    """
    if width <= 0 or depth <= 0:
        raise ValueError("a grass patch needs positive width and depth")
    if spec.tuft_height <= 0:
        raise ValueError("tuft height must be positive")
    wanted = int(round(spec.density * width * depth))
    wanted = max(1, min(wanted, tuft_capacity(spec)))
    # A grid whose cells are as square as the patch allows.
    columns = max(1, int(round(math.sqrt(wanted * width / max(1e-6, depth)))))
    rows = max(1, int(math.ceil(wanted / columns)))
    rng = _rng(spec.seed)
    cells = tuple(spec.atlas_cells) or (0,)
    cell_uvs = [atlas_uvs(spec.atlas_columns, cell) for cell in cells]
    slope_limit = math.cos(math.radians(max(0.0, min(89.9, spec.slope_limit_deg))))

    verts, faces, uvs = [], [], []
    placed = 0
    for row in range(rows):
        for column in range(columns):
            if placed >= wanted:
                break
            # Jitter inside the cell, never across it.
            x = (column + rng(.15, .85)) / columns * width - width * .5 + origin[0]
            y = (row + rng(.15, .85)) / rows * depth - depth * .5 + origin[1]
            height_offset, normal = surface(x, y)
            # Density is consulted before slope: a masked-out point costs one
            # draw either way, and consuming the draw unconditionally keeps the
            # arrangement stable when only the mask changes.
            density = 1.0 if mask is None else max(0.0, min(1.0, mask(x, y)))
            if rng() >= density:
                continue
            length = math.sqrt(sum(v * v for v in normal)) or 1.0
            if normal[2] / length < slope_limit:
                # Too steep to root on; the tuft is simply not placed, which
                # thins the scatter toward a slope instead of ending it at a
                # hard line.
                continue
            placed += 1
            tuft = spec.tuft_height * (1.0 + rng(-spec.height_variation,
                                                 spec.height_variation))
            card_width = max(.04, tuft * spec.tuft_aspect)
            lean = math.radians(spec.lean_deg) * rng(-1.0, 1.0)
            yaw = rng(0.0, math.tau)
            corner_uvs = cell_uvs[int(rng(0.0, len(cell_uvs))) % len(cell_uvs)]
            # Lean tilts the blade away from vertical; yaw turns the whole
            # tuft, so a field does not share one facing.
            along = (math.cos(yaw) * math.sin(lean),
                     math.sin(yaw) * math.sin(lean),
                     math.cos(lean))
            across = (-math.sin(yaw), math.cos(yaw), 0.0)
            base = (x, y, height_offset + origin[2])
            # A blade rises FROM the ground; centring it on the surface would
            # bury half of every tuft.
            centre = tuple(base[i] + along[i] * tuft * .5 for i in range(3))
            for cross in range(max(1, spec.crossings)):
                axis = across if not cross else (
                    along[1] * across[2] - along[2] * across[1],
                    along[2] * across[0] - along[0] * across[2],
                    along[0] * across[1] - along[1] * across[0])
                start = len(verts)
                verts.extend(card_corners(centre, axis, along, card_width, tuft))
                faces.append((start, start + 1, start + 2, start + 3))
                uvs.extend(corner_uvs)
    return verts, faces, uvs
