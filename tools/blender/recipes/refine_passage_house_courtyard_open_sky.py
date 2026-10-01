"""Open the central court sightline while keeping the lodging door sheltered."""
from __future__ import annotations
import bpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "projects/hichaukitoden-game/assets/authoring/environments/passage_house_courtyard.blend"


def main():
    if not bpy.data.filepath:
        bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    scene=bpy.context.scene
    if Path(bpy.data.filepath).resolve()!=SOURCE.resolve() or scene.get("courtyard_revision")!=6:
        raise RuntimeError("Expected Passage House courtyard revision 6")
    source=bpy.data.collections["TH_SOURCE"]
    root=bpy.data.objects["Passage House arrival court"]
    roof=bpy.data.materials["Court terracotta"]
    plaster=bpy.data.materials["Court limewash"]
    for name in ("lodging_west_roof", "lodging_west_roof_court_gable", "lodging_west_roof_lodging_gable"):
        obj=bpy.data.objects.get(name)
        if obj: bpy.data.objects.remove(obj,do_unlink=True)
    x0,xm,x1=4.25,7.0,9.75
    y0,y1=-1.95,1.9
    eave,ridge,thick=4.05,5.35,.17
    verts=[(x0,y0,eave),(x0,y1,eave),(xm,y0,ridge),(xm,y1,ridge),
           (x1,y0,eave),(x1,y1,eave),(x0,y0,eave-thick),(x0,y1,eave-thick),
           (xm,y0,ridge-thick),(xm,y1,ridge-thick),(x1,y0,eave-thick),(x1,y1,eave-thick)]
    faces=[(0,1,3,2),(2,3,5,4),(4,5,11,10),(10,11,9,8),(8,9,7,6),
           (6,7,1,0),(0,2,8,6),(2,4,10,8),(1,7,9,3),(3,9,11,5)]
    mesh=bpy.data.meshes.new("lodging_west_roof_open_sky_mesh")
    mesh.from_pydata(verts,[],faces);mesh.materials.append(roof);mesh.update()
    obj=bpy.data.objects.new("lodging_west_roof",mesh);source.objects.link(obj);obj.parent=root;obj["sr_bake_source"]=True
    for y, tag, face in ((y0,"court",(0,1,2)),(y1,"lodging",(2,1,0))):
        data=bpy.data.meshes.new(f"lodging_west_open_{tag}_gable_mesh")
        data.from_pydata([(x0,y,eave-.03),(xm,y,ridge-.03),(x1,y,eave-.03)],[ ],[face]);data.materials.append(plaster);data.update()
        panel=bpy.data.objects.new(f"lodging_west_roof_{tag}_gable",data);source.objects.link(panel);panel.parent=root;panel["sr_bake_source"]=True
    scene["courtyard_revision"]=7
    scene["roof_context"]="open central sky court and raised backstreet skyline; entry lean-to shelters the lodging door"
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE))
    print("PASSAGE COURTYARD OPEN SKY OK",SOURCE)


if __name__=="__main__":main()
