"""Fix counter support and add a wall-connected timber service screen."""
import argparse,sys,json
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools/blender'),str(ROOT/'tools/blender/recipes')]
import interior as kit
import furnishings as furn
import source_dependencies

def support_counter(obj):
    """Edit the existing joined box islands; preserve their materials and UVs."""
    mesh=obj.data;neighbors=[set() for v in mesh.vertices]
    for edge in mesh.edges:
        a,b=edge.vertices;neighbors[a].add(b);neighbors[b].add(a)
    remaining=set(range(len(mesh.vertices)));components=[]
    while remaining:
        queue=[remaining.pop()];indices=set(queue)
        while queue:
            for index in neighbors[queue.pop()] & remaining:
                remaining.remove(index);indices.add(index);queue.append(index)
        lo=[min(mesh.vertices[i].co[a] for i in indices) for a in range(3)]
        hi=[max(mesh.vertices[i].co[a] for i in indices) for a in range(3)]
        span=[hi[a]-lo[a] for a in range(3)]
        components.append(dict(indices=indices,lo=lo,hi=hi,span=span))
    body=max(components,key=lambda c:c['span'][0]*c['span'][1]*c['span'][2])
    top=max(components,key=lambda c:c['span'][0]*c['span'][1])
    gap=top['lo'][2]-body['hi'][2]
    if not 0<gap<.25:raise ValueError(f'Unexpected counter support geometry: gap={gap}')
    for index in body['indices']:
        if abs(mesh.vertices[index].co.z-body['hi'][2])<1e-5:
            mesh.vertices[index].co.z=top['lo'][2]
    mesh.update()
    return gap

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    if a.output.exists():p.error('Use a new source revision')
    bpy.ops.wm.open_mainfile(filepath=str(a.source.resolve()));source_dependencies.assert_available()
    gap=support_counter(bpy.data.objects['registry_counter'])
    room=kit.Interior.__new__(kit.Interior);room.root=bpy.data.objects['PASSAGE_OFFICE'];room.lift=0
    room.parts=[o for o in bpy.data.objects if o.type=='MESH']
    room.wood=bpy.data.materials['registry_worked_hardwood'];paint=bpy.data.materials['registry_worn_green_paint']
    probe=kit.Interior.__new__(kit.Interior);probe.parts=[bpy.data.objects['back_wall_0_pier_1']]
    rear=probe.bounds()[0][0]
    furn.service_screen(room,'wall_connected_service_screen',front=.89,rear=rear,
                        left=1.245,right=-2.645,panel_mat=paint)
    kit.recalculate_normals(room.parts)
    bpy.context.scene['registry_plan_description']='Wall-connected L-shaped timber service screen supported by the counter'
    bpy.context.scene['registry_counter_gap_repaired_metres']=gap
    bpy.ops.wm.save_as_mainfile(filepath=str(a.output.resolve()))
    print(f'REGISTRY SERVICE BAY OK; counter gap repaired: {gap:.4f}m')

if __name__=='__main__':main()
