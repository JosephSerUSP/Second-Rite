"""Attempt 01 -- THE CISTERN LIP.

Spatial idea: monumental compression.

One colossal blind retaining wall runs the whole width and exceeds the frame in
every direction. The player walks a broad stone lip at its foot, with an open
cistern shaft dropping away on the near side. There is no skyline and almost no
sky -- the composition is deliberately airless, and the protagonist is a small
figure at the base of civic infrastructure that does not acknowledge them.

Ornament is rationed to three things: a rhythm of tall narrow drain slots (the
1:4 motif at its largest), a line of oxidised iron tie-rings, and one madder
door. The door is the only saturated colour in the frame.

The near edge is deliberately NOT a slab. A slab across the bottom would hide
the floor and read as a device added to satisfy occlusion. Instead the cistern
edge is a low kerb plus a run of thin iron standards, so the player reads the
floor *through* the foreground and the occlusion is honest.

Expensive source: the wall is a set of heavily subdivided flat panels laid out
around real openings, each carrying displacement from the ashlar height map.

REVISION (owner-selected). The divergence version of this scene scored the
worst architectural_specificity of all nine (4.00) and was called "generic",
"empty" and "a test scene" by every evaluator. This pass keeps the idea --
monumental compression, the quiet enormous wall, the hood shadow the panel
singled out as its one memorable element -- and attacks the specific
criticisms:

  * architectural specificity: the wall is now visibly a WORKING cistern
    head. Water crosses the lip in stone runnels under iron grates, and a
    graduated bronze depth gauge with a float rod is fixed beside the door.
    A civic measuring instrument is a particular decision no kit supplies.
  * density zone: the space under the hood becomes an occupied station --
    bench, notice board with pinned bills, coiled rope on pegs, tally sticks,
    a lantern. The wall stays quiet everywhere else, which is the point.
  * occupied foreground: a windlass over the cistern edge with a rope running
    down the shaft, and a figure working it. The near plane is now something
    happening, not something placed.
  * NPC staging: the figures form a situation -- two at the station under the
    hood, one working the windlass in the foreground.

The original divergence render is retained as 01-divergence.png.
"""
from __future__ import annotations

from .. import geom, mats, scene as cr_scene, staging, vocab

CONCEPT = "monumental compression; a lip at the foot of blind infrastructure"

GROUND = -4.20
WALL_X = 24.00
KERB_X = 15.40
LIP_FRONT = 12.20

DOOR_Y, DOOR_W, DOOR_H = 9.55, 0.98, 2.05
SLOT_Y = (-6.4, -2.1, 1.0, 1.9, 5.8, 12.9, 13.8, 17.6)
SLOT_H = (1.85, 2.30, 1.60, 1.60, 2.55, 1.95, 1.95, 2.20)


def build(out_dir, attempt_id="01"):
    cr_scene.reset()
    stage = cr_scene.make_stage()
    vocab.build_vocabulary()
    S = stage.source
    staging.use(stage, "civic_ashlar", "street_setts", "paint_madder",
                "metal_verdigris", "grime_moss", "timber_dark",
                "plaster_verdigris", "roof_lead", "cloth_awning",
                "boards_dark", "limewash_pale", "plaster_bone", "glass_leaded")

    holes = [{"y0": sy - sh / 8.0, "y1": sy + sh / 8.0,
              "z0": GROUND + 0.55, "z1": GROUND + 0.55 + sh}
             for sy, sh in zip(SLOT_Y, SLOT_H)]
    holes.append({"y0": DOOR_Y - DOOR_W * 0.5, "y1": DOOR_Y + DOOR_W * 0.5,
                  "z0": GROUND, "z1": GROUND + DOOR_H + 0.28})

    for piece in geom.slotted_panel("SRC_WALL", S, x=WALL_X, y0=-14.0, y1=24.0,
                                    z0=GROUND - 0.5, z1=9.0, holes=holes,
                                    cuts_per_m=11.0):
        mats.apply(piece, "civic_ashlar")
        staging.relief(stage, piece, "civic_ashlar", strength=0.19)
        cr_scene.shade_smooth(piece)

    for i, h in enumerate(holes):
        back = geom.slab("SRC_RECESS%d" % i, S,
                         x0=WALL_X + 0.12, x1=WALL_X + 1.00,
                         y0=h["y0"] - 0.24, y1=h["y1"] + 0.24,
                         z0=h["z0"] - 0.24, z1=h["z1"] + 0.24)
        mats.apply(back, "grime_moss")

    course = geom.slab("SRC_COURSE", S, x0=WALL_X - 0.26, x1=WALL_X + 0.1,
                       y0=-14.0, y1=24.0, z0=1.62, z1=1.94)
    geom.bevel(course, 0.055, 2)
    mats.apply(course, "civic_ashlar")

    for i, (sy, sh) in enumerate(zip(SLOT_Y, SLOT_H)):
        w = sh / 4.0
        jamb = geom.slab("SRC_SLOTJ%d" % i, S,
                         x0=WALL_X - 0.13, x1=WALL_X + 0.02,
                         y0=sy - w * 0.5 - 0.16, y1=sy + w * 0.5 + 0.16,
                         z0=GROUND + 0.38, z1=GROUND + 0.76 + sh)
        geom.bevel(jamb, 0.04, 2)
        mats.apply(jamb, "civic_ashlar")

    # the one thing that breaks the wall: a projecting stone-and-lead hood.
    # It exists to cast a large shadow; a uniformly lit wall reads as wallpaper.
    hood = geom.prism("SRC_HOOD", S, extrude_axis="y",
                      profile=[(WALL_X, 0.62), (WALL_X - 2.55, 1.34),
                               (WALL_X - 2.55, 1.52), (WALL_X, 1.18)],
                      start=-1.2, end=6.4)
    mats.apply(hood, "roof_lead")
    fascia = geom.slab("SRC_HOOD_FASCIA", S, x0=WALL_X - 2.70, x1=WALL_X - 2.50,
                       y0=-1.35, y1=6.55, z0=0.96, z1=1.56)
    geom.bevel(fascia, 0.04, 2)
    mats.apply(fascia, "timber_dark")
    for i, by in enumerate((-1.0, 1.6, 4.0, 6.2)):
        brace = geom.prism("SRC_BRACE%d" % i, S, extrude_axis="y",
                           profile=[(WALL_X, 0.58), (WALL_X - 2.45, 1.28),
                                    (WALL_X - 2.20, 1.28), (WALL_X, -0.85)],
                           start=by - 0.085, end=by + 0.085)
        mats.apply(brace, "timber_dark")
    for i, by in enumerate((-0.6, 2.4, 5.8)):
        tie = geom.cylinder("SRC_HOODTIE%d" % i, S,
                            center=(WALL_X - 2.30, by, 1.30),
                            radius=0.030, height=1.25, segments=6, axis="z")
        mats.apply(tie, "metal_verdigris")

    # a badly patched render scar, ragged because it is authored as several
    # overlapping pieces rather than one clean rectangle
    for i, (py, pz, pw, ph) in enumerate((
            (11.9, GROUND + 1.15, 1.15, 0.95),
            (12.5, GROUND + 1.70, 0.90, 1.05),
            (12.1, GROUND + 0.80, 0.70, 0.55))):
        scar = geom.panel("SRC_SCAR%d" % i, S, x=WALL_X - 0.055,
                          y0=py - pw * 0.5, y1=py + pw * 0.5,
                          z0=pz, z1=pz + ph, cuts_y=26, cuts_z=24)
        mats.apply(scar, "plaster_verdigris")
        staging.relief(stage, scar, "plaster_verdigris", strength=0.05)

    leaf = geom.slab("SRC_DOOR", S, x0=WALL_X + 0.20, x1=WALL_X + 0.29,
                     y0=DOOR_Y - DOOR_W * 0.5, y1=DOOR_Y + DOOR_W * 0.5,
                     z0=GROUND, z1=GROUND + DOOR_H)
    geom.bevel(leaf, 0.03, 2)
    mats.apply(leaf, "paint_madder")
    lintel = geom.slab("SRC_DOOR_LINTEL", S, x0=WALL_X - 0.30, x1=WALL_X + 0.12,
                       y0=DOOR_Y - 1.02, y1=DOOR_Y + 1.02,
                       z0=GROUND + DOOR_H + 0.26, z1=GROUND + DOOR_H + 0.66)
    geom.bevel(lintel, 0.06, 2)
    mats.apply(lintel, "civic_ashlar")
    for i in range(2):
        st = geom.slab("SRC_DSTEP%d" % i, S,
                       x0=WALL_X - 0.62 + i * 0.30, x1=WALL_X,
                       y0=DOOR_Y - 1.05, y1=DOOR_Y + 1.05,
                       z0=GROUND - 0.002, z1=GROUND + 0.11 * (i + 1))
        geom.bevel(st, 0.03, 2)
        mats.apply(st, "civic_ashlar")

    for ry in (-4.2, 0.6, 6.9, 15.4):
        boss = geom.cylinder("SRC_BOSS%d" % int(ry * 10), S,
                             center=(WALL_X - 0.08, ry, GROUND + 1.28),
                             radius=0.13, height=0.18, segments=12, axis="x")
        mats.apply(boss, "metal_verdigris")
        ring = geom.cylinder("SRC_RING%d" % int(ry * 10), S,
                             center=(WALL_X - 0.24, ry, GROUND + 0.96),
                             radius=0.035, height=0.44, segments=8, axis="z")
        mats.apply(ring, "metal_verdigris")

    lip = geom.ground("SRC_LIP", S, x0=LIP_FRONT, x1=WALL_X + 0.05,
                      y0=-14.0, y1=24.0, z=GROUND, cuts=40)
    mats.apply(lip, "street_setts")
    staging.relief(stage, lip, "street_setts", strength=0.055)

    # runnels: the drain slots discharge across the lip into the cistern.
    # This is what makes the wall read as infrastructure rather than scenery.
    for i, ry in enumerate((-6.4, 1.9, 12.9, 17.6)):
        chan = geom.slab("SRC_RUNNEL%d" % i, S, x0=KERB_X, x1=WALL_X,
                         y0=ry - 0.26, y1=ry + 0.26,
                         z0=GROUND - 0.13, z1=GROUND - 0.005)
        mats.apply(chan, "grime_moss")
        for side in (-1, 1):
            lip_edge = geom.slab("SRC_RUNLIP%d_%d" % (i, side), S,
                                 x0=KERB_X, x1=WALL_X,
                                 y0=ry + side * 0.30 - 0.05,
                                 y1=ry + side * 0.30 + 0.05,
                                 z0=GROUND - 0.02, z1=GROUND + 0.045)
            geom.bevel(lip_edge, 0.015, 2)
            mats.apply(lip_edge, "civic_ashlar")
        for g in range(7):
            bar = geom.slab("SRC_GRATE%d_%d" % (i, g), S,
                            x0=17.4 + g * 0.32, x1=17.62 + g * 0.32,
                            y0=ry - 0.28, y1=ry + 0.28,
                            z0=GROUND - 0.03, z1=GROUND + 0.025)
            mats.apply(bar, "metal_verdigris")

    # the depth gauge: a graduated bronze scale and float rod beside the door.
    gauge_y = DOOR_Y - 2.35
    back_plate = geom.slab("SRC_GAUGE", S, x0=WALL_X - 0.14, x1=WALL_X - 0.02,
                           y0=gauge_y - 0.19, y1=gauge_y + 0.19,
                           z0=GROUND + 0.20, z1=GROUND + 3.65)
    geom.bevel(back_plate, 0.02, 2)
    mats.apply(back_plate, "timber_dark")
    for g in range(14):
        major = (g % 5 == 0)
        tick = geom.slab("SRC_TICK%d" % g, S,
                         x0=WALL_X - 0.20, x1=WALL_X - 0.13,
                         y0=gauge_y - (0.21 if major else 0.12),
                         y1=gauge_y + (0.21 if major else 0.12),
                         z0=GROUND + 0.34 + g * 0.235,
                         z1=GROUND + 0.34 + g * 0.235 + (0.075 if major else 0.045))
        mats.apply(tick, "limewash_pale" if major else "cloth_awning")
    rod = geom.cylinder("SRC_FLOATROD", S,
                        center=(WALL_X - 0.26, gauge_y, GROUND + 0.30),
                        radius=0.022, height=2.55, segments=6, axis="z")
    mats.apply(rod, "metal_verdigris")
    pointer = geom.slab("SRC_POINTER", S, x0=WALL_X - 0.34, x1=WALL_X - 0.16,
                        y0=gauge_y - 0.24, y1=gauge_y + 0.24,
                        z0=GROUND + 1.62, z1=GROUND + 1.73)
    geom.bevel(pointer, 0.02, 2)
    mats.apply(pointer, "paint_madder")
    bracket = geom.slab("SRC_GAUGEBR", S, x0=WALL_X - 0.30, x1=WALL_X - 0.04,
                        y0=gauge_y - 0.10, y1=gauge_y + 0.10,
                        z0=GROUND + 2.92, z1=GROUND + 3.04)
    mats.apply(bracket, "metal_verdigris")

    kerb = geom.slab("SRC_KERB", S, x0=KERB_X, x1=KERB_X + 0.42,
                     y0=-14.0, y1=24.0, z0=GROUND, z1=GROUND + 0.30)
    geom.bevel(kerb, 0.05, 2)
    mats.apply(kerb, "civic_ashlar")
    shaft = geom.slab("SRC_SHAFT", S, x0=LIP_FRONT - 3.0, x1=KERB_X,
                      y0=-14.0, y1=24.0, z0=GROUND - 6.0, z1=GROUND - 0.02)
    mats.apply(shaft, "grime_moss")

    rail_top = GROUND + 1.06
    for i in range(21):
        sy = -13.0 + i * 1.85
        post = geom.slab("SRC_POST%d" % i, S,
                         x0=KERB_X + 0.10, x1=KERB_X + 0.18,
                         y0=sy - 0.04, y1=sy + 0.04, z0=GROUND + 0.28,
                         z1=rail_top + (0.16 if i % 3 == 0 else 0.0))
        mats.apply(post, "metal_verdigris")
    for zz in (rail_top, GROUND + 0.62):
        rail = geom.slab("SRC_RAIL%d" % int(zz * 100), S,
                         x0=KERB_X + 0.11, x1=KERB_X + 0.17,
                         y0=-13.2, y1=24.0, z0=zz - 0.035, z1=zz + 0.035)
        mats.apply(rail, "metal_verdigris")

    # ---- THE DENSITY ZONE: the keeper station under the hood ------------
    # One crowded band against an otherwise enormous quiet wall. Finding 1:
    # a quiet surface only reads as quiet when something beside it is dense.
    bench = geom.slab("SRC_BENCH", S, x0=WALL_X - 0.92, x1=WALL_X - 0.06,
                      y0=-0.30, y1=3.70, z0=GROUND + 0.40, z1=GROUND + 0.54)
    geom.bevel(bench, 0.03, 2)
    mats.apply(bench, "timber_dark")
    for by in (-0.15, 3.55):
        leg = geom.slab("SRC_BENCHLEG%d" % int(by * 10), S,
                        x0=WALL_X - 0.82, x1=WALL_X - 0.62,
                        y0=by - 0.08, y1=by + 0.08, z0=GROUND, z1=GROUND + 0.42)
        mats.apply(leg, "timber_dark")

    board = geom.slab("SRC_NOTICE", S, x0=WALL_X - 0.16, x1=WALL_X - 0.05,
                      y0=4.35, y1=6.15, z0=GROUND + 1.05, z1=GROUND + 2.35)
    geom.bevel(board, 0.02, 2)
    mats.apply(board, "boards_dark")
    frame_n = geom.slab("SRC_NOTICEFR", S, x0=WALL_X - 0.21, x1=WALL_X - 0.14,
                        y0=4.24, y1=6.26, z0=GROUND + 0.96, z1=GROUND + 2.44)
    geom.bevel(frame_n, 0.02, 2)
    mats.apply(frame_n, "timber_dark")
    for i, (by, bz, bw, bh) in enumerate((
            (4.70, 1.62, 0.34, 0.44), (5.18, 1.70, 0.28, 0.38),
            (5.62, 1.55, 0.31, 0.47), (4.86, 1.16, 0.36, 0.32),
            (5.44, 1.10, 0.26, 0.36))):
        bill = geom.slab("SRC_BILL%d" % i, S, x0=WALL_X - 0.19, x1=WALL_X - 0.165,
                         y0=by - bw * 0.5, y1=by + bw * 0.5,
                         z0=GROUND + bz, z1=GROUND + bz + bh)
        mats.apply(bill, "limewash_pale" if i % 2 else "plaster_bone")

    for i, py in enumerate((0.55, 1.45, 2.35)):
        peg = geom.cylinder("SRC_PEG%d" % i, S,
                            center=(WALL_X - 0.10, py, GROUND + 1.55),
                            radius=0.035, height=0.26, segments=6, axis="x")
        mats.apply(peg, "metal_verdigris")
        coil = geom.cylinder("SRC_COIL%d" % i, S,
                             center=(WALL_X - 0.30, py, GROUND + 1.02),
                             radius=0.19 + 0.03 * i, height=0.16,
                             segments=14, axis="x")
        mats.apply(coil, "cloth_awning")
    for i in range(9):
        stick = geom.slab("SRC_TALLY%d" % i, S,
                          x0=WALL_X - 0.62, x1=WALL_X - 0.20,
                          y0=2.62 + i * 0.045, y1=2.645 + i * 0.045,
                          z0=GROUND + 0.54, z1=GROUND + 0.575)
        mats.apply(stick, "timber_dark")
    crock = geom.cylinder("SRC_CROCK", S,
                          center=(WALL_X - 0.52, 0.30, GROUND + 0.54),
                          radius=0.14, height=0.22, segments=10, axis="z")
    mats.apply(crock, "paint_madder")
    station_lamp = geom.slab("SRC_STATIONLAMP", S,
                             x0=WALL_X - 0.44, x1=WALL_X - 0.20,
                             y0=3.94, y1=4.18,
                             z0=GROUND + 2.02, z1=GROUND + 2.36)
    geom.bevel(station_lamp, 0.025, 2)
    mats.apply(station_lamp, vocab.glazing_lit("glass_station",
                                               warmth=mats.hexc("FFB05A"),
                                               strength=10.0).id)
    lamp_arm = geom.slab("SRC_STATIONARM", S, x0=WALL_X - 0.48, x1=WALL_X - 0.06,
                         y0=4.02, y1=4.10,
                         z0=GROUND + 2.36, z1=GROUND + 2.44)
    mats.apply(lamp_arm, "metal_verdigris")

    # ---- OCCUPIED FOREGROUND: a windlass over the cistern ----------------
    # Sited ON the kerb line so it breaks the railing rather than floating in
    # the shaft, and built tall enough that the A-frames read as structure at
    # 27 px per metre. The first version sat low and back and read as a barrel.
    wy, wx = 5.05, 15.10
    for side in (-1, 1):
        for lean in (-0.30, 0.30):
            leg = geom.prism("SRC_WINDLEG%d_%d" % (side, int(lean * 10)), S,
                             extrude_axis="y",
                             profile=[(wx + lean - 0.09, GROUND),
                                      (wx + lean + 0.09, GROUND),
                                      (wx + 0.08, GROUND + 1.72),
                                      (wx - 0.08, GROUND + 1.72)],
                             start=wy + side * 0.66 - 0.075,
                             end=wy + side * 0.66 + 0.075)
            mats.apply(leg, "timber_dark")
        cap = geom.slab("SRC_WINDCAP%d" % side, S,
                        x0=wx - 0.17, x1=wx + 0.17,
                        y0=wy + side * 0.66 - 0.13,
                        y1=wy + side * 0.66 + 0.13,
                        z0=GROUND + 1.68, z1=GROUND + 1.86)
        geom.bevel(cap, 0.025, 2)
        mats.apply(cap, "timber_dark")
    drum = geom.cylinder("SRC_WINDDRUM", S,
                         center=(wx, wy - 0.60, GROUND + 1.52),
                         radius=0.24, height=1.20, segments=16, axis="y")
    mats.apply(drum, "boards_dark")
    for i in range(5):
        band = geom.cylinder("SRC_WINDBAND%d" % i, S,
                             center=(wx, wy - 0.50 + i * 0.25, GROUND + 1.52),
                             radius=0.258, height=0.055, segments=16, axis="y")
        mats.apply(band, "metal_verdigris")
    axle_w = geom.cylinder("SRC_WINDAXLE", S,
                           center=(wx, wy - 0.82, GROUND + 1.52),
                           radius=0.055, height=1.64, segments=10, axis="y")
    mats.apply(axle_w, "metal_verdigris")
    arm = geom.slab("SRC_WINDARM", S, x0=wx - 0.06, x1=wx + 0.06,
                    y0=wy + 0.78, y1=wy + 0.90,
                    z0=GROUND + 1.02, z1=GROUND + 1.58)
    mats.apply(arm, "metal_verdigris")
    crank = geom.cylinder("SRC_WINDCRANK", S,
                          center=(wx, wy + 0.84, GROUND + 0.86),
                          radius=0.032, height=0.34, segments=8, axis="y")
    mats.apply(crank, "timber_dark")
    ratchet = geom.cylinder("SRC_WINDRATCHET", S,
                            center=(wx, wy - 1.02, GROUND + 1.52),
                            radius=0.19, height=0.07, segments=12, axis="y")
    mats.apply(ratchet, "metal_verdigris")
    pawl = geom.slab("SRC_WINDPAWL", S, x0=wx - 0.03, x1=wx + 0.03,
                     y0=wy - 1.10, y1=wy - 0.96,
                     z0=GROUND + 1.28, z1=GROUND + 1.72)
    mats.apply(pawl, "metal_verdigris")
    rope = geom.slab("SRC_WINDROPE", S, x0=wx - 0.04, x1=wx + 0.04,
                     y0=wy - 0.06, y1=wy + 0.06,
                     z0=GROUND - 3.30, z1=GROUND + 1.48)
    mats.apply(rope, "timber_dark")
    pail_w = geom.cylinder("SRC_WINDPAIL", S,
                           center=(wx, wy, GROUND - 3.62),
                           radius=0.24, height=0.34, segments=12, axis="z")
    mats.apply(pail_w, "metal_verdigris")

    # the water the whole apparatus exists for
    water = geom.ground("SRC_WATER", S, x0=LIP_FRONT - 3.0, x1=KERB_X,
                        y0=-14.0, y1=24.0, z=GROUND - 4.30, cuts=4)
    mats.apply(water, "glass_leaded")

    block = geom.slab("SRC_BLOCK", S, x0=13.6, x1=14.35, y0=2.35, y1=3.55,
                      z0=GROUND, z1=GROUND + 1.05)
    geom.bevel(block, 0.07, 2)
    mats.apply(block, "civic_ashlar")
    load = geom.prism("SRC_LOAD", S, extrude_axis="y",
                      profile=[(16.4, GROUND), (18.5, GROUND),
                               (18.2, GROUND + 0.86), (16.7, GROUND + 0.94)],
                      start=8.6, end=11.4)
    mats.apply(load, "cloth_awning")

    staging.runtime_box(stage, "RUN_WALL", x0=WALL_X, x1=WALL_X + 1.5,
                        y0=-14.0, y1=24.0, z0=GROUND - 0.5, z1=9.0)
    staging.runtime_box(stage, "RUN_HOOD", x0=WALL_X - 2.35, x1=WALL_X,
                        y0=1.4, y1=8.2, z0=GROUND + 4.3, z1=GROUND + 5.6)
    staging.runtime_plane(stage, "RUN_LIP", x0=LIP_FRONT, x1=WALL_X,
                          y0=-14.0, y1=24.0, z=GROUND)
    staging.runtime_box(stage, "RUN_KERB", x0=KERB_X, x1=KERB_X + 0.42,
                        y0=-14.0, y1=24.0, z0=GROUND, z1=GROUND + 1.10)
    staging.runtime_box(stage, "RUN_BLOCK", x0=13.6, x1=14.35, y0=2.35, y1=3.55,
                        z0=GROUND, z1=GROUND + 1.05)
    staging.runtime_box(stage, "RUN_WINDLASS", x0=14.72, x1=15.42,
                        y0=4.20, y1=5.95, z0=GROUND, z1=GROUND + 1.88)
    staging.runtime_box(stage, "RUN_STATION", x0=WALL_X - 1.00, x1=WALL_X - 0.02,
                        y0=-0.40, y1=6.30, z0=GROUND, z1=GROUND + 2.50)
    staging.runtime_box(stage, "RUN_GAUGE", x0=WALL_X - 0.36, x1=WALL_X - 0.01,
                        y0=DOOR_Y - 2.62, y1=DOOR_Y - 2.08,
                        z0=GROUND + 0.20, z1=GROUND + 3.65)
    staging.runtime_box(stage, "RUN_DOOR", x0=WALL_X - 0.05, x1=WALL_X + 0.2,
                        y0=DOOR_Y - 0.7, y1=DOOR_Y + 0.7,
                        z0=GROUND, z1=GROUND + DOOR_H + 0.7)

    staging.collider(stage, "COL_WALL", x0=WALL_X - 0.3, x1=WALL_X + 0.4,
                     y0=-14.0, y1=24.0, z0=GROUND, z1=GROUND + 3.0)
    staging.collider(stage, "COL_WINDLASS", x0=14.72, x1=15.42,
                     y0=4.20, y1=5.95, z0=GROUND, z1=GROUND + 1.60)
    staging.collider(stage, "COL_STATION", x0=WALL_X - 1.00, x1=WALL_X,
                     y0=-0.40, y1=6.30, z0=GROUND, z1=GROUND + 1.20)
    staging.collider(stage, "COL_KERB", x0=KERB_X, x1=KERB_X + 0.42,
                     y0=-14.0, y1=24.0, z0=GROUND, z1=GROUND + 1.1)
    staging.collider(stage, "COL_FLOOR", x0=KERB_X, x1=WALL_X,
                     y0=-14.0, y1=24.0, z0=GROUND - 0.2, z1=GROUND)

    staging.walk_bounds(stage, y_min=-8.0, y_max=19.0, x=19.90, z=GROUND)
    staging.doorway(stage, "door_cistern", (WALL_X - 0.35, DOOR_Y, GROUND))
    # a situation, not a spacing: two at the station under the hood -- one on
    # the bench, one at the notice board -- and one working the windlass in
    # the foreground, half-occluded by the railing.
    staging.cast(stage,
                 hero={"at": (19.90, 7.10, GROUND), "frame": 0},
                 npcs=[{"at": (22.85, 1.55, GROUND), "frame": 3},
                       {"at": (23.05, 5.10, GROUND), "frame": 2},
                       {"at": (16.05, 6.35, GROUND), "frame": 4}])

    cr_scene.sky(stage, top=(0.055, 0.075, 0.115), horizon=(0.150, 0.152, 0.140),
                 strength=1.0)
    cr_scene.sun(stage, energy=6.4, color=(1.0, 0.86, 0.66),
                 azimuth=79.0, elevation=17.0, size=0.026)
    cr_scene.sun(stage, energy=0.95, color=(0.54, 0.66, 0.88),
                 azimuth=-138.0, elevation=-14.0, size=0.6, name="TH_BOUNCE")
    # a soft key aimed at the lip and the station, so the dense zone is not
    # simply lost in the wall shadow the hood casts
    cr_scene.area(stage, location=(17.6, 3.0, GROUND + 3.10), energy=260.0,
                  color=(1.0, 0.90, 0.78), size=5.5, rotation=(64, 0, -28),
                  name="TH_LIPFILL")
    cr_scene.point(stage, location=(WALL_X - 1.0, DOOR_Y, GROUND + 1.5),
                   energy=34.0, color=(1.0, 0.64, 0.30), radius=0.34)
    # the station lantern: a second warm source, marking the dense zone
    cr_scene.point(stage, location=(WALL_X - 0.9, 4.06, GROUND + 2.16),
                   energy=26.0, color=(1.0, 0.62, 0.26), radius=0.20)
    # a cold bounce off the water below, so the cistern reads as wet
    cr_scene.area(stage, location=(14.6, 5.5, GROUND - 4.20),
                  energy=140.0, color=(0.44, 0.60, 0.82), size=7.0,
                  rotation=(0, 0, 0), name="TH_WATERBOUNCE")

    return staging.finish(stage, out_dir, attempt_id, concept=CONCEPT,
                          samples=110)
