"""Attempt 06 -- THE STEPPED LANE.

Spatial idea: a level change along the walking axis, and age stratification.

The lane is cut into a slope, so the route itself rises as the player walks
right: a lower level on screen-left, a short flight in the middle, an upper
terrace on screen-right. That is a level change with no platforming grammar --
the player walks up it exactly as they walk along it.

The level change is also the age boundary. Everything at the lower level is
old, heavy and mineral: rough mossy retaining stone, a blocked arch, a
worn-out plinth. Everything on the upper terrace is later, lighter and
domestic: bone limewash, timber, painted shutters. The town visibly grew
upward and newer.

Because the ground moves, the foreground device moves with it: a stone
balustrade guards only the upper terrace, so the near plane appears halfway
through the frame instead of running across all of it.
"""
from __future__ import annotations

from .. import geom, mats, scene as cr_scene, staging, vocab

CONCEPT = "lane stepping up along the route; old stone below, new town above"

LOW = -4.85
HIGH = -3.35
STEP_Y0, STEP_Y1 = 4.30, 8.20
NSTEPS = 6
BACK = 26.60
BAL_X = 16.30
DOOR_Y = 14.60


def ground_at(y):
    if y <= STEP_Y0:
        return LOW
    if y >= STEP_Y1:
        return HIGH
    t = (y - STEP_Y0) / (STEP_Y1 - STEP_Y0)
    return LOW + (HIGH - LOW) * t


def build(out_dir, attempt_id="06"):
    cr_scene.reset()
    stage = cr_scene.make_stage()
    vocab.build_vocabulary()
    S = stage.source
    staging.use(stage, "stone_mossy", "civic_ashlar", "street_setts",
                "plaster_bone", "limewash_pale", "timber_dark", "paint_madder",
                "metal_verdigris", "grime_moss", "roof_lead", "boards_dark",
                "glass_leaded", "cloth_awning")

    # ---- the two floors and the flight between them -----------------------
    lower = geom.ground("SRC_LOWER", S, x0=11.0, x1=BACK + 0.1,
                        y0=-20.0, y1=STEP_Y0 + 0.02, z=LOW, cuts=34)
    mats.apply(lower, "street_setts")
    staging.relief(stage, lower, "street_setts", strength=0.07)
    upper = geom.ground("SRC_UPPER", S, x0=11.0, x1=BACK + 0.1,
                        y0=STEP_Y1 - 0.02, y1=30.0, z=HIGH, cuts=34)
    mats.apply(upper, "street_setts")
    staging.relief(stage, upper, "street_setts", strength=0.055)

    rise = (HIGH - LOW) / NSTEPS
    run = (STEP_Y1 - STEP_Y0) / NSTEPS
    for i in range(NSTEPS):
        tread = geom.slab("SRC_TREAD%d" % i, S, x0=11.0, x1=BACK,
                          y0=STEP_Y0 + i * run, y1=STEP_Y1 + 0.02,
                          z0=LOW - 0.4, z1=LOW + rise * (i + 1))
        geom.bevel(tread, 0.035, 2)
        mats.apply(tread, "civic_ashlar")
    # a worn ramp channel down one side of the flight, for barrows
    ramp = geom.prism("SRC_RAMP", S, extrude_axis="x",
                      profile=[(STEP_Y0, LOW + 0.02), (STEP_Y1, HIGH + 0.02),
                               (STEP_Y1, HIGH - 0.16), (STEP_Y0, LOW - 0.16)],
                      start=22.90, end=24.40)
    mats.apply(ramp, "stone_mossy")

    # ---- lower level: old, heavy, mineral ---------------------------------
    low_holes = [{"y0": -8.10, "y1": -6.30, "z0": LOW, "z1": LOW + 2.85}]
    for wy, wz, wh in ((-3.10, LOW + 1.35, 1.55), (0.85, LOW + 1.35, 1.55)):
        low_holes.append({"y0": wy - wh / 8.0, "y1": wy + wh / 8.0,
                          "z0": wz, "z1": wz + wh})
    for piece in geom.slotted_panel("SRC_LOWWALL", S, x=BACK, y0=-20.0,
                                    y1=STEP_Y1, z0=LOW, z1=LOW + 5.10,
                                    holes=low_holes, cuts_per_m=10.0):
        mats.apply(piece, "stone_mossy")
        staging.relief(stage, piece, "stone_mossy", strength=0.17)
        cr_scene.shade_smooth(piece)
    # the blocked arch: an opening that has been walled up, brighter infill
    blocked = geom.slab("SRC_BLOCKED", S, x0=BACK + 0.04, x1=BACK + 0.34,
                        y0=-8.10, y1=-6.30, z0=LOW, z1=LOW + 2.85)
    mats.apply(blocked, "limewash_pale")
    arch_ring = geom.prism("SRC_ARCHRING", S, extrude_axis="x",
                           profile=geom.arched_opening_profile(2.30, 1.15, 1.00),
                           start=BACK - 0.22, end=BACK + 0.02,
                           offset=(-7.20, LOW))
    mats.apply(arch_ring, "civic_ashlar")
    for i, wy in enumerate((-3.10, 0.85)):
        rec = geom.slab("SRC_LOWREC%d" % i, S, x0=BACK + 0.10, x1=BACK + 1.00,
                        y0=wy - 0.30, y1=wy + 0.30,
                        z0=LOW + 1.10, z1=LOW + 3.10)
        mats.apply(rec, "grime_moss")
    plinth = geom.slab("SRC_PLINTH", S, x0=BACK - 0.28, x1=BACK + 0.06,
                       y0=-20.0, y1=STEP_Y1, z0=LOW, z1=LOW + 0.92)
    geom.bevel(plinth, 0.06, 2)
    mats.apply(plinth, "civic_ashlar")

    # ---- upper terrace: later, lighter, domestic --------------------------
    up_holes = [{"y0": DOOR_Y - 0.62, "y1": DOOR_Y + 0.62,
                 "z0": HIGH, "z1": HIGH + 2.30}]
    for wy, wz, wh in ((10.30, HIGH + 1.20, 1.60), (12.20, HIGH + 1.20, 1.60),
                       (18.10, HIGH + 1.35, 1.75), (21.40, HIGH + 1.35, 1.75),
                       (11.30, HIGH + 3.55, 1.30), (19.60, HIGH + 3.75, 1.30)):
        up_holes.append({"y0": wy - wh / 8.0, "y1": wy + wh / 8.0,
                         "z0": wz, "z1": wz + wh})
    for piece in geom.slotted_panel("SRC_UPWALL", S, x=BACK, y0=STEP_Y1,
                                    y1=30.0, z0=HIGH, z1=HIGH + 6.20,
                                    holes=up_holes, cuts_per_m=11.0):
        mats.apply(piece, "plaster_bone")
        staging.relief(stage, piece, "plaster_bone", strength=0.06)
        cr_scene.shade_smooth(piece)
    for i, h in enumerate(up_holes):
        back = geom.slab("SRC_UPREV%d" % i, S, x0=BACK + 0.10, x1=BACK + 1.05,
                         y0=h["y0"] - 0.26, y1=h["y1"] + 0.26,
                         z0=h["z0"] - 0.26, z1=h["z1"] + 0.26)
        mats.apply(back, "timber_dark" if i == 0 else "glass_leaded")
        if i:
            for side in (-1, 1):
                sh = geom.slab("SRC_SHUT%d_%d" % (i, side), S,
                               x0=BACK - 0.14, x1=BACK - 0.05,
                               y0=(h["y0"] - 0.30 if side < 0 else h["y1"] + 0.04),
                               y1=(h["y0"] - 0.04 if side < 0 else h["y1"] + 0.30),
                               z0=h["z0"], z1=h["z1"])
                geom.bevel(sh, 0.025, 2)
                mats.apply(sh, "boards_dark")

    eaves = geom.prism("SRC_EAVES", S, extrude_axis="y",
                       profile=[(BACK - 0.85, HIGH + 6.10), (BACK + 2.6, HIGH + 6.10),
                                (BACK + 2.6, HIGH + 6.42), (BACK - 0.85, HIGH + 6.52)],
                       start=STEP_Y1 - 0.3, end=30.0)
    mats.apply(eaves, "roof_lead")
    # the party wall that says these are two houses, not one long facade
    party = geom.slab("SRC_PARTY", S, x0=BACK - 0.42, x1=BACK + 0.10,
                      y0=16.10, y1=16.70, z0=HIGH, z1=HIGH + 6.95)
    geom.bevel(party, 0.05, 2)
    mats.apply(party, "civic_ashlar")

    # the door on the upper terrace
    leaf = geom.slab("SRC_DOOR", S, x0=BACK + 0.20, x1=BACK + 0.29,
                     y0=DOOR_Y - 0.56, y1=DOOR_Y + 0.56, z0=HIGH, z1=HIGH + 2.18)
    geom.bevel(leaf, 0.03, 2)
    mats.apply(leaf, "paint_madder")
    dsur = geom.slab("SRC_DSUR", S, x0=BACK - 0.16, x1=BACK + 0.06,
                     y0=DOOR_Y - 0.90, y1=DOOR_Y + 0.90, z0=HIGH, z1=HIGH + 2.62)
    geom.bevel(dsur, 0.045, 2)
    mats.apply(dsur, "civic_ashlar")
    dstep = geom.slab("SRC_DSTEP", S, x0=BACK - 0.72, x1=BACK,
                      y0=DOOR_Y - 0.95, y1=DOOR_Y + 0.95,
                      z0=HIGH - 0.002, z1=HIGH + 0.14)
    geom.bevel(dstep, 0.03, 2)
    mats.apply(dstep, "civic_ashlar")
    awn = geom.prism("SRC_AWN", S, extrude_axis="y",
                     profile=[(BACK - 0.10, HIGH + 2.72), (BACK - 2.05, HIGH + 2.28),
                              (BACK - 2.05, HIGH + 2.36), (BACK - 0.10, HIGH + 2.80)],
                     start=17.30, end=20.20)
    mats.apply(awn, "cloth_awning")

    # ---- foreground: a balustrade on the UPPER terrace only ---------------
    for i in range(16):
        by = STEP_Y1 + 0.35 + i * 1.42
        if by > 29.0:
            break
        bal = geom.slab("SRC_BAL%d" % i, S, x0=BAL_X + 0.06, x1=BAL_X + 0.26,
                        y0=by - 0.12, y1=by + 0.12,
                        z0=HIGH + 0.22, z1=HIGH + 0.94)
        geom.bevel(bal, 0.035, 2)
        mats.apply(bal, "civic_ashlar")
    coping = geom.slab("SRC_COPING", S, x0=BAL_X - 0.06, x1=BAL_X + 0.38,
                       y0=STEP_Y1, y1=30.0, z0=HIGH + 0.94, z1=HIGH + 1.12)
    geom.bevel(coping, 0.05, 2)
    mats.apply(coping, "civic_ashlar")
    bal_base = geom.slab("SRC_BALBASE", S, x0=BAL_X, x1=BAL_X + 0.34,
                         y0=STEP_Y1, y1=30.0, z0=HIGH - 2.2, z1=HIGH + 0.22)
    mats.apply(bal_base, "stone_mossy")
    newel = geom.slab("SRC_NEWEL", S, x0=BAL_X - 0.10, x1=BAL_X + 0.42,
                      y0=STEP_Y1 - 0.30, y1=STEP_Y1 + 0.30,
                      z0=HIGH - 2.2, z1=HIGH + 1.42)
    geom.bevel(newel, 0.05, 2)
    mats.apply(newel, "civic_ashlar")
    lantern = geom.slab("SRC_NEWEL_LANT", S, x0=BAL_X + 0.02, x1=BAL_X + 0.30,
                        y0=STEP_Y1 - 0.16, y1=STEP_Y1 + 0.16,
                        z0=HIGH + 1.42, z1=HIGH + 1.84)
    geom.bevel(lantern, 0.035, 2)
    mats.apply(lantern, "metal_verdigris")

    # one object on the lower level, so it is not empty
    trough = geom.slab("SRC_TROUGH", S, x0=17.20, x1=18.60, y0=-1.60, y1=1.90,
                       z0=LOW, z1=LOW + 0.62)
    geom.bevel(trough, 0.05, 2)
    mats.apply(trough, "stone_mossy")

    # ---- runtime -----------------------------------------------------------
    staging.runtime_plane(stage, "RUN_LOWER", x0=11.0, x1=BACK,
                          y0=-20.0, y1=STEP_Y0, z=LOW)
    staging.runtime_plane(stage, "RUN_UPPER", x0=11.0, x1=BACK,
                          y0=STEP_Y1, y1=30.0, z=HIGH)
    staging.runtime_box(stage, "RUN_FLIGHT", x0=11.0, x1=BACK,
                        y0=STEP_Y0, y1=STEP_Y1, z0=LOW - 0.4, z1=HIGH)
    staging.runtime_box(stage, "RUN_LOWWALL", x0=BACK, x1=BACK + 1.2,
                        y0=-20.0, y1=STEP_Y1, z0=LOW, z1=LOW + 5.10)
    staging.runtime_box(stage, "RUN_UPWALL", x0=BACK, x1=BACK + 1.2,
                        y0=STEP_Y1, y1=30.0, z0=HIGH, z1=HIGH + 6.50)
    staging.runtime_box(stage, "RUN_BAL", x0=BAL_X, x1=BAL_X + 0.38,
                        y0=STEP_Y1, y1=30.0, z0=HIGH - 2.2, z1=HIGH + 1.12)
    staging.runtime_box(stage, "RUN_NEWEL", x0=BAL_X - 0.10, x1=BAL_X + 0.42,
                        y0=STEP_Y1 - 0.30, y1=STEP_Y1 + 0.30,
                        z0=HIGH - 2.2, z1=HIGH + 1.84)
    staging.runtime_box(stage, "RUN_TROUGH", x0=17.20, x1=18.60,
                        y0=-1.60, y1=1.90, z0=LOW, z1=LOW + 0.62)

    staging.collider(stage, "COL_BACK", x0=BACK - 0.4, x1=BACK + 0.4,
                     y0=-20.0, y1=30.0, z0=LOW, z1=HIGH + 3.0)
    staging.collider(stage, "COL_BAL", x0=BAL_X, x1=BAL_X + 0.38,
                     y0=STEP_Y1, y1=30.0, z0=HIGH, z1=HIGH + 1.12)
    staging.collider(stage, "COL_LOWFLOOR", x0=17.0, x1=BACK,
                     y0=-20.0, y1=STEP_Y0, z0=LOW - 0.2, z1=LOW)
    staging.collider(stage, "COL_UPFLOOR", x0=BAL_X, x1=BACK,
                     y0=STEP_Y1, y1=30.0, z0=HIGH - 0.2, z1=HIGH)
    staging.collider(stage, "COL_FLIGHT", x0=17.0, x1=BACK,
                     y0=STEP_Y0, y1=STEP_Y1, z0=LOW - 0.4, z1=HIGH)

    staging.walk_bounds(stage, y_min=-11.0, y_max=24.0, x=21.10, z=HIGH)
    stage.walk["profile"] = [[round(y, 2), round(ground_at(y), 3)]
                             for y in (-11.0, STEP_Y0, STEP_Y1, 24.0)]
    staging.doorway(stage, "door_terrace", (BACK - 0.8, DOOR_Y, HIGH))
    staging.cast(stage,
                 hero={"at": (21.10, 1.65, ground_at(1.65)), "frame": 0},
                 npcs=[{"at": (22.40, 12.60, ground_at(12.60)), "frame": 2},
                       {"at": (19.70, -4.90, ground_at(-4.90)), "frame": 5},
                       {"at": (23.30, 19.90, ground_at(19.90)), "frame": 3}])

    cr_scene.sky(stage, top=(0.130, 0.180, 0.290), horizon=(0.370, 0.350, 0.305),
                 strength=1.0)
    cr_scene.sun(stage, energy=4.8, color=(1.0, 0.89, 0.71),
                 azimuth=-68.0, elevation=29.0, size=0.036)
    cr_scene.sun(stage, energy=0.42, color=(0.52, 0.63, 0.86),
                 azimuth=120.0, elevation=58.0, size=0.7, name="TH_SKYFILL")
    cr_scene.point(stage, location=(BAL_X + 0.16, STEP_Y1, HIGH + 1.62),
                   energy=15.0, color=(1.0, 0.66, 0.32), radius=0.20)
    cr_scene.point(stage, location=(BACK - 1.0, DOOR_Y, HIGH + 1.4),
                   energy=14.0, color=(1.0, 0.66, 0.34), radius=0.28)

    return staging.finish(stage, out_dir, attempt_id, concept=CONCEPT,
                          samples=110)
