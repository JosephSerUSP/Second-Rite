"""Refine the existing Registry source: book silhouettes and material hierarchy."""
import argparse,sys
from pathlib import Path
import bpy,bmesh
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools/blender'),str(ROOT/'tools/blender/recipes')]
import interior as kit
import furnishings as furn
import source_dependencies

def tint(name, semantic, rgb):
    """An authored flat finish, retaining its semantic binding; RGB is sRGB."""
    mat=kit.material(semantic).copy();mat.name=name
    bsdf=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    for socket in ('Base Color','Normal'):
        for link in list(bsdf.inputs[socket].links):mat.node_tree.links.remove(link)
    linear=tuple(c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4 for c in rgb)
    bsdf.inputs['Base Color'].default_value=(*linear,1)
    bsdf.inputs['Roughness'].default_value=.82
    mat.diffuse_color=(*linear,1)
    return mat

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    if a.output.exists():p.error('Use a new revision')
    bpy.ops.wm.open_mainfile(filepath=str(a.source.resolve()));source_dependencies.assert_available()
    room=kit.Interior.__new__(kit.Interior);room.root=bpy.data.objects['PASSAGE_OFFICE'];room.lift=0
    room.wood=tint('registry_walnut','dark_wood',(.30,.19,.105))
    room.paper=tint('registry_rag_paper','paper',(.86,.78,.59))
    room.leather=tint('registry_oxblood','book_leather',(.34,.085,.065))
    green=tint('registry_green_binding','book_leather',(.11,.25,.19))
    ochre=tint('registry_ochre_binding','book_leather',(.49,.29,.09))
    lime=tint('registry_limewash','whitewash',(.80,.77,.65))
    paint=tint('registry_counter_paint','dark_wood',(.14,.28,.26))
    oak=tint('registry_oak','dark_wood',(.48,.31,.16))
    ink=tint('registry_stamp_ink','writing_ink',(.055,.045,.035))
    for obj in bpy.data.objects:
        if obj.type!='MESH':continue
        for i,mat in enumerate(obj.data.materials):
            if not mat:continue
            semantic=mat.get('sr_material_id')
            if semantic=='whitewash':obj.data.materials[i]=lime
            if semantic=='writing_ink':obj.data.materials[i]=ink
            if semantic=='book_leather':obj.data.materials[i]=room.leather
            if semantic=='paper':obj.data.materials[i]=room.paper
            if semantic=='dark_wood' and obj.name in ('registry_counter','record_pigeonholes','waiting_bench'):
                obj.data.materials[i]=oak if obj.name=='waiting_bench' else room.wood
        if obj.name=='registry_counter':
            obj.data.materials.append(paint)
            for face in obj.data.polygons:
                if abs(face.normal.z)<.5:face.material_index=len(obj.data.materials)-1
    for name in ('current_ledger','previous_ledger'):
        bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
    # Preserve the shelf geometry, replace anonymous paper bricks with real volumes.
    shelf=bpy.data.objects['record_pigeonholes'];mesh=shelf.data
    bm=bmesh.new();bm.from_mesh(mesh)
    remove=[v for v in bm.verts if all(mesh.materials[f.material_index].get('sr_material_id') in ('paper','book_leather') for f in v.link_faces)]
    bmesh.ops.delete(bm,geom=remove,context='VERTS');bm.to_mesh(mesh);bm.free()
    room.parts=[o for o in bpy.data.objects if o.type=='MESH']
    for row in range(4):
        with room.surface(row*2.35/4+.035):
            for col in range(5):
                # Deliberate gaps and mixed spine colours survive the small native frame.
                y=-.7-1.4+(col+.5)*2.8/5
                for j in range(3 if (row+col)%3 else 2):
                    furn.bound_volume(room,f'archive_volume_{row}_{col}_{j}',(3.59,y+(j-1)*.13),
                        height=.40+.045*((row+col+j)%3),thickness=.11,cover_mat=(room.leather,green,ochre)[(row+col+j)%3])
    with room.surface(1.007):
        furn.ledger(room,'previous_ledger',(.46,-.18),length=.48,width=.32)
        # An open spread with a raised gutter and sloping page blocks.
        with room.piece('current_ledger'):
            room.part('ledger_boards',(.38,.62,.018),(.43,-.95,.009),room.leather)
            for side in (-1,1):
                bm=bmesh.new()
                verts=[bm.verts.new((x,y,z)) for x,y,z in [(-.175,.012,.02),(.175,.012,.02),(.175,.292,.02),(-.175,.292,.02),(-.175,.012,.092),(.175,.012,.092),(.175,.292,.042),(-.175,.292,.042)]]
                for face in [(0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)]:bm.faces.new([verts[i] for i in face])
                obj=furn.asset_core.mesh_object_from_bmesh('sloping_pages',bm)
                furn.asset_core.parent_local(obj,room.root,loc=(.43,-.95,room.lift),rot=(0,0,0 if side==1 else 3.14159265))
                furn.asset_core.assign_material(obj,room.paper);room.parts.append(obj)
            room.part('exposed_gutter',(.36,.025,.028),(.43,-.95,.027),room.leather)
    kit.recalculate_normals(room.parts);bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(a.output.resolve()))
    print('REGISTRY BOOK AND MATERIAL REFINEMENT OK')

if __name__=='__main__':main()
