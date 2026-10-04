"""Compile a small relational JSON scaffold through existing Interior/builders.

This is a scaffold authoring pilot, not a reconstruction path for adopted sources.
Run inside pinned Blender with --spec and --blend; source saves retain overwrite guards.
"""
import argparse
import inspect
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE/'recipes')]
import bpy
import furnishings
import interior
import furnishing_geometry as geometry
import placement_rules as placement
import material_library

SHELL={'floor','back_wall','side_walls','ceiling','window','side_window',
       'exit_threshold','window_light','side_window_light','doorway_light'}


def strict_keys(value, allowed, field):
    unknown=set(value)-allowed
    if unknown: raise ValueError(f'{field}: unknown fields {sorted(unknown)}')


def compile_spec(spec):
    strict_keys(spec,{'version','id','room','shell','furnishings','keepClear'},'spec')
    if spec.get('version')!=1: raise ValueError('spec.version: expected 1')
    room=interior.Interior(spec['id'],**spec['room'])
    def bindings(value):
        if isinstance(value,dict) and set(value)=={'material'}:
            return material_library.build_material(interior.asset_core,value['material'])
        if isinstance(value,list): return [bindings(v) for v in value]
        if isinstance(value,dict): return {k:bindings(v) for k,v in value.items()}
        return value
    for i,operation in enumerate(spec.get('shell',[])):
        field=f'shell[{i}]'
        strict_keys(operation,{'call','args','params'},field)
        if operation['call'] not in SHELL: raise ValueError(f'{field}.call: unknown shell operation')
        method=getattr(room,operation['call'])
        args=bindings(operation.get('args',[])); kwargs=bindings(operation.get('params',{}))
        try:
            inspect.signature(method).bind(*args,**kwargs)
            method(*args,**kwargs)
        except (TypeError,ValueError) as error: raise ValueError(f'{field}: {error}') from error
    emitted={}; measured={}
    for i,item in enumerate(spec['furnishings']):
        field=f'furnishings[{i}]({item.get("id","?")})'
        strict_keys(item,{'id','builder','params','place'},field)
        name=item['id']
        if name in emitted: raise ValueError(f'{field}.id: duplicate')
        builder=item['builder']
        if builder.startswith('_') or not inspect.isfunction(getattr(furnishings,builder,None)):
            raise ValueError(f'{field}.builder: unknown public furnishing {builder}')
        method=getattr(furnishings,builder)
        if 'at' not in inspect.signature(method).parameters:
            raise ValueError(f'{field}.builder: pilot supports at-based furnishings; use shell/recipe for wall fittings')
        params=bindings(item.get('params',{}))
        if set(params)&{'room','name','at'}: raise ValueError(f'{field}.params: placement owns room/name/at')
        start=len(room.parts)
        try:
            inspect.signature(method).bind(room,name,(0,0),**params)
            method(room,name,(0,0),**params)
            parts=room.parts[start:]; child=geometry.bounds(parts)
            relation=item['place']
            if set(relation)=={'at'}:
                position=relation['at']
                if len(position)!=2: raise ValueError('place.at: expected [x,y] floor metres')
                delta=[position[0],position[1],-child[0][2]]
            elif 'on' in relation:
                strict_keys(relation,{'on','offset'},field+'.place')
                target=relation['on']
                if target not in emitted: raise ValueError(f'place.on: unknown/forward support {target}')
                surface=geometry.rectangular_top(emitted[target],field+'.place.on')
                delta=placement.on_surface(child,surface,relation.get('offset',[0,0]),field+'.place.on')
            elif 'beside' in relation:
                strict_keys(relation,{'beside','axis','side','gap'},field+'.place')
                target=relation['beside']
                if target not in measured: raise ValueError(f'place.beside: unknown/forward target {target}')
                delta=placement.beside(child,measured[target],relation['axis'],relation['side'],relation['gap'],field+'.place.beside')
            else: raise ValueError('place: choose at, on, or beside')
            geometry.translate(parts,delta)
            actual=geometry.bounds(parts)
            placement.assert_keep_clear(actual,spec.get('keepClear',{}),field)
        except (TypeError,ValueError) as error: raise ValueError(f'{field}: {error}') from error
        emitted[name]=parts; measured[name]=actual
    room.finish()
    return room,measured


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec',type=Path,required=True)
    parser.add_argument('--blend',type=Path,required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    room,measured=compile_spec(json.loads(args.spec.read_text(encoding='utf-8')))
    interior.save_source_blend(args.blend,force=False)
    print(json.dumps({'spec':str(args.spec),'blend':str(args.blend),'bounds':measured},indent=2))
