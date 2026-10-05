"""The Church -- a second design for Sister Agnes's chapel on the Praca.

An alternative to `st_maria_chapel.py`, authored against the same camera and
the same side-on lane (the aisle, altar at screen left, main door at screen
right). The first chapel is a rectangular hall whose far wall is four small
windows and whose altar is seen only in profile. This one changes the plan and
the light, not the lane:

* **A cruciform plan.** The far wall steps back into a deep transept chapel
  facing the camera, under a segmental arch. Its gilt-framed altar is the one
  retable the player sees front-on, so the building's centre of gravity is a
  face and not a profile. (The retable's recess is left empty on purpose --
  what the church keeps there is the owner's call, as in the first chapel.)
* **A real nave elevation.** The far wall is an arcade of round-headed windows
  between pilasters, under a stone cornice, over an azulejo dado; the chancel
  end carries the tall azulejo panel. The roof is pitched timber with tie
  beams, and brass hanging lamps are the room's practical lights.
* **Warmer, lighter surfaces.** A terracotta nave floor and a stone chancel
  instead of grey stone throughout, so the largest surface in the frame
  differs from the first chapel's.
* **Round-headed openings.** The door, the windows and the transept arch are
  round-headed (`church.py`), which is what reads as "church" at 256 px.

Blender Y is screen LEFT. Exported with `--span 16`, engine lane Y is
`8 - blender_y`: the altar end is engine Y ~0, the door end ~16.

    python tools/blender/run.py tools/blender/recipes/st_maria_church.py -- --blend out/church/st_maria_church.blend
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))

import church  # noqa: E402
import furnishings as furn  # noqa: E402
import interior as kit  # noqa: E402

ASSET_ID = "st_maria_church"

HALF_LENGTH = 8.0
DEPTH = 6.4
CEILING_Z = 5.4
ROOF_RISE = 1.6

# The chancel at the altar end, its steps facing down the nave.
LOWER_STEP_Y = 4.9
UPPER_STEP_Y = 5.4
LOWER_RISE = 0.16
UPPER_RISE = 0.32
ALTAR_AT = (0.9, 6.9)
CHANCEL_Y = 4.9

# The transept chapel: the far wall steps back under a segmental arch.
TRANSEPT = (-1.7, 1.7, 2.6)       # y0, y1, depth
TRANSEPT_SPRING = 3.0
TRANSEPT_RISE = 1.2

# Round-headed windows in the far wall: (centre y, sill z), half-span 0.5.
WINDOW_HALF = 0.5
WINDOW_SPRING = 3.7
WINDOWS = ((-5.6, 1.9), (-3.2, 1.9), (3.2, 1.9), (5.6, 2.7))
PILASTERS = (-7.1, -4.4, -1.95, 1.95, 4.4, 7.1)

# The main door in the end wall opposite the altar, centred on the aisle.
DOOR_HALF = 0.75
DOOR_SPRING = 2.9
EXIT_Y = -HALF_LENGTH + 0.6

PEW_ROWS_Y = tuple(3.4 - 0.95 * i for i in range(9))
FRONT_BANK = (-1.0, 1.1)
BACK_BANK = (1.4, 1.8)

CARPET_Y = (-HALF_LENGTH + 0.3, 4.4)
NAVE_DADO = 1.2
CHANCEL_PANEL = 2.5
TRANSEPT_TILE = 3.2
TIE_BEAM_Y = (-6.0, -3.0, 0.0, 3.0, 6.0)


def window_opening(y, sill):
    return (y - WINDOW_HALF, y + WINDOW_HALF, sill, WINDOW_SPRING + WINDOW_HALF)


def build(lighting="neutral", haze=False):
    room = kit.Interior(ASSET_ID, half_width=HALF_LENGTH, depth=DEPTH,
                        ceiling_z=CEILING_Z)
    back_x = room.back_x
    front_x = room.front_x
    t_y0, t_y1, t_depth = TRANSEPT
    t_centre = (t_y0 + t_y1) / 2.0
    t_half = (t_y1 - t_y0) / 2.0
    apex = TRANSEPT_SPRING + TRANSEPT_RISE

    room.floor(mat=room.terracotta)
    openings = [window_opening(y, sill) for y, sill in WINDOWS]
    room.back_wall(openings=openings, alcoves=[TRANSEPT], arch_z=apex)
    # The chancel end wall carries a round-headed window above the retable.
    end_window = (back_x - 3.6, back_x - 1.8, 3.5, 4.9)
    door = (-DOOR_HALF, DOOR_HALF, 0.0, DOOR_SPRING + DOOR_HALF)
    door_window = (1.7, 2.9, 1.9, 4.1)   # x0, x1, z0, z1 in the door-end wall
    room.side_walls(openings={-1: [door, door_window], 1: [end_window]})
    room.pitched_ceiling(rise=ROOF_RISE, bays=9)

    # --- round heads: window arcade, transept arch, door, end window --------
    for index, (y, sill) in enumerate(WINDOWS):
        opening = window_opening(y, sill)
        room.window(*opening)
        church.arch_infill(room, f"window_head_{index}", "back", y, WINDOW_HALF,
                           WINDOW_SPRING, opening[3])
        church.arch_ring(room, f"window_arch_{index}", "back", y, WINDOW_HALF,
                         WINDOW_SPRING, band=0.14, proud=0.06, segments=9)
        church.window_tracery(room, f"window_bars_{index}", y, WINDOW_SPRING,
                              WINDOW_HALF, sill)
    church.arch_infill(room, "transept_head", "back", t_centre, t_half,
                       TRANSEPT_SPRING, apex, rise=TRANSEPT_RISE, strips=26)
    church.arch_ring(room, "transept_arch", "back", t_centre, t_half,
                     TRANSEPT_SPRING, rise=TRANSEPT_RISE, band=0.3,
                     proud=0.1, segments=19)

    door_cx = 0.0
    door_wall = -HALF_LENGTH
    church.arch_infill(room, "door_head", "-y", door_cx, DOOR_HALF, DOOR_SPRING,
                       DOOR_SPRING + DOOR_HALF)
    church.arch_ring(room, "door_arch", "-y", door_cx, DOOR_HALF, DOOR_SPRING,
                     band=0.22, proud=0.08, segments=11)
    # The floor runs on through the wall as the threshold; the leaf stands
    # open, folded back against the end wall; daylight beyond.
    room.part("door_threshold", (DOOR_HALF * 2.0 - 0.12, 0.5 + room.wall_thick,
                                 room.floor_thick),
              (door_cx, door_wall - (0.5 + room.wall_thick) / 2.0,
               -room.floor_thick / 2.0), room.stone)
    room.part("door_daylight", (DOOR_HALF * 2.0 + 0.6, 0.05, DOOR_SPRING + DOOR_HALF + 0.6),
              (door_cx, door_wall - (room.wall_thick + 0.58),
               (DOOR_SPRING + DOOR_HALF + 0.6) / 2.0), room.daylight)
    room.part("door_leaf", (1.0, 0.07, DOOR_SPRING - 0.1),
              (DOOR_HALF + 0.6, door_wall + 0.09, (DOOR_SPRING - 0.1) / 2.0),
              room.wood)

    dw_c, dw_h = (door_window[0] + door_window[1]) / 2.0, (door_window[1] - door_window[0]) / 2.0
    room.side_window(-1, *door_window)
    church.arch_infill(room, "door_window_head", "-y", dw_c, dw_h,
                       door_window[3] - dw_h, door_window[3])
    church.arch_ring(room, "door_window_arch", "-y", dw_c, dw_h,
                     door_window[3] - dw_h, band=0.14, proud=0.06, segments=9)
    room.side_window_light(-1, dw_c, 3.0, energy=180.0)

    ex0, ex1 = end_window[0], end_window[1]
    ew_centre, ew_half = (ex0 + ex1) / 2.0, (ex1 - ex0) / 2.0
    room.side_window(1, ex0, ex1, end_window[2], end_window[3])
    church.arch_infill(room, "end_window_head", "+y", ew_centre, ew_half,
                       end_window[3] - ew_half, end_window[3])
    church.arch_ring(room, "end_window_arch", "+y", ew_centre, ew_half,
                     end_window[3] - ew_half, band=0.14, proud=0.06, segments=9)

    # --- the chancel ----------------------------------------------------------
    room.platform("chancel_step", front_x, back_x, LOWER_STEP_Y, HALF_LENGTH,
                  LOWER_RISE, mat=room.stone, edge="-y")
    room.platform("chancel", front_x, back_x, UPPER_STEP_Y, HALF_LENGTH,
                  UPPER_RISE, mat=room.stone, edge="-y")
    # The transept chapel's own step: the one riser that faces the camera.
    room.platform("transept_step", back_x - 0.55, back_x + t_depth, t_y0, t_y1,
                  0.2, mat=room.stone, edge="-x")

    # --- surfaces: dado, chancel panel, pilasters, cornice -------------------
    furn.azulejo_dado(room, height=NAVE_DADO, y0=-HALF_LENGTH, y1=t_y0)
    furn.azulejo_dado(room, height=NAVE_DADO, y0=t_y1, y1=CHANCEL_Y)
    with room.piece("chancel_panel"):
        room.part("chancel_panel_tiles", (0.02, HALF_LENGTH - CHANCEL_Y, CHANCEL_PANEL),
                  (back_x - 0.01, (HALF_LENGTH + CHANCEL_Y) / 2.0, CHANCEL_PANEL / 2.0),
                  room.azulejo)
        room.part("chancel_panel_rail", (0.06, HALF_LENGTH - CHANCEL_Y, 0.07),
                  (back_x - 0.02, (HALF_LENGTH + CHANCEL_Y) / 2.0, CHANCEL_PANEL + 0.035),
                  room.wood)
    # The same band on the transept's returns, so the chapel reads as tiled.
    with room.piece("transept_dado"):
        for side, y in enumerate((t_y0, t_y1)):
            sign = 1.0 if side == 0 else -1.0
            room.part(f"transept_dado_{side}", (t_depth, 0.02, TRANSEPT_TILE),
                      (back_x + t_depth / 2.0, y + sign * 0.01, TRANSEPT_TILE / 2.0),
                      room.azulejo)
    for index, y in enumerate(PILASTERS):
        church.pilaster(room, f"pilaster_{index}", y, CEILING_Z - 0.2)
    church.cornice(room, "cornice", CEILING_Z - 0.3)

    # --- roof furniture: tie beams and the lamps hung from them --------------
    church.tie_beams(room, "tie_beams", TIE_BEAM_Y, CEILING_Z - 0.2)
    for index, y in enumerate((-4.6, -1.6, 2.4)):
        church.hanging_lamp(room, f"hanging_lamp_{index}", (-0.3, y),
                            CEILING_Z - 0.32, 3.1)
    church.hanging_lamp(room, "transept_lamp", (back_x + t_depth * 0.55, 0.0),
                        CEILING_Z, 3.5, energy=30.0)

    # --- the altars -----------------------------------------------------------
    with room.surface(UPPER_RISE):
        furn.altar(room, "altar", ALTAR_AT, turn=90)
    with room.surface(0.2):
        church.side_altar(room, "transept_altar", t_centre, t_depth)
    church.pulpit(room, "pulpit", 4.4)
    # Red drapes gathered at the transept arch, and a confessional by the door.
    for index, y in enumerate((t_y0 + 0.4, t_y1 - 0.4)):
        church.curtain(room, f"transept_curtain_{index}", y, 0.25, 3.6,
                       width=0.8, folds=6, x=back_x + 0.3)
    church.confessional(room, "confessional", -6.6)
    # The rail across the chancel step, open at the lane so the player can
    # walk up to Agnes and the step.
    with room.surface(LOWER_RISE):
        church.communion_rail(room, "communion_rail", UPPER_STEP_Y - 0.15,
                              0.5, back_x - 0.3)

    # --- the congregation -----------------------------------------------------
    for row, y in enumerate(PEW_ROWS_Y):
        for bank, (x, length) in (("front", FRONT_BANK), ("back", BACK_BANK)):
            furn.pew(room, f"pew_{bank}_{row}", (x, y), length=length, turn=90)
    carpet_y0, carpet_y1 = CARPET_Y
    furn.woven_runner(room, "aisle_carpet", (0.02, (carpet_y0 + carpet_y1) / 2.0),
                      length=carpet_y1 - carpet_y0, width=0.9,
                      cloth_mat=kit.material("red_wool"), border_mat=room.terracotta,
                      motif_mat=room.wax)

    # --- furniture of the door and the chancel -------------------------------
    furn.font(room, "font", (DOOR_HALF + 1.35, door_wall + 0.5))
    furn.votive_stand(room, "votive_stand", (back_x - 0.45, LOWER_STEP_Y - 0.9),
                      lit=3)
    for index, y in enumerate((UPPER_STEP_Y + 0.4, HALF_LENGTH - 0.5)):
        church.chancel_candlestand(room, f"candlestand_{index}",
                                   (back_x - 0.6 if index == 0 else front_x + 1.0, y))

    # --- the repair in progress, as in the first chapel ----------------------
    step_face = LOWER_STEP_Y - room.floor_thick
    room.part("lifted_step_stone", (0.58, 0.34, 0.15), (0.75, step_face - 0.35, 0.075),
              room.stone, rotation=(0.0, 0.0, 0.3))
    room.part("fresh_mortar", (0.62, 0.012, 0.12),
              (0.75, step_face - 0.006, LOWER_RISE / 2.0), room.whitewash)
    furn.mortar_tub(room, "mortar_tub", (1.5, step_face - 0.35))

    # --- light: windows, hanging lamps (above), candles, the open door -------
    for index, (y, sill) in enumerate(WINDOWS):
        light = room.window_light(y, (sill + WINDOW_SPRING + WINDOW_HALF) / 2.0,
                                  energy=170.0)
        light.name = f"light_window_{index}"
    room.side_window_light(1, ew_centre, (end_window[2] + end_window[3]) / 2.0,
                           energy=200.0)
    # Daylight bouncing off the terracotta and the limewash: two soft sources
    # high over the nave, so the pews read as carved wood and not as silhouettes.
    for index, y in enumerate((-3.2, 2.2)):
        room.light(f"light_nave_bounce_{index}", "AREA",
                   ((front_x + back_x) / 2.0 - 0.4, y, CEILING_Z - 0.6),
                   (0.25, 0.0, -1.0), 230.0, (1.0, 0.9, 0.74),
                   size=3.0, size_y=4.5)
    room.light("light_transept", "AREA",
               (back_x + t_depth * 0.5, 0.0, apex - 0.4), (0.0, 0.0, -1.0),
               90.0, (1.0, 0.82, 0.58), size=1.8, size_y=2.2)
    altar_x, altar_y = ALTAR_AT
    room.light("light_altar_candles", "POINT",
               (altar_x - 0.3, altar_y - 0.6, UPPER_RISE + 1.6), (0.0, 0.0, -1.0),
               26.0, (1.0, 0.76, 0.46), radius=0.2)
    room.light("light_votives", "POINT", (back_x - 0.8, LOWER_STEP_Y - 0.9, 1.3),
               (0.0, 0.0, -1.0), 30.0, (1.0, 0.74, 0.44), radius=0.12)
    room.light("light_door_daylight", "AREA", (door_cx, door_wall + 0.4, 1.6),
               (0.0, 1.0, -0.35), 150.0, (0.86, 0.92, 1.0), size=1.4, size_y=2.4)

    if lighting != "neutral":
        dramatic_lighting(room, lighting, front_x, back_x, apex)
    if haze:
        # Plate-only: a volume cannot be baked into the runtime atlas.
        haze_volume(front_x, back_x)

    room.finish()
    return room


def _drop(*prefixes):
    for obj in list(bpy.data.objects):
        if obj.type == "LIGHT" and obj.name.startswith(prefixes):
            bpy.data.objects.remove(obj, do_unlink=True)


def _scale(prefix, k):
    for obj in bpy.data.objects:
        if obj.type == "LIGHT" and obj.name.startswith(prefix):
            obj.data.energy *= k


def dramatic_lighting(room, preset, front_x, back_x, apex):
    """Replace the soft rig with a hard one.

    `shafts`: one low sun outside the far wall. It reaches the room only
    through the window openings, so the patches on the floor and pews take
    the windows' own shape, bars included, and slide toward the chancel.
    `vigil`: the same church at dusk. The windows go cold and dim, and the
    room is lit by its lamps, candles and the transept alone.
    """
    _drop("light_nave_bounce", "light_window_")
    # The daylight planes behind each opening are opaque surfaces: hidden from
    # shadow rays they still glow to the camera, but the sun can pass them.
    for obj in bpy.data.objects:
        if obj.type == "MESH" and "daylight" in obj.name:
            obj.visible_shadow = False
    if preset == "shafts":
        room.light("light_sun_through_windows", "SUN",
                   (back_x + 3.0, 0.0, 8.0), (-0.8, 0.3, -0.62),
                   30.0, (1.0, 0.84, 0.58))
        bpy.data.lights["light_sun_through_windows"].angle = 0.02
        _scale("light_hanging_lamp", 0.5)
        _scale("light_transept", 1.6)
    elif preset == "vigil":
        for index, (y, sill) in enumerate(WINDOWS):
            room.window_light(y, (sill + WINDOW_SPRING + WINDOW_HALF) / 2.0,
                              energy=45.0).data.color = (0.45, 0.58, 1.0)
        _scale("light_hanging_lamp", 3.2)
        _scale("light_transept", 2.4)
        _scale("light_altar_candles", 3.0)
        _scale("light_votives", 3.0)
        _scale("light_side_window", 0.25)
        _scale("light_door_daylight", 0.3)
    else:
        raise SystemExit(f"unknown lighting preset {preset!r}")


def haze_volume(front_x, back_x):
    """Thin, forward-scattering dust in the nave, so the shafts are visible."""
    bpy.ops.mesh.primitive_cube_add(
        location=((front_x + back_x) / 2.0, 0.0, CEILING_Z / 2.0 - 0.1))
    cube = bpy.context.active_object
    cube.name = "haze_volume"
    cube.scale = ((back_x - front_x) / 2.0 - 0.05, HALF_LENGTH - 0.1,
                  CEILING_Z / 2.0 - 0.05)
    material = bpy.data.materials.new("haze")
    material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()
    volume = tree.nodes.new("ShaderNodeVolumePrincipled")
    volume.inputs["Density"].default_value = 0.045
    volume.inputs["Anisotropy"].default_value = 0.55
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    tree.links.new(volume.outputs["Volume"], out.inputs["Volume"])
    cube.data.materials.append(material)
    cube.display_type = "WIRE"


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(prog=ASSET_ID)
    parser.add_argument("--blend", type=Path,
                        default=kit.ENVIRONMENT_DIR / f"{ASSET_ID}.blend")
    parser.add_argument("--force", action="store_true",
                        help="overwrite the source .blend, DISCARDING any "
                             "hand-authoring in it")
    parser.add_argument("--lighting", choices=("neutral", "shafts", "vigil"),
                        default="neutral")
    parser.add_argument("--haze", action="store_true")
    args = parser.parse_args(argv)

    room = build(args.lighting, args.haze)
    bpy.context.view_layer.update()
    blend = kit.save_source_blend(args.blend, force=args.force)
    kit.report(room, blend)


if __name__ == "__main__":
    main()
