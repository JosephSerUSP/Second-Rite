"""Sampled selected-to-active ray preflight with authored receiver/source bindings.

This is geometric evidence, not an exhaustive texel or visual acceptance claim.
"""
import fnmatch
import json
import math
from pathlib import Path

OWNER_ATTRIBUTE = "sr_bake_receiver_owner"
OWNER_RECORD = "sr_bake_receiver_names"
SOURCE_ATTRIBUTE = "sr_bake_source_owner"
SOURCE_RECORD = "sr_bake_source_names"


def registry(objects):
    return sorted(obj.name for obj in objects if obj.type == "MESH")


def tag(mesh, owner, names):
    attribute = mesh.attributes.get(OWNER_ATTRIBUTE) or mesh.attributes.new(OWNER_ATTRIBUTE, "INT", "FACE")
    attribute.data.foreach_set("value", [names.index(owner)] * len(mesh.polygons))


def validate(source, target, contract_path, *, extrusion, ray_distance, report_path=None):
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    contract = json.loads(Path(contract_path).read_text(encoding="utf-8"))
    if contract.get("schemaVersion") != 1 or not contract.get("bindings"):
        raise ValueError("Invalid bake bindings: require schemaVersion 1 and nonempty bindings")
    source_names = json.loads(source[SOURCE_RECORD])
    target_names = json.loads(target[OWNER_RECORD])
    source_marks = source.data.attributes[SOURCE_ATTRIBUTE]
    target_marks = target.data.attributes[OWNER_ATTRIBUTE]
    source.data.calc_loop_triangles(); target.data.calc_loop_triangles()
    triangles = source.data.loop_triangles
    owners = [source_names[source_marks.data[tri.polygon_index].value] for tri in triangles]
    bvh = BVHTree.FromPolygons([source.matrix_world@v.co for v in source.data.vertices],
                              [tuple(tri.vertices) for tri in triangles], all_triangles=True)
    normal_matrix = target.matrix_world.to_3x3().inverted().transposed()
    rows = []; errors = []; seen = set()
    for binding in contract["bindings"]:
        name = binding["receiver"]
        if name in seen: raise ValueError("Duplicate bake receiver binding: " + name)
        seen.add(name)
        patterns = binding.get("sources")
        if not isinstance(patterns,list) or not patterns or not all(isinstance(p,str) for p in patterns):
            raise ValueError("Require source patterns for " + name)
        expected = {candidate for candidate in source_names if any(fnmatch.fnmatchcase(candidate,p) for p in patterns)}
        if not expected: raise ValueError("No source matches bake receiver " + name)
        if "normal" in binding and (len(binding["normal"]) != 3 or
                not all(math.isfinite(v) for v in binding["normal"]) or
                sum(v*v for v in binding["normal"]) < 1e-10):
            raise ValueError("Invalid three-dimensional sample normal for " + name)
        facing = Vector(binding["normal"]).normalized() if "normal" in binding else None
        row = {"receiver":name,"samples":0,"missing":0,"wrongSource":0,"examples":[]}
        for tri in target.data.loop_triangles:
            if target_names[target_marks.data[tri.polygon_index].value] != name: continue
            polygon = target.data.polygons[tri.polygon_index]
            if polygon.use_smooth:
                raise ValueError("Bound receiver uses smooth normals unsupported by flat-normal preflight: " + name)
            normal = (normal_matrix@polygon.normal).normalized()
            if facing is not None and normal.dot(facing) <= binding.get("minNormalDot",0.25): continue
            points = [target.matrix_world@target.data.vertices[i].co for i in tri.vertices]
            for weights in [(1/3,1/3,1/3),(.6,.2,.2),(.2,.6,.2),(.2,.2,.6)]:
                point = sum((p*w for p,w in zip(points,weights)), Vector())
                hit, _, index, distance = bvh.ray_cast(point+normal*extrusion,-normal,ray_distance)
                owner = owners[index] if index is not None else None
                row["samples"] += 1
                if owner is None: row["missing"] += 1
                elif owner not in expected: row["wrongSource"] += 1
                if owner not in expected and len(row["examples"]) < 4:
                    row["examples"].append({"point":list(point),"hit":owner,"distance":distance})
        if not row["samples"]: errors.append(name+": receiver missing, culled, or facing away")
        elif row["missing"] or row["wrongSource"]:
            errors.append(f"{name}: {row['missing']} missing and {row['wrongSource']} wrong-source rays of {row['samples']}; examples {row['examples']}")
        rows.append(row)
    report = {"method":"four barycentric samples per bound front-facing triangle; flat receiver normals; no cage",
              "extrusion":extrusion,"maxRayDistance":ray_distance,"bindings":rows,"errors":errors}
    if report_path is not None:
        Path(report_path).write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8",newline="\n")
    if errors: raise ValueError("Bake correspondence failed: " + "; ".join(errors))
    return report
