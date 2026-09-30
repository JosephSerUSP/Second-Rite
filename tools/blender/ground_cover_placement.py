"""Ground-cover placement on the adopted Praca: the candidate layouts and how they are painted (#1270).

Shared by the placement study (`study_ground_cover_placement.py`, which photographs every
candidate) and the adoption recipe (`recipes/adopt_praca_ground_cover.py`, which puts the owner's
choice into the source document). Runs inside Blender.

A layout is a function from a point on the ground to a density weight in [0, 1]. The weight is
painted onto a scratch terrain guide as a vertex group, so after adoption the density stays a
thing the owner can repaint in Blender; the guide is the procedural handle, not the picture.
Every layout obeys the same rules: density only inside the plate frame (menu rows included), never
under a building, and a hard tuft budget met by scaling the density until the realised count
fits, not by truncating in index order.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector, kdtree, noise

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import ground_cover  # noqa: E402

GROUP = "cover_density"
PLATE = (906, 240)
MENU_TOP_ROW = 144          # the persistent menu covers rows 144-240 of the plate
SCAFFOLD_PREFIXES = ("SCALE_", "LD_", "COL_", "RT_")
BUILDING_PREFIXES = ("ARCH_west_house", "BUILD_", "STUDY_")
GUIDE_X = (-3.0, 14.0)
GUIDE_Y = (-5.0, 28.7)
GUIDE_STEP = 0.25
LANE_X = (6.8, 8.8)
LANE_Y = (0.0, 23.699)



def smoothstep(edge0, edge1, x):
    t = min(1.0, max(0.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def _is_building(obj):
    return obj.type == "MESH" and obj.name.startswith(BUILDING_PREFIXES) and not obj.name.endswith("_roof")



class Field:
    """Per-vertex facts about the guide that every candidate layout is built from."""

    def __init__(self, scene, ground):
        self.z = ground.matrix_world.translation.z
        xs = [GUIDE_X[0] + i * GUIDE_STEP for i in range(int((GUIDE_X[1] - GUIDE_X[0]) / GUIDE_STEP) + 1)]
        ys = [GUIDE_Y[0] + j * GUIDE_STEP for j in range(int((GUIDE_Y[1] - GUIDE_Y[0]) / GUIDE_STEP) + 1)]
        self.nx, self.ny = len(xs), len(ys)
        self.points = [(x, y) for x in xs for y in ys]

        base_points = []
        for obj in scene.objects:
            if _is_building(obj):
                for v in obj.data.vertices:
                    w = obj.matrix_world @ v.co
                    if w.z < 0.5:
                        base_points.append(w)
        building_bases = kdtree.KDTree(max(1, len(base_points)))
        for i, p in enumerate(base_points):
            building_bases.insert((p.x, p.y, 0.0), i)
        building_bases.balance()

        trunks = []
        for obj in scene.objects:
            if obj.name.startswith("FG_praca_tree_BRANCHES"):
                low = [obj.matrix_world @ v.co for v in obj.data.vertices]
                floor = min(p.z for p in low)
                base = [p for p in low if p.z < floor + 0.4]
                trunks.append((sum(p.x for p in base) / len(base), sum(p.y for p in base) / len(base)))
        self.trunks = trunks

        camera = scene.camera
        depsgraph = bpy.context.evaluated_depsgraph_get()
        self.covered, self.pixel, self.d_building, self.d_trunk = [], [], [], []
        for x, y in self.points:
            # Under a building or its roof: cast down from above; a building hit means covered.
            hit, _loc, _n, _i, obj, _m = scene.ray_cast(depsgraph, Vector((x, y, 12.0)), Vector((0, 0, -1)))
            self.covered.append(bool(hit and _is_building_or_roof(obj)))
            ndc = world_to_camera_view(scene, camera, Vector((x, y, self.z)))
            self.pixel.append(((ndc.x * PLATE[0]), ((1.0 - ndc.y) * PLATE[1]), ndc.z > 0))
            _co, _idx, dist = building_bases.find((x, y, 0.0)) if base_points else (None, None, 99.0)
            self.d_building.append(dist)
            self.d_trunk.append(min((math.hypot(x - tx, y - ty) for tx, ty in trunks), default=99.0))

        self.covered = self._dilated(self.covered)
        # The same one-cell margin inside the plate frame: a face straddling the frame edge would
        # root tufts just outside it, spending budget on grass nobody sees.
        outside = self._dilated([not self._raw_in_frame(i) for i in range(len(self.points))])
        self.frame_ok = [not o for o in outside]

    def _dilated(self, covered):
        """Grow the covered set by one cell in every direction.

        A tuft can land anywhere on a guide face, so a face with even one covered corner must carry
        no density: otherwise points fall on the building side of an edge that runs between two
        vertices, and root under a wall or an overhanging roof.
        """
        grown = list(covered)
        for i in range(self.nx):
            for j in range(self.ny):
                if not covered[i * self.ny + j]:
                    continue
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        a, b = i + di, j + dj
                        if 0 <= a < self.nx and 0 <= b < self.ny:
                            grown[a * self.ny + b] = True
        return grown

    def _raw_in_frame(self, i):
        px, py, front = self.pixel[i]
        return front and 0.0 <= px <= PLATE[0] and 0.0 <= py <= PLATE[1]

    def in_frame(self, i):
        return self.frame_ok[i]


def _is_building_or_roof(obj):
    return obj is not None and obj.type == "MESH" and obj.name.startswith(BUILDING_PREFIXES)


# -- the candidate layouts: (x, y, field index) -> weight in [0, 1] ---------------------

def layout_bases(f, i, x, y):
    """Growing where walls meet the ground: a fringe along every building base."""
    d = f.d_building[i]
    return 0.0 if d < 0.12 or d > 3.0 else math.exp(-(d - 0.12) / 0.75)


def layout_trees(f, i, x, y):
    """A ring around each tree, where roots and shade let it grow."""
    d = f.d_trunk[i]
    return max(0.0, 1.0 - abs(d - 1.7) / 1.1)


def layout_lane_edges(f, i, x, y):
    """Creeping in from both sides of the walkable lane, thinning with distance."""
    dx = max(LANE_X[0] - x, x - LANE_X[1], 0.0)
    if dx <= 0.0:
        return 0.0
    along = smoothstep(LANE_Y[0] - 2.0, LANE_Y[0] + 1.0, y) * (1.0 - smoothstep(LANE_Y[1] - 1.0, LANE_Y[1] + 2.0, y))
    return math.exp(-dx / 0.9) * along


def layout_patches(f, i, x, y):
    """Worn paving giving way: irregular patches, no relation to any object."""
    n = noise.fractal(Vector((x / 2.2, y / 2.2, 3.7)), 0.5, 2.0, 3)
    return smoothstep(0.05, 0.3, n)


def layout_mixed(f, i, x, y):
    """Base fringe, tree rings and lane edges together, each at reduced weight."""
    return max(0.9 * layout_bases(f, i, x, y), 0.9 * layout_trees(f, i, x, y),
               0.6 * layout_lane_edges(f, i, x, y))


CANDIDATES = {
    "A_bases": ("Building bases", layout_bases),
    "B_trees": ("Tree rings", layout_trees),
    "C_lane_edges": ("Lane edges", layout_lane_edges),
    "D_patches": ("Worn-paving patches", layout_patches),
    "E_mixed": ("Bases + trees + lane edges", layout_mixed),
}


def build_guide(field, scene, name="COVER_GUIDE", collection=None):
    verts = [(x, y, field.z) for x, y in field.points]
    faces = []
    for i in range(field.nx - 1):
        for j in range(field.ny - 1):
            a = i * field.ny + j
            faces.append((a, a + field.ny, a + field.ny + 1, a + 1))
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    guide = bpy.data.objects.new(name, mesh)
    (collection or scene.collection).objects.link(guide)
    guide.hide_render = True
    guide.vertex_groups.new(name=GROUP)
    return guide


def paint(guide, field, layout):
    group = guide.vertex_groups[GROUP]
    for i, (x, y) in enumerate(field.points):
        weight = 0.0
        if field.in_frame(i) and not field.covered[i]:
            weight = max(0.0, min(1.0, layout(field, i, x, y)))
        group.add([i], weight, "REPLACE")


def tufts(host):
    mesh = ground_cover.evaluated_mesh(host)
    verts = [v.co.copy() for v in mesh.vertices]
    count = len(verts) // 8
    bases = []
    for k in range(count):
        chunk = verts[k * 8:(k + 1) * 8]
        bases.append((sum(v.x for v in chunk) / 8, sum(v.y for v in chunk) / 8, min(v.z for v in chunk)))
    host.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh_clear()
    return bases


def fit_to_budget(host, budget):
    """The largest density whose realised tuft count does not exceed the budget."""
    low, high = 0.05, 400.0
    for _ in range(22):
        middle = math.sqrt(low * high)
        ground_cover.configure(host, **{"Density": middle, "Max Tufts": 100000})
        if len(tufts(host)) <= budget:
            low = middle
        else:
            high = middle
    ground_cover.configure(host, **{"Density": low, "Max Tufts": budget})
    return low
