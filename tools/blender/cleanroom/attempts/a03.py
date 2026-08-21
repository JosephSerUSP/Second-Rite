"""Attempt 03 -- THE RIB WALK.

Spatial idea: darkness framing light; traversal as passage.

The route runs the length of a covered way. Transverse masonry ribs spring
across the street at irregular intervals along the walking axis, so the player
passes UNDER architecture rather than in front of it. Because the camera looks
perpendicular to the vault axis, each rib reads as a complete arch in
silhouette, and the gaps between them read as bays.

The composition is mostly dark. The whole right-hand end opens to daylight,
which is the only bright region in the frame and is therefore where the eye
goes and where the player wants to walk. That is the entire lighting idea:
the level tells you where to go by being darker everywhere else.

Deep recess: the doorway is cut into the far arcade wall inside a bay, with a
real reveal, so it is legible as a hole in mass rather than a decal.
"""
from __future__ import annotations

import math

from .. import geom, mats, scene as cr_scene, staging, vocab

CONCEPT = "covered way; transverse ribs, darkness opening to one bright end"

GROUND = -4.20
NEAR_PIER = 15.60
FAR_WALL = 27.40
RIB_Y = (-9.4, -4.10, 0.85, 6.60, 13.20, 19.10)
DOOR_Y = 3.55


def _rib_profile():
    """(x, z) section of one rib: two piers and a segmental arch between."""
    springing = GROUND + 2.35
    crown = GROUND + 4.55
    inner_a, inner_b = NEAR_PIER + 0.95, FAR_WALL - 0.95
    mid = 0.5 * (inner_a + inner_b)
    half = 0.5 * (inner_b - inner_a)
    pts = [(NEAR_PIER, GROUND), (inner_a, GROUND), (inner_a, springing)]
    segs = 16
    for i in range(segs + 1):
        t = math.pi * i / segs
        pts.append((mid - half * math.cos(t),
                    springing + (crown - springing) * math.sin(t)))
    pts.append((inner_b, springing))
    pts.append((inner_b, GROUND))
    pts.append((FAR_WALL, GROUND))
    pts.append((FAR_WALL, crown + 0.85))
    pts.append((NEAR_PIER, crown + 0.85))
    return pts


def build(out_dir, attempt_id="03"):
    cr_scene.reset()
    stage = cr_scene.make_stage()
    vocab.build_vocabulary()
    S = stage.source
    staging.use(stage, "civic_ashlar", "stone_fine", "stone_mossy",
                "street_setts", "paint_madder", "metal_verdigris",
                "grime_moss", "timber_dark", "glass_leaded", "roof_lead")

    floor = geom.ground("SRC_FLOOR", S, x0=11.5, x1=FAR_WALL + 0.1,
                        y0=-16.0, y1=26.0, z=GROUND, cuts=46)
    mats.apply(floor, "street_setts")
    staging.relief(stage, floor, "street_setts", strength=0.06)

    # ---- the far arcade wall, pierced -------------------------------------
    holes = [{"y0": DOOR_Y - 0.62, "y1": DOOR_Y + 0.62,
              "z0": GROUND, "z1": GROUND + 2.45}]
    for wy, wz, wh in ((-6.90, GROUND + 2.10, 1.90), (9.60, GROUND + 2.10, 1.90),
                       (16.40, GROUND + 2.30, 2.10)):
        holes.append({"y0": wy - wh / 8.0, "y1": wy + wh / 8.0,
                      "z0": wz, "z1": wz + wh})
    for piece in geom.slotted_panel("SRC_FARWALL", S, x=FAR_WALL, y0=-16.0,
                                    y1=26.0, z0=GROUND, z1=GROUND + 5.60,
                                    holes=holes, cuts_per_m=10.0):
        mats.apply(piece, "stone_fine")
        staging.relief(stage, piece, "stone_fine", strength=0.13)
        cr_scene.shade_smooth(piece)
    for i, h in enumerate(holes):
        back = geom.slab("SRC_REVEAL%d" % i, S,
                         x0=FAR_WALL + 0.10, x1=FAR_WALL + 1.10,
                         y0=h["y0"] - 0.26, y1=h["y1"] + 0.26,
                         z0=h["z0"] - 0.26, z1=h["z1"] + 0.26)
        mats.apply(back, "grime_moss" if i else "timber_dark")

    leaf = geom.slab("SRC_DOOR", S, x0=FAR_WALL + 0.30, x1=FAR_WALL + 0.39,
                     y0=DOOR_Y - 0.56, y1=DOOR_Y + 0.56,
                     z0=GROUND, z1=GROUND + 2.28)
    geom.bevel(leaf, 0.03, 2)
    mats.apply(leaf, "paint_madder")
    surround = geom.slab("SRC_DOOR_SUR", S, x0=FAR_WALL - 0.16, x1=FAR_WALL + 0.06,
                         y0=DOOR_Y - 0.92, y1=DOOR_Y + 0.92,
                         z0=GROUND, z1=GROUND + 2.80)
    geom.bevel(surround, 0.05, 2)
    mats.apply(surround, "civic_ashlar")

    # ---- the ribs ----------------------------------------------------------
    prof = _rib_profile()
    for i, ry in enumerate(RIB_Y):
        width = 0.62 + 0.10 * (i % 3)
        rib = geom.prism("SRC_RIB%d" % i, S, extrude_axis="y", profile=prof,
                         start=ry - width * 0.5, end=ry + width * 0.5)
        mats.apply(rib, "civic_ashlar")
        # an impost block where the arch springs -- the only moulding
        for px in (NEAR_PIER + 0.95, FAR_WALL - 0.95):
            imp = geom.slab("SRC_IMP%d_%d" % (i, int(px * 10)), S,
                            x0=px - 0.20, x1=px + 0.20,
                            y0=ry - width * 0.5 - 0.10,
                            y1=ry + width * 0.5 + 0.10,
                            z0=GROUND + 2.25, z1=GROUND + 2.48)
            geom.bevel(imp, 0.035, 2)
            mats.apply(imp, "civic_ashlar")

    # the soffit between ribs, seen only as a dark ceiling plane
    soffit = geom.ground("SRC_SOFFIT", S, x0=NEAR_PIER + 0.95, x1=FAR_WALL - 0.95,
                         y0=-16.0, y1=26.0, z=GROUND + 4.62, cuts=6)
    mats.apply(soffit, "stone_mossy")

    # ---- the near arcade: piers only, so the player is seen between them --
    for i, ry in enumerate(RIB_Y):
        base = geom.slab("SRC_NBASE%d" % i, S,
                         x0=NEAR_PIER - 0.14, x1=NEAR_PIER + 1.10,
                         y0=ry - 0.52, y1=ry + 0.52,
                         z0=GROUND, z1=GROUND + 0.68)
        geom.bevel(base, 0.06, 2)
        mats.apply(base, "civic_ashlar")

    # ---- one deep bay of domestic accretion, in the dark half ------------
    ledge = geom.slab("SRC_LEDGE", S, x0=FAR_WALL - 0.95, x1=FAR_WALL,
                      y0=-3.90, y1=0.70, z0=GROUND + 0.72, z1=GROUND + 0.90)
    geom.bevel(ledge, 0.04, 2)
    mats.apply(ledge, "civic_ashlar")
    for i, cy in enumerate((-3.30, -2.55, -1.05)):
        crate = geom.slab("SRC_CRATE%d" % i, S,
                          x0=FAR_WALL - 1.55 + 0.12 * i, x1=FAR_WALL - 0.72,
                          y0=cy - 0.34, y1=cy + 0.34,
                          z0=GROUND, z1=GROUND + 0.62 + 0.14 * (i % 2))
        geom.bevel(crate, 0.03, 2)
        mats.apply(crate, "timber_dark")
    for i, hy in enumerate((-6.30, 11.70)):
        hook = geom.cylinder("SRC_HOOK%d" % i, S,
                             center=(FAR_WALL - 0.30, hy, GROUND + 2.55),
                             radius=0.030, height=0.62, segments=6, axis="z")
        mats.apply(hook, "metal_verdigris")

    # ---- the bright end ----------------------------------------------------
    # a wall closes the LEFT end so light can only arrive from the right
    endwall = geom.slab("SRC_ENDWALL", S, x0=NEAR_PIER, x1=FAR_WALL,
                        y0=-13.4, y1=-12.6, z0=GROUND, z1=GROUND + 5.6)
    mats.apply(endwall, "stone_mossy")
    staging.relief(stage, endwall, "stone_mossy", strength=0.0)
    # the far daylight surface the bright end opens onto
    daylight = geom.slab("SRC_DAYLIGHT", S, x0=FAR_WALL + 4.0, x1=FAR_WALL + 4.6,
                         y0=20.5, y1=34.0, z0=GROUND, z1=GROUND + 7.0)
    mats.apply(daylight, "limewash_pale")

    # ---- runtime -----------------------------------------------------------
    staging.runtime_plane(stage, "RUN_FLOOR", x0=11.5, x1=FAR_WALL,
                          y0=-16.0, y1=26.0, z=GROUND)
    staging.runtime_box(stage, "RUN_FARWALL", x0=FAR_WALL, x1=FAR_WALL + 1.2,
                        y0=-16.0, y1=26.0, z0=GROUND, z1=GROUND + 5.6)
    staging.runtime_box(stage, "RUN_SOFFIT", x0=NEAR_PIER, x1=FAR_WALL,
                        y0=-16.0, y1=26.0, z0=GROUND + 4.55, z1=GROUND + 5.45)
    for i, ry in enumerate(RIB_Y):
        staging.runtime_box(stage, "RUN_RIB%d" % i, x0=NEAR_PIER, x1=NEAR_PIER + 0.95,
                            y0=ry - 0.36, y1=ry + 0.36, z0=GROUND, z1=GROUND + 4.6)
    staging.runtime_box(stage, "RUN_ENDWALL", x0=NEAR_PIER, x1=FAR_WALL,
                        y0=-13.4, y1=-12.6, z0=GROUND, z1=GROUND + 5.6)

    staging.collider(stage, "COL_FAR", x0=FAR_WALL - 0.4, x1=FAR_WALL + 0.4,
                     y0=-16.0, y1=26.0, z0=GROUND, z1=GROUND + 3.0)
    staging.collider(stage, "COL_NEAR", x0=NEAR_PIER, x1=NEAR_PIER + 1.10,
                     y0=-16.0, y1=26.0, z0=GROUND, z1=GROUND + 1.0)
    staging.collider(stage, "COL_FLOOR", x0=NEAR_PIER, x1=FAR_WALL,
                     y0=-16.0, y1=26.0, z0=GROUND - 0.2, z1=GROUND)

    staging.walk_bounds(stage, y_min=-11.5, y_max=21.0, x=20.80, z=GROUND)
    staging.doorway(stage, "door_bay", (FAR_WALL - 0.5, DOOR_Y, GROUND))
    staging.cast(stage,
                 hero={"at": (20.80, 4.55, GROUND), "frame": 0},
                 npcs=[{"at": (22.60, -2.10, GROUND), "frame": 4},
                       {"at": (19.40, 11.10, GROUND), "frame": 2},
                       {"at": (21.90, 17.60, GROUND), "frame": 5}])

    # ---- light: almost none, except from the right-hand end ---------------
    cr_scene.sky(stage, top=(0.030, 0.040, 0.062), horizon=(0.075, 0.078, 0.072),
                 strength=1.0)
    cr_scene.sun(stage, energy=7.0, color=(1.0, 0.93, 0.79),
                 azimuth=118.0, elevation=13.0, size=0.030)
    cr_scene.area(stage, location=(21.0, 24.5, GROUND + 2.2), energy=900.0,
                  color=(1.0, 0.95, 0.86), size=6.5, rotation=(90, 0, 0),
                  name="TH_DAYLIGHT")
    cr_scene.point(stage, location=(FAR_WALL - 1.0, DOOR_Y, GROUND + 1.5),
                   energy=26.0, color=(1.0, 0.62, 0.28), radius=0.30)
    cr_scene.point(stage, location=(NEAR_PIER + 2.2, -5.6, GROUND + 2.3),
                   energy=13.0, color=(1.0, 0.58, 0.26), radius=0.26)

    return staging.finish(stage, out_dir, attempt_id, concept=CONCEPT,
                          samples=128)
