"""Batch B refinement layer: organic deformation instead of flat repetition.

The first Blender-native pass proved that asymmetry/negative space were useful,
but visual review exposed two failures: Mimic Tongue read as a forked plaque and
Phoenix Pinion as a comb. This layer deliberately fixes those with *sectional
shape change*: variable-width/variable-thickness ribbons for flesh and pointed,
overlapping, individually tilted vanes for the feather.

It imports the original found-object recipe so the four successful models remain
byte-for-byte governed by the same source, replaces only the two failed builders,
and then exports the complete cohort through the same shared Blender asset core.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "found_object_base", HERE / "build_found_object_showcase.py"
)
base = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(base)

# The semantic registry does not currently contain flesh. Treating a tongue as
# green wet residue made the geometry harder to read, so this item-specific
# surface stays explicitly legacy-derived rather than pretending to be a shared
# semantic material.
base.MAT["mimic_flesh"] = base.asset_core.make_material(
    "mimic_flesh", color=(0.36, 0.12, 0.14), metallic=0.0,
    roughness=0.74, scope="legacy_derived",
)
base.MAT["mimic_inner"] = base.asset_core.make_material(
    "mimic_inner", color=(0.56, 0.24, 0.24), metallic=0.0,
    roughness=0.68, scope="legacy_derived",
)


def add_section_ribbon(parent, name, sections, material, *, bevel=0.035):
    """A bent fleshy strip with width, thickness and depth changing per section.

    Each section is ``(x, z, half_width, thickness, y_center)``. Cross-sections
    stay perpendicular to the local XZ tangent while the Y centre can curl out
    of plane. Unlike a flat extruded polygon this gives deformation to the
    *volume itself*, not merely to its outline.
    """
    if len(sections) < 2:
        raise ValueError("section ribbon needs two or more sections")

    verts = []
    for index, (x, z, half_width, thickness, y_center) in enumerate(sections):
        before = sections[max(0, index - 1)]
        after = sections[min(len(sections) - 1, index + 1)]
        dx, dz = after[0] - before[0], after[1] - before[1]
        length = math.hypot(dx, dz)
        if length <= 1e-6:
            raise ValueError(f"{name}: collapsed section tangent at {index}")
        px, pz = -dz / length, dx / length
        lx, lz = x + px * half_width, z + pz * half_width
        rx, rz = x - px * half_width, z - pz * half_width
        yf, yb = y_center - thickness / 2, y_center + thickness / 2
        verts.extend([
            (lx, yf, lz), (rx, yf, rz),
            (lx, yb, lz), (rx, yb, rz),
        ])

    faces = []
    for i in range(len(sections) - 1):
        a, b = i * 4, (i + 1) * 4
        faces.extend([
            (a + 0, b + 0, b + 1, a + 1),  # front
            (a + 2, a + 3, b + 3, b + 2),  # back
            (a + 0, a + 2, b + 2, b + 0),  # left edge
            (a + 1, b + 1, b + 3, a + 3),  # right edge
        ])
    faces.append((0, 1, 3, 2))
    end = (len(sections) - 1) * 4
    faces.append((end + 0, end + 2, end + 3, end + 1))

    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    base.COLLECTION.objects.link(obj)
    return base.finish_mesh(obj, parent, material, bevel=bevel)


def add_pointed_vane(parent, name, inner, outer, half_width, depth, material, *,
                     y=0.0, tilt=0.0):
    """A feather vane with a narrow root, broad belly and true pointed tip."""
    ix, iz = inner
    ox, oz = outer
    dx, dz = ox - ix, oz - iz
    length = math.hypot(dx, dz)
    if length <= 1e-6:
        raise ValueError(f"{name}: zero-length vane")
    ux, uz = dx / length, dz / length
    px, pz = -uz, ux
    mx, mz = ix + ux * length * 0.58, iz + uz * length * 0.58
    outline = [
        (ix + px * half_width * 0.22, iz + pz * half_width * 0.22),
        (mx + px * half_width, mz + pz * half_width),
        (ox, oz),
        (mx - px * half_width * 0.82, mz - pz * half_width * 0.82),
        (ix - px * half_width * 0.22, iz - pz * half_width * 0.22),
    ]
    obj = base.add_prism(
        parent, name, outline, depth, material,
        loc=(0, y, 0), bevel=0.025,
    )
    obj.rotation_euler.x += math.radians(tilt)
    return obj


def build_mimic_tongue_v2():
    r = base.root(
        "Mimic Tongue", "mimic_tongue",
        "A severed mimic tongue whose thick body curls into two mismatched living forks.",
    )

    body = [
        (-0.05, -1.02, 0.52, 0.30, 0.03),
        (-0.10, -0.72, 0.55, 0.33, 0.00),
        (-0.04, -0.39, 0.50, 0.31, -0.05),
        ( 0.06, -0.05, 0.43, 0.28, -0.10),
        ( 0.12,  0.25, 0.34, 0.24, -0.09),
        ( 0.08,  0.51, 0.24, 0.20, -0.02),
        ( 0.03,  0.65, 0.19, 0.18, 0.04),
    ]
    add_section_ribbon(r, "TongueBody", body, "mimic_flesh", bevel=0.075)

    # Both forks continue the same volume but disagree in length, curl and
    # depth. They overlap the trunk at the root rather than joining as two flat
    # plaques pasted onto its end.
    left = [
        (0.00, 0.56, 0.20, 0.18, 0.01),
        (-0.18, 0.78, 0.17, 0.16, -0.03),
        (-0.42, 1.02, 0.12, 0.12, -0.12),
        (-0.70, 1.23, 0.055, 0.07, -0.23),
        (-0.87, 1.32, 0.018, 0.035, -0.29),
    ]
    right = [
        (0.08, 0.56, 0.18, 0.17, 0.04),
        (0.24, 0.75, 0.15, 0.14, 0.11),
        (0.42, 0.91, 0.10, 0.10, 0.20),
        (0.58, 1.02, 0.025, 0.045, 0.29),
    ]
    add_section_ribbon(r, "LongFork", left, "mimic_flesh", bevel=0.055)
    add_section_ribbon(r, "ShortFork", right, "mimic_inner", bevel=0.05)

    # A raised central mucosal seam makes the topography visible even at the
    # small item-view size and prevents the broad body reading as a signboard.
    base.add_tube(
        r, "MucosalSeam",
        [(-0.04, -0.165, -0.78), (0.00, -0.19, -0.40),
         (0.07, -0.20, -0.05), (0.09, -0.16, 0.30),
         (0.04, -0.08, 0.58)],
        0.027, "mimic_inner",
    )

    papillae = [
        (-0.30, -0.18, -0.69, .060), (0.29, -0.19, -0.58, .052),
        (-0.36, -0.18, -0.34, .055), (0.31, -0.18, -0.22, .047),
        (-0.27, -0.17,  0.02, .050), (0.25, -0.16,  0.15, .044),
        (-0.17, -0.12,  0.36, .043),
    ]
    for i, (x, y, z, s) in enumerate(papillae):
        base.add_ico(r, f"Papilla{i}", (x, y, z),
                     (s, s * .55, s * 1.15), "mimic_inner")

    base.add_tube(
        r, "SalivaThread",
        [(0.40, 0.17, 0.88), (0.48, 0.28, 0.62), (0.44, 0.34, 0.35)],
        0.014, "crystal",
    )
    return r


def build_phoenix_pinion_v2():
    r = base.root(
        "Phoenix Pinion", "phoenix_pinion",
        "A broad singed pinion with overlapping pointed vanes and one conspicuous missing bite.",
    )

    shaft = [
        (-0.38, 0.02, -1.08), (-0.30, 0.00, -0.72),
        (-0.20, -0.01, -0.34), (-0.08, 0.01, 0.05),
        (0.02, 0.02, 0.43), (0.10, 0.02, 0.78), (0.13, 0.01, 1.10),
    ]
    radii = [0.095, 0.088, 0.078, 0.067, 0.056, 0.045, 0.028]
    for i in range(len(shaft) - 1):
        base.add_cone_between(
            r, f"Quill{i}", shaft[i], shaft[i + 1],
            radii[i], radii[i + 1], "bone", vertices=7,
        )

    left = [
        ((-0.31,-0.76), (-0.83,-0.94), .13, -11),
        ((-0.27,-0.57), (-1.00,-0.70), .15,  -7),
        ((-0.22,-0.37), (-1.12,-0.39), .16,  -3),
        ((-0.16,-0.15), (-1.15,-0.02), .17,   2),
        ((-0.09, 0.08), (-1.08, 0.34), .16,   6),
        ((-0.03, 0.31), (-0.91, 0.65), .15,  10),
        (( 0.03, 0.53), (-0.69, 0.87), .13,  13),
        (( 0.08, 0.73), (-0.43, 1.02), .10,  16),
    ]
    right = [
        ((-0.30,-0.70), (0.49,-0.91), .12,  8),
        ((-0.25,-0.49), (0.69,-0.63), .15,  5),
        ((-0.19,-0.27), (0.82,-0.30), .16,  1),
        # deliberate missing vane around the middle of the trailing edge
        ((-0.06, 0.18), (0.88, 0.31), .15, -6),
        (( 0.00, 0.40), (0.79, 0.57), .14, -10),
        (( 0.06, 0.61), (0.63, 0.80), .12, -14),
        (( 0.10, 0.79), (0.42, 0.98), .09, -17),
    ]
    for i, (inner, outer, width, tilt) in enumerate(left):
        add_pointed_vane(
            r, f"LeftVane{i}", inner, outer, width,
            0.075 + (i % 2) * 0.012, "wax",
            y=-0.035 - i * 0.007, tilt=tilt,
        )
    for i, (inner, outer, width, tilt) in enumerate(right):
        material = "wrought_iron" if i in (4, 5) else "wax"
        add_pointed_vane(
            r, f"RightVane{i}", inner, outer, width,
            0.072 + ((i + 1) % 2) * 0.012, material,
            y=0.035 + i * 0.007, tilt=tilt,
        )

    # Repair seams follow individual vanes instead of forming another radial
    # emblem. They read as evidence of damage rather than generic ornament.
    for i, (a, b) in enumerate((
        ((-0.17, -0.10), (-0.64, 0.00)),
        ((0.00, 0.38), (0.50, 0.50)),
    )):
        base.add_cylinder_between(
            r, f"GoldScar{i}",
            (a[0], -0.10, a[1]), (b[0], -0.10, b[1]),
            0.016, "ritual_gold", vertices=5,
        )
    return r


base.BUILDERS = (
    base.build_cerberus_fang,
    build_mimic_tongue_v2,
    base.build_forbidden_lamp,
    base.build_pile_bunker,
    base.build_celestial_fossil,
    build_phoenix_pinion_v2,
)

if __name__ == "__main__":
    base.build()
