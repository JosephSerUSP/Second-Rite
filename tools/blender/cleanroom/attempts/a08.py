"""Attempt 08 -- THE TALLY CRANE.  (convergence, authored from an empty scene)

Findings applied: 4 (one bold, specific, slightly strange architectural idea),
2 (objects that imply use), 3 (a foreground that is DOING something), 5 (NPCs
in a situation), 6 (light the door).

Nothing from 01-06 is imported or re-derived.

The idea: a goods lane whose entire silhouette is decided by one machine. A
timber treadwheel crane is built INTO the gable of a stone counting house and
leans its jib out over the street. That single object gives the frame an
asymmetric, immediately recognisable outline that could not be dropped into
another game, and it explains everything else in the scene: the tally board,
the weighbeam, the stacked sacks, the rope runs, the bollards worn round.

The foreground occluder is a pallet hanging on the crane rope, halfway down. It
crosses the near plane and it is unambiguously mid-task, which is the answer to
"a slab added to satisfy occlusion".
"""
from __future__ import annotations

import math

from .. import geom, mats, scene as cr_scene, staging, vocab

CONCEPT = "goods lane under a working treadwheel crane; a load in mid-air"

GROUND = -4.30
HOUSE = 26.80
JIB_TIP = 15.20
DOOR_Y = 12.40
LOAD_Y = 4.10


def build(out_dir, attempt_id="08"):
    cr_scene.reset()
    stage = cr_scene.make_stage()
    vocab.build_vocabulary()
    S = stage.source
    staging.use(stage, "civic_ashlar", "stone_fine", "stone_mossy",
                "street_setts", "timber_dark", "boards_dark", "paint_madder",
                "metal_verdigris", "cloth_awning", "glass_leaded",
                "grime_moss", "roof_lead", "plaster_bone")

    lane = geom.ground("SRC_LANE", S, x0=10.5, x1=HOUSE + 0.1,
                       y0=-20.0, y1=30.0, z=GROUND, cuts=46)
    mats.apply(lane, "street_setts")
    staging.relief(stage, lane, "street_setts", strength=0.065)

    # ---- the counting house ------------------------------------------------
    holes = [{"y0": DOOR_Y - 0.72, "y1": DOOR_Y + 0.72,
              "z0": GROUND, "z1": GROUND + 2.50}]
    for wy, wz, wh in ((7.40, GROUND + 1.60, 1.70), (9.80, GROUND + 1.60, 1.70),
                       (15.90, GROUND + 1.70, 1.85), (8.60, GROUND + 4.35, 1.45),
                       (14.60, GROUND + 4.35, 1.45)):
        holes.append({"y0": wy - wh / 8.0, "y1": wy + wh / 8.0,
                      "z0": wz, "z1": wz + wh})
    # the loading hatch the crane actually serves: a big square opening high up
    holes.append({"y0": 2.55, "y1": 5.65, "z0": GROUND + 6.95,
                  "z1": GROUND + 8.60})
    for piece in geom.slotted_panel("SRC_HOUSE", S, x=HOUSE, y0=-20.0, y1=30.0,
                                    z0=GROUND, z1=GROUND + 9.20, holes=holes,
                                    cuts_per_m=10.0):
        mats.apply(piece, "stone_fine")
        staging.relief(stage, piece, "stone_fine", strength=0.13)
        cr_scene.shade_smooth(piece)
    for i, h in enumerate(holes):
        deep = 2.60 if i == len(holes) - 1 else 1.05
        back = geom.slab("SRC_REV%d" % i, S, x0=HOUSE + 0.10, x1=HOUSE + deep,
                         y0=h["y0"] - 0.26, y1=h["y1"] + 0.26,
                         z0=h["z0"] - 0.26, z1=h["z1"] + 0.26)
        mats.apply(back, "grime_moss" if i == len(holes) - 1
                   else ("timber_dark" if i == 0 else "glass_leaded"))

    base = geom.slab("SRC_HOUSE_BASE", S, x0=HOUSE - 0.30, x1=HOUSE + 0.06,
                     y0=-20.0, y1=30.0, z0=GROUND, z1=GROUND + 1.05)
    geom.bevel(base, 0.06, 2)
    mats.apply(base, "civic_ashlar")
    band = geom.slab("SRC_HOUSE_BAND", S, x0=HOUSE - 0.24, x1=HOUSE + 0.06,
                     y0=-20.0, y1=30.0, z0=GROUND + 4.05, z1=GROUND + 4.32)
    geom.bevel(band, 0.045, 2)
    mats.apply(band, "civic_ashlar")

    # the gable the crane is built into: a raised, stepped parapet
    for i, (gy0, gy1, gz) in enumerate(((1.30, 6.90, 9.20), (0.55, 1.30, 8.30),
                                        (6.90, 7.65, 8.30))):
        gab = geom.slab("SRC_GABLE%d" % i, S, x0=HOUSE - 0.36, x1=HOUSE + 0.9,
                        y0=gy0, y1=gy1, z0=GROUND + 7.30, z1=GROUND + gz)
        geom.bevel(gab, 0.06, 2)
        mats.apply(gab, "civic_ashlar")

    # ---- THE CRANE ----------------------------------------------------------
    # The whole machine is brought DOWN into frame on purpose. Raked up into
    # the gable it left the frame at the top and read as a stray pole; the
    # silhouette only works if the wheel, the jib and the load are all visible
    # in the same 426x240 image.
    WHEEL_X, WHEEL_Z = 25.10, GROUND + 5.05
    # the timber cage that carries the wheel, cantilevered out of the wall
    for i, (cz0, cz1) in enumerate(((GROUND + 3.10, GROUND + 3.34),
                                    (GROUND + 6.76, GROUND + 7.00))):
        rail = geom.slab("SRC_CAGE%d" % i, S, x0=WHEEL_X - 1.95, x1=HOUSE,
                         y0=2.35, y1=5.85, z0=cz0, z1=cz1)
        geom.bevel(rail, 0.035, 2)
        mats.apply(rail, "timber_dark")
    for side, sy in ((-1, 2.45), (1, 5.75)):
        upr = geom.slab("SRC_CAGEUP%d" % side, S,
                        x0=WHEEL_X - 1.95, x1=WHEEL_X - 1.71,
                        y0=sy - 0.12, y1=sy + 0.12,
                        z0=GROUND + 3.10, z1=GROUND + 7.00)
        mats.apply(upr, "timber_dark")
        dia = geom.prism("SRC_CAGEDIA%d" % side, S, extrude_axis="y",
                         profile=[(WHEEL_X - 1.85, GROUND + 3.30),
                                  (HOUSE - 0.10, GROUND + 6.60),
                                  (HOUSE - 0.10, GROUND + 6.82),
                                  (WHEEL_X - 1.85, GROUND + 3.52)],
                         start=sy - 0.08, end=sy + 0.08)
        mats.apply(dia, "timber_dark")

    # the treadwheel, out in the open where it can actually be read
    for k, r in enumerate((1.58, 1.22)):
        for i in range(22):
            a0 = 2 * math.pi * i / 22
            seg = geom.slab("SRC_WHEEL%d_%d" % (k, i), S,
                            x0=WHEEL_X - 0.90 + k * 1.55,
                            x1=WHEEL_X - 0.72 + k * 1.55,
                            y0=4.10 + r * math.cos(a0) - 0.15,
                            y1=4.10 + r * math.cos(a0) + 0.15,
                            z0=WHEEL_Z + r * math.sin(a0) - 0.095,
                            z1=WHEEL_Z + r * math.sin(a0) + 0.095)
            mats.apply(seg, "timber_dark")
    for i in range(8):                       # spokes
        a0 = 2 * math.pi * i / 8
        sp = geom.slab("SRC_SPOKE%d" % i, S,
                       x0=WHEEL_X - 0.86, x1=WHEEL_X - 0.76,
                       y0=4.10 + 0.79 * math.cos(a0) - 0.055,
                       y1=4.10 + 0.79 * math.cos(a0) + 0.055,
                       z0=WHEEL_Z + 0.79 * math.sin(a0) - 0.79,
                       z1=WHEEL_Z + 0.79 * math.sin(a0) + 0.79)
        mats.apply(sp, "timber_dark")
    axle = geom.cylinder("SRC_AXLE", S,
                         center=(WHEEL_X - 0.81, 2.45, WHEEL_Z),
                         radius=0.17, height=3.30, segments=12, axis="y")
    mats.apply(axle, "timber_dark")
    drum = geom.cylinder("SRC_DRUM", S,
                         center=(WHEEL_X - 0.81, 5.95, WHEEL_Z),
                         radius=0.42, height=0.66, segments=14, axis="y")
    mats.apply(drum, "metal_verdigris")

    # the jib: a strong diagonal running down and forward, wholly in frame
    for side, sy in ((-1, 3.70), (1, 4.50)):
        jib = geom.prism("SRC_JIB%d" % side, S, extrude_axis="y",
                         profile=[(HOUSE - 0.30, GROUND + 5.70),
                                  (JIB_TIP, GROUND + 3.55),
                                  (JIB_TIP + 0.36, GROUND + 3.84),
                                  (HOUSE - 0.30, GROUND + 6.08)],
                         start=sy - 0.16, end=sy + 0.16)
        mats.apply(jib, "timber_dark")
    stay = geom.prism("SRC_STAY", S, extrude_axis="y",
                      profile=[(JIB_TIP + 0.30, GROUND + 3.80),
                               (HOUSE - 0.20, GROUND + 6.92),
                               (HOUSE - 0.20, GROUND + 7.06),
                               (JIB_TIP + 0.30, GROUND + 3.96)],
                      start=4.02, end=4.20)
    mats.apply(stay, "timber_dark")
    tip_beam = geom.slab("SRC_TIPBEAM", S, x0=JIB_TIP - 0.06, x1=JIB_TIP + 0.40,
                         y0=3.40, y1=4.80, z0=GROUND + 3.52, z1=GROUND + 3.90)
    geom.bevel(tip_beam, 0.04, 2)
    mats.apply(tip_beam, "timber_dark")
    sheave = geom.cylinder("SRC_SHEAVE", S,
                           center=(JIB_TIP + 0.17, LOAD_Y, GROUND + 3.44),
                           radius=0.28, height=0.20, segments=16, axis="y")
    mats.apply(sheave, "metal_verdigris")
    for i in range(4):
        t = (i + 1) / 5.0
        sx = HOUSE - 0.30 + (JIB_TIP - HOUSE + 0.30) * t
        sz = GROUND + 5.70 + (3.55 - 5.70) * t
        strap = geom.slab("SRC_STRAP%d" % i, S, x0=sx - 0.06, x1=sx + 0.42,
                          y0=3.45, y1=4.75, z0=sz + 0.10, z1=sz + 0.20)
        mats.apply(strap, "metal_verdigris")

    # ---- the load in mid-air: the foreground, and it is mid-task ----------
    for oy in (LOAD_Y - 0.34, LOAD_Y + 0.34):
        rope = geom.slab("SRC_ROPE%d" % int(oy * 10), S,
                         x0=JIB_TIP + 0.13, x1=JIB_TIP + 0.21,
                         y0=oy - 0.035, y1=oy + 0.035,
                         z0=GROUND + 1.95, z1=GROUND + 3.46)
        mats.apply(rope, "timber_dark")
    hook = geom.slab("SRC_HOOKBLOCK", S, x0=JIB_TIP + 0.03, x1=JIB_TIP + 0.31,
                     y0=LOAD_Y - 0.44, y1=LOAD_Y + 0.44,
                     z0=GROUND + 1.86, z1=GROUND + 2.12)
    geom.bevel(hook, 0.03, 2)
    mats.apply(hook, "metal_verdigris")
    pallet = geom.slab("SRC_PALLET", S, x0=JIB_TIP - 0.62, x1=JIB_TIP + 0.96,
                       y0=LOAD_Y - 1.15, y1=LOAD_Y + 1.15,
                       z0=GROUND + 1.60, z1=GROUND + 1.80)
    geom.bevel(pallet, 0.03, 2)
    mats.apply(pallet, "boards_dark")
    for i, (sy, sx0, h) in enumerate(((LOAD_Y - 0.70, -0.48, 0.62),
                                      (LOAD_Y + 0.02, -0.30, 0.74),
                                      (LOAD_Y + 0.68, -0.52, 0.58))):
        sack = geom.prism("SRC_SACK%d" % i, S, extrude_axis="y",
                          profile=[(JIB_TIP + sx0, GROUND + 1.80),
                                   (JIB_TIP + sx0 + 1.12, GROUND + 1.80),
                                   (JIB_TIP + sx0 + 0.92, GROUND + 1.80 + h),
                                   (JIB_TIP + sx0 + 0.18, GROUND + 1.80 + h * 0.9)],
                          start=sy - 0.30, end=sy + 0.30)
        mats.apply(sack, "cloth_awning")
    guide = geom.slab("SRC_GUIDEROPE", S, x0=JIB_TIP + 0.60, x1=JIB_TIP + 0.68,
                      y0=LOAD_Y - 1.10, y1=LOAD_Y - 1.02,
                      z0=GROUND + 0.05, z1=GROUND + 1.62)
    mats.apply(guide, "timber_dark")

    # ---- the yard's working furniture ---------------------------------------
    tally = geom.slab("SRC_TALLY", S, x0=HOUSE - 0.16, x1=HOUSE - 0.05,
                      y0=DOOR_Y + 1.15, y1=DOOR_Y + 2.75,
                      z0=GROUND + 1.35, z1=GROUND + 2.60)
    geom.bevel(tally, 0.025, 2)
    mats.apply(tally, "boards_dark")
    tframe = geom.slab("SRC_TALLYFRAME", S, x0=HOUSE - 0.22, x1=HOUSE - 0.14,
                       y0=DOOR_Y + 1.05, y1=DOOR_Y + 2.85,
                       z0=GROUND + 1.25, z1=GROUND + 2.70)
    geom.bevel(tframe, 0.02, 2)
    mats.apply(tframe, "paint_madder")

    post = geom.slab("SRC_BEAMPOST", S, x0=19.30, x1=19.62,
                     y0=17.55, y1=17.87, z0=GROUND, z1=GROUND + 2.55)
    geom.bevel(post, 0.03, 2)
    mats.apply(post, "timber_dark")
    beam = geom.slab("SRC_WEIGHBEAM", S, x0=19.10, x1=19.82,
                     y0=15.90, y1=19.60, z0=GROUND + 2.48, z1=GROUND + 2.62)
    geom.bevel(beam, 0.025, 2)
    mats.apply(beam, "timber_dark")
    for i, py in enumerate((16.20, 19.30)):
        ch = geom.slab("SRC_CHAIN%d" % i, S, x0=19.42, x1=19.50,
                       y0=py - 0.035, y1=py + 0.035,
                       z0=GROUND + 1.62, z1=GROUND + 2.48)
        mats.apply(ch, "metal_verdigris")
        pan = geom.cylinder("SRC_PAN%d" % i, S,
                            center=(19.46, py, GROUND + 1.48),
                            radius=0.34, height=0.13, segments=12, axis="z")
        mats.apply(pan, "metal_verdigris")

    for i, (by, r) in enumerate(((-3.20, 0.30), (0.90, 0.28), (8.90, 0.32),
                                 (20.40, 0.29))):
        bol = geom.cylinder("SRC_BOLLARD%d" % i, S,
                            center=(21.90, by, GROUND), radius=r, height=0.72,
                            segments=12, axis="z")
        geom.bevel(bol, 0.09, 3)
        mats.apply(bol, "civic_ashlar")

    for i, (sy, sh) in enumerate(((-6.40, 0.58), (-5.75, 0.66), (-6.05, 1.22),
                                  (22.90, 0.62), (23.55, 0.55))):
        st = geom.prism("SRC_STACK%d" % i, S, extrude_axis="y",
                        profile=[(24.30, GROUND + (0.62 if sh > 1 else 0.0)),
                                 (25.55, GROUND + (0.62 if sh > 1 else 0.0)),
                                 (25.38, GROUND + sh + (0.62 if sh > 1 else 0.0)),
                                 (24.46, GROUND + sh + (0.62 if sh > 1 else 0.0) - 0.08)],
                        start=sy - 0.32, end=sy + 0.32)
        mats.apply(st, "cloth_awning")
    tarp = geom.hanging_sheet("SRC_TARP", S, x=24.10, y0=-6.90, y1=-5.30,
                              z_top=GROUND + 1.32, drop=1.05,
                              cuts_y=12, cuts_z=12, sway=0.07)
    mats.apply(tarp, "boards_dark")

    # ---- the door, lit -------------------------------------------------------
    leaf = geom.slab("SRC_DOOR", S, x0=HOUSE - 0.06, x1=HOUSE + 0.03,
                     y0=DOOR_Y + 0.10, y1=DOOR_Y + 1.38,
                     z0=GROUND + 0.06, z1=GROUND + 2.44)
    geom.bevel(leaf, 0.028, 2)
    mats.apply(leaf, "paint_madder")
    dfr = geom.slab("SRC_DFRAME", S, x0=HOUSE - 0.22, x1=HOUSE + 0.05,
                    y0=DOOR_Y - 0.96, y1=DOOR_Y + 0.96,
                    z0=GROUND, z1=GROUND + 2.78)
    geom.bevel(dfr, 0.045, 2)
    mats.apply(dfr, "civic_ashlar")
    hoodm = geom.prism("SRC_DOORHOOD", S, extrude_axis="y",
                       profile=[(HOUSE - 0.12, GROUND + 2.86),
                                (HOUSE - 1.68, GROUND + 2.58),
                                (HOUSE - 1.68, GROUND + 2.74),
                                (HOUSE - 0.12, GROUND + 3.06)],
                       start=DOOR_Y - 1.20, end=DOOR_Y + 1.20)
    mats.apply(hoodm, "roof_lead")
    lant = geom.slab("SRC_LANTERN", S, x0=HOUSE - 0.72, x1=HOUSE - 0.46,
                     y0=DOOR_Y - 1.34, y1=DOOR_Y - 1.08,
                     z0=GROUND + 2.16, z1=GROUND + 2.54)
    geom.bevel(lant, 0.03, 2)
    mats.apply(lant, vocab.glazing_lit("glass_lantern",
                                       warmth=mats.hexc("FFB05A"),
                                       strength=9.0).id)
    dstep = geom.slab("SRC_DSTEP", S, x0=HOUSE - 0.82, x1=HOUSE,
                      y0=DOOR_Y - 1.05, y1=DOOR_Y + 1.05,
                      z0=GROUND - 0.002, z1=GROUND + 0.15)
    geom.bevel(dstep, 0.03, 2)
    mats.apply(dstep, "civic_ashlar")

    # ---- runtime -------------------------------------------------------------
    staging.runtime_plane(stage, "RUN_LANE", x0=10.5, x1=HOUSE,
                          y0=-20.0, y1=30.0, z=GROUND)
    staging.runtime_box(stage, "RUN_HOUSE", x0=HOUSE, x1=HOUSE + 1.4,
                        y0=-20.0, y1=30.0, z0=GROUND, z1=GROUND + 9.20)
    staging.runtime_box(stage, "RUN_JIB", x0=JIB_TIP, x1=HOUSE,
                        y0=3.40, y1=4.80, z0=GROUND + 3.44, z1=GROUND + 6.10)
    staging.runtime_box(stage, "RUN_WHEEL", x0=23.15, x1=HOUSE,
                        y0=2.35, y1=5.85, z0=GROUND + 3.10, z1=GROUND + 7.00)
    staging.runtime_box(stage, "RUN_LOAD", x0=JIB_TIP - 0.62, x1=JIB_TIP + 0.96,
                        y0=LOAD_Y - 1.15, y1=LOAD_Y + 1.15,
                        z0=GROUND + 1.60, z1=GROUND + 2.60)
    staging.runtime_box(stage, "RUN_BEAM", x0=19.10, x1=19.82,
                        y0=15.90, y1=19.60, z0=GROUND, z1=GROUND + 2.62)
    staging.runtime_box(stage, "RUN_STACKS", x0=24.30, x1=25.55,
                        y0=-6.90, y1=-5.30, z0=GROUND, z1=GROUND + 1.90)
    staging.runtime_box(stage, "RUN_DOOR", x0=HOUSE - 1.70, x1=HOUSE + 0.10,
                        y0=DOOR_Y - 1.20, y1=DOOR_Y + 1.20,
                        z0=GROUND, z1=GROUND + 3.06)

    staging.collider(stage, "COL_HOUSE", x0=HOUSE - 0.4, x1=HOUSE + 0.4,
                     y0=-20.0, y1=30.0, z0=GROUND, z1=GROUND + 3.0)
    staging.collider(stage, "COL_BEAM", x0=19.10, x1=19.82,
                     y0=15.90, y1=19.60, z0=GROUND, z1=GROUND + 1.6)
    staging.collider(stage, "COL_STACKS", x0=24.30, x1=25.55,
                     y0=-6.90, y1=-5.30, z0=GROUND, z1=GROUND + 1.6)
    staging.collider(stage, "COL_FLOOR", x0=14.0, x1=HOUSE,
                     y0=-20.0, y1=30.0, z0=GROUND - 0.2, z1=GROUND)

    staging.walk_bounds(stage, y_min=-10.0, y_max=24.0, x=21.30, z=GROUND)
    staging.doorway(stage, "door_counting_house", (HOUSE - 1.0, DOOR_Y, GROUND))
    # a situation: two hauling on the guide rope under the load, one at the
    # tally board by the lit door
    staging.cast(stage,
                 hero={"at": (21.30, 6.55, GROUND), "frame": 0},
                 npcs=[{"at": (18.40, 2.35, GROUND), "frame": 4},
                       {"at": (19.10, 3.30, GROUND), "frame": 5},
                       {"at": (24.60, DOOR_Y + 2.05, GROUND), "frame": 2}])

    cr_scene.sky(stage, top=(0.100, 0.140, 0.230), horizon=(0.300, 0.290, 0.255),
                 strength=1.0)
    cr_scene.sun(stage, energy=5.0, color=(1.0, 0.88, 0.70),
                 azimuth=-63.0, elevation=38.0, size=0.034)
    cr_scene.sun(stage, energy=0.42, color=(0.50, 0.62, 0.86),
                 azimuth=115.0, elevation=45.0, size=0.7, name="TH_SKYFILL")
    cr_scene.area(stage, location=(HOUSE + 0.5, DOOR_Y + 0.7, GROUND + 1.2),
                  energy=75.0, color=(1.0, 0.63, 0.27), size=1.3,
                  rotation=(90, 0, -90), name="TH_DOORGLOW")
    cr_scene.point(stage, location=(HOUSE - 0.60, DOOR_Y - 1.22, GROUND + 2.36),
                   energy=13.0, color=(1.0, 0.60, 0.24), radius=0.13)
    cr_scene.point(stage, location=(23.60, 4.10, GROUND + 5.05),
                   energy=18.0, color=(1.0, 0.74, 0.46), radius=0.6)

    return staging.finish(stage, out_dir, attempt_id, concept=CONCEPT,
                          samples=128)
