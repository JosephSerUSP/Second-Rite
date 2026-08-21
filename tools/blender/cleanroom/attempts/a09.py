"""Attempt 09 -- THE OFFERING WALL.  (convergence, authored from an empty scene)

Findings applied: 1 (an extreme density ZONE against one large quiet mass),
4 (colour incident and a bold specific idea), 2 (objects that imply use),
3 (an occupied foreground), 5 (NPCs in a situation), 6 (light the door),
7 (structured contrast rather than global darkness).

Nothing from 01-06 is imported or re-derived.

The idea: the town's votive corner. One low wall carries several hundred small
recessed niches, each holding a candle, a plaque or a folded cloth. That wall
is the densest surface in the whole gauntlet -- deliberately, because finding 1
says a quiet surface only reads as quiet next to something genuinely dense.
Directly above it rises a completely blank ashlar mass with a single opening,
so the frame is split between the busiest and the emptiest thing here.

Colour incident: madder banners on a rail, and the candle field itself, which
is the only warm light source in the composition and reads as a horizontal band
of small bright points at exactly waist height for a 48-pixel character.

Foreground: a candle-seller's stall, short in Y, with a figure behind it.
"""
from __future__ import annotations

from .. import geom, mats, scene as cr_scene, staging, vocab

CONCEPT = "votive corner; a wall of small offerings under one blank stone mass"

GROUND = -4.10
WALL = 24.60
STALL_X = 15.30
DOOR_Y = 15.20


def build(out_dir, attempt_id="09"):
    cr_scene.reset()
    stage = cr_scene.make_stage()
    vocab.build_vocabulary()
    S = stage.source
    staging.use(stage, "civic_ashlar", "stone_fine", "stone_mossy",
                "paving_granite", "timber_dark", "boards_dark", "paint_madder",
                "metal_verdigris", "cloth_awning", "glass_leaded",
                "grime_moss", "roof_lead", "limewash_pale")

    court = geom.ground("SRC_COURT", S, x0=10.5, x1=WALL + 0.1,
                        y0=-20.0, y1=30.0, z=GROUND, cuts=44)
    mats.apply(court, "paving_granite")

    # ---- the great quiet mass above ---------------------------------------
    upper_holes = [{"y0": DOOR_Y - 0.78, "y1": DOOR_Y + 0.78,
                    "z0": GROUND + 2.60, "z1": GROUND + 5.90}]
    for piece in geom.slotted_panel("SRC_MASS", S, x=WALL, y0=-20.0, y1=30.0,
                                    z0=GROUND + 2.55, z1=GROUND + 11.0,
                                    holes=upper_holes, cuts_per_m=8.0):
        mats.apply(piece, "civic_ashlar")
        staging.relief(stage, piece, "civic_ashlar", strength=0.15)
        cr_scene.shade_smooth(piece)
    corbel = geom.prism("SRC_CORBEL", S, extrude_axis="y",
                        profile=[(WALL - 0.86, GROUND + 8.10), (WALL, GROUND + 8.10),
                                 (WALL, GROUND + 8.62), (WALL - 0.86, GROUND + 8.50)],
                        start=-20.0, end=30.0)
    geom.bevel(corbel, 0.05, 2)
    mats.apply(corbel, "civic_ashlar")
    # the ONE opening in the whole mass, deep and unglazed
    arch = geom.prism("SRC_ARCHRING", S, extrude_axis="x",
                      profile=geom.arched_opening_profile(1.56, 1.55, 0.78),
                      start=WALL - 0.30, end=WALL + 0.04,
                      offset=(DOOR_Y, GROUND + 2.60))
    mats.apply(arch, "stone_fine")
    void = geom.slab("SRC_VOID", S, x0=WALL + 0.06, x1=WALL + 1.60,
                     y0=DOOR_Y - 0.86, y1=DOOR_Y + 0.86,
                     z0=GROUND + 2.50, z1=GROUND + 6.00)
    mats.apply(void, "grime_moss")

    # ---- THE OFFERING WALL: the densest surface in the gauntlet ----------
    backer = geom.panel("SRC_BACKER", S, x=WALL, y0=-20.0, y1=30.0,
                        z0=GROUND, z1=GROUND + 2.62, cuts_y=200, cuts_z=30)
    mats.apply(backer, "stone_fine")
    staging.relief(stage, backer, "stone_fine", strength=0.10)
    cr_scene.shade_smooth(backer)

    lit = vocab.glazing_lit("glass_candle", warmth=mats.hexc("FFA23C"),
                            strength=14.0)
    cells = ((-9.20, GROUND + 0.62, 13, 4, 0.9), (2.60, GROUND + 0.62, 15, 4, 1.4),
             (14.40, GROUND + 0.62, 11, 3, 0.7), (22.60, GROUND + 0.86, 7, 2, 1.1))
    surrounds, cavities = geom.niche_wall(
        "SRC_NICHE", S, x=WALL - 0.02, depth=0.30, cells=cells,
        cell_w=0.235, cell_h=0.315, gap=0.075)
    for s in surrounds:
        mats.apply(s, "stone_fine")
    for i, c in enumerate(cavities):
        # not every niche is occupied, and that is the storytelling
        if i % 9 == 4:
            mats.apply(c, "grime_moss")
        elif i % 11 == 7:
            mats.apply(c, "metal_verdigris")
        elif i % 13 == 5:
            mats.apply(c, "paint_madder")
        else:
            mats.apply(c, lit.id)

    shelf = geom.slab("SRC_SHELF", S, x0=WALL - 0.34, x1=WALL + 0.02,
                      y0=-20.0, y1=30.0, z0=GROUND + 0.44, z1=GROUND + 0.58)
    geom.bevel(shelf, 0.03, 2)
    mats.apply(shelf, "civic_ashlar")
    drip = geom.panel("SRC_DRIP", S, x=WALL - 0.36, y0=-20.0, y1=30.0,
                      z0=GROUND, z1=GROUND + 0.46, cuts_y=120, cuts_z=8)
    mats.apply(drip, "limewash_pale")
    cornice = geom.slab("SRC_CORNICE", S, x0=WALL - 0.40, x1=WALL + 0.04,
                        y0=-20.0, y1=30.0, z0=GROUND + 2.36, z1=GROUND + 2.62)
    geom.bevel(cornice, 0.045, 2)
    mats.apply(cornice, "civic_ashlar")
    soot = geom.panel("SRC_SOOT", S, x=WALL - 0.055, y0=-20.0, y1=30.0,
                      z0=GROUND + 1.95, z1=GROUND + 2.40, cuts_y=140, cuts_z=10)
    mats.apply(soot, "grime_moss")

    # ---- colour incident: a banner rail ------------------------------------
    rail = geom.slab("SRC_BANNERRAIL", S, x0=WALL - 1.02, x1=WALL - 0.88,
                     y0=-11.0, y1=9.0, z0=GROUND + 4.30, z1=GROUND + 4.44)
    mats.apply(rail, "metal_verdigris")
    for i, (by0, by1, drop) in enumerate(((-9.80, -8.60, 2.55), (-6.90, -5.90, 1.95),
                                          (-2.40, -1.30, 2.85), (1.60, 2.70, 2.20),
                                          (6.10, 7.20, 2.45))):
        ban = geom.hanging_sheet("SRC_BANNER%d" % i, S, x=WALL - 0.95,
                                 y0=by0, y1=by1, z_top=GROUND + 4.28, drop=drop,
                                 cuts_y=10, cuts_z=22, sway=0.055)
        mats.apply(ban, "paint_madder" if i % 2 else "cloth_awning")
        for by in (by0 + 0.06, by1 - 0.06):
            tie = geom.slab("SRC_BTIE%d_%d" % (i, int(by * 10)), S,
                            x0=WALL - 1.00, x1=WALL - 0.86,
                            y0=by - 0.03, y1=by + 0.03,
                            z0=GROUND + 4.26, z1=GROUND + 4.48)
            mats.apply(tie, "timber_dark")
    for i, py in enumerate((-11.1, -1.0, 9.1)):
        brk = geom.prism("SRC_BRK%d" % i, S, extrude_axis="y",
                         profile=[(WALL - 0.10, GROUND + 4.95),
                                  (WALL - 1.05, GROUND + 4.34),
                                  (WALL - 1.05, GROUND + 4.48),
                                  (WALL - 0.10, GROUND + 5.20)],
                         start=py - 0.06, end=py + 0.06)
        mats.apply(brk, "metal_verdigris")

    # ---- the step platform in front of the wall ---------------------------
    for i in range(2):
        pl = geom.slab("SRC_PLAT%d" % i, S, x0=WALL - 2.10 + i * 0.55, x1=WALL,
                       y0=-20.0, y1=30.0,
                       z0=GROUND - 0.002, z1=GROUND + 0.17 * (i + 1))
        geom.bevel(pl, 0.03, 2)
        mats.apply(pl, "stone_mossy")

    # ---- occupied foreground: the candle-seller's stall -------------------
    # No canopy. The first version put a cloth roof at exactly the height of
    # the niche band and hid the one thing the scene exists to show. The stall
    # is now low, short in Y and pushed to frame-left, so it reads as occupied
    # foreground without covering the offering wall.
    sy0, sy1 = 1.10, 4.30
    counter = geom.slab("SRC_COUNTER", S, x0=STALL_X, x1=STALL_X + 0.86,
                        y0=sy0, y1=sy1, z0=GROUND + 0.66, z1=GROUND + 0.82)
    geom.bevel(counter, 0.03, 2)
    mats.apply(counter, "boards_dark")
    front = geom.hanging_sheet("SRC_STALLCLOTH", S, x=STALL_X - 0.05,
                               y0=sy0 - 0.10, y1=sy1 + 0.10,
                               z_top=GROUND + 0.68, drop=0.60,
                               cuts_y=18, cuts_z=10, sway=0.035)
    mats.apply(front, "paint_madder")
    for py in (sy0 + 0.16, sy1 - 0.16):
        leg = geom.slab("SRC_SLEG%d" % int(py * 10), S,
                        x0=STALL_X + 0.10, x1=STALL_X + 0.24,
                        y0=py - 0.07, y1=py + 0.07, z0=GROUND, z1=GROUND + 0.68)
        mats.apply(leg, "timber_dark")
    for i in range(9):
        cy = sy0 + 0.28 + i * 0.40
        if cy > sy1 - 0.18:
            break
        cand = geom.cylinder("SRC_CAND%d" % i, S,
                             center=(STALL_X + 0.32 + 0.13 * (i % 3), cy,
                                     GROUND + 0.82),
                             radius=0.032, height=0.22 + 0.05 * (i % 4),
                             segments=6, axis="z")
        mats.apply(cand, "limewash_pale")
    tray = geom.slab("SRC_TRAY", S, x0=STALL_X + 0.50, x1=STALL_X + 0.82,
                     y0=sy0 + 0.26, y1=sy0 + 1.16,
                     z0=GROUND + 0.82, z1=GROUND + 0.90)
    mats.apply(tray, "metal_verdigris")
    crate = geom.slab("SRC_SCRATE", S, x0=STALL_X + 0.16, x1=STALL_X + 0.82,
                      y0=sy1 + 0.26, y1=sy1 + 0.92, z0=GROUND, z1=GROUND + 0.50)
    geom.bevel(crate, 0.025, 2)
    mats.apply(crate, "timber_dark")
    lamp = geom.slab("SRC_STALLLAMP", S, x0=STALL_X + 0.28, x1=STALL_X + 0.52,
                     y0=sy1 - 0.42, y1=sy1 - 0.18,
                     z0=GROUND + 0.84, z1=GROUND + 1.18)
    geom.bevel(lamp, 0.025, 2)
    mats.apply(lamp, vocab.glazing_lit("glass_stall", warmth=mats.hexc("FFB05A"),
                                       strength=12.0).id)

    # a swept pile of spent candle stubs against the platform: recent use
    sweep = geom.prism("SRC_SWEEP", S, extrude_axis="y",
                       profile=[(WALL - 2.55, GROUND), (WALL - 2.05, GROUND),
                                (WALL - 2.18, GROUND + 0.16)],
                       start=10.20, end=12.10)
    mats.apply(sweep, "limewash_pale")

    # ---- runtime -------------------------------------------------------------
    staging.runtime_plane(stage, "RUN_COURT", x0=10.5, x1=WALL,
                          y0=-20.0, y1=30.0, z=GROUND)
    staging.runtime_box(stage, "RUN_MASS", x0=WALL, x1=WALL + 1.4,
                        y0=-20.0, y1=30.0, z0=GROUND, z1=GROUND + 11.0)
    staging.runtime_box(stage, "RUN_PLAT", x0=WALL - 2.10, x1=WALL,
                        y0=-20.0, y1=30.0, z0=GROUND, z1=GROUND + 0.34)
    staging.runtime_box(stage, "RUN_BANNERS", x0=WALL - 1.10, x1=WALL - 0.80,
                        y0=-11.0, y1=9.0, z0=GROUND + 1.40, z1=GROUND + 4.48)
    staging.runtime_box(stage, "RUN_STALL", x0=STALL_X - 0.10, x1=STALL_X + 0.90,
                        y0=sy0 - 0.12, y1=sy1 + 0.95, z0=GROUND, z1=GROUND + 1.18)
    staging.runtime_box(stage, "RUN_ARCH", x0=WALL - 0.30, x1=WALL + 0.10,
                        y0=DOOR_Y - 0.90, y1=DOOR_Y + 0.90,
                        z0=GROUND + 2.55, z1=GROUND + 6.00)

    staging.collider(stage, "COL_WALL", x0=WALL - 0.4, x1=WALL + 0.4,
                     y0=-20.0, y1=30.0, z0=GROUND, z1=GROUND + 3.0)
    staging.collider(stage, "COL_PLAT", x0=WALL - 2.10, x1=WALL,
                     y0=-20.0, y1=30.0, z0=GROUND, z1=GROUND + 0.34)
    staging.collider(stage, "COL_STALL", x0=STALL_X, x1=STALL_X + 0.90,
                     y0=sy0 - 0.12, y1=sy1 + 0.95, z0=GROUND, z1=GROUND + 1.2)
    staging.collider(stage, "COL_FLOOR", x0=STALL_X, x1=WALL,
                     y0=-20.0, y1=30.0, z0=GROUND - 0.2, z1=GROUND)

    staging.walk_bounds(stage, y_min=-11.0, y_max=24.0, x=20.90, z=GROUND)
    staging.doorway(stage, "door_shrine", (WALL - 1.2, DOOR_Y, GROUND))
    # a situation: the seller behind the stall, a customer at the counter,
    # one figure alone at the candle field
    staging.cast(stage,
                 hero={"at": (20.90, 9.35, GROUND), "frame": 0},
                 npcs=[{"at": (16.85, 2.55, GROUND), "frame": 3},
                       {"at": (17.70, 0.55, GROUND), "frame": 1},
                       {"at": (22.85, -1.85, GROUND), "frame": 5}])

    # ---- light: structured, not globally dark ------------------------------
    cr_scene.sky(stage, top=(0.085, 0.115, 0.195), horizon=(0.235, 0.230, 0.210),
                 strength=1.0)
    cr_scene.sun(stage, energy=3.4, color=(0.94, 0.93, 0.98),
                 azimuth=-72.0, elevation=61.0, size=0.055)
    cr_scene.sun(stage, energy=0.38, color=(0.50, 0.62, 0.86),
                 azimuth=110.0, elevation=36.0, size=0.8, name="TH_SKYFILL")
    # the candle field itself is the warm key, sampled as a long low strip
    for i, cy in enumerate((-9.2, -3.0, 2.6, 8.4, 14.4, 22.6)):
        cr_scene.point(stage, location=(WALL - 1.05, cy, GROUND + 1.05),
                       energy=26.0, color=(1.0, 0.55, 0.20), radius=0.75,
                       name="TH_CANDLE%d" % i)
    cr_scene.point(stage, location=(WALL + 1.0, DOOR_Y, GROUND + 3.6),
                   energy=45.0, color=(1.0, 0.66, 0.32), radius=0.6)

    return staging.finish(stage, out_dir, attempt_id, concept=CONCEPT,
                          samples=140)
