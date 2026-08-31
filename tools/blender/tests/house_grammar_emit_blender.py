"""In-Blender probe for the house grammar's Blender emitter.

Prints one `PROBE {json}` line that `test_house_grammar_emit.py` asserts
against, so the whole emitter suite costs one Blender spawn.

The records here are hand-built with `MeshBuilder` rather than taken from
`house_grammar.build`, because the emitter is coupled to the record contract
and not to the builders that happen to produce records today.
"""

import json
import sys
import traceback
from dataclasses import replace
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "blender"))

from recipes.house_grammar.records import MeshBuilder, ModifierSpec  # noqa: E402
from recipes.house_grammar import emit_blender, library, staging  # noqa: E402
from recipes.house_grammar.recipe import build  # noqa: E402


class StubExterior:
    """Only the lane conversion the emitter is allowed to use.

    Deliberately does NOT supply `material`/`emissive`, so the probe exercises
    the library fallback -- the path a study without an Exterior takes.
    """

    def __init__(self, lane_centre):
        self.lane_centre = float(lane_centre)

    def y(self, lane_y):
        return self.lane_centre - float(lane_y)


def body_record():
    builder = MeshBuilder("body")
    builder.add_box_sided((0.0, -2.0, 0.0), (4.0, 2.0, 3.0),
                          {"-x": "whitewash"}, default="rough_limestone")
    return builder.record("body")


def roof_record():
    builder = MeshBuilder("roof")
    builder.add_box((-0.3, -2.3, 3.0), (4.3, 0.0, 3.4), "roof_tile")
    return builder.record("roof", origin=(0.0, 0.0, 3.0),
                          modifiers=(ModifierSpec("MIRROR", axes=("Y",)),))


def window_record():
    builder = MeshBuilder("window")
    builder.add_box((-0.06, -0.5, 1.1), (0.0, 0.5, 2.2), "smoked_glass")
    builder.add_box((-0.16, -0.62, 1.0), (-0.06, 0.62, 1.1), "dark_wood")
    return builder.record("window:w0", origin=(0.0, 1.4, 0.0),
                          metadata={"lit": True})


def world_bounds(obj):
    """Scene-frame AABB of an emitted object, in the frame `staging.place`
    predicts in: parent offset included, no modifiers evaluated."""
    # Parent transforms are evaluated lazily, and a stale matrix_world silently
    # drops the root's lane position out of the comparison.
    bpy.context.view_layer.update()
    matrix = obj.matrix_world
    points = [matrix @ vertex.co for vertex in obj.data.vertices]
    axes = list(zip(*[tuple(point) for point in points]))
    return ([round(min(axis), 6) for axis in axes],
            [round(max(axis), 6) for axis in axes])


def predicted_bounds(record, *, back_x, lane_y, lane_centre):
    low, high = staging.place(record, back_x=back_x, lane_y=lane_y,
                              lane_centre=lane_centre)
    return ([round(value, 6) for value in low],
            [round(value, 6) for value in high])


def polygon_semantics(obj):
    return [obj.data.materials[polygon.material_index].name
            for polygon in obj.data.polygons]


def normals_point_outward(obj):
    """Every face normal leans away from the centroid.

    Only meaningful for a single convex box, which is why the multi-member
    window assembly is not measured this way.
    """
    mesh = obj.data
    centre = Vector((0.0, 0.0, 0.0))
    for vertex in mesh.vertices:
        centre += vertex.co
    centre /= len(mesh.vertices)
    return all((polygon.center - centre).dot(polygon.normal) > 0.0
               for polygon in mesh.polygons)


def outward_by_volume(obj):
    """Signed volume of a closed mesh, positive when normals face out.

    The convex centroid test cannot judge a multi-member assembly like the real
    body, and the flip is exactly the kind of bug that only shows on one.
    """
    mesh = obj.data
    total = 0.0
    for polygon in mesh.polygons:
        indices = list(polygon.vertices)
        a = mesh.vertices[indices[0]].co
        for first, second in zip(indices[1:-1], indices[2:]):
            b = mesh.vertices[first].co
            c = mesh.vertices[second].co
            total += a.dot(b.cross(c)) / 6.0
    return total > 0.0


def object_count(collection):
    return len(collection.objects)


def clear_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def capture(callback):
    try:
        callback()
    except Exception as exc:
        return {"raised": True, "message": str(exc)}
    return {"raised": False, "message": ""}


def main():
    out = {}
    collection = bpy.context.scene.collection
    clear_scene()

    records = [body_record(), roof_record(), window_record()]
    exterior = StubExterior(lane_centre=10.0)
    result = emit_blender.emit(records, name="HOUSE", collection=collection,
                               lane_y=3.0, exterior=exterior)

    root = result["root"]
    out["objects"] = list(result["objects"])
    out["rootName"] = root.name
    out["rootY"] = round(root.location.y, 6)
    out["baselineRoles"] = sorted(result["baseline"])
    out["provenance"] = {
        "recipe": root["th_house_recipe"],
        "version": root["th_house_version"],
        "params": json.loads(root["th_house_params"]),
        "baseline": json.loads(root["th_house_baseline"]),
    }

    children = {}
    for record in records:
        name = emit_blender.object_name("STUDY_", "HOUSE", record.role)
        obj = bpy.data.objects[name]
        children[record.role] = {
            "name": name,
            "parent": obj.parent.name if obj.parent else None,
            "scale": [round(value, 6) for value in obj.scale],
            "rotation": [round(value, 6) for value in obj.rotation_euler],
            "location": [round(value, 6) for value in obj.location],
            "origin": [round(value, 6) for value in record.origin],
            "parentInverseIdentity": obj.matrix_parent_inverse == obj.matrix_parent_inverse.Identity(4),
            "vertexCount": len(obj.data.vertices),
            "faceCount": len(obj.data.polygons),
            "polygonSemantics": polygon_semantics(obj),
            "recordSemantics": ["sr_" + semantic
                                for semantic in record.face_materials],
            # The window is two boxes, so the convex test does not apply.
            "normalsOutward": (normals_point_outward(obj)
                               if record.role in ("body", "roof") else None),
            "modifiers": [{"type": modifier.type,
                           "axes": [axis for axis, on
                                    in zip("XYZ", modifier.use_axis) if on]}
                          for modifier in obj.modifiers],
        }
    out["children"] = children
    # The lit window swaps only its glass, and only for a `lit` record.
    out["litWindowSemantics"] = sorted(set(children["window:w0"]["polygonSemantics"]))

    # An inverted winding must come back outward, or the recalc is a no-op that
    # nothing would notice until the roof rendered inside out.
    flipped = replace(body_record(), faces=tuple(
        tuple(reversed(face)) for face in body_record().faces))
    inverted = emit_blender.emit([flipped], name="FLIP", collection=collection,
                                 lane_y=0.0, namespace="PROBE_")
    out["invertedNormalsFixed"] = normals_point_outward(
        bpy.data.objects[inverted["objects"][1]])

    # -- staging agreement -------------------------------------------------
    # The body and roof above are symmetric in Y and hide a sign error
    # completely, which is how the local-Y flip survived the first suite. This
    # record is deliberately asymmetric about the lane centre.
    lopsided = MeshBuilder("lopsided")
    lopsided.add_box((0.0, 0.0, 0.0), (1.0, 3.0, 2.0), "whitewash")
    lopsided_record = lopsided.record("body", origin=(0.0, 0.5, 0.0))
    sided = emit_blender.emit([lopsided_record], name="SIDED",
                              collection=collection, lane_y=3.0,
                              exterior=exterior, namespace="PROBE_")
    sided_obj = bpy.data.objects[sided["objects"][1]]
    out["asymmetricEmitted"] = world_bounds(sided_obj)
    # back_x = 0: emit() puts the root on the lane and leaves the terrace
    # depth to the caller, so the prediction is compared at the same X origin.
    out["asymmetricPredicted"] = predicted_bounds(
        lopsided_record, back_x=0.0, lane_y=3.0, lane_centre=10.0)
    out["asymmetricNormalsOutward"] = normals_point_outward(sided_obj)

    # The real building: only the off-centre front door can see the bug.
    recipe = library.narrow_townhouse()
    house = emit_blender.emit(build(recipe), name=recipe.id,
                              collection=collection, lane_y=4.0,
                              exterior=exterior, namespace="REAL_",
                              recipe=recipe)
    door_record = next(record for record in build(recipe)
                       if record.role == "door:front_door")
    door_obj = bpy.data.objects[emit_blender.object_name(
        "REAL_", recipe.id, "door:front_door")]
    out["doorEmitted"] = world_bounds(door_obj)
    out["doorPredicted"] = predicted_bounds(door_record, back_x=0.0,
                                            lane_y=4.0, lane_centre=10.0)
    out["realProvenance"] = {
        "recipe": house["root"]["th_house_recipe"],
        "version": house["root"]["th_house_version"],
        "params": json.loads(house["root"]["th_house_params"]),
    }
    out["realNormalsOutward"] = outward_by_volume(
        bpy.data.objects[emit_blender.object_name("REAL_", recipe.id, "body")])

    # -- collision ---------------------------------------------------------
    out["collision"] = capture(lambda: emit_blender.emit(
        records, name="HOUSE", collection=collection, lane_y=3.0,
        exterior=exterior))
    out["collisionLeftCount"] = object_count(collection)
    # Counted, not hard-coded: the point of the assertion is that the refused
    # emission added nothing, not how many objects the probe made before it.
    out["collisionLeftExpected"] = (4 + 2 + 2 + len(house["objects"]))

    # -- diff --------------------------------------------------------------
    out["diffIdentical"] = emit_blender.diff(root, [body_record(),
                                                    roof_record(),
                                                    window_record()])
    moved = body_record()
    moved.vertices = tuple((x, y, z + 0.4) if index == 0 else (x, y, z)
                           for index, (x, y, z) in enumerate(moved.vertices))
    out["diffMoved"] = emit_blender.diff(root, [moved, roof_record(),
                                                window_record()])

    grown = MeshBuilder("body")
    grown.add_box_sided((0.0, -2.0, 0.0), (4.0, 2.0, 3.6),
                        {"-x": "whitewash"}, default="rough_limestone")
    grown.add_box((0.0, -2.0, 3.6), (4.0, 2.0, 3.9), "old_limestone")
    out["diffGrown"] = emit_blender.diff(root, [grown.record("body"),
                                                roof_record()])

    # A hand-scaled object must show up as unclean, or the report is blind to
    # exactly the edit it exists to protect.
    bpy.data.objects[children["body"]["name"]].scale = (1.0, 1.2, 1.0)
    out["diffAfterHandScale"] = emit_blender.diff(root, [moved])["body"]

    # -- atomic rollback ---------------------------------------------------
    clear_scene()
    malformed = replace(body_record(), face_materials=tuple(
        7 for _ in body_record().faces))
    out["rollback"] = capture(lambda: emit_blender.emit(
        [roof_record(), malformed], name="BAD", collection=collection,
        lane_y=0.0, exterior=exterior))
    out["rollbackLeftCount"] = object_count(collection)
    out["rollbackLeftNames"] = [obj.name for obj in collection.objects]

    # Without an Exterior the caller is already in Blender Y.
    clear_scene()
    plain = emit_blender.emit([body_record()], name="PLAIN",
                              collection=collection, lane_y=2.5)
    out["plainRootY"] = round(plain["root"].location.y, 6)
    out["savedNothing"] = not bpy.data.is_saved

    print("PROBE " + json.dumps(out, sort_keys=True))
    sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.stdout.flush()
        raise SystemExit(1)
