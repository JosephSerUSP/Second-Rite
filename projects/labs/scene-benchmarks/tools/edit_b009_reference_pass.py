"""One-time in-place edit of the adopted B009 source (2026-10-06 reference pass).
Run: blender -b assets/authoring/environments/b009_encounter.blend --python tools/edit_b009_reference_pass.py
Then export with build_b009_models.py --export-only. Never regenerates the source.
Changes, from direct comparison with the Day 1 rat battle frame:
- rat palette: crimson body/head/tail, pale mottled back plates (was inverted);
- doors: cream frames, brighter crimson leaves, vertical brass push bars;
- corridor wall/floor extended so the Wide surface edge shows real geometry.
"""
import bpy
from pathlib import Path
SOURCE=Path(bpy.data.filepath)
if bpy.data.objects.get("Door push bar"): raise RuntimeError("reference pass already applied")
M=bpy.data.materials
def tint(name,rgb):
    m=M[name];m.diffuse_color=(*rgb,1)
    n=m.node_tree and m.node_tree.nodes.get("Principled BSDF")
    if n: n.inputs["Base Color"].default_value=(*rgb,1) if not n.inputs["Base Color"].is_linked else n.inputs["Base Color"].default_value
tint("Exposed mutant muscle",(.62,.05,.04))
tint("Mutant mottled grey",(.66,.68,.66))
tint("Rat tail",(.55,.06,.05))
tint("Backstage door crimson",(.48,.03,.035))
tint("Door stone frame",(.6,.56,.46))
tint("Door hardware",(.78,.56,.2))
red=M["Exposed mutant muscle"];grey=M["Mutant mottled grey"]
for cname in ("rat","rat_windup","rat_lunge"):
    for o in bpy.data.collections[cname].objects:
        base=o.name.rsplit(".",1)[0]
        if base in ("Rat body","Rat shoulders","Rat head","Rat muzzle"):
            o.material_slots[0].material=red
        if base=="Dorsal ridge":
            o.scale=(o.scale[0]*1.9,o.scale[1]*1.4,o.scale[2]*1.25)
cor=bpy.data.collections["corridor"]
for h in [o for o in cor.objects if o.name.startswith("Brass door handle")]:
    x=sum((h.matrix_world@v.co).x for v in h.data.vertices)/len(h.data.vertices)
    bpy.ops.mesh.primitive_cube_add(size=1,location=(x,5.0,1.35))
    b=bpy.context.object;b.name="Door push bar";b.scale=(.07,.07,1.1)
    b.data.materials.append(M["Door hardware"])
    for c in list(b.users_collection): c.objects.unlink(b)
    cor.objects.link(b)
# Extend: copy wall/floor pieces from the left half 8 units further left,
# and from the right half 8.4 units further right.
pieces=[o for o in cor.objects if o.name.startswith(("Masonry block","Worn stone paving","Foreground paving"))]
for o in pieces:
    x=o.matrix_world.translation.x
    for lo,hi,dx in ((-8.0,0.0,-8.0),(0.0,4.4,8.4)):
        if lo<=x<hi:
            d=o.copy();d.location.x+=dx;cor.objects.link(d)
for n in ("Corridor foundation","Upper cornice","Wall baseboard"):
    o=bpy.data.objects[n]
    for v in o.data.vertices:
        v.co.x = -16.0/o.scale.x if v.co.x<0 else 12.6/o.scale.x
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE))
print("REFERENCE PASS SAVED",len(cor.objects))
# Step 2 (same day, after first capture): the reference rat's back is a pale
# mottled saddle, so the rear body mass returns to the mottled material.
# Applied separately with: --python-expr after the first save.
def saddle():
    for cname in ("rat","rat_windup","rat_lunge"):
        for o in bpy.data.collections[cname].objects:
            if o.name.rsplit(".",1)[0]=="Rat body": o.material_slots[0].material=M["Mutant mottled grey"]
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE))
