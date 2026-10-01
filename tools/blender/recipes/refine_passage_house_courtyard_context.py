"""Open a roof-lightwell over the lodging entry and retain a covered door approach."""
from __future__ import annotations

import bpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "projects/hichaukitoden-game/assets/authoring/environments/passage_house_courtyard.blend"
CANDIDATE = ROOT / "projects/hichaukitoden-game/assets/authoring/candidates/passage_house_courtyard"
sys.path.insert(0, str(ROOT / "tools/blender/recipes"))
from first_stratum.common import box_geometry


def main():
    scene = bpy.context.scene
    if Path(bpy.data.filepath).resolve() != SOURCE.resolve():
        raise RuntimeError("Open the editable courtyard source")
    if scene.get("courtyard_revision") != 3:
        raise RuntimeError("Expected the reviewed spatial revision 3 source")
    source = bpy.data.collections["TH_SOURCE"]
    root = bpy.data.objects["Passage House arrival court"]
    roof = bpy.data.materials["Court terracotta"]
    plaster = bpy.data.materials["Court limewash"]
    wood = bpy.data.materials["Court tropical hardwood"]
    stone = bpy.data.materials["Court threshold stone"]

    for name in ["lodging_pitched_roof", *[f"pantile_ridge_{i}" for i in range(20)]]:
        obj = bpy.data.objects.get(name)
        if obj is not None:
            bpy.data.objects.remove(obj, do_unlink=True)

    def mesh(name, verts, faces, material):
        data = bpy.data.meshes.new(name + "_mesh")
        data.from_pydata(verts, [], faces)
        data.materials.append(material)
        data.update()
        obj = bpy.data.objects.new(name, data)
        source.objects.link(obj)
        obj.parent = root
        obj["sr_bake_source"] = True
        return obj

    def roof_section(name, y0, y1, eaves=4.05, ridge=5.35):
        x0, xm, x1 = 4.25, 7.0, 9.75
        t = .17
        verts = [(x0,y0,eaves),(x0,y1,eaves),(xm,y0,ridge),(xm,y1,ridge),
                 (x1,y0,eaves),(x1,y1,eaves),(x0,y0,eaves-t),(x0,y1,eaves-t),
                 (xm,y0,ridge-t),(xm,y1,ridge-t),(x1,y0,eaves-t),(x1,y1,eaves-t)]
        faces = [(0,1,3,2),(2,3,5,4),(4,5,11,10),(10,11,9,8),
                 (8,9,7,6),(6,7,1,0),(0,2,8,6),(2,4,10,8),
                 (1,7,9,3),(3,9,11,5)]
        mesh(name, verts, faces, roof)
        # The cut ends are finished gables, not open roof shells.
        for y, suffix in ((y0, "west"), (y1, "east")):
            mesh(f"{name}_{suffix}_gable", [(x0,y,eaves-.03),(xm,y,ridge-.03),(x1,y,eaves-.03)],
                 [(0,1,2)], plaster)
            mesh(f"{name}_{suffix}_gable_return", [(x0,y+.10,eaves-.03),(xm,y+.10,ridge-.03),(x1,y+.10,eaves-.03)],
                 [(2,1,0)], plaster)

    # Two inhabited roof wings flank a full-width roof lightwell. Their gable
    # ends and the open strip expose the second Cortico roofline behind them.
    roof_section("lodging_west_roof", -1.95, 7.65)
    roof_section("lodging_east_roof", 15.0, 21.95)

    # A compact lean-to continues the existing gallery over the real lodging door.
    # It leaves the side portions of the lightwell open to the sky and the houses beyond.
    x0, x1, y0, y1 = 4.05, 8.0, 9.55, 13.45
    z0, z1, thickness = 4.12, 3.45, .16
    verts = [(x0,y0,z0),(x0,y1,z0),(x1,y0,z1),(x1,y1,z1),
             (x0,y0,z0-thickness),(x0,y1,z0-thickness),
             (x1,y0,z1-thickness),(x1,y1,z1-thickness)]
    faces = [(0,1,3,2),(2,3,7,6),(6,7,5,4),(4,5,1,0),
             (0,2,6,4),(1,5,7,3)]
    mesh("lodging_entry_lean_to", verts, faces, roof)
    # Two timber posts bear the back beam, outside the walkable route line.
    for y, tag in ((9.20, "west"), (13.80, "east")):
        obj = bpy.data.meshes.new("lodging_entry_post_"+tag+"_mesh")
        v, f = box_geometry((.20,.20,3.18))
        obj.from_pydata(v, [], f)
        obj.materials.append(wood)
        item = bpy.data.objects.new("lodging_entry_post_"+tag, obj)
        source.objects.link(item)
        item.parent = root
        item.location = (7.88,y,1.62)
        item["sr_bake_source"] = True

    # Delicate terracotta ridge caps remain shallow baked texture, not repeated
    # runtime roof furniture.
    for prefix, ya, yb in (("lodging_west", -1.65, 7.35), ("lodging_east", 15.3, 21.65)):
        count = int((yb-ya)/.34)
        for i in range(count):
            y = ya + i*.34
            bpy.ops.mesh.primitive_cube_add(size=1, location=(7.0,y,5.28))
            obj = bpy.context.object
            obj.name = f"{prefix}_ridge_{i:02d}"
            obj.dimensions = (5.52,.11,.08)
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            obj.data.materials.append(roof)
            for collection in list(obj.users_collection): collection.objects.unlink(obj)
            source.objects.link(obj)
            obj.parent = root
            obj["sr_bake_role"] = "source"
            obj["sr_bake_source"] = True

    scene["courtyard_revision"] = 4
    scene["roof_context"] = "two roofed lodging wings, open lightwell, covered entry lean-to"
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE))
    print("PASSAGE COURTYARD LIGHTWELL OK", SOURCE)


if __name__ == "__main__":
    main()
