"""Extend existing service joinery to the right wall and add a wall-backed cabinet."""
import argparse,json,math,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools/blender'),str(ROOT/'tools/blender/recipes')]
import interior as kit
import furnishings as furn
import source_dependencies
from fit_registry_ceiling import bounds,signature

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    if a.output.exists():p.error('Use a new source revision')
    bpy.ops.wm.open_mainfile(filepath=str(a.source.resolve()));source_dependencies.assert_available()
    shell=[bpy.data.objects['ceiling'],*[o for o in bpy.data.objects if o.name.startswith('ceiling_beam_')]]
    before=signature(shell)
    wall=bounds(bpy.data.objects['side_wall_0_pier_0'])[1][1]
    old=bpy.data.objects['registry_counter'];low,high=bounds(old)
    counter_left=high[1];length=counter_left-wall
    left=1.245;right=wall+.06;front=.89
    ceiling=bounds(shell[0])[0][2];rear=bounds(bpy.data.objects['back_wall_0_pier_1'])[0][0]
    beam_bounds=[bounds(o) for o in shell[1:]]
    crossings=[(lo,hi) for lo,hi in beam_bounds if lo[0]<front<hi[0] and lo[1]<left and hi[1]>right]
    underside=min(lo[2] for lo,hi in crossings)
    for name in ('registry_counter','ceiling_fitted_service_screen','registry_counter_returns'):
        bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
    room=kit.Interior.__new__(kit.Interior);room.root=bpy.data.objects['PASSAGE_OFFICE'];room.lift=0
    room.parts=[o for o in bpy.data.objects if o.type=='MESH']
    room.wood=bpy.data.materials['registry_worked_hardwood'];room.iron=bpy.data.materials['sr_wrought_iron']
    paint=bpy.data.materials['registry_worn_green_paint']
    start=len(room.parts)
    furn.counter(room,'registry_counter',(.45,(counter_left+wall)/2),length=length,width=.88,height=.92,
                 panels=8,body_mat=paint,panel_mat=paint)
    # The original left return remains; the right end terminates at the masonry.
    with room.piece('registry_counter_left_return'):
        room.part('left_return',(.95,.075,.82),(1.345,left,.41),paint)
        room.part('left_return_cap',(1.01,.12,.075),(1.345,left,.945),room.wood)
        room.part('left_return_plinth',(.95,.10,.10),(1.345,left,.05),room.wood)
    furn.service_screen(room,'wall_to_wall_service_frontage',front=front,rear=rear,left=left,right=right,
        height=ceiling,transom_top=underside-.04,beam_spans=[(lo[1],hi[1]) for lo,hi in crossings],panel_mat=paint)
    furn.cabinet(room,'right_wall_records_cabinet',(0,0),width=1.35,depth=.56,height=2.3)
    cabinet=bpy.data.objects['right_wall_records_cabinet']
    cabinet.rotation_euler.z=-math.pi/2
    cabinet.location.x=3.65;cabinet.location.y=wall+.28
    bpy.context.view_layer.update()
    # Seat the projecting cornice against the wall instead of burying it in masonry.
    cabinet.location.y+=wall-bounds(cabinet)[0][1]
    kit.recalculate_normals(room.parts[start:]);bpy.context.view_layer.update()
    counter_bounds=bounds(bpy.data.objects['registry_counter']);cabinet_bounds=bounds(cabinet)
    assert abs(counter_bounds[0][1]-wall)<1e-5,'Counter does not meet right wall'
    assert abs(cabinet_bounds[0][1]-wall)<1e-5,'Cabinet back does not meet right wall'
    assert signature(shell)==before,'Ceiling or beams changed'
    record=dict(rightWallY=wall,counterLength=length,counterMeetsWall=True,cabinetBackMeetsWall=True,
                ceilingAndBeamsPreserved=True,shellSignature=before)
    bpy.context.scene['registry_frontage_fit']=json.dumps(record)
    bpy.ops.wm.save_as_mainfile(filepath=str(a.output.resolve()))
    print('REGISTRY EXTENDED FRONTAGE OK '+json.dumps(record))

if __name__=='__main__':main()
