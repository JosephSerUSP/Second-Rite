"""Attempt 02 -- THE SAG.

Spatial idea: openness, and the skyline as the subject.

The opposite pole from a compressed lane. The buildings are pushed far back
(x = 29 and beyond), which is the only way rooflines get into frame at this
lens, and the street in front of them is wide and largely empty. The eye is
meant to go to the silhouette first and the people second.

Asymmetry is the whole composition: a squat, broad, blank civic shed occupies
screen-left; three tall narrow houses crowd screen-right; and between them the
authored subject is a GAP -- a column of sky with one distant tower in it.

The houses visibly sag toward one another. Their eaves are not parallel, their
storeys are not level, and no two are the same width. Controlled negative
space: the shed's roof plane and the open street are deliberately quiet, so
the crowded right-hand third can carry all the detail.
"""
from __future__ import annotations

from .. import geom, mats, scene as cr_scene, staging, vocab

CONCEPT = "open street; asymmetric skyline with an authored gap of sky"

GROUND = -4.20
STREET_BACK = 29.20
DOOR_Y = 9.10


def _house(S, stage, tag, *, y0, y1, x_face, eaves, ridge, lean, mat,
           window_rows, door=None):
    """One narrow house. Every house is authored with its own numbers."""
    body = geom.prism("SRC_%s_BODY" % tag, S, extrude_axis="y",
                      profile=[(x_face, GROUND), (x_face + 3.4, GROUND),
                               (x_face + 3.4, eaves), (x_face + lean, eaves)],
                      start=y0, end=y1)
    mats.apply(body, mat)
    roof = geom.prism("SRC_%s_ROOF" % tag, S, extrude_axis="y",
                      profile=[(x_face + lean - 0.34, eaves - 0.10),
                               (x_face + 3.5, eaves - 0.10),
                               (x_face + 3.5, eaves + 0.16),
                               (x_face + 1.7 + lean * 0.5, ridge),
                               (x_face + lean - 0.34, eaves + 0.16)],
                      start=y0 - 0.22, end=y1 + 0.22)
    mats.apply(roof, "roof_lead")
    eave = geom.slab("SRC_%s_EAVE" % tag, S,
                     x0=x_face + lean - 0.40, x1=x_face + lean - 0.12,
                     y0=y0 - 0.24, y1=y1 + 0.24,
                     z0=eaves - 0.24, z1=eaves + 0.06)
    geom.bevel(eave, 0.04, 2)
    mats.apply(eave, "timber_dark")

    for (wy, wz, wh) in window_rows:
        ww = wh / 4.0                      # the recurring 1:4 slot proportion
        rec = geom.slab("SRC_%s_W%d" % (tag, int(wy * 10 + wz * 7)), S,
                        x0=x_face + lean + 0.14, x1=x_face + lean + 0.58,
                        y0=wy - ww * 0.5, y1=wy + ww * 0.5, z0=wz, z1=wz + wh)
        mats.apply(rec, "glass_leaded")
        sur = geom.slab("SRC_%s_S%d" % (tag, int(wy * 10 + wz * 7)), S,
                        x0=x_face + lean - 0.10, x1=x_face + lean + 0.12,
                        y0=wy - ww * 0.5 - 0.15, y1=wy + ww * 0.5 + 0.15,
                        z0=wz - 0.16, z1=wz + wh + 0.16)
        geom.bevel(sur, 0.035, 2)
        mats.apply(sur, "plaster_bone")
        sill = geom.slab("SRC_%s_L%d" % (tag, int(wy * 10 + wz * 7)), S,
                         x0=x_face + lean - 0.20, x1=x_face + lean + 0.10,
                         y0=wy - ww * 0.5 - 0.22, y1=wy + ww * 0.5 + 0.22,
                         z0=wz - 0.20, z1=wz - 0.12)
        geom.bevel(sill, 0.025, 2)
        mats.apply(sill, "civic_ashlar")
    return body


def build(out_dir, attempt_id="02"):
    cr_scene.reset()
    stage = cr_scene.make_stage()
    vocab.build_vocabulary()
    S = stage.source
    staging.use(stage, "street_setts", "plaster_bone", "plaster_verdigris",
                "limewash_pale", "roof_lead", "timber_dark", "paint_madder",
                "metal_verdigris", "glass_leaded", "civic_ashlar",
                "boards_dark", "cloth_awning")

    street = geom.ground("SRC_STREET", S, x0=11.0, x1=STREET_BACK + 0.1,
                         y0=-22.0, y1=32.0, z=GROUND, cuts=52)
    mats.apply(street, "street_setts")
    staging.relief(stage, street, "street_setts", strength=0.06)

    # ---- screen-left: the low broad shed. Quiet on purpose. --------------
    shed = geom.prism("SRC_SHED", S, extrude_axis="y",
                      profile=[(STREET_BACK, GROUND), (STREET_BACK + 7.0, GROUND),
                               (STREET_BACK + 7.0, -0.85), (STREET_BACK, -0.45)],
                      start=-22.0, end=2.10)
    mats.apply(shed, "limewash_pale")
    staging.relief(stage, shed, "limewash_pale", strength=0.0)
    shed_roof = geom.prism("SRC_SHED_ROOF", S, extrude_axis="y",
                           profile=[(STREET_BACK - 0.55, -0.60),
                                    (STREET_BACK + 7.2, -1.00),
                                    (STREET_BACK + 7.2, -0.74),
                                    (STREET_BACK - 0.55, -0.30)],
                           start=-22.4, end=2.34)
    mats.apply(shed_roof, "roof_lead")
    # exactly two openings in the whole shed, both the 1:4 slot
    for oy, oz, oh in ((-6.4, GROUND + 0.55, 2.30), (-1.15, GROUND + 0.55, 2.30)):
        ow = oh / 4.0
        rec = geom.slab("SRC_SHED_O%d" % int(oy * 10), S,
                        x0=STREET_BACK + 0.10, x1=STREET_BACK + 0.70,
                        y0=oy - ow * 0.5, y1=oy + ow * 0.5, z0=oz, z1=oz + oh)
        mats.apply(rec, "grime_moss")
        jam = geom.slab("SRC_SHED_J%d" % int(oy * 10), S,
                        x0=STREET_BACK - 0.12, x1=STREET_BACK + 0.08,
                        y0=oy - ow * 0.5 - 0.17, y1=oy + ow * 0.5 + 0.17,
                        z0=oz - 0.18, z1=oz + oh + 0.20)
        geom.bevel(jam, 0.04, 2)
        mats.apply(jam, "civic_ashlar")
    plinth = geom.slab("SRC_SHED_PLINTH", S, x0=STREET_BACK - 0.22,
                       x1=STREET_BACK + 0.06, y0=-22.0, y1=2.20,
                       z0=GROUND, z1=GROUND + 0.72)
    geom.bevel(plinth, 0.05, 2)
    mats.apply(plinth, "civic_ashlar")

    # ---- the authored gap of sky, y in 2.2 .. 6.4, with a distant tower ---
    tower = geom.prism("SRC_TOWER", S, extrude_axis="y",
                       profile=[(47.0, GROUND), (52.0, GROUND),
                                (52.0, 4.30), (49.5, 6.40), (47.0, 4.30)],
                       start=2.90, end=6.00)
    mats.apply(tower, "plaster_verdigris")
    tower_cap = geom.prism("SRC_TOWER_CAP", S, extrude_axis="y",
                           profile=[(46.6, 4.10), (52.4, 4.10), (52.4, 4.50),
                                    (46.6, 4.50)],
                           start=2.70, end=6.20)
    mats.apply(tower_cap, "roof_lead")

    # ---- screen-right: three tall narrow houses, each authored alone -----
    _house(S, stage, "HA", y0=6.45, y1=10.30, x_face=STREET_BACK,
           eaves=2.55, ridge=3.95, lean=-0.42, mat="plaster_bone",
           window_rows=[(7.30, GROUND + 3.05, 1.55), (9.55, GROUND + 3.05, 1.55),
                        (8.40, GROUND + 5.35, 1.20)])
    _house(S, stage, "HB", y0=10.55, y1=13.60, x_face=STREET_BACK + 0.55,
           eaves=3.35, ridge=4.60, lean=0.30, mat="plaster_verdigris",
           window_rows=[(11.35, GROUND + 2.85, 1.80), (12.85, GROUND + 2.85, 1.80),
                        (12.10, GROUND + 5.55, 1.35)])
    _house(S, stage, "HC", y0=13.85, y1=18.90, x_face=STREET_BACK - 0.35,
           eaves=1.95, ridge=3.10, lean=-0.18, mat="limewash_pale",
           window_rows=[(14.75, GROUND + 3.15, 1.45), (17.90, GROUND + 3.15, 1.45)])

    # the raised door: three steps, madder, screen-centre-right
    for i in range(3):
        st = geom.slab("SRC_STEP%d" % i, S,
                       x0=STREET_BACK - 1.45 + i * 0.40, x1=STREET_BACK,
                       y0=DOOR_Y - 1.50, y1=DOOR_Y + 1.50,
                       z0=GROUND - 0.002, z1=GROUND + 0.19 * (i + 1))
        geom.bevel(st, 0.035, 2)
        mats.apply(st, "civic_ashlar")
    dz = GROUND + 0.57
    door_rec = geom.slab("SRC_DOOR_REC", S,
                         x0=STREET_BACK - 0.36, x1=STREET_BACK + 0.55,
                         y0=DOOR_Y - 0.62, y1=DOOR_Y + 0.62, z0=dz, z1=dz + 2.30)
    mats.apply(door_rec, "grime_moss")
    leaf = geom.slab("SRC_DOOR", S, x0=STREET_BACK - 0.14, x1=STREET_BACK - 0.05,
                     y0=DOOR_Y - 0.56, y1=DOOR_Y + 0.56, z0=dz, z1=dz + 2.16)
    geom.bevel(leaf, 0.03, 2)
    mats.apply(leaf, "paint_madder")
    hoodm = geom.prism("SRC_DOORHOOD", S, extrude_axis="y",
                       profile=[(STREET_BACK - 0.50, dz + 2.36),
                                (STREET_BACK - 1.62, dz + 2.10),
                                (STREET_BACK - 1.62, dz + 2.28),
                                (STREET_BACK - 0.50, dz + 2.60)],
                       start=DOOR_Y - 1.05, end=DOOR_Y + 1.05)
    mats.apply(hoodm, "roof_lead")

    # a single awning, the only cloth in the frame
    awn = geom.prism("SRC_AWNING", S, extrude_axis="y",
                     profile=[(STREET_BACK - 0.20, GROUND + 2.55),
                              (STREET_BACK - 2.30, GROUND + 2.05),
                              (STREET_BACK - 2.30, GROUND + 2.13),
                              (STREET_BACK - 0.20, GROUND + 2.63)],
                     start=11.10, end=13.30)
    mats.apply(awn, "cloth_awning")

    # ---- foreground: one lamp standard, near y = 5.5 where the window is --
    lamp_y, lamp_x = 4.35, 15.10
    base = geom.slab("SRC_LAMP_BASE", S, x0=lamp_x - 0.24, x1=lamp_x + 0.24,
                     y0=lamp_y - 0.24, y1=lamp_y + 0.24,
                     z0=GROUND, z1=GROUND + 0.44)
    geom.bevel(base, 0.05, 2)
    mats.apply(base, "civic_ashlar")
    col = geom.cylinder("SRC_LAMP_COL", S,
                        center=(lamp_x, lamp_y, GROUND + 0.40),
                        radius=0.075, height=3.55, segments=10, axis="z")
    mats.apply(col, "metal_verdigris")
    lant = geom.slab("SRC_LAMP_LANT", S, x0=lamp_x - 0.19, x1=lamp_x + 0.19,
                     y0=lamp_y - 0.19, y1=lamp_y + 0.19,
                     z0=GROUND + 3.95, z1=GROUND + 4.42)
    geom.bevel(lant, 0.04, 2)
    mats.apply(lant, "metal_verdigris")

    # a low stack of boards leaning where the street meets the shed plinth
    stack = geom.prism("SRC_STACK", S, extrude_axis="y",
                       profile=[(24.60, GROUND), (26.05, GROUND),
                                (25.85, GROUND + 1.30), (24.75, GROUND + 1.18)],
                       start=0.20, end=2.05)
    mats.apply(stack, "boards_dark")

    # ---- runtime -----------------------------------------------------------
    staging.runtime_plane(stage, "RUN_STREET", x0=11.0, x1=STREET_BACK,
                          y0=-22.0, y1=32.0, z=GROUND)
    staging.runtime_box(stage, "RUN_SHED", x0=STREET_BACK, x1=STREET_BACK + 7.0,
                        y0=-22.0, y1=2.20, z0=GROUND, z1=-0.45)
    for tag, y0, y1, top in (("HA", 6.45, 10.30, 3.95), ("HB", 10.55, 13.60, 4.60),
                             ("HC", 13.85, 18.90, 3.10)):
        staging.runtime_box(stage, "RUN_%s" % tag, x0=STREET_BACK - 0.45,
                            x1=STREET_BACK + 3.5, y0=y0, y1=y1,
                            z0=GROUND, z1=top)
    staging.runtime_box(stage, "RUN_TOWER", x0=47.0, x1=52.0, y0=2.90, y1=6.00,
                        z0=GROUND, z1=6.40)
    staging.runtime_box(stage, "RUN_LAMP", x0=lamp_x - 0.24, x1=lamp_x + 0.24,
                        y0=lamp_y - 0.24, y1=lamp_y + 0.24,
                        z0=GROUND, z1=GROUND + 4.42)
    staging.runtime_box(stage, "RUN_STEPS", x0=STREET_BACK - 1.45, x1=STREET_BACK,
                        y0=DOOR_Y - 1.50, y1=DOOR_Y + 1.50,
                        z0=GROUND, z1=GROUND + 0.57)

    staging.collider(stage, "COL_BACK", x0=STREET_BACK - 0.5, x1=STREET_BACK + 0.5,
                     y0=-22.0, y1=32.0, z0=GROUND, z1=GROUND + 3.0)
    staging.collider(stage, "COL_LAMP", x0=lamp_x - 0.3, x1=lamp_x + 0.3,
                     y0=lamp_y - 0.3, y1=lamp_y + 0.3, z0=GROUND, z1=GROUND + 1.2)
    staging.collider(stage, "COL_FLOOR", x0=13.0, x1=STREET_BACK,
                     y0=-22.0, y1=32.0, z0=GROUND - 0.2, z1=GROUND)

    staging.walk_bounds(stage, y_min=-9.0, y_max=20.0, x=21.40, z=GROUND)
    staging.doorway(stage, "door_shed", (STREET_BACK - 1.5, DOOR_Y, GROUND))
    staging.cast(stage,
                 hero={"at": (21.40, 6.05, GROUND), "frame": 0},
                 npcs=[{"at": (25.80, 11.90, GROUND), "frame": 2},
                       {"at": (23.10, 1.35, GROUND), "frame": 5},
                       {"at": (26.60, 16.40, GROUND), "frame": 3}])

    cr_scene.sky(stage, top=(0.155, 0.215, 0.335), horizon=(0.480, 0.455, 0.395),
                 strength=1.05)
    cr_scene.sun(stage, energy=4.2, color=(1.0, 0.90, 0.75),
                 azimuth=-46.0, elevation=33.0, size=0.045)
    cr_scene.point(stage, location=(STREET_BACK - 1.1, DOOR_Y, GROUND + 1.6),
                   energy=16.0, color=(1.0, 0.68, 0.36), radius=0.32)

    return staging.finish(stage, out_dir, attempt_id, concept=CONCEPT,
                          samples=110)
