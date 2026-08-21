"""Attempt 05 -- THE OVERHANG.

Spatial idea: stacked depth, with warm interior light as the destination.

Four clearly separated depth planes, chosen so that at this lens each one lands
in a different band of the frame:

    x ~ 13.9  hanging cloth and a bracket, screen-left, unlit and very large
    x ~ 17.4  a jettied upper storey whose UNDERSIDE fills the top of frame
    x ~ 24.0  the ground-floor facade the player actually walks past
    x ~ 37.0  a further roof glimpsed through one deliberate gap

The street below the jetty is in permanent shadow, and the only warm light in
the frame spills out of one open doorway and across the setts. The composition
is a dark tunnel with a bright doorway two thirds along it.

The jetty is the foreground-depth interaction: the player walks *under* it, and
its posts cross in front of them at intervals without ever becoming a slab.
"""
from __future__ import annotations

from .. import geom, mats, scene as cr_scene, staging, vocab

CONCEPT = "jettied overhang; four depth planes, one warm doorway"

GROUND = -4.20
CLOTH_X = 13.90
JETTY_X = 17.40
FACE_X = 24.00
FAR_X = 37.00
DOOR_Y = 8.40


def build(out_dir, attempt_id="05"):
    cr_scene.reset()
    stage = cr_scene.make_stage()
    vocab.build_vocabulary()
    S = stage.source
    staging.use(stage, "street_setts", "plaster_bone", "boards_dark",
                "timber_dark", "paint_madder", "metal_verdigris",
                "grime_moss", "cloth_awning", "roof_lead", "glass_leaded",
                "civic_ashlar", "stone_mossy")

    street = geom.ground("SRC_STREET", S, x0=10.5, x1=FACE_X + 0.1,
                         y0=-18.0, y1=28.0, z=GROUND, cuts=48)
    mats.apply(street, "street_setts")
    staging.relief(stage, street, "street_setts", strength=0.065)

    # ---- plane 3: the ground-floor facade ---------------------------------
    holes = [{"y0": DOOR_Y - 0.68, "y1": DOOR_Y + 0.68,
              "z0": GROUND, "z1": GROUND + 2.42}]
    for wy, wz, wh in ((1.55, GROUND + 1.15, 1.70), (4.35, GROUND + 1.15, 1.70),
                       (13.10, GROUND + 1.25, 1.85), (16.60, GROUND + 1.25, 1.85)):
        holes.append({"y0": wy - wh / 8.0, "y1": wy + wh / 8.0,
                      "z0": wz, "z1": wz + wh})
    for piece in geom.slotted_panel("SRC_FACE", S, x=FACE_X, y0=-18.0, y1=28.0,
                                    z0=GROUND, z1=GROUND + 3.30, holes=holes,
                                    cuts_per_m=11.0):
        mats.apply(piece, "plaster_bone")
        staging.relief(stage, piece, "plaster_bone", strength=0.055)
        cr_scene.shade_smooth(piece)
    for i, h in enumerate(holes):
        back = geom.slab("SRC_REV%d" % i, S, x0=FACE_X + 0.10, x1=FACE_X + 1.20,
                         y0=h["y0"] - 0.26, y1=h["y1"] + 0.26,
                         z0=h["z0"] - 0.26, z1=h["z1"] + 0.26)
        mats.apply(back, "timber_dark" if i == 0 else "glass_leaded")
    base = geom.slab("SRC_FACE_BASE", S, x0=FACE_X - 0.26, x1=FACE_X + 0.06,
                     y0=-18.0, y1=28.0, z0=GROUND, z1=GROUND + 0.78)
    geom.bevel(base, 0.05, 2)
    mats.apply(base, "stone_mossy")

    # the open door: no leaf at all, because the light IS the door
    thresh = geom.slab("SRC_THRESH", S, x0=FACE_X - 0.55, x1=FACE_X + 0.12,
                       y0=DOOR_Y - 0.95, y1=DOOR_Y + 0.95,
                       z0=GROUND - 0.002, z1=GROUND + 0.13)
    geom.bevel(thresh, 0.03, 2)
    mats.apply(thresh, "civic_ashlar")
    leaf = geom.slab("SRC_DOOR", S, x0=FACE_X - 0.10, x1=FACE_X - 0.02,
                     y0=DOOR_Y + 0.20, y1=DOOR_Y + 1.32,
                     z0=GROUND + 0.10, z1=GROUND + 2.40)
    geom.bevel(leaf, 0.03, 2)
    mats.apply(leaf, "paint_madder")
    dframe = geom.slab("SRC_DFRAME", S, x0=FACE_X - 0.18, x1=FACE_X + 0.04,
                       y0=DOOR_Y - 0.92, y1=DOOR_Y + 0.92,
                       z0=GROUND, z1=GROUND + 2.72)
    geom.bevel(dframe, 0.045, 2)
    mats.apply(dframe, "timber_dark")

    # ---- plane 2: the jetty ------------------------------------------------
    soffit = geom.ground("SRC_JETTY_SOFFIT", S, x0=JETTY_X, x1=FACE_X + 0.05,
                         y0=-18.0, y1=28.0, z=GROUND + 3.35, cuts=8)
    mats.apply(soffit, "boards_dark")
    front = geom.panel("SRC_JETTY_FRONT", S, x=JETTY_X, y0=-18.0, y1=28.0,
                       z0=GROUND + 3.30, z1=GROUND + 6.60, cuts_y=180, cuts_z=40)
    mats.apply(front, "plaster_bone")
    staging.relief(stage, front, "plaster_bone", strength=0.06)
    cr_scene.shade_smooth(front)
    bressumer = geom.slab("SRC_BRESSUMER", S, x0=JETTY_X - 0.16, x1=JETTY_X + 0.14,
                          y0=-18.0, y1=28.0,
                          z0=GROUND + 3.14, z1=GROUND + 3.52)
    geom.bevel(bressumer, 0.045, 2)
    mats.apply(bressumer, "timber_dark")

    # the posts: the honest foreground occluder for this scene
    for i, py in enumerate((-6.20, -1.05, 3.60, 10.80, 15.40, 20.90)):
        post = geom.slab("SRC_POST%d" % i, S,
                         x0=JETTY_X + 0.05, x1=JETTY_X + 0.30,
                         y0=py - 0.14, y1=py + 0.14,
                         z0=GROUND, z1=GROUND + 3.34)
        geom.bevel(post, 0.03, 2)
        mats.apply(post, "timber_dark")
        brack = geom.prism("SRC_BRACK%d" % i, S, extrude_axis="y",
                           profile=[(JETTY_X + 0.30, GROUND + 2.30),
                                    (JETTY_X + 1.15, GROUND + 3.30),
                                    (JETTY_X + 0.30, GROUND + 3.30)],
                           start=py - 0.10, end=py + 0.10)
        mats.apply(brack, "timber_dark")
        pad = geom.slab("SRC_PAD%d" % i, S,
                        x0=JETTY_X - 0.04, x1=JETTY_X + 0.40,
                        y0=py - 0.24, y1=py + 0.24,
                        z0=GROUND, z1=GROUND + 0.24)
        geom.bevel(pad, 0.03, 2)
        mats.apply(pad, "civic_ashlar")

    # upper-storey windows, close-set, so the jetty face is the busy surface
    for wy, wz, wh in ((-4.40, GROUND + 4.10, 1.45), (-2.60, GROUND + 4.10, 1.45),
                       (2.10, GROUND + 4.10, 1.45), (3.90, GROUND + 4.10, 1.45),
                       (12.30, GROUND + 4.35, 1.60), (14.20, GROUND + 4.35, 1.60),
                       (19.60, GROUND + 4.10, 1.45)):
        ww = wh / 4.0
        rec = geom.slab("SRC_UW%d" % int(wy * 10), S,
                        x0=JETTY_X + 0.12, x1=JETTY_X + 0.52,
                        y0=wy - ww * 0.5, y1=wy + ww * 0.5, z0=wz, z1=wz + wh)
        mats.apply(rec, "glass_leaded")
        sur = geom.slab("SRC_US%d" % int(wy * 10), S,
                        x0=JETTY_X - 0.09, x1=JETTY_X + 0.10,
                        y0=wy - ww * 0.5 - 0.13, y1=wy + ww * 0.5 + 0.13,
                        z0=wz - 0.14, z1=wz + wh + 0.14)
        geom.bevel(sur, 0.03, 2)
        mats.apply(sur, "timber_dark")

    eave = geom.prism("SRC_EAVE", S, extrude_axis="y",
                      profile=[(JETTY_X - 0.50, GROUND + 6.45),
                               (JETTY_X + 2.40, GROUND + 6.45),
                               (JETTY_X + 2.40, GROUND + 6.78),
                               (JETTY_X - 0.50, GROUND + 6.86)],
                      start=-18.2, end=28.2)
    mats.apply(eave, "roof_lead")

    # ---- plane 4: one gap, one glimpsed roof --------------------------------
    far = geom.prism("SRC_FAR", S, extrude_axis="y",
                     profile=[(FAR_X, GROUND), (FAR_X + 6.0, GROUND),
                              (FAR_X + 6.0, GROUND + 6.6),
                              (FAR_X + 3.0, GROUND + 8.4),
                              (FAR_X, GROUND + 6.6)],
                     start=5.60, end=12.10)
    mats.apply(far, "roof_lead")
    far_wall = geom.panel("SRC_FARWALL", S, x=FAR_X - 0.02, y0=5.60, y1=12.10,
                          z0=GROUND, z1=GROUND + 6.6, cuts_y=40, cuts_z=40)
    mats.apply(far_wall, "plaster_verdigris") if "plaster_verdigris" in \
        mats.all_materials() else mats.apply(far_wall, "plaster_bone")

    # ---- plane 1: the near cloth and its bracket ---------------------------
    cbeam = geom.slab("SRC_CBEAM", S, x0=CLOTH_X - 0.12, x1=CLOTH_X + 0.12,
                      y0=1.30, y1=5.60, z0=GROUND + 2.55, z1=GROUND + 2.78)
    geom.bevel(cbeam, 0.03, 2)
    mats.apply(cbeam, "timber_dark")
    for cy in (1.45, 5.45):
        cp = geom.slab("SRC_CPOST%d" % int(cy * 10), S,
                       x0=CLOTH_X - 0.10, x1=CLOTH_X + 0.10,
                       y0=cy - 0.10, y1=cy + 0.10,
                       z0=GROUND, z1=GROUND + 2.60)
        mats.apply(cp, "timber_dark")
    for i, (cy0, cy1, drop) in enumerate(((1.60, 2.70, 1.55),
                                          (2.95, 3.85, 2.10),
                                          (4.10, 5.35, 1.30))):
        sheet = geom.panel("SRC_CLOTH%d" % i, S, x=CLOTH_X + 0.06,
                           y0=cy0, y1=cy1,
                           z0=GROUND + 2.60 - drop, z1=GROUND + 2.62,
                           cuts_y=14, cuts_z=16)
        mats.apply(sheet, "cloth_awning")
    ring = geom.cylinder("SRC_CRING", S,
                         center=(CLOTH_X, 3.40, GROUND + 2.78),
                         radius=0.05, height=0.24, segments=8, axis="z")
    mats.apply(ring, "metal_verdigris")

    # ---- runtime ------------------------------------------------------------
    staging.runtime_plane(stage, "RUN_STREET", x0=10.5, x1=FACE_X,
                          y0=-18.0, y1=28.0, z=GROUND)
    staging.runtime_box(stage, "RUN_FACE", x0=FACE_X, x1=FACE_X + 1.2,
                        y0=-18.0, y1=28.0, z0=GROUND, z1=GROUND + 3.30)
    staging.runtime_box(stage, "RUN_JETTY", x0=JETTY_X, x1=FACE_X,
                        y0=-18.0, y1=28.0, z0=GROUND + 3.30, z1=GROUND + 6.80)
    for i, py in enumerate((-6.20, -1.05, 3.60, 10.80, 15.40, 20.90)):
        staging.runtime_box(stage, "RUN_POST%d" % i, x0=JETTY_X, x1=JETTY_X + 0.30,
                            y0=py - 0.14, y1=py + 0.14, z0=GROUND, z1=GROUND + 3.34)
    staging.runtime_box(stage, "RUN_CLOTH", x0=CLOTH_X - 0.12, x1=CLOTH_X + 0.12,
                        y0=1.30, y1=5.60, z0=GROUND, z1=GROUND + 2.78)
    staging.runtime_box(stage, "RUN_FAR", x0=FAR_X, x1=FAR_X + 6.0,
                        y0=5.60, y1=12.10, z0=GROUND, z1=GROUND + 8.4)

    staging.collider(stage, "COL_FACE", x0=FACE_X - 0.4, x1=FACE_X + 0.4,
                     y0=-18.0, y1=28.0, z0=GROUND, z1=GROUND + 3.0)
    staging.collider(stage, "COL_JETTYLINE", x0=JETTY_X, x1=JETTY_X + 0.30,
                     y0=-18.0, y1=28.0, z0=GROUND, z1=GROUND + 3.0)
    staging.collider(stage, "COL_FLOOR", x0=JETTY_X, x1=FACE_X,
                     y0=-18.0, y1=28.0, z0=GROUND - 0.2, z1=GROUND)

    staging.walk_bounds(stage, y_min=-9.5, y_max=22.5, x=21.30, z=GROUND)
    staging.doorway(stage, "door_warm", (FACE_X - 0.7, DOOR_Y, GROUND))
    staging.cast(stage,
                 hero={"at": (21.30, 5.20, GROUND), "frame": 0},
                 npcs=[{"at": (22.70, 9.35, GROUND), "frame": 2},
                       {"at": (19.80, 0.40, GROUND), "frame": 4},
                       {"at": (22.10, 16.10, GROUND), "frame": 1}])

    # ---- light: the street is in shadow; the doorway is the only warmth ----
    cr_scene.sky(stage, top=(0.075, 0.100, 0.160), horizon=(0.185, 0.190, 0.180),
                 strength=1.0)
    cr_scene.sun(stage, energy=4.6, color=(1.0, 0.91, 0.76),
                 azimuth=-58.0, elevation=47.0, size=0.040)
    cr_scene.area(stage, location=(FACE_X + 0.55, DOOR_Y, GROUND + 1.15),
                  energy=95.0, color=(1.0, 0.62, 0.26), size=1.5,
                  rotation=(90, 0, -90), name="TH_DOORGLOW")
    cr_scene.point(stage, location=(FACE_X - 1.2, DOOR_Y, GROUND + 0.55),
                   energy=11.0, color=(1.0, 0.60, 0.24), radius=0.5)

    return staging.finish(stage, out_dir, attempt_id, concept=CONCEPT,
                          samples=128)
