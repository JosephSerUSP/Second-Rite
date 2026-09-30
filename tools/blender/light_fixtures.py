"""Let a lamp shine out of a fixture smaller than itself: the housing stops shadowing its light.

The corridor's wall lanterns are a 12 W point light, 0.14 m in radius, at the middle of an opaque
0.09 m flame box inside a 0.16 m cage. Cycles lights the wall around them: the light's sphere is
larger than the housing, so most of it is outside. EEVEE treats the light as a point and the housing
as a closed box around it, so the whole lantern is shadowed and the wall stays dark: the lantern
reads as an unlit silhouette. Measured on the corridor plate, the wall beside the lantern is 17 lit
in EEVEE and 28 in Cycles; with the housing's shadow off it is 34. (A light that is not inside
anything is unaffected, which is why the same scene lit fine everywhere else.)

Only a housing SMALLER than the light is released: half its longest side under the light's radius,
so the sphere pokes out all round, which is when Cycles lets the glow out. The shops' lanterns are
0.27 x 0.16 x 0.32 m around the same 0.14 m light; Cycles shades those too (their plates show a dim
lantern and no halo), and releasing them made EEVEE blaze where Cycles does not, so they are left
alone and the plates agree.

At render time only, never in the source document: each such mesh gets Ray Visibility > Shadow
switched off. It still draws; it just no longer darkens what its lamp lights.

Blender-side: import it from a script run with `blender --python`.
"""
from __future__ import annotations

import bpy
from mathutils import Vector

MAX_FIXTURE_SIZE = 0.6          # metres; a fixture is small, a wall or a table is not


def _bounds(obj):
    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    return Vector(map(min, zip(*corners))), Vector(map(max, zip(*corners)))


def release_fixture_lights(scene, max_size: float = MAX_FIXTURE_SIZE) -> dict:
    """Switch off shadow casting on every small mesh around a light. Returns what was released."""
    meshes = [o for o in scene.objects if o.type == "MESH" and not o.hide_render
              and max(o.dimensions) <= max_size]
    released: dict[str, list[str]] = {}
    # Point and spot lamps are the ones set inside fixtures; an area light is a window or a panel.
    for light in (o for o in scene.objects if o.type == "LIGHT" and o.data.type in ("POINT", "SPOT")):
        centre = light.matrix_world.translation
        margin = float(getattr(light.data, "shadow_soft_size", 0.0))
        for mesh in meshes:
            low, high = _bounds(mesh)
            smaller_than_the_light = max(high - low) / 2.0 < margin
            if smaller_than_the_light and all(low[i] - margin <= centre[i] <= high[i] + margin for i in range(3)):
                mesh.visible_shadow = False
                released.setdefault(light.name, []).append(mesh.name)
    return {"released": released, "maxFixtureSize": max_size}
