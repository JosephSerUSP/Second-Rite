"""Keep a generated source document editable: join repeated pieces, name the groups.

A recipe that places a roof one pantile at a time leaves 600 objects in the outliner
that nobody can select, move or reason about. The geometry is right; the structure is
the problem. `consolidate` fixes the structure only:

  * objects that are the SAME THING repeated (a roof plane's tiles, a window's louvre
    slats, a drainage run) become ONE object per group, named for the group;
  * groups are filed in a collection per building part, so the outliner reads as the
    building, not as a list.

Evaluated geometry is unchanged: modifiers are applied (not discarded) before the join,
and nothing is moved, merged, welded or re-material'd. `geometry_summary` / `summaries_match` prove it.

What counts as the same thing is deliberately narrow: same parent, same name once its
trailing index is removed, same material, same bake properties, visible, not a bake
receiver, and at least `MIN_GROUP` of them. Anything else stays as authored.
"""
from __future__ import annotations

import re
from collections import defaultdict

import bpy
from mathutils import Vector

MIN_GROUP = 4
MIN_ARRAY = 8
_INDEX = re.compile(r"(?:[ ._]\d+)+$")


def family_name(name: str) -> str:
    """'East street tile barrel 0 17' -> 'East street tile barrel 0' (one trailing index)."""
    stripped = re.sub(r"\.\d{3}$", "", name)
    head, _, tail = stripped.rpartition(" ")
    return head if head and tail.isdigit() else stripped


def array_name(name: str) -> str:
    """Strip EVERY trailing index: 'Court drain slot 12 1' -> 'Court drain slot'."""
    return _INDEX.sub("", re.sub(r"\.\d{3}$", "", name))


def _props(obj):
    return tuple(sorted((k, str(obj[k])) for k in obj.keys() if k.startswith(("sr_", "th_"))))


def _groupable(obj):
    if obj.type != "MESH" or obj.hide_render or obj.hide_viewport:
        return False
    if obj.get("sr_bake_role") == "receiver":
        return False
    return len(obj.material_slots) == 1 and obj.active_material is not None


def consolidate(collection):
    """Join repeated pieces inside `collection`. Returns {group name: pieces joined}.

    Two passes. First, pieces that share a name once ONE trailing index is removed
    (a roof plane's tiles: 'East street tile barrel 0 17'), four or more of them.
    Then, pieces that share a name once EVERY trailing index is removed (a grid of
    drain slots: 'Court drain slot 12 1'), eight or more: a larger bar, because
    dropping every index can merge things that were numbered as different parts.
    """
    joined = {}
    for namer, minimum in ((family_name, MIN_GROUP), (array_name, MIN_ARRAY)):
        joined.update(_join_pass(collection, namer, minimum))
    return joined


def _join_pass(collection, namer, minimum):
    groups = defaultdict(list)
    for obj in collection.all_objects:
        if _groupable(obj):
            key = (obj.parent.name if obj.parent else "", namer(obj.name),
                   obj.active_material.name, _props(obj))
            groups[key].append(obj)
    joined = {}
    for (parent, family, _material, _props_key), members in sorted(groups.items()):
        if len(members) < minimum:
            continue
        members.sort(key=lambda o: o.name)
        bpy.ops.object.select_all(action="DESELECT")
        for member in members:
            member.select_set(True)
        active = members[0]
        bpy.context.view_layer.objects.active = active
        # Apply modifiers (bevels) so the join keeps the evaluated shape.
        bpy.ops.object.convert(target="MESH")
        bpy.context.view_layer.objects.active = active
        bpy.ops.object.join()
        active.name = family
        active.data.name = f"{family}_mesh"
        joined[family if not parent else f"{parent} / {family}"] = len(members)
    return joined


def file_by_part(collection, words=2):
    """File every object under a child collection named for its building part."""
    parts = {}
    for obj in list(collection.all_objects):
        label = " ".join(re.sub(r"\.\d{3}$", "", obj.name).split(" ")[:words])
        child = parts.get(label)
        if child is None:
            child = bpy.data.collections.new(label)
            collection.children.link(child)
            parts[label] = child
        for owner in list(obj.users_collection):
            owner.objects.unlink(obj)
        child.objects.link(obj)
    return sorted(parts)


def geometry_summary(collection=None):
    """The evaluated, world-space triangles of a collection, by material.

    {material: [(centroid, area), ...]}. Structure-free: two documents that draw the
    same triangles with the same materials give the same lists up to order, however
    their objects are arranged or joined.
    """
    graph = bpy.context.evaluated_depsgraph_get()
    objects = collection.all_objects if collection else bpy.data.objects
    summary = defaultdict(list)
    for obj in objects:
        if obj.type != "MESH" or obj.hide_render or obj.get("sr_bake_role") == "receiver":
            continue
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        matrix = obj.matrix_world
        world = [matrix @ v.co for v in mesh.vertices]
        for tri in mesh.loop_triangles:
            material = (evaluated.material_slots[tri.material_index].material.name
                        if evaluated.material_slots else "")
            a, b, c = (world[i] for i in tri.vertices)
            summary[material].append(((a + b + c) / 3.0, (b - a).cross(c - a).length / 2.0))
        evaluated.to_mesh_clear()
    return dict(summary)


def summaries_match(before, after, tolerance=1e-3, area_tolerance=1e-5):
    """True when every triangle in `before` has its own partner in `after` and vice versa.

    A partner is a triangle of the same material whose centroid is within `tolerance`
    (1 mm) and whose area agrees. Joining re-expresses vertices in another object's
    space, which adds float noise far below that; a moved, dropped or added triangle is
    caught individually, however small it is next to the whole.
    """
    from mathutils.kdtree import KDTree
    if set(before) != set(after):
        return False
    for material, triangles in before.items():
        others = after[material]
        if len(triangles) != len(others):
            return False
        tree = KDTree(len(others))
        for index, (centroid, _area) in enumerate(others):
            tree.insert(centroid, index)
        tree.balance()
        used = set()
        for centroid, area in triangles:
            partner = next((index for _co, index, _dist in tree.find_range(centroid, tolerance)
                            if index not in used and abs(others[index][1] - area) <= area_tolerance), None)
            if partner is None:
                return False
            used.add(partner)
    return True
