"""The Blender emitter for the house grammar.

This module is the ONLY part of the package that imports ``bpy``, and it
computes no geometry: it walks the frozen :class:`~house_grammar.records.MeshRecord`
list and turns each record into one object.  If a change here needs a vertex
position, the change belongs in the grammar instead -- that split is what keeps
the grammar unit-testable without a spawned Blender.

Two things are deliberately concentrated here rather than spread out:

* the runtime-lane -> Blender-Y conversion, which goes through ``Exterior.y()``
  exactly once (the determinant -1 basis of issue #935 leaks the moment a
  second caller does its own arithmetic);
* the emissive swap for a lit opening, because emissive materials are
  per-scene and the grammar therefore cannot name one.

The emitter never saves, never applies a modifier, and never touches an object
it did not create in the current call.  Everything the owner has hand-edited is
reported by :func:`diff` and left alone.
"""

from __future__ import annotations

import json

import bmesh
import bpy

# The library datablock naming convention: one material per semantic, shared by
# every recipe in the file.
MATERIAL_PREFIX = "sr_"
# Daylight seen through a window, matching the exterior vocabulary's
# `window_glow`.  Kept here as a fallback so the emitter still works against a
# bare scene with no Exterior instance to borrow from.
LIT_MATERIAL = "sr_window_daylight"
LIT_COLOUR = (0.92, 0.95, 1.0)
# The semantic a lit opening replaces.  Only glass glows; a lit door does not
# turn its timber into a lamp.
LIT_SEMANTIC = "smoked_glass"


def object_name(namespace, name, role):
    # ':' is legal in a role but reads as a library path separator in Blender's
    # own naming, so opening roles flatten to an underscore.
    return "%s%s_%s" % (namespace, name, role.replace(":", "_"))


def root_name(namespace, name):
    return "%s%s_ROOT" % (namespace, name)


def _vocabulary():
    """The exterior vocabulary module, imported lazily.

    Tolerates both import shapes because the recipes directory is on sys.path
    for scripts run inside Blender and a package for everything else.
    """
    try:
        from .. import exterior as module  # noqa: WPS433
    except ImportError:  # pragma: no cover -- flat sys.path inside Blender
        import exterior as module  # noqa: WPS433
    return module


def _material_factory(exterior):
    """The callable that builds a missing ``sr_*`` material.

    Prefers whatever the caller handed in, so a study driving this from an
    Exterior gets that scene's binding, and falls back to importing the
    vocabulary lazily -- importing `exterior` at module scope would drag the
    whole interior toolchain into every emit.
    """
    factory = getattr(exterior, "material", None)
    if callable(factory):
        return factory
    return _vocabulary().material


def _emissive_factory(exterior):
    factory = getattr(exterior, "emissive", None)
    if callable(factory):
        return factory
    return _vocabulary().emissive


def _resolve_material(semantic, record, exterior):
    """One semantic -> one material datablock, reusing the library."""
    if semantic == LIT_SEMANTIC and record.metadata.get("lit"):
        existing = bpy.data.materials.get(LIT_MATERIAL)
        if existing is not None:
            return existing
        return _emissive_factory(exterior)(LIT_MATERIAL, LIT_COLOUR)
    name = MATERIAL_PREFIX + semantic
    existing = bpy.data.materials.get(name)
    if existing is not None:
        return existing
    return _material_factory(exterior)(semantic)


def _install_modifiers(obj, record):
    for spec in record.modifiers:
        if spec.kind != "MIRROR":
            raise ValueError("unsupported modifier kind %r" % (spec.kind,))
        modifier = obj.modifiers.new(name="MIRROR", type="MIRROR")
        # Never applied: a symmetry the recipe still calls intentional has to
        # stay something the owner can switch off in the modifier stack.
        modifier.use_axis = tuple(axis in spec.axes for axis in ("X", "Y", "Z"))
        for field, value in spec.settings.items():
            setattr(modifier, field, value)


def _recalc_outward(mesh):
    scratch = bmesh.new()
    scratch.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(scratch, faces=scratch.faces)
    scratch.to_mesh(mesh)
    scratch.free()
    mesh.update()


def _build_object(record, name, exterior):
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata([tuple(vertex) for vertex in record.vertices], [],
                     [tuple(face) for face in record.faces])
    mesh.update()

    # Deterministic slot order: the diff compares material sets across
    # rebuilds, and a set that depends on face order is not comparable.
    semantics = sorted(set(record.face_materials))
    slots = {}
    for semantic in semantics:
        slots[semantic] = len(mesh.materials)
        mesh.materials.append(_resolve_material(semantic, record, exterior))
    for polygon, semantic in zip(mesh.polygons, record.face_materials):
        polygon.material_index = slots[semantic]

    _recalc_outward(mesh)
    obj = bpy.data.objects.new(name, mesh)
    _install_modifiers(obj, record)
    return obj


def emit(records, *, name, collection, lane_y, exterior=None,
         namespace="STUDY_", recipe=None):
    """Emit one building's records as objects under a single empty root.

    ``recipe`` is optional only so the emitter stays usable against
    hand-constructed records in tests; a real emission passes it, because the
    provenance it writes onto the root is what makes :func:`diff` possible
    later.
    """
    if bpy.context.mode != "OBJECT":
        raise RuntimeError("the house emitter runs in Object Mode only, not %s"
                           % (bpy.context.mode,))

    roles = [record.role for record in records]
    if len(set(roles)) != len(roles):
        raise ValueError("two records share a role: %s" % (sorted(roles),))

    targets = [root_name(namespace, name)]
    targets.extend(object_name(namespace, name, role) for role in roles)
    # Checked up front rather than per object: a collision discovered halfway
    # leaves the owner's file holding half a house.
    clashes = [target for target in targets if target in bpy.data.objects]
    if clashes:
        raise ValueError("objects already exist: %s" % (", ".join(clashes),))

    created = []
    try:
        root = bpy.data.objects.new(targets[0], None)
        collection.objects.link(root)
        created.append(root)
        root.empty_display_type = "PLAIN_AXES"
        # The one place the lane conversion happens.  Without an Exterior there
        # is no lane to convert and the caller is authoring in Blender Y.
        blender_y = exterior.y(lane_y) if exterior is not None else float(lane_y)
        root.location = (0.0, blender_y, 0.0)

        baseline = {}
        object_names = {}
        for record in records:
            child_name = object_name(namespace, name, record.role)
            obj = _build_object(record, child_name, exterior)
            collection.objects.link(obj)
            created.append(obj)
            obj.parent = root
            # An explicit local placement under an explicit parent must not
            # also carry a keep-world inverse: with one, the outliner looks
            # right while the object sits wherever it happened to be created.
            obj.matrix_parent_inverse.identity()
            obj.location = tuple(record.origin)
            obj.rotation_euler = (0.0, 0.0, 0.0)
            obj.scale = (1.0, 1.0, 1.0)
            baseline[record.role] = record.fingerprint()
            object_names[record.role] = child_name

        root["th_house_recipe"] = getattr(recipe, "id", "") or ""
        root["th_house_version"] = int(getattr(recipe, "version", 0) or 0)
        root["th_house_params"] = json.dumps(
            recipe.as_json() if recipe is not None else {}, sort_keys=True)
        root["th_house_baseline"] = json.dumps(baseline, sort_keys=True)
        # Roles are not recoverable from the object names once a namespace is
        # in play, and diff() needs the mapping to find hand-edited objects.
        root["th_house_objects"] = json.dumps(object_names, sort_keys=True)
    except BaseException:
        for obj in reversed(created):
            mesh = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if mesh is not None and mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        raise

    return {"root": root, "objects": [obj.name for obj in created],
            "baseline": baseline}


def _object_semantics(obj):
    return sorted(
        slot.name[len(MATERIAL_PREFIX):] if slot.name.startswith(MATERIAL_PREFIX)
        else slot.name
        for slot in obj.data.materials if slot is not None)


def _object_modifiers(obj):
    summary = []
    for modifier in obj.modifiers:
        entry = {"kind": modifier.type}
        if modifier.type == "MIRROR":
            entry["axes"] = [axis for axis, on
                             in zip(("X", "Y", "Z"), modifier.use_axis) if on]
        summary.append(entry)
    return summary


def _record_modifiers(record):
    return [{"kind": spec.kind, "axes": list(spec.axes)}
            for spec in record.modifiers]


def _transform_is_clean(obj):
    return (all(abs(value - 1.0) < 1e-6 for value in obj.scale)
            and all(abs(value) < 1e-6 for value in obj.rotation_euler))


def diff(root_object, records):
    """Report how freshly built records differ from what the root was emitted with.

    Reports only.  A hand-edited object is a decision the owner made in the
    .blend, and an emitter that quietly re-fitted it would destroy that
    decision with no diff to show for it -- so nothing here writes.
    """
    baseline = json.loads(root_object.get("th_house_baseline") or "{}")
    names = json.loads(root_object.get("th_house_objects") or "{}")
    fresh = {record.role: record for record in records}

    report = {}
    for role in sorted(set(baseline) | set(fresh)):
        if role not in fresh:
            report[role] = {"status": "missing"}
            continue
        if role not in baseline:
            report[role] = {"status": "added"}
            continue
        record = fresh[role]
        if record.fingerprint() == baseline[role]:
            report[role] = {"status": "identical"}
            continue

        entry = {"status": "changed"}
        obj = bpy.data.objects.get(names.get(role, ""))
        if obj is None:
            # The baseline knows the role but the object is gone from the file;
            # that is a deletion, not a geometry change.
            report[role] = {"status": "missing"}
            continue
        entry["vertexDelta"] = len(record.vertices) - len(obj.data.vertices)
        entry["faceDelta"] = len(record.faces) - len(obj.data.polygons)
        current = set(_object_semantics(obj))
        wanted = set(record.face_materials)
        entry["materialsAdded"] = sorted(wanted - current)
        entry["materialsRemoved"] = sorted(current - wanted)
        entry["modifiersWere"] = _object_modifiers(obj)
        entry["modifiersNow"] = _record_modifiers(record)
        entry["modifiersChanged"] = entry["modifiersWere"] != entry["modifiersNow"]
        entry["transformClean"] = _transform_is_clean(obj)
        report[role] = entry
    return report
