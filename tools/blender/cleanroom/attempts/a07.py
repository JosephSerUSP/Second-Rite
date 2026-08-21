"""Attempt 07 -- THE DRYING LANE.  (convergence, authored from an empty scene)

Findings applied: 1 (a real density ZONE), 2 (objects that imply use), 3 (an
OCCUPIED foreground), 5 (NPCs as a situation), 6 (light the door), 8 (keep the
continuous quiet floor band).

Nothing from 01-06 is imported, duplicated or re-derived. The lane, its
dimensions, its walls and every object here are authored fresh.

The idea: a back lane that the town uses as a drying yard. The floor is left
almost empty and quiet, exactly as the traversal scoring asked. Everything
above waist height is crowded: five laundry lines at four different heights
crossing the frame, sheets hanging at different drops, a fixed ladder, pots on
sills, a drying rack, bird boxes under the eaves, a mended gutter. The density
band sits from z ~ 0.9 m to the top of frame and the eye reads it as a place
people are constantly in, not a corridor they pass through.

The foreground is a laundry trough with a woman working at it -- an object with
a person attached to it, which is what "occupied" means. It crosses the bottom
of the frame without being a slab, because the trough is short in Y and you can
see the floor either side of it.
"""
from __future__ import annotations

from .. import geom, mats, scene as cr_scene, staging, vocab

CONCEPT = "drying lane; a dense band of daily use over a quiet floor"

GROUND = -4.05
BACK = 25.30
NEAR = 17.10
TROUGH_X = 14.60
DOOR_Y = 7.85


def build(out_dir, attempt_id="07"):
    cr_scene.reset()
    stage = cr_scene.make_stage()
    vocab.build_vocabulary()
    S = stage.source
    staging.use(stage, "plaster_bone", "plaster_verdigris", "limewash_pale",
                "stone_mossy", "civic_ashlar", "street_setts", "timber_dark",
                "boards_dark", "paint_madder", "metal_verdigris",
                "cloth_awning", "glass_leaded", "grime_moss", "roof_lead")

    floor = geom.ground("SRC_FLOOR", S, x0=11.0, x1=BACK + 0.1,
                        y0=-18.0, y1=28.0, z=GROUND, cuts=44)
    mats.apply(floor, "street_setts")
    staging.relief(stage, floor, "street_setts", strength=0.06)
    drain = geom.slab("SRC_DRAIN", S, x0=20.60, x1=21.15, y0=-18.0, y1=28.0,
                      z0=GROUND - 0.09, z1=GROUND + 0.005)
    mats.apply(drain, "stone_mossy")

    # ---- far wall: the surface everything is fixed to ---------------------
    holes = [{"y0": DOOR_Y - 0.64, "y1": DOOR_Y + 0.64,
              "z0": GROUND, "z1": GROUND + 2.34}]
    win = ((-4.90, GROUND + 1.55, 1.55), (-1.20, GROUND + 1.55, 1.55),
           (3.10, GROUND + 1.70, 1.70), (11.60, GROUND + 1.55, 1.55),
           (14.90, GROUND + 1.70, 1.70), (-3.05, GROUND + 4.05, 1.35),
           (5.40, GROUND + 4.20, 1.45), (13.10, GROUND + 4.05, 1.35))
    for wy, wz, wh in win:
        holes.append({"y0": wy - wh / 8.0, "y1": wy + wh / 8.0,
                      "z0": wz, "z1": wz + wh})
    for piece in geom.slotted_panel("SRC_BACK", S, x=BACK, y0=-18.0, y1=28.0,
                                    z0=GROUND, z1=GROUND + 7.40, holes=holes,
                                    cuts_per_m=11.0):
        mats.apply(piece, "plaster_bone")
        staging.relief(stage, piece, "plaster_bone", strength=0.06)
        cr_scene.shade_smooth(piece)
    plinth = geom.slab("SRC_PLINTH", S, x0=BACK - 0.26, x1=BACK + 0.06,
                       y0=-18.0, y1=28.0, z0=GROUND, z1=GROUND + 0.88)
    geom.bevel(plinth, 0.05, 2)
    mats.apply(plinth, "stone_mossy")

    for i, h in enumerate(holes):
        back = geom.slab("SRC_REV%d" % i, S, x0=BACK + 0.10, x1=BACK + 1.05,
                         y0=h["y0"] - 0.24, y1=h["y1"] + 0.24,
                         z0=h["z0"] - 0.24, z1=h["z1"] + 0.24)
        mats.apply(back, "timber_dark" if i == 0 else "glass_leaded")

    # window furniture: shutters, sills, and what people put on sills
    for i, (wy, wz, wh) in enumerate(win):
        ww = wh / 4.0
        sill = geom.slab("SRC_SILL%d" % i, S, x0=BACK - 0.26, x1=BACK + 0.04,
                         y0=wy - ww * 0.5 - 0.24, y1=wy + ww * 0.5 + 0.24,
                         z0=wz - 0.16, z1=wz - 0.05)
        geom.bevel(sill, 0.025, 2)
        mats.apply(sill, "civic_ashlar")
        for side in (-1, 1):
            if (i + (side > 0)) % 3 == 0:
                continue                      # some shutters are open, some gone
            sh = geom.slab("SRC_SH%d_%d" % (i, side), S,
                           x0=BACK - 0.15, x1=BACK - 0.06,
                           y0=(wy - ww * 0.5 - 0.30 if side < 0 else wy + ww * 0.5 + 0.04),
                           y1=(wy - ww * 0.5 - 0.04 if side < 0 else wy + ww * 0.5 + 0.30),
                           z0=wz - 0.02, z1=wz + wh + 0.02)
            geom.bevel(sh, 0.022, 2)
            mats.apply(sh, "boards_dark" if i % 2 else "paint_madder")
        if i in (0, 3, 6):
            pot = geom.cylinder("SRC_POT%d" % i, S,
                                center=(BACK - 0.14, wy + 0.14, wz - 0.05),
                                radius=0.11, height=0.19, segments=10, axis="z")
            mats.apply(pot, "paint_madder")
        if i in (2, 4):
            box = geom.slab("SRC_WBOX%d" % i, S, x0=BACK - 0.34, x1=BACK - 0.06,
                            y0=wy - 0.34, y1=wy + 0.34,
                            z0=wz - 0.30, z1=wz - 0.14)
            geom.bevel(box, 0.02, 2)
            mats.apply(box, "timber_dark")

    # ---- near wall: only a low return, so the lane stays open -------------
    near = geom.panel("SRC_NEAR", S, x=NEAR, y0=-18.0, y1=28.0,
                      z0=GROUND, z1=GROUND + 2.05, cuts_y=170, cuts_z=24)
    mats.apply(near, "plaster_verdigris")
    staging.relief(stage, near, "plaster_verdigris", strength=0.06)
    cr_scene.shade_smooth(near)
    cop = geom.slab("SRC_NEARCOP", S, x0=NEAR - 0.14, x1=NEAR + 0.20,
                    y0=-18.0, y1=28.0, z0=GROUND + 2.03, z1=GROUND + 2.22)
    geom.bevel(cop, 0.045, 2)
    mats.apply(cop, "civic_ashlar")

    # ---- THE DENSITY BAND -------------------------------------------------
    # five lines at four heights, each with its own sag and its own load
    lines = ((GROUND + 4.35, 0.34, ((-6.10, -4.40, 1.55), (-3.60, -2.30, 1.05),
                                    (-1.60, 0.35, 1.95))),
             (GROUND + 3.55, 0.28, ((2.20, 3.60, 1.35), (4.10, 5.90, 0.85))),
             (GROUND + 4.85, 0.42, ((8.90, 11.20, 2.15), (12.00, 13.10, 1.25))),
             (GROUND + 3.15, 0.24, ((15.20, 16.60, 1.05), (17.30, 19.40, 1.65))),
             (GROUND + 5.55, 0.50, ((0.60, 2.90, 1.10), (13.90, 16.20, 1.40))))
    for li, (lz, sag, sheets) in enumerate(lines):
        cord = geom.catenary("SRC_CORD%d" % li, S, y0=-8.60, y1=21.40,
                             x=NEAR + 2.20 + 0.55 * li, z_ends=lz, sag=sag,
                             width=0.030, segments=30)
        mats.apply(cord, "timber_dark")
        for si, (sy0, sy1, drop) in enumerate(sheets):
            t = ((sy0 + sy1) * 0.5 + 8.60) / 30.0
            zz = lz - sag * 4.0 * t * (1.0 - t)
            sheet = geom.hanging_sheet("SRC_SHEET%d_%d" % (li, si), S,
                                       x=NEAR + 2.20 + 0.55 * li,
                                       y0=sy0, y1=sy1, z_top=zz, drop=drop,
                                       cuts_y=16, cuts_z=18, sway=0.075)
            mats.apply(sheet, "cloth_awning" if (li + si) % 3 else "limewash_pale")
            for py in (sy0 + 0.10, sy1 - 0.10):
                peg = geom.slab("SRC_PEG%d_%d_%d" % (li, si, int(py * 10)), S,
                                x0=NEAR + 2.16 + 0.55 * li,
                                x1=NEAR + 2.25 + 0.55 * li,
                                y0=py - 0.025, y1=py + 0.025,
                                z0=zz - 0.06, z1=zz + 0.07)
                mats.apply(peg, "timber_dark")

    geom.ladder("SRC_LADDER", S, x=BACK - 0.34, y=-6.70,
                z0=GROUND, z1=GROUND + 4.55, width=0.46, rungs=11)
    for part in [o for o in S.objects if o.name.startswith("SRC_LADDER")]:
        mats.apply(part, "timber_dark")

    # a drying rack leaning against the near coping -- someone put it there
    for i in range(6):
        bar = geom.slab("SRC_RACK%d" % i, S, x0=NEAR + 0.30, x1=NEAR + 0.86,
                        y0=18.30 + i * 0.19, y1=18.36 + i * 0.19,
                        z0=GROUND + 0.20 + i * 0.24, z1=GROUND + 0.27 + i * 0.24)
        mats.apply(bar, "timber_dark")

    # the gutter, mended once with a different metal
    gut = geom.slab("SRC_GUTTER", S, x0=BACK - 0.40, x1=BACK - 0.16,
                    y0=-18.0, y1=28.0, z0=GROUND + 6.55, z1=GROUND + 6.78)
    mats.apply(gut, "metal_verdigris")
    patchg = geom.slab("SRC_GUTTER_PATCH", S, x0=BACK - 0.44, x1=BACK - 0.12,
                       y0=2.40, y1=4.30, z0=GROUND + 6.52, z1=GROUND + 6.82)
    mats.apply(patchg, "roof_lead")
    for i, dy in enumerate((-6.0, 1.6, 9.4, 17.2)):
        dp = geom.slab("SRC_DOWN%d" % i, S, x0=BACK - 0.32, x1=BACK - 0.20,
                       y0=dy - 0.06, y1=dy + 0.06,
                       z0=GROUND + 0.90, z1=GROUND + 6.55)
        mats.apply(dp, "metal_verdigris")
        stain = geom.panel("SRC_STAIN%d" % i, S, x=BACK - 0.052,
                           y0=dy - 0.34, y1=dy + 0.34,
                           z0=GROUND + 0.85, z1=GROUND + 4.10,
                           cuts_y=8, cuts_z=22)
        mats.apply(stain, "grime_moss")

    eaves = geom.prism("SRC_EAVES", S, extrude_axis="y",
                       profile=[(BACK - 0.95, GROUND + 6.85), (BACK + 2.4, GROUND + 6.85),
                                (BACK + 2.4, GROUND + 7.20), (BACK - 0.95, GROUND + 7.32)],
                       start=-18.0, end=28.0)
    mats.apply(eaves, "roof_lead")
    for i, by in enumerate((-7.4, -0.9, 6.2, 12.8, 19.6)):
        bird = geom.slab("SRC_BIRD%d" % i, S, x0=BACK - 0.78, x1=BACK - 0.52,
                         y0=by - 0.13, y1=by + 0.13,
                         z0=GROUND + 6.40, z1=GROUND + 6.72)
        geom.bevel(bird, 0.02, 2)
        mats.apply(bird, "boards_dark")

    # ---- the door, and it is the brightest warm thing in frame ------------
    leaf = geom.slab("SRC_DOOR", S, x0=BACK - 0.06, x1=BACK + 0.03,
                     y0=DOOR_Y + 0.14, y1=DOOR_Y + 1.28,
                     z0=GROUND + 0.06, z1=GROUND + 2.30)
    geom.bevel(leaf, 0.028, 2)
    mats.apply(leaf, "paint_madder")
    dfr = geom.slab("SRC_DFRAME", S, x0=BACK - 0.20, x1=BACK + 0.05,
                    y0=DOOR_Y - 0.90, y1=DOOR_Y + 0.90,
                    z0=GROUND, z1=GROUND + 2.62)
    geom.bevel(dfr, 0.04, 2)
    mats.apply(dfr, "timber_dark")
    lint = geom.slab("SRC_DLINTEL", S, x0=BACK - 0.34, x1=BACK + 0.06,
                     y0=DOOR_Y - 1.10, y1=DOOR_Y + 1.10,
                     z0=GROUND + 2.58, z1=GROUND + 2.84)
    geom.bevel(lint, 0.04, 2)
    mats.apply(lint, "civic_ashlar")
    lamp_br = geom.slab("SRC_LAMPBR", S, x0=BACK - 0.62, x1=BACK - 0.18,
                        y0=DOOR_Y - 1.28, y1=DOOR_Y - 1.20,
                        z0=GROUND + 2.72, z1=GROUND + 2.82)
    mats.apply(lamp_br, "metal_verdigris")
    lant = geom.slab("SRC_LANTERN", S, x0=BACK - 0.68, x1=BACK - 0.44,
                     y0=DOOR_Y - 1.36, y1=DOOR_Y - 1.12,
                     z0=GROUND + 2.36, z1=GROUND + 2.72)
    geom.bevel(lant, 0.03, 2)
    mats.apply(lant, vocab.glazing_lit("glass_lantern",
                                       warmth=mats.hexc("FFB05A"),
                                       strength=9.0).id)
    step = geom.slab("SRC_DSTEP", S, x0=BACK - 0.76, x1=BACK,
                     y0=DOOR_Y - 0.98, y1=DOOR_Y + 0.98,
                     z0=GROUND - 0.002, z1=GROUND + 0.14)
    geom.bevel(step, 0.03, 2)
    mats.apply(step, "civic_ashlar")

    # ---- OCCUPIED FOREGROUND: a laundry trough, short in Y ---------------
    ty0, ty1 = 2.40, 7.30
    tub = geom.slab("SRC_TROUGH", S, x0=TROUGH_X, x1=TROUGH_X + 1.35,
                    y0=ty0, y1=ty1, z0=GROUND, z1=GROUND + 0.86)
    geom.bevel(tub, 0.055, 2)
    mats.apply(tub, "stone_mossy")
    rim = geom.slab("SRC_TROUGH_RIM", S, x0=TROUGH_X - 0.09, x1=TROUGH_X + 1.44,
                    y0=ty0 - 0.09, y1=ty1 + 0.09,
                    z0=GROUND + 0.86, z1=GROUND + 0.99)
    geom.bevel(rim, 0.035, 2)
    mats.apply(rim, "civic_ashlar")
    water = geom.ground("SRC_WATER", S, x0=TROUGH_X + 0.10, x1=TROUGH_X + 1.25,
                        y0=ty0 + 0.10, y1=ty1 - 0.10, z=GROUND + 0.79, cuts=3)
    mats.apply(water, "glass_leaded")
    board = geom.prism("SRC_WASHBOARD", S, extrude_axis="y",
                       profile=[(TROUGH_X + 0.16, GROUND + 0.92),
                                (TROUGH_X + 0.72, GROUND + 1.52),
                                (TROUGH_X + 0.84, GROUND + 1.46),
                                (TROUGH_X + 0.28, GROUND + 0.86)],
                       start=3.10, end=3.85)
    mats.apply(board, "boards_dark")
    basket = geom.cylinder("SRC_BASKET", S,
                           center=(TROUGH_X + 0.62, ty1 + 0.85, GROUND),
                           radius=0.42, height=0.44, segments=14, axis="z")
    mats.apply(basket, "cloth_awning")
    for i, (by, drop) in enumerate(((ty1 + 0.62, 0.30), (ty1 + 1.02, 0.24))):
        spill = geom.hanging_sheet("SRC_SPILL%d" % i, S, x=TROUGH_X + 0.30,
                                   y0=by - 0.28, y1=by + 0.28,
                                   z_top=GROUND + 0.46, drop=drop,
                                   cuts_y=8, cuts_z=8, sway=0.05)
        mats.apply(spill, "limewash_pale")
    pail = geom.cylinder("SRC_PAIL", S,
                         center=(TROUGH_X + 1.05, ty0 - 0.70, GROUND),
                         radius=0.20, height=0.30, segments=10, axis="z")
    mats.apply(pail, "metal_verdigris")
    broom = geom.cylinder("SRC_BROOM", S,
                          center=(NEAR - 0.22, 12.10, GROUND),
                          radius=0.035, height=1.55, segments=6, axis="z")
    mats.apply(broom, "timber_dark")

    # ---- runtime -----------------------------------------------------------
    staging.runtime_plane(stage, "RUN_FLOOR", x0=11.0, x1=BACK,
                          y0=-18.0, y1=28.0, z=GROUND - 0.06)
    # Camera-facing runtime proxies sit slightly IN FRONT of their source
    # surface, never coincident and never behind it. Blender's cageless
    # selected-to-active bake pushes the ray origin OUTWARD along the target
    # normal by cage_extrusion and then casts INWARD, so it only sees sources
    # that lie behind the target face. Coincident faces are degenerate and
    # bake black; a proxy placed behind its source is missed entirely. Both
    # mistakes were made here in turn and both produced a black facade.
    # 0.25 m in front is robust and, at 27.4 px/m, shifts the wall by well
    # under one native pixel.
    staging.runtime_box(stage, "RUN_BACK", x0=BACK - 0.25, x1=BACK + 1.4,
                        y0=-18.0, y1=28.0, z0=GROUND, z1=GROUND + 7.40)
    staging.runtime_box(stage, "RUN_NEAR", x0=NEAR - 0.14, x1=NEAR + 0.47,
                        y0=-18.0, y1=28.0, z0=GROUND, z1=GROUND + 2.22)
    staging.runtime_box(stage, "RUN_TROUGH", x0=TROUGH_X - 0.09, x1=TROUGH_X + 1.44,
                        y0=ty0 - 0.09, y1=ty1 + 0.09, z0=GROUND, z1=GROUND + 0.99)
    # One small runtime proxy PER SHEET, sized to that sheet.
    #
    # Two wrong answers preceded this one. A single box enclosing all five
    # lines was 2.5 m deep, so the far sheets sat beyond max_ray_distance and
    # never baked. Replacing it with five full-width planes was worse: they
    # are opaque 30 m x 4.65 m surfaces standing in front of the facade, so
    # they occluded the entire back wall and baked black everywhere a sheet
    # did not happen to be. A proxy must cover its source and nothing else.
    for li, (lz, sag, sheets) in enumerate(lines):
        lx = NEAR + 2.20 + 0.55 * li
        for si, (sy0, sy1, drop) in enumerate(sheets):
            t = ((sy0 + sy1) * 0.5 + 8.60) / 30.0
            zz = lz - sag * 4.0 * t * (1.0 - t)
            staging.runtime_box(stage, "RUN_SHEET%d_%d" % (li, si),
                                x0=lx - 0.10, x1=lx + 0.05,
                                y0=sy0 - 0.06, y1=sy1 + 0.06,
                                z0=zz - drop - 0.04, z1=zz + 0.06)

    staging.runtime_box(stage, "RUN_DOOR", x0=BACK - 0.35, x1=BACK + 0.10,
                        y0=DOOR_Y - 1.10, y1=DOOR_Y + 1.10,
                        z0=GROUND, z1=GROUND + 2.84)

    staging.collider(stage, "COL_BACK", x0=BACK - 0.4, x1=BACK + 0.4,
                     y0=-18.0, y1=28.0, z0=GROUND, z1=GROUND + 3.0)
    staging.collider(stage, "COL_NEAR", x0=NEAR, x1=NEAR + 0.35,
                     y0=-18.0, y1=28.0, z0=GROUND, z1=GROUND + 2.2)
    staging.collider(stage, "COL_TROUGH", x0=TROUGH_X, x1=TROUGH_X + 1.44,
                     y0=ty0, y1=ty1, z0=GROUND, z1=GROUND + 1.0)
    staging.collider(stage, "COL_FLOOR", x0=NEAR, x1=BACK,
                     y0=-18.0, y1=28.0, z0=GROUND - 0.2, z1=GROUND)

    staging.walk_bounds(stage, y_min=-9.0, y_max=22.0, x=21.60, z=GROUND)
    staging.doorway(stage, "door_lane", (BACK - 0.9, DOOR_Y, GROUND))
    # a situation, not a spacing: two in conversation at the trough, one
    # working the rack, one waiting in the lit doorway
    staging.cast(stage,
                 hero={"at": (21.60, 4.70, GROUND), "frame": 0},
                 npcs=[{"at": (16.35, 5.95, GROUND), "frame": 2},
                       {"at": (17.95, 7.55, GROUND), "frame": 4},
                       {"at": (24.10, DOOR_Y - 0.15, GROUND), "frame": 3}])

    cr_scene.sky(stage, top=(0.115, 0.155, 0.250), horizon=(0.325, 0.315, 0.280),
                 strength=1.0)
    cr_scene.sun(stage, energy=4.6, color=(1.0, 0.90, 0.73),
                 azimuth=-52.0, elevation=54.0, size=0.038)
    cr_scene.sun(stage, energy=0.40, color=(0.52, 0.63, 0.86),
                 azimuth=126.0, elevation=40.0, size=0.7, name="TH_SKYFILL")
    cr_scene.area(stage, location=(BACK + 0.5, DOOR_Y + 0.6, GROUND + 1.15),
                  energy=70.0, color=(1.0, 0.63, 0.27), size=1.25,
                  rotation=(90, 0, -90), name="TH_DOORGLOW")
    cr_scene.point(stage, location=(BACK - 0.56, DOOR_Y - 1.24, GROUND + 2.54),
                   energy=13.0, color=(1.0, 0.60, 0.24), radius=0.13)

    return staging.finish(stage, out_dir, attempt_id, concept=CONCEPT,
                          samples=128)
