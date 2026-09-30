"""Where should grass grow on the adopted Praça? Candidate layouts at the plate camera (#1270).

Placement is the owner's decision, so this shows it instead of asking for it in words. It
opens `st_maria_praca_modelled.blend` (never saving it), puts the `SR_GroundCover`
modifier on a scratch terrain guide under several candidate density fields, and
photographs each through the plate camera at the plate's 906 x 240 with EEVEE.

Every candidate obeys the same rules, so the layouts differ only in *where*:

  * density exists only inside the plate frame (including the rows the menu covers),
    and never under a building or on the walkable lane;
  * the budget is a hard ceiling (`--budget` tufts, four triangles each), reached by
    scaling the density until the count fits, not by truncating in index order, which
    would bias the layout toward whichever end of the mesh comes first.

Run through the pinned Blender:

    blender -b --factory-startup --python tools/blender/study_ground_cover_placement.py -- \
        --out out/grass-study

It writes `baseline.png`, one PNG per candidate, and `placement.json` (counts, how many
tufts fall above and under the menu rows, and every tuft's plate pixel). Then
`study_ground_cover_sheet.py` builds the contact sheet.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector, kdtree, noise

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import ground_cover  # noqa: E402

BLEND = ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring" / "environments" / "st_maria_praca_modelled.blend"
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


def prepare_render(scene):
    for obj in scene.objects:
        if obj.name.startswith(SCAFFOLD_PREFIXES):
            obj.hide_render = True
    scene.render.engine = "BLENDER_EEVEE"
    # No reconstruction filter: the tufts are drawn at native pixels, nearest-sampled, in the
    # game. Film > Filter Size (1.5 px by default) would blur a 9 px tuft into a smear.
    scene.render.filter_size = 0.0
    scene.render.resolution_x, scene.render.resolution_y = PLATE
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"


def render(scene, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(path.resolve())
    bpy.ops.render.render(write_still=True)


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

    def in_frame(self, i):
        px, py, front = self.pixel[i]
        return front and 0.0 <= px <= PLATE[0] and 0.0 <= py <= PLATE[1]


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


def build_guide(field, scene):
    verts = [(x, y, field.z) for x, y in field.points]
    faces = []
    for i in range(field.nx - 1):
        for j in range(field.ny - 1):
            a = i * field.ny + j
            faces.append((a, a + field.ny, a + field.ny + 1, a + 1))
    mesh = bpy.data.meshes.new("COVER_GUIDE_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    guide = bpy.data.objects.new("COVER_GUIDE", mesh)
    scene.collection.objects.link(guide)
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "out" / "grass-study")
    parser.add_argument("--budget", type=int, default=375)
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])

    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    scene = bpy.context.scene
    prepare_render(scene)
    ground = bpy.data.objects["ARCH_square_ground"]
    render(scene, args.out / "baseline.png")

    field = Field(scene, ground)
    guide = build_guide(field, scene)
    lane = next(o for o in scene.objects if o.name.startswith("LD_walkable_lane"))
    keep_out = bpy.data.collections.new(ground_cover.KEEP_OUT_COLLECTION)
    keep_out.objects.link(lane)
    host = ground_cover.add(guide, keep_out=keep_out, density_group=GROUP,
                            **{"Slope Limit": 38.0, "Keep Out Margin": 0.3, "Seed": args.seed,
                               "Max Tufts": 100000, "Tuft Height": 0.34})
    # The host is a plain mesh on the guide's transform; the modifier's own output is what renders.

    report = {"budget": args.budget, "menuTopRow": MENU_TOP_ROW, "plate": list(PLATE),
              "groundZ": field.z, "trunks": field.trunks, "candidates": {}}
    camera = scene.camera
    for key, (label, layout) in CANDIDATES.items():
        paint(guide, field, layout)
        density = fit_to_budget(host, args.budget)
        bases = tufts(host)
        placed = []
        for x, y, z in bases:
            ndc = world_to_camera_view(scene, camera, Vector((x, y, z)))
            placed.append({"x": round(x, 3), "y": round(y, 3),
                           "px": round(ndc.x * PLATE[0], 1), "py": round((1.0 - ndc.y) * PLATE[1], 1)})
        above = sum(1 for p in placed if p["py"] < MENU_TOP_ROW)
        report["candidates"][key] = {
            "label": label, "tufts": len(placed), "triangles": len(placed) * 4, "density": round(density, 3),
            "aboveMenu": above, "underMenu": len(placed) - above,
            "outOfFrame": sum(1 for p in placed if not (0 <= p["px"] <= PLATE[0] and 0 <= p["py"] <= PLATE[1])),
            "tuftPixels": placed}
        render(scene, args.out / f"{key}.png")
        print(f"{key}: {len(placed)} tufts, {above} above / {len(placed) - above} under the menu, density {density:.2f}")
    (args.out / "placement.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print("GRASS STUDY OK", args.out)


if __name__ == "__main__":
    main()
