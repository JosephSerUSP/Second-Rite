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
                "plaster_verdigris", "roof_lead", "cloth_awning")

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

    block = geom.slab("SRC_BLOCK", S, x0=13.6, x1=14.9, y0=3.1, y1=4.7,
                      z0=GROUND, z1=GROUND + 1.15)
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
    staging.runtime_box(stage, "RUN_BLOCK", x0=13.6, x1=14.9, y0=3.1, y1=4.7,
                        z0=GROUND, z1=GROUND + 1.15)
    staging.runtime_box(stage, "RUN_DOOR", x0=WALL_X - 0.05, x1=WALL_X + 0.2,
                        y0=DOOR_Y - 0.7, y1=DOOR_Y + 0.7,
                        z0=GROUND, z1=GROUND + DOOR_H + 0.7)

    staging.collider(stage, "COL_WALL", x0=WALL_X - 0.3, x1=WALL_X + 0.4,
                     y0=-14.0, y1=24.0, z0=GROUND, z1=GROUND + 3.0)
    staging.collider(stage, "COL_KERB", x0=KERB_X, x1=KERB_X + 0.42,
                     y0=-14.0, y1=24.0, z0=GROUND, z1=GROUND + 1.1)
    staging.collider(stage, "COL_FLOOR", x0=KERB_X, x1=WALL_X,
                     y0=-14.0, y1=24.0, z0=GROUND - 0.2, z1=GROUND)

    staging.walk_bounds(stage, y_min=-8.0, y_max=19.0, x=19.90, z=GROUND)
    staging.doorway(stage, "door_cistern", (WALL_X - 0.35, DOOR_Y, GROUND))
    staging.cast(stage,
                 hero={"at": (19.90, 3.60, GROUND), "frame": 0},
                 npcs=[{"at": (21.30, 9.30, GROUND), "frame": 3},
                       {"at": (18.60, -2.40, GROUND), "frame": 1},
                       {"at": (22.10, 15.60, GROUND), "frame": 4}])

    cr_scene.sky(stage, top=(0.055, 0.075, 0.115), horizon=(0.150, 0.152, 0.140),
                 strength=1.0)
    cr_scene.sun(stage, energy=6.4, color=(1.0, 0.86, 0.66),
                 azimuth=79.0, elevation=17.0, size=0.026)
    cr_scene.sun(stage, energy=0.55, color=(0.52, 0.64, 0.86),
                 azimuth=-138.0, elevation=-24.0, size=0.6, name="TH_BOUNCE")
    cr_scene.point(stage, location=(WALL_X - 1.0, DOOR_Y, GROUND + 1.5),
                   energy=34.0, color=(1.0, 0.64, 0.30), radius=0.34)

    return staging.finish(stage, out_dir, attempt_id, concept=CONCEPT,
                          samples=110)
