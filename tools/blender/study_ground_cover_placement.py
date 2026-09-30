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
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import ground_cover  # noqa: E402

BLEND = ROOT / "projects" / "hichaukitoden-game" / "assets" / "authoring" / "environments" / "st_maria_praca_modelled.blend"
from ground_cover_placement import (  # noqa: E402
    BUILDING_PREFIXES, CANDIDATES, GROUP, MENU_TOP_ROW, PLATE, SCAFFOLD_PREFIXES, Field,
    build_guide, fit_to_budget, paint, tufts)


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
