"""Shared, adjustable exterior door and window families.

Families keep silhouette and opening geometry while letting the receiver carry
fine joinery through the bake.  ``host.part`` is the one Blender emission seam;
the candidate courtyard and the measured Exterior vocabulary use this same
family builder.
"""


def door(host, name, lane_y, *, width=1.15, height=2.25, x=None,
         lintel=True, panels=0, frame=0.18, panel_material=None,
         source=False):
    base_x = host.back_x if x is None else float(x)
    cy = host.y(lane_y)
    objs = []

    def part(suffix, size, location, material):
        obj = host.part(f"{name}_{suffix}", size, location, material)
        if source:
            obj["sr_bake_role"] = "source"
        objs.append(obj)
        return obj

    part("leaf", (0.12, width, height),
         (base_x - 0.015, cy, height / 2), host.wood)
    for side, tag in ((-1, "l"), (1, "r")):
        part(f"jamb_{tag}", (0.16, frame, height + 0.18),
             (base_x - 0.12, cy + side * (width / 2 + frame / 2),
              (height + 0.18) / 2), host.stone)
    part("threshold", (0.52, width + 0.42, 0.16),
         (base_x - 0.22, cy, 0.08), host.stone)
    if lintel:
        part("lintel", (0.26, width + 0.5, 0.24),
             (base_x - 0.16, cy, height + 0.12), host.stone)
        part("drip", (0.34, width + 0.68, 0.10),
             (base_x - 0.21, cy, height + 0.29), host.terracotta)
    # Panel count changes detail density without changing the reusable leaf.
    count = int(panels)
    for index in range(count):
        z = height * (0.22 + 0.56 * (index + 0.5) / count)
        panel_h = height * 0.44 / count
        panel_w = width * 0.56
        panel = part(f"panel_{index + 1}", (0.035, panel_w, panel_h),
                     (base_x - 0.09, cy, z), panel_material or host.wood)
        panel["sr_bake_detail"] = True
    return objs


def window(host, name, lane_y, *, width=0.95, height=1.25, sill_z=1.15,
           x=None, shutters=True, grille=False, lit=False, frame=0.14,
           source=False):
    base_x = host.back_x if x is None else float(x)
    cy = host.y(lane_y)
    pane_material = host.window_glow if lit else host.glass
    objs = []

    def part(suffix, size, location, material):
        obj = host.part(f"{name}_{suffix}", size, location, material)
        if source:
            obj["sr_bake_role"] = "source"
        objs.append(obj)
        return obj

    part("pane", (0.08, width, height),
         (base_x - 0.015, cy, sill_z + height / 2), pane_material)
    for side, tag in ((-1, "l"), (1, "r")):
        part(f"jamb_{tag}", (0.16, frame, height + 0.22),
             (base_x - 0.10, cy + side * (width / 2 + frame / 2),
              sill_z + height / 2), host.stone)
    part("head", (0.18, width + 0.42, 0.16),
         (base_x - 0.11, cy, sill_z + height + 0.11), host.stone)
    part("sill", (0.38, width + 0.46, 0.14),
         (base_x - 0.16, cy, sill_z - 0.07), host.stone)
    part("mullion", (0.08, 0.07, height),
         (base_x - 0.08, cy, sill_z + height / 2), host.wood)
    part("frame_top", (0.10, width, 0.08),
         (base_x - 0.08, cy, sill_z + height - 0.04), host.wood)
    part("frame_bottom", (0.10, width, 0.08),
         (base_x - 0.08, cy, sill_z + 0.04), host.wood)
    if shutters:
        for side, tag in ((-1, "l"), (1, "r")):
            part(f"shutter_{tag}", (0.08, width * 0.52, height),
                 (base_x - 0.16, cy + side * (width * 0.76),
                  sill_z + height / 2), host.wood)
    if grille:
        part("grille", (0.06, width + 0.1, height + 0.1),
             (base_x - 0.20, cy, sill_z + height / 2), host.iron)
    return objs
