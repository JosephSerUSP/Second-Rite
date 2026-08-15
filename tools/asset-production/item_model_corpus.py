"""Corpus-level analysis of the item model library.

The per-asset validity rubric that produced the current library scores each
model in isolation, so a renamed box passes every check. These are the checks
that only make sense across the whole corpus:

- ``distinctness``  two items must not resolve to the same normalized geometry
- ``silhouette``    two items must not be indistinguishable at display size
- ``uv``            a model routed to the texturing track must carry UVs

Nothing here renders through LOVE; the silhouette test rasterizes the mesh
itself so the check stays runnable without a GPU.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
ITEMS_JSON = REPO_ROOT / "data" / "items.json"

# Normalized geometry is rounded to this many decimals before hashing. Coarse
# enough that float noise from two runs of the same recipe collapses together,
# fine enough that two genuinely different shapes never do.
GEOMETRY_PRECISION = 4

# Silhouettes are compared at the resolution the player actually sees an item
# at, not at authoring resolution. Two shapes that differ only below this
# threshold are one shape as far as the game is concerned.
SILHOUETTE_RES = 64

# Two bars, on purpose.
#
# The loose one is what the legacy library is measured against: it was
# calibrated to catch renamed boxes, and holding 200 known-bad models to a real
# standard would only produce hundreds of baseline entries nobody reads.
#
# The strict one applies to new work. The first lathe cohort cleared 0.97 with
# a top pair at 0.9616 -- eight variations of one ring, passing a gate that was
# never asking for design variety. A cohort should have visible margin, not
# eight thousandths.
SILHOUETTE_IOU_LIMIT = 0.97
SILHOUETTE_IOU_LIMIT_NEW = 0.85


@dataclass
class Mesh:
    """A parsed OBJ, reduced to what the corpus checks need."""

    path: Path
    vertices: np.ndarray  # (n, 3) float64
    faces: list[list[int]] = field(default_factory=list)  # vertex indices, 0-based
    faces_with_uv: int = 0

    @property
    def name(self) -> str:
        return self.path.stem


class ItemModelError(RuntimeError):
    """Raised when the corpus cannot be assembled at all."""


def parse_obj(path: Path) -> Mesh:
    """Parse the subset of OBJ this repository emits.

    Faces are triangulated by fanning, which is correct for the convex polygons
    the mesh recipes produce and is only ever used for silhouette coverage.
    """
    vertices: list[tuple[float, float, float]] = []
    faces: list[list[int]] = []
    faces_with_uv = 0

    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            parts = line.split()
            if not parts:
                continue
            tag = parts[0]
            if tag == "v":
                if len(parts) < 4:
                    raise ItemModelError(f"{path}: malformed vertex: {line.strip()!r}")
                vertices.append(tuple(float(v) for v in parts[1:4]))
            elif tag == "f":
                corners = parts[1:]
                if len(corners) < 3:
                    raise ItemModelError(f"{path}: face with {len(corners)} corners")
                indices = []
                has_uv = True
                for corner in corners:
                    fields = corner.split("/")
                    indices.append(int(fields[0]) - 1)
                    if len(fields) < 2 or not fields[1]:
                        has_uv = False
                for i in range(1, len(indices) - 1):
                    faces.append([indices[0], indices[i], indices[i + 1]])
                if has_uv:
                    faces_with_uv += 1

    if not vertices:
        raise ItemModelError(f"{path}: no vertices")

    return Mesh(
        path=path,
        vertices=np.asarray(vertices, dtype=np.float64),
        faces=faces,
        faces_with_uv=faces_with_uv,
    )


def normalized_vertices(mesh: Mesh) -> np.ndarray:
    """Centre on the centroid and scale so the largest extent is 1.

    Normalizing before hashing is what makes the check catch a duplicate that
    was merely moved or resized, which per-asset validity never would.
    """
    verts = mesh.vertices - mesh.vertices.mean(axis=0)
    extent = float(np.abs(verts).max())
    if extent <= 0.0 or not math.isfinite(extent):
        raise ItemModelError(f"{mesh.path}: degenerate extent {extent}")
    return verts / extent


def geometry_hash(mesh: Mesh) -> str:
    """Stable identity for a shape, independent of position, scale and name."""
    verts = np.round(normalized_vertices(mesh), GEOMETRY_PRECISION)
    # Sort so that a re-ordered vertex list is still recognised as the same
    # shape; the recipes are deterministic but a reorder must not launder a
    # duplicate past the gate.
    order = np.lexsort((verts[:, 2], verts[:, 1], verts[:, 0]))
    payload = verts[order].tobytes()
    return hashlib.sha256(payload).hexdigest()


def _rasterize(points_2d: np.ndarray, faces: list[list[int]], res: int) -> np.ndarray:
    """Fill triangles into a boolean mask of ``res`` x ``res``.

    Coordinates arrive already normalized into [-1, 1] by a single uniform
    scale, and are mapped to the raster with that same fixed domain. Fitting
    each view to its own bounding box instead would stretch every silhouette to
    fill the frame, which makes proportion invisible: a tall narrow bottle and
    a short wide one would rasterize identically, and so would a slim ring and
    a chunky one. Proportion is most of what distinguishes these objects.
    """
    mask = np.zeros((res, res), dtype=bool)
    pixels = (points_2d + 1.0) * 0.5 * (res - 1)

    grid_x, grid_y = np.meshgrid(np.arange(res), np.arange(res))
    for face in faces:
        a, b, c = pixels[face[0]], pixels[face[1]], pixels[face[2]]
        min_x = max(int(math.floor(min(a[0], b[0], c[0]))), 0)
        max_x = min(int(math.ceil(max(a[0], b[0], c[0]))), res - 1)
        min_y = max(int(math.floor(min(a[1], b[1], c[1]))), 0)
        max_y = min(int(math.ceil(max(a[1], b[1], c[1]))), res - 1)
        if min_x > max_x or min_y > max_y:
            continue

        px = grid_x[min_y : max_y + 1, min_x : max_x + 1]
        py = grid_y[min_y : max_y + 1, min_x : max_x + 1]
        denom = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(denom) < 1e-12:
            # Edge-on or degenerate triangle contributes no area from this view.
            continue
        w0 = ((b[1] - c[1]) * (px - c[0]) + (c[0] - b[0]) * (py - c[1])) / denom
        w1 = ((c[1] - a[1]) * (px - c[0]) + (a[0] - c[0]) * (py - c[1])) / denom
        w2 = 1.0 - w0 - w1
        inside = (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9)
        mask[min_y : max_y + 1, min_x : max_x + 1] |= inside

    return mask


def silhouettes(mesh: Mesh, res: int = SILHOUETTE_RES) -> np.ndarray:
    """Orthographic alpha masks down each canonical axis, stacked.

    Three views rather than one, because a great many of these shapes are
    rotationally symmetric and would collide from the front while differing
    from above.
    """
    verts = normalized_vertices(mesh)
    views = [verts[:, [0, 1]], verts[:, [0, 2]], verts[:, [1, 2]]]
    return np.stack([_rasterize(view, mesh.faces, res) for view in views])


def silhouette_iou(left: np.ndarray, right: np.ndarray) -> float:
    """Mean per-view intersection-over-union, in [0, 1]."""
    scores = []
    for a, b in zip(left, right):
        union = np.count_nonzero(a | b)
        if union == 0:
            scores.append(1.0)
            continue
        scores.append(np.count_nonzero(a & b) / union)
    return float(np.mean(scores))


def load_item_models(items_json: Path = ITEMS_JSON) -> dict[str, Path]:
    """Map item name to the model file it references.

    Keyed by item rather than by file: two items pointing at one file is itself
    a duplicate, and reading the directory instead would hide that.
    """
    items = json.loads(items_json.read_text(encoding="utf-8"))
    models: dict[str, Path] = {}
    for item in items:
        model = item.get("model")
        if not model:
            continue
        path = REPO_ROOT / model
        if not path.exists():
            raise ItemModelError(f"item {item.get('name')!r} references missing {model}")
        models[item["name"]] = path
    return models
