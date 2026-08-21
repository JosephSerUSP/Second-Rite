"""Attempt 04 -- THE BUTTRESS GAPS.

Spatial idea: rhythm from structure, life in the gaps.

The flank of one enormous civic building fills the back of the frame. Four
buttresses project from it toward the camera at genuinely different depths and
widths, which produces a strong, irregular vertical rhythm without a single
repeated module -- they are authored one at a time, and no two are alike.

The domestic life of the town has silted up in the recesses BETWEEN the
buttresses: a lean-to, a stone stair, a stack of boards, a shrine niche. The
buttresses are quiet and enormous; the gaps are dense and small. That is the
whole contrast.

The doorway sits in the deepest recess, so reaching it means walking *into*
depth rather than along the frame -- the one place where this side-view street
has a Z-axis intention.
"""
from __future__ import annotations

from .. import geom, mats, scene as cr_scene, staging, vocab

CONCEPT = "buttressed civic flank; domestic accretion silted into the recesses"

GROUND = -4.20
FLANK = 32.60
DOOR_Y = 6.15

# each buttress authored individually: (y_centre, width, front_x, height)
BUTTRESS = (
    (-5.90, 2.35, 25.10, 5.10),
    (0.90, 1.85, 26.80, 4.35),
    (10.20, 2.75, 24.20, 5.85),
    (17.60, 2.05, 26.10, 4.70),
)


def build(out_dir, attempt_id="04"):
    cr_scene.reset()
    stage = cr_scene.make_stage()
    vocab.build_vocabulary()
    S = stage.source
    staging.use(stage, "civic_ashlar", "stone_fine", "stone_mossy",
                "paving_granite", "paint_madder", "metal_verdigris",
                "grime_moss", "timber_dark", "cloth_awning", "roof_lead",
                "boards_dark", "glass_leaded")

    yard = geom.ground("SRC_YARD", S, x0=11.0, x1=FLANK + 0.1,
                       y0=-18.0, y1=28.0, z=GROUND, cuts=50)
    mats.apply(yard, "paving_granite")

    # ---- the flank ---------------------------------------------------------
    holes = [{"y0": DOOR_Y - 0.70, "y1": DOOR_Y + 0.70,
              "z0": GROUND, "z1": GROUND + 2.75}]
    for wy, wz, wh in ((-2.60, GROUND + 3.30, 2.60), (4.10, GROUND + 3.30, 2.60),
                       (13.90, GROUND + 3.55, 2.90), (20.40, GROUND + 3.30, 2.60)):
        holes.append({"y0": wy - wh / 8.0, "y1": wy + wh / 8.0,
                      "z0": wz, "z1": wz + wh})
    for piece in geom.slotted_panel("SRC_FLANK", S, x=FLANK, y0=-18.0, y1=28.0,
                                    z0=GROUND, z1=GROUND + 11.5, holes=holes,
                                    cuts_per_m=9.0):
        mats.apply(piece, "stone_fine")
        staging.relief(stage, piece, "stone_fine", strength=0.14)
        cr_scene.shade_smooth(piece)
    for i, h in enumerate(holes):
        back = geom.slab("SRC_REV%d" % i, S, x0=FLANK + 0.12, x1=FLANK + 1.30,
                         y0=h["y0"] - 0.28, y1=h["y1"] + 0.28,
                         z0=h["z0"] - 0.28, z1=h["z1"] + 0.28)
        mats.apply(back, "grime_moss" if i else "glass_leaded")

    band = geom.slab("SRC_BAND", S, x0=FLANK - 0.30, x1=FLANK + 0.08,
                     y0=-18.0, y1=28.0, z0=GROUND + 6.35, z1=GROUND + 6.82)
    geom.bevel(band, 0.06, 2)
    mats.apply(band, "civic_ashlar")

    # ---- the buttresses ----------------------------------------------------
    for i, (by, bw, bx, bh) in enumerate(BUTTRESS):
        body = geom.prism("SRC_BUT%d" % i, S, extrude_axis="y",
                          profile=[(bx, GROUND), (FLANK, GROUND),
                                   (FLANK, GROUND + bh + 3.4),
                                   (bx + 1.05, GROUND + bh)],
                          start=by - bw * 0.5, end=by + bw * 0.5)
        mats.apply(body, "civic_ashlar")
        staging.relief(stage, body, "civic_ashlar", strength=0.0)
        # a weathering set-off, sloped so it sheds -- and catches a highlight
        off = geom.prism("SRC_BUTOFF%d" % i, S, extrude_axis="y",
                         profile=[(bx - 0.16, GROUND + bh - 0.10),
                                  (bx + 1.30, GROUND + bh + 0.34),
                                  (bx + 1.30, GROUND + bh + 0.62),
                                  (bx - 0.16, GROUND + bh + 0.18)],
                         start=by - bw * 0.5 - 0.16, end=by + bw * 0.5 + 0.16)
        mats.apply(off, "roof_lead")
        plinth = geom.slab("SRC_BUTP%d" % i, S, x0=bx - 0.22, x1=FLANK,
                           y0=by - bw * 0.5 - 0.20, y1=by + bw * 0.5 + 0.20,
                           z0=GROUND, z1=GROUND + 0.86)
        geom.bevel(plinth, 0.07, 2)
        mats.apply(plinth, "civic_ashlar")
        stain = geom.panel("SRC_BUTS%d" % i, S, x=bx - 0.24,
                           y0=by - bw * 0.5 - 0.18, y1=by + bw * 0.5 + 0.18,
                           z0=GROUND + 0.80, z1=GROUND + bh * 0.55,
                           cuts_y=20, cuts_z=26)
        mats.apply(stain, "grime_moss")

    # ---- gap 1 (y ~ -2.5): a lean-to ---------------------------------------
    roof = geom.prism("SRC_LEANTO", S, extrude_axis="y",
                      profile=[(FLANK - 0.15, GROUND + 2.95),
                               (25.90, GROUND + 2.05), (25.90, GROUND + 2.20),
                               (FLANK - 0.15, GROUND + 3.10)],
                      start=-4.30, end=-0.35)
    mats.apply(roof, "boards_dark")
    for py in (-4.10, -0.55):
        postl = geom.slab("SRC_LPOST%d" % int(py * 10), S,
                          x0=25.90, x1=26.12, y0=py - 0.11, y1=py + 0.11,
                          z0=GROUND, z1=GROUND + 2.10)
        mats.apply(postl, "timber_dark")
    bench = geom.slab("SRC_BENCH", S, x0=29.10, x1=30.60, y0=-3.90, y1=-0.75,
                      z0=GROUND + 0.40, z1=GROUND + 0.54)
    geom.bevel(bench, 0.03, 2)
    mats.apply(bench, "timber_dark")
    cloth = geom.prism("SRC_LCLOTH", S, extrude_axis="y",
                       profile=[(25.95, GROUND + 2.02), (26.30, GROUND + 2.02),
                                (26.30, GROUND + 1.05), (25.95, GROUND + 1.00)],
                       start=-3.60, end=-1.90)
    mats.apply(cloth, "cloth_awning")

    # ---- gap 2 (y ~ 6.2): the door, deepest in ------------------------------
    for i in range(3):
        st = geom.slab("SRC_DSTEP%d" % i, S,
                       x0=FLANK - 1.55 + i * 0.44, x1=FLANK,
                       y0=DOOR_Y - 1.35, y1=DOOR_Y + 1.35,
                       z0=GROUND - 0.002, z1=GROUND + 0.16 * (i + 1))
        geom.bevel(st, 0.035, 2)
        mats.apply(st, "civic_ashlar")
    leaf = geom.slab("SRC_DOOR", S, x0=FLANK + 0.34, x1=FLANK + 0.43,
                     y0=DOOR_Y - 0.63, y1=DOOR_Y + 0.63,
                     z0=GROUND + 0.48, z1=GROUND + 2.72)
    geom.bevel(leaf, 0.03, 2)
    mats.apply(leaf, "paint_madder")
    jamb = geom.slab("SRC_DOOR_JAMB", S, x0=FLANK - 0.20, x1=FLANK + 0.08,
                     y0=DOOR_Y - 1.02, y1=DOOR_Y + 1.02,
                     z0=GROUND, z1=GROUND + 3.20)
    geom.bevel(jamb, 0.06, 2)
    mats.apply(jamb, "civic_ashlar")
    lamp = geom.slab("SRC_DOORLAMP", S, x0=FLANK - 0.62, x1=FLANK - 0.34,
                     y0=DOOR_Y + 1.12, y1=DOOR_Y + 1.40,
                     z0=GROUND + 2.42, z1=GROUND + 2.86)
    geom.bevel(lamp, 0.035, 2)
    mats.apply(lamp, "metal_verdigris")

    # ---- gap 3 (y ~ 14): an external stone stair ----------------------------
    for i in range(9):
        tread = geom.slab("SRC_STAIR%d" % i, S,
                          x0=FLANK - 2.35, x1=FLANK - 0.10,
                          y0=12.35 + i * 0.315, y1=12.68 + i * 0.315,
                          z0=GROUND, z1=GROUND + 0.245 * (i + 1))
        geom.bevel(tread, 0.03, 2)
        mats.apply(tread, "stone_mossy")
    landing = geom.slab("SRC_LANDING", S, x0=FLANK - 2.35, x1=FLANK - 0.10,
                        y0=15.20, y1=16.70, z0=GROUND + 2.05, z1=GROUND + 2.32)
    geom.bevel(landing, 0.04, 2)
    mats.apply(landing, "stone_mossy")
    for i in range(7):
        bal = geom.cylinder("SRC_BAL%d" % i, S,
                            center=(FLANK - 2.20, 12.55 + i * 0.58,
                                    GROUND + 0.30 + 0.26 * i),
                            radius=0.035, height=0.95, segments=6, axis="z")
        mats.apply(bal, "metal_verdigris")

    # ---- gap 4 (y ~ 20.5): a shrine niche -----------------------------------
    niche = geom.slab("SRC_NICHE", S, x0=FLANK + 0.10, x1=FLANK + 0.68,
                      y0=19.85, y1=20.60, z0=GROUND + 1.05, z1=GROUND + 2.75)
    mats.apply(niche, "grime_moss")
    nsur = geom.slab("SRC_NICHE_SUR", S, x0=FLANK - 0.22, x1=FLANK + 0.06,
                     y0=19.55, y1=20.90, z0=GROUND + 0.80, z1=GROUND + 3.05)
    geom.bevel(nsur, 0.05, 2)
    mats.apply(nsur, "civic_ashlar")

    # ---- foreground: a well-head, sited where the frame can see it --------
    wx, wy = 16.90, 5.70
    curb = geom.cylinder("SRC_WELL", S, center=(wx, wy, GROUND),
                         radius=0.95, height=0.92, segments=16, axis="z")
    geom.bevel(curb, 0.05, 2)
    mats.apply(curb, "civic_ashlar")
    for py in (wy - 0.92, wy + 0.92):
        up = geom.slab("SRC_WELLPOST%d" % int(py * 10), S,
                       x0=wx - 0.09, x1=wx + 0.09, y0=py - 0.09, y1=py + 0.09,
                       z0=GROUND + 0.88, z1=GROUND + 2.30)
        mats.apply(up, "timber_dark")
    beam = geom.slab("SRC_WELLBEAM", S, x0=wx - 0.11, x1=wx + 0.11,
                     y0=wy - 1.05, y1=wy + 1.05,
                     z0=GROUND + 2.26, z1=GROUND + 2.46)
    geom.bevel(beam, 0.03, 2)
    mats.apply(beam, "timber_dark")
    bucket = geom.cylinder("SRC_BUCKET", S, center=(wx, wy, GROUND + 1.42),
                           radius=0.20, height=0.30, segments=10, axis="z")
    mats.apply(bucket, "metal_verdigris")

    # ---- runtime -----------------------------------------------------------
    staging.runtime_plane(stage, "RUN_YARD", x0=11.0, x1=FLANK,
                          y0=-18.0, y1=28.0, z=GROUND)
    staging.runtime_box(stage, "RUN_FLANK", x0=FLANK, x1=FLANK + 1.4,
                        y0=-18.0, y1=28.0, z0=GROUND, z1=GROUND + 11.5)
    for i, (by, bw, bx, bh) in enumerate(BUTTRESS):
        staging.runtime_box(stage, "RUN_BUT%d" % i, x0=bx, x1=FLANK,
                            y0=by - bw * 0.5, y1=by + bw * 0.5,
                            z0=GROUND, z1=GROUND + bh + 3.4)
    staging.runtime_box(stage, "RUN_WELL", x0=wx - 0.95, x1=wx + 0.95,
                        y0=wy - 1.05, y1=wy + 1.05, z0=GROUND, z1=GROUND + 2.46)
    staging.runtime_box(stage, "RUN_STAIR", x0=FLANK - 2.35, x1=FLANK,
                        y0=12.35, y1=16.70, z0=GROUND, z1=GROUND + 2.32)

    staging.collider(stage, "COL_FLANK", x0=FLANK - 0.4, x1=FLANK + 0.4,
                     y0=-18.0, y1=28.0, z0=GROUND, z1=GROUND + 3.0)
    for i, (by, bw, bx, bh) in enumerate(BUTTRESS):
        staging.collider(stage, "COL_BUT%d" % i, x0=bx, x1=FLANK,
                         y0=by - bw * 0.5, y1=by + bw * 0.5,
                         z0=GROUND, z1=GROUND + 2.0)
    staging.collider(stage, "COL_WELL", x0=wx - 1.0, x1=wx + 1.0,
                     y0=wy - 1.1, y1=wy + 1.1, z0=GROUND, z1=GROUND + 1.0)
    staging.collider(stage, "COL_FLOOR", x0=14.0, x1=FLANK,
                     y0=-18.0, y1=28.0, z0=GROUND - 0.2, z1=GROUND)

    staging.walk_bounds(stage, y_min=-10.0, y_max=22.0, x=21.60, z=GROUND)
    staging.doorway(stage, "door_flank", (FLANK - 1.7, DOOR_Y, GROUND))
    staging.cast(stage,
                 hero={"at": (21.60, 3.20, GROUND), "frame": 0},
                 npcs=[{"at": (29.40, -2.35, GROUND), "frame": 3},
                       {"at": (23.20, 9.80, GROUND), "frame": 1},
                       {"at": (28.10, 14.30, GROUND), "frame": 5}])

    cr_scene.sky(stage, top=(0.105, 0.145, 0.235), horizon=(0.290, 0.285, 0.255),
                 strength=1.0)
    cr_scene.sun(stage, energy=5.2, color=(1.0, 0.87, 0.68),
                 azimuth=71.0, elevation=24.0, size=0.032)
    cr_scene.sun(stage, energy=0.45, color=(0.50, 0.62, 0.85),
                 azimuth=-125.0, elevation=52.0, size=0.7, name="TH_SKYFILL")
    cr_scene.point(stage, location=(FLANK - 0.9, DOOR_Y + 1.25, GROUND + 2.6),
                   energy=22.0, color=(1.0, 0.64, 0.30), radius=0.26)

    return staging.finish(stage, out_dir, attempt_id, concept=CONCEPT,
                          samples=110)
