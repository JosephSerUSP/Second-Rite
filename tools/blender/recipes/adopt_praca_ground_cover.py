"""Adopt the Geometry Nodes ground cover into the adopted St. Maria Praca (#1270).

A surgical edit in the style of `replace_st_maria_tree.py`, not a rebuild. It opens the adopted
source, adds ONE collection (`GROUND_COVER_SET`) holding everything the cover needs, and saves. It
touches no existing object, mesh, material or setting, and it is idempotent: run it again and it
finds its own host, reports that it is already adopted, and writes nothing.

What the collection holds, all of it ordinary and editable in the document:

  * `GROUND_COVER_GUIDE`: a scratch terrain guide (never rendered) carrying the painted density as
    the vertex group `cover_density`. Repaint it in Blender to move the grass. The layout it was
    painted from (`--layout`, default E: building bases, tree rings and lane edges) is recorded on
    the host, but after adoption the paint is the authority, not the layout function;
  * `GROUND_COVER_LANE`: a copy of the walkable lane, the keep-out footprint (the original lane
    object is left where it is);
  * `GROUND_COVER_CARDS`: the crossed-quad tuft sources, one per atlas cell;
  * `GROUND_COVER`: the host carrying the `SR_GroundCover` modifier and the `sr_bake_source` marker
    the exterior exporter includes it by.

The tuft budget is a hard ceiling met by scaling the density until the realised count fits, not by
`Max Tufts` truncation (which would bias the layout toward the low-index end of the guide); `Max
Tufts` is then set to the budget as a backstop.

Blender must not have the document open: it holds no lock, so a running session would overwrite
this edit on its next save. Run through the pinned Blender:

    blender -b -noaudio --factory-startup -P tools/blender/recipes/adopt_praca_ground_cover.py

Pass ``-- --dry-run`` to report what would change without writing, ``-- --document PATH`` to work on
a copy. The adopted `.blend` is edited only by this script; the shipped package is not regenerated
by it (a regeneration is an owner-signed step).
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender"))
import environment_sources  # noqa: E402
import ground_cover  # noqa: E402
import ground_cover_placement as placement  # noqa: E402
import tree_material  # noqa: E402

DOCUMENT = ROOT / "projects/hichaukitoden-game/assets/authoring/environments/st_maria_praca_modelled.blend"
SET_COLLECTION = "GROUND_COVER_SET"
GUIDE_NAME = "GROUND_COVER_GUIDE"
LANE_COPY = "GROUND_COVER_LANE"
#: Custom properties recording how the cover was made, on the host.
PROPERTY_LAYOUT, PROPERTY_BUDGET, PROPERTY_SEED = "sr_cover_layout", "sr_cover_budget", "sr_cover_seed"
DEFAULT_LAYOUT = "E_mixed"
DEFAULT_BUDGET = 375
DEFAULT_SEED = 1


def existing_host():
    host = bpy.data.objects.get(ground_cover.HOST_NAME)
    return host if host is not None and host.get(ground_cover.BAKE_PROPERTY) else None


def protect_orphans() -> list[str]:
    """Give every datablock nothing uses a fake user, so saving does not silently delete it.

    Blender drops a datablock with no users when it writes a file. This document carries some (nine
    unused actor-sprite preview materials), and every save through Blender would take them. Adopting
    the cover is not a reason to lose them, so they are kept, and named in the report.
    """
    kept = []
    for collection in (bpy.data.materials, bpy.data.meshes, bpy.data.images, bpy.data.node_groups,
                       bpy.data.textures, bpy.data.worlds, bpy.data.lights, bpy.data.cameras,
                       bpy.data.curves, bpy.data.actions, bpy.data.collections):
        for datablock in collection:
            if getattr(datablock, "type", "") in ("RENDER_RESULT", "COMPOSITING"):
                continue                        # a transient image Blender makes, not authored data
            if datablock.users == 0 and not datablock.use_fake_user:
                datablock.use_fake_user = True
                kept.append(f"{type(datablock).__name__}:{datablock.name}")
    return kept


def adopt(layout: str, budget: int, seed: int) -> dict:
    scene = bpy.context.scene
    if layout not in placement.CANDIDATES:
        raise SystemExit(f"unknown layout {layout!r}; choose from {sorted(placement.CANDIDATES)}")
    ground = bpy.data.objects["ARCH_square_ground"]
    lane = next(o for o in scene.objects if o.name.startswith("LD_walkable_lane"))

    holder = bpy.data.collections.new(SET_COLLECTION)
    # The exterior exporter bakes what is reachable from TH_SOURCE, so the set must live there: a
    # collection linked to the scene alone is invisible to the bake and the cover would silently
    # never reach the package (the first full bake of this recipe showed exactly that).
    source = bpy.data.collections.get("TH_SOURCE")
    if source is None:
        raise SystemExit("the document has no TH_SOURCE collection; refusing to guess where the cover goes")
    source.children.link(holder)

    field = placement.Field(scene, ground)
    guide = placement.build_guide(field, scene, name=GUIDE_NAME, collection=holder)
    guide.hide_render = True

    keep_out = bpy.data.collections.new(ground_cover.KEEP_OUT_COLLECTION)
    holder.children.link(keep_out)
    lane_copy = lane.copy()
    lane_copy.name = LANE_COPY
    keep_out.objects.link(lane_copy)
    lane_copy.hide_render = True

    cards = ground_cover.build_cards()
    holder.children.link(cards)
    for card in cards.objects:
        card.hide_render = True
    cards.hide_viewport = True
    for image in bpy.data.images:
        if image.filepath and Path(bpy.path.abspath(image.filepath)).name == tree_material.GRASS_ATLAS.name:
            try:                                  # relative to the document, so the repo can move
                image.filepath = bpy.path.relpath(str(tree_material.GRASS_ATLAS))
            except ValueError:                    # a copy on another drive has no relative path
                pass

    host = ground_cover.add(guide, keep_out=keep_out, cards=cards, density_group=placement.GROUP,
                            parent_collection=holder,
                            **{"Slope Limit": 38.0, "Keep Out Margin": 0.3, "Seed": seed,
                               "Max Tufts": 100000, "Tuft Height": 0.34})
    placement.paint(guide, field, placement.CANDIDATES[layout][1])
    density = placement.fit_to_budget(host, budget)
    host[PROPERTY_LAYOUT], host[PROPERTY_BUDGET], host[PROPERTY_SEED] = layout, budget, seed
    count = len(placement.tufts(host))
    return {"layout": layout, "budget": budget, "tufts": count, "triangles": count * 4,
            "density": round(density, 3), "seed": seed}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--layout", default=DEFAULT_LAYOUT)
    parser.add_argument("--budget", type=int, default=DEFAULT_BUDGET)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--document", type=Path, default=DOCUMENT)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])

    environment_sources.refuse_superseded(args.document)
    bpy.ops.wm.open_mainfile(filepath=str(args.document.resolve()))
    host = existing_host()
    if host is not None:
        print("GROUND COVER ALREADY ADOPTED " + json.dumps({
            "layout": host.get(PROPERTY_LAYOUT), "budget": host.get(PROPERTY_BUDGET),
            "seed": host.get(PROPERTY_SEED)}) + " -- nothing written")
        return
    kept = protect_orphans()
    if kept:
        print(f"kept {len(kept)} unused datablock(s) that a save would have dropped: {', '.join(sorted(kept))}")
    report = adopt(args.layout, args.budget, args.seed)
    print("GROUND COVER " + json.dumps(report))
    if args.dry_run:
        print("DRY RUN, nothing written")
        return
    backup = args.document.with_suffix(".blend.bak")
    shutil.copy2(args.document, backup)
    bpy.ops.wm.save_mainfile(filepath=str(args.document.resolve()))
    print(f"SAVED {args.document} (previous version kept at {backup.name})")


if __name__ == "__main__":
    main()
