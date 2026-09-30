"""Companion area lights for emissive surfaces, so EEVEE lights a room the way a glowing surface should.

In Cycles an emissive mesh is a light: a window pane, a forge's embers or a glowing doorway
reveal light the walls around them. EEVEE draws the glow but does not cast it. A baked light
probe volume does pick emission up (`capture_emission`), but measured on a sealed white room it
returns about a quarter of what Cycles does, and raytracing returns none. A real area light
returns 78-85% of Cycles with the same probe volume bouncing it, and it is the lighting an
artist would author by hand.

So, at render time and never in the source document, each emissive patch that faces into the room
gets a rectangular area light on it:

    watts = pi x emission strength x emitting area        (a Lambertian emitter's flux)
    colour = the material's emission colour               (radiance is colour x strength)

The pi was measured, not assumed: against Cycles with bounces off, an area light of that power
matches to 3-12% on 0.6 m and 1.6 m emitters. Every companion gets an explicit cut-off distance,
because EEVEE's `light_threshold` otherwise gives a dim, small light a short reach and the far
floor goes dark (measured: a 23 W companion lit the floor at a third of its real level).

Run this after the lamp scale and the window emission scale, which it reads, and before the probe
volume bakes, so the bake sees the companions. Turn the probe's `capture_emission` off when
companions exist, or the same glow is counted twice.

Blender-side: import it from a script run with `blender --python`.
"""
from __future__ import annotations

import math

import bpy
from mathutils import Matrix, Vector

FLUX_PER_STRENGTH_AREA = math.pi
GROUP_COSINE = math.cos(math.radians(20.0))
OFFSET = 0.01
CUTOFF_DISTANCE = 30.0
MIN_WATTS = 0.5
LIGHT_PREFIX = "SR_EMIT_"


def emission(material):
    """(strength, (r, g, b)) of a constant emission, or None for a material that does not glow."""
    if material is None or not material.use_nodes:
        return None
    for node in material.node_tree.nodes:
        if node.type == "BSDF_PRINCIPLED":
            strength, colour = node.inputs["Emission Strength"], node.inputs["Emission Color"]
        elif node.type == "EMISSION":
            strength, colour = node.inputs["Strength"], node.inputs["Color"]
        else:
            continue
        if strength.is_linked or colour.is_linked:
            continue
        rgb = tuple(float(v) for v in colour.default_value[:3])
        if strength.default_value > 0.0 and max(rgb) > 0.0:
            return float(strength.default_value), rgb
    return None


def _polygon_area(points) -> float:
    total = Vector((0.0, 0.0, 0.0))
    for i in range(len(points)):
        total += points[i].cross(points[(i + 1) % len(points)])
    return 0.5 * total.length


def room_centre(scene, emitters) -> Vector:
    """The middle of everything that is not an emitter: which side of a face is 'into the room'."""
    corners = [obj.matrix_world @ Vector(c) for obj in scene.objects
               if obj.type == "MESH" and obj not in emitters for c in obj.bound_box]
    if not corners:
        raise ValueError("no non-emissive mesh to take the room's centre from")
    low, high = Vector(map(min, zip(*corners))), Vector(map(max, zip(*corners)))
    return (low + high) / 2.0


def _faces(obj):
    """Per emissive material slot: [(world normal, world centre, world area, world verts)]."""
    mesh = obj.data
    world = obj.matrix_world
    rotation = world.to_3x3().inverted().transposed()
    glowing = {i: emission(slot.material) for i, slot in enumerate(obj.material_slots)}
    found: dict[int, list] = {}
    for poly in mesh.polygons:
        glow = glowing.get(poly.material_index)
        if glow is None:
            continue
        verts = [world @ mesh.vertices[v].co for v in poly.vertices]
        normal = (rotation @ poly.normal).normalized()
        found.setdefault(poly.material_index, []).append(
            (normal, sum(verts, Vector()) / len(verts), _polygon_area(verts), verts))
    return found, glowing


def _groups(faces):
    """Faces facing the same way, greedily: one rectangle of light per group."""
    groups: list[dict] = []
    for face in faces:
        normal = face[0]
        for group in groups:
            if group["normal"].dot(normal) >= GROUP_COSINE:
                group["faces"].append(face)
                total = sum((f[0] * f[2] for f in group["faces"]), Vector())
                group["normal"] = total.normalized() if total.length > 0 else group["normal"]
                break
        else:
            groups.append({"normal": normal.copy(), "faces": [face]})
    return groups


def _rectangle(normal: Vector, verts) -> tuple[Vector, Vector, Vector, float, float]:
    """(centre, u, v, size_u, size_v): the bounding rectangle of `verts` in the plane of `normal`."""
    up = Vector((0.0, 0.0, 1.0)) if abs(normal.z) < 0.9 else Vector((1.0, 0.0, 0.0))
    u = up.cross(normal).normalized()
    v = normal.cross(u).normalized()
    mean = sum(verts, Vector()) / len(verts)
    us = [(p - mean).dot(u) for p in verts]
    vs = [(p - mean).dot(v) for p in verts]
    centre = mean + u * ((max(us) + min(us)) / 2.0) + v * ((max(vs) + min(vs)) / 2.0)
    return centre, u, v, max(us) - min(us), max(vs) - min(vs)


def add_companion_lights(scene, exclude=(), min_watts: float = MIN_WATTS, gain: float = 1.0,
                         ignore=()) -> dict:
    """One rectangular area light per room-facing emissive patch. `exclude` names materials to skip.

    `ignore` lists objects that carry the same emissive faces as others (the atlas study's joined room
    mesh, which is made of the source meshes) so the glow is not lit twice.

    Returns a report: the lights added, in watts, and what was left out and why.
    """
    emitters = [obj for obj in scene.objects if obj.type == "MESH" and not obj.hide_render
                and obj not in ignore and any(emission(s.material) is not None for s in obj.material_slots)]
    if not emitters:
        return {"lights": [], "skipped": []}
    centre = room_centre(scene, set(emitters))
    added, skipped = [], []
    for obj in emitters:
        by_slot, glowing = _faces(obj)
        for slot, faces in by_slot.items():
            material = obj.material_slots[slot].material
            if material.name in exclude:
                skipped.append({"object": obj.name, "material": material.name, "why": "excluded"})
                continue
            strength, colour = glowing[slot]
            facing = [f for f in faces if f[0].dot(centre - f[1]) > 0.0]
            for number, group in enumerate(_groups(facing)):
                area = sum(f[2] for f in group["faces"])
                watts = FLUX_PER_STRENGTH_AREA * strength * area * gain
                name = f"{LIGHT_PREFIX}{obj.name}_{material.name}_{number}"
                if watts < min_watts:
                    skipped.append({"object": obj.name, "material": material.name,
                                    "why": f"{watts:.2f} W is under {min_watts:g} W"})
                    continue
                normal = group["normal"]
                verts = [p for f in group["faces"] for p in f[3]]
                middle, u, v, size_u, size_v = _rectangle(normal, verts)
                light = bpy.data.lights.new(name, "AREA")
                light.shape = "RECTANGLE"
                light.size, light.size_y = max(size_u, 0.02), max(size_v, 0.02)
                light.color = colour
                light.energy = watts
                light.use_custom_distance = True
                light.cutoff_distance = CUTOFF_DISTANCE
                holder = bpy.data.objects.new(name, light)
                holder["sr_companion_of"] = obj.name
                scene.collection.objects.link(holder)
                # A light shines along its own -Z, and its X and Y are the rectangle's sides.
                holder.matrix_world = Matrix.Translation(middle + normal * OFFSET) @ \
                    Matrix((u, -v, -normal)).transposed().to_4x4()
                added.append({"light": name, "watts": round(watts, 2), "areaM2": round(area, 4),
                              "strength": round(strength, 3), "sizeM": [round(light.size, 3), round(light.size_y, 3)]})
    return {"lights": added, "skipped": skipped, "roomCentre": [round(c, 3) for c in centre]}
