"""Generic staging helpers shared by every attempt.

Strictly generic. Nothing here knows about any building, layout, coordinate or
architectural motif -- attempts supply all of that themselves. These helpers
exist so that nine independent scenes still satisfy one runtime contract.
"""
from __future__ import annotations

import json
from pathlib import Path

import bpy

from . import geom, mats, scene as cr_scene


def runtime_box(stage, name, *, x0, x1, y0, y1, z0, z1):
    """One coarse TH_RENDER solid. The bake target; no material of its own."""
    obj = geom.slab(name, stage.render, x0=x0, x1=x1, y0=y0, y1=y1, z0=z0, z1=z1)
    obj["thestra_runtime"] = True
    return obj


def runtime_plane(stage, name, *, x0, x1, y0, y1, z):
    obj = geom.ground(name, stage.render, x0=x0, x1=x1, y0=y0, y1=y1, z=z, cuts=1)
    obj["thestra_runtime"] = True
    return obj


def collider(stage, name, *, x0, x1, y0, y1, z0, z1):
    obj = geom.slab(name, stage.collision, x0=x0, x1=x1, y0=y0, y1=y1,
                    z0=z0, z1=z1)
    obj["thestra_collision"] = True
    return obj


def walk_bounds(stage, *, y_min, y_max, x, z):
    """Declare the horizontal walking lane and publish it as anchors."""
    stage.anchor("walk_min", (x, y_min, z), kind="bound")
    stage.anchor("walk_max", (x, y_max, z), kind="bound")
    stage.walk = {"x": x, "z": z, "yMin": y_min, "yMax": y_max}
    return stage.walk


def cast(stage, *, hero, npcs):
    """Stage the protagonist and NPC stand-ins from walker.png frames only.

    walker.png is a 6-frame 24x48 strip and is the ONLY pre-existing visual
    asset this gauntlet consumes. NPC stand-ins are different frames of it.
    """
    objs = {"hero": cr_scene.actor(stage, "TH_ACTOR_HERO", anchor=hero["at"],
                                   frame_index=hero.get("frame", 0))}
    stage.anchor("spawn", hero["at"], kind="spawn")
    for i, npc in enumerate(npcs):
        name = "TH_ACTOR_NPC%d" % (i + 1)
        objs[name] = cr_scene.actor(stage, name, anchor=npc["at"],
                                    frame_index=npc.get("frame", 1 + i))
        stage.anchor("npc_%d" % (i + 1), npc["at"], kind="npc")
    return objs


def doorway(stage, name, at, *, forward=(-1, 0, 0)):
    return stage.anchor(name, at, kind="door", forward=forward)


def relief(stage, obj, material_id, *, strength=0.12, mid_level=None,
           subdivisions=None):
    """Attach real displacement driven by a material's own height map.

    mid_level defaults to the map's own mean so the panel neither inflates nor
    sinks relative to the coarse mass it sits on.
    """
    material = mats.get(material_id)
    if not material.height_path:
        return obj
    tex = mats.height_texture("H_%s_%s" % (obj.name, material_id),
                              material.height_path)
    if mid_level is None:
        mid_level = _mean_of(material.height_path)
    geom.displace(obj, tex, strength=strength, mid_level=mid_level)
    return obj


_MEAN_CACHE = {}


def _mean_of(path):
    path = str(path)
    if path not in _MEAN_CACHE:
        img = bpy.data.images.load(path, check_existing=True)
        px = list(img.pixels)
        # RGBA interleaved; sample the red channel sparsely
        vals = px[0::64]
        _MEAN_CACHE[path] = sum(vals) / max(1, len(vals))
    return _MEAN_CACHE[path]


def census(stage):
    """Source vs runtime triangle census, measured after modifiers."""
    dg = bpy.context.evaluated_depsgraph_get()
    src = geom.triangles(list(stage.source.objects), dg)
    run = geom.triangles(list(stage.render.objects), dg)
    col = geom.triangles(list(stage.collision.objects), dg)
    return {
        "sourceTriangles": src,
        "renderTriangles": run,
        "collisionTriangles": col,
        "reductionRatio": round(src / run, 2) if run else None,
    }


def finish(stage, out_dir, attempt_id, *, concept, samples=110,
           exposure=0.0, look="None"):
    """Render the beauty frame, save the .blend and write the attempt record.

    TH_RENDER is hidden for the beauty render: coincident untextured runtime
    boxes z-fight with the source and photograph as flat grey slabs.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cr_scene.hide_render(stage.render, True)
    cr_scene.hide_render(stage.collision, True)
    cr_scene.hide_render(stage.cols["TH_ANCHORS"], True)
    cr_scene.hide_render(stage.cols["TH_CAMERA_PREVIEW"], True)
    bpy.context.view_layer.update()

    stats = census(stage)
    png = out_dir / ("%s.png" % attempt_id)
    cr_scene.render(png, samples=samples, exposure=exposure, look=look)
    blend = cr_scene.save(out_dir / ("%s.blend" % attempt_id))

    record = {
        "id": attempt_id,
        "concept": concept,
        "render": str(png),
        "blend": str(blend),
        "camera": {
            "lensMm": round(stage.solve["lensMm"], 4),
            "pitchDegrees": stage.solve["pitchDegrees"],
            "hFovDegrees": round(stage.solve["hFovDegrees"], 7),
            "eye": [round(v, 4) for v in stage.solve["eye"]],
            "actionPlaneX": round(stage.plane_x, 4),
            "walkerPixels": round(stage.solve["measuredPx"], 4),
        },
        "stats": stats,
        "anchors": stage.anchors,
        "walk": getattr(stage, "walk", None),
        "materials": sorted(getattr(stage, "used_materials", [])),
    }
    (out_dir / ("%s.json" % attempt_id)).write_text(
        json.dumps(record, indent=2), encoding="utf-8")
    print("[attempt] %s src=%d run=%d ratio=%s" % (
        attempt_id, stats["sourceTriangles"], stats["renderTriangles"],
        stats["reductionRatio"]))
    print("[attempt] ATTEMPT_OK %s" % attempt_id)
    return record


def use(stage, *material_ids):
    used = getattr(stage, "used_materials", None)
    if used is None:
        used = set()
        stage.used_materials = used
    used.update(material_ids)
