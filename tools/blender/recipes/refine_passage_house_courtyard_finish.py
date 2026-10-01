"""Refine roof continuity, reveal the backstreet, and simplify the tile finish."""
from __future__ import annotations

import bpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "projects/hichaukitoden-game/assets/authoring/environments/passage_house_courtyard.blend"
sys.path.insert(0, str(ROOT / "tools/blender/recipes"))
from first_stratum.common import box_geometry


def main():
    scene = bpy.context.scene
    if Path(bpy.data.filepath).resolve() != SOURCE.resolve() or scene.get("courtyard_revision") != 4:
        raise RuntimeError("Expected the editable Passage House source at revision 4")
    source = bpy.data.collections["TH_SOURCE"]
    root = bpy.data.objects["Passage House arrival court"]
    roof = bpy.data.materials["Court terracotta"]
    plaster = bpy.data.materials["Court limewash"]
    pale = bpy.data.materials["Court threshold stone"]
    blue = bpy.data.materials["Court azulejo blue"]

    prefixes = ("lodging_west_roof", "lodging_east_roof",
                "lodging_west_ridge_", "lodging_east_ridge_",
                "passage_azulejo_")
    for obj in list(bpy.data.objects):
        if obj.name == "passage_azulejo_receiver" or obj.name.startswith(prefixes):
            bpy.data.objects.remove(obj, do_unlink=True)

    def mesh(name, verts, faces, material):
        data=bpy.data.meshes.new(name+"_mesh")
        data.from_pydata(verts,[],faces)
        data.materials.append(material)
        data.update()
        obj=bpy.data.objects.new(name,data)
        source.objects.link(obj)
        obj.parent=root
        obj["sr_bake_source"]=True
        return obj

    def roof_section(name,y0,y1):
        x0,xm,x1=4.25,7.0,9.75
        eave,ridge,thick=4.05,5.35,.17
        verts=[(x0,y0,eave),(x0,y1,eave),(xm,y0,ridge),(xm,y1,ridge),
               (x1,y0,eave),(x1,y1,eave),(x0,y0,eave-thick),(x0,y1,eave-thick),
               (xm,y0,ridge-thick),(xm,y1,ridge-thick),(x1,y0,eave-thick),(x1,y1,eave-thick)]
        faces=[(0,1,3,2),(2,3,5,4),(4,5,11,10),(10,11,9,8),(8,9,7,6),
               (6,7,1,0),(0,2,8,6),(2,4,10,8),(1,7,9,3),(3,9,11,5)]
        mesh(name,verts,faces,roof)
        for y,tag,reverse in ((y0,"court",False),(y1,"lodging",True)):
            tri=[(x0,y,eave-.03),(xm,y,ridge-.03),(x1,y,eave-.03)]
            mesh(f"{name}_{tag}_gable",tri,[(2,1,0) if reverse else (0,1,2)],plaster)

    roof_section("lodging_west_roof",-1.95,6.55)
    roof_section("lodging_east_roof",16.25,21.95)

    # Replace scattered blue blocks with a continuous, opening-aware azulejo dado.
    # Each run is a shallow source strip baked onto its own simple receiver card.
    runs=[(-1.45,-.11),(1.11,2.89),(4.11,6.19),(7.41,10.8),(12.2,21.5)]
    for index,(lo,hi) in enumerate(runs):
        length=hi-lo
        centre=(lo+hi)/2
        obj=bpy.data.meshes.new(f"Passage azulejo dados {index}_mesh")
        verts,faces=box_geometry((.045,length,.42))
        obj.from_pydata(verts,[],faces)
        obj.materials.append(pale)
        obj.update()
        panel=bpy.data.objects.new(f"Passage azulejo dados {index}",obj)
        source.objects.link(panel);panel.parent=root;panel.location=(4.31,centre,.94)
        panel["sr_bake_role"]="source";panel["sr_bake_source"]=True
        # Two restrained blue ceramic bands define the glazed dado.
        for edge,z in (("lower",.78),("upper",1.10)):
            verts,faces=box_geometry((.055,length,.055))
            data=bpy.data.meshes.new(f"Passage azulejo {index} {edge}_mesh")
            data.from_pydata(verts,[],faces);data.materials.append(blue);data.update()
            stripe=bpy.data.objects.new(f"Passage azulejo {index} {edge}",data)
            source.objects.link(stripe);stripe.parent=root;stripe.location=(4.285,centre,z)
            stripe["sr_bake_role"]="source";stripe["sr_bake_source"]=True
        receiver_mesh=bpy.data.meshes.new(f"Passage azulejo receiver {index}_mesh")
        receiver_mesh.from_pydata([(0,-length/2,.26),(0,-length/2,-.26),
                                   (0,length/2,-.26),(0,length/2,.26)],[],[(0,1,2,3)])
        receiver_mesh.update()
        receiver=bpy.data.objects.new(f"Passage azulejo receiver {index}",receiver_mesh)
        source.objects.link(receiver);receiver.parent=root;receiver.location=(4.34,centre,.94)
        receiver["sr_bake_role"]="receiver";receiver["sr_bake_open_surface"]=True
        receiver["sr_bake_source"]=True;receiver.hide_render=True

    scene["courtyard_revision"]=5
    scene["roof_context"]="split lodging roof with open lightwell, background houses visible above courtyard wall"
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE))
    print("PASSAGE COURTYARD FINISH OK",SOURCE)


if __name__=="__main__":
    main()
