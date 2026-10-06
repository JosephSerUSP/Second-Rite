"""Preflight and preview three drawn shadows before scaffolding a NEW source.

Host: ``python tools/blender/shadow_volume.py check SPEC.json`` or
``preview SPEC.json --output out/shadows.svg``. ``build`` uses run.py and
refuses to replace a saved source. After creation, edit its Blender masks.
"""
from __future__ import annotations

import argparse
import html
import json
import math
import re
import subprocess
import sys
from pathlib import Path

PLANES = {'front': (0, 2), 'side': (1, 2), 'top': (0, 1)}
EPSILON = 1e-8


def number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{label}: expected a finite number')
    return float(value)


def cross(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])


def segments_touch(a, b, c, d):
    signs = (cross(a,b,c), cross(a,b,d), cross(c,d,a), cross(c,d,b))
    if signs[0]*signs[1] < 0 and signs[2]*signs[3] < 0:
        return True
    for value, p, lo, hi in ((signs[0],c,a,b),(signs[1],d,a,b),(signs[2],a,c,d),(signs[3],b,c,d)):
        if abs(value) <= EPSILON and all(min(lo[k],hi[k])-EPSILON <= p[k] <= max(lo[k],hi[k])+EPSILON for k in (0,1)):
            return True
    return False


def outline(points, label):
    if not isinstance(points, (list, tuple)) or len(points) < 3:
        raise ValueError(f'{label}: at least three distinct corners required')
    result = []
    for i, point in enumerate(points):
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ValueError(f'{label}[{i}]: expected two coordinates')
        result.append(tuple(number(v, f'{label}[{i}]') for v in point))
    # Closure is implicit. An explicitly repeated last point is an error.
    edges = list(zip(result, result[1:]+result[:1]))
    for i, (a,b) in enumerate(edges):
        if math.dist(a,b) <= EPSILON:
            raise ValueError(f'{label}: zero-length edge {i}; do not repeat the closing corner')
        prev=result[i-1]
        if abs(cross(prev,a,b)) <= EPSILON:
            raise ValueError(f'{label}: collinear corner {i}; remove it before building')
        for j, (c,d) in enumerate(edges):
            if j <= i or j == i+1 or (i == 0 and j == len(edges)-1):
                continue
            if segments_touch(a,b,c,d):
                raise ValueError(f'{label}: edges {i} and {j} self-intersect or touch')
    area=sum(a[0]*b[1]-b[0]*a[1] for a,b in edges)/2
    if abs(area) <= EPSILON:
        raise ValueError(f'{label}: outline has no area')
    return result if area > 0 else list(reversed(result))


def validate(spec):
    if not isinstance(spec, dict):
        raise ValueError('shadow spec must be an object')
    allowed={'version','id','front','side','top','cuts','bevel','smooth','color'}
    unknown=set(spec)-allowed
    if unknown:
        raise ValueError(f'unknown shadow fields: {sorted(unknown)}')
    if spec.get('version') != 1 or isinstance(spec.get('version'), bool):
        raise ValueError('shadow spec version must be 1')
    name=spec.get('id')
    if not isinstance(name,str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,63}',name):
        raise ValueError('id must be a lowercase permanent identifier')
    result={'version':1,'id':name}
    for plane in PLANES:
        result[plane]=outline(spec.get(plane),plane)
    result['bevel']=number(spec.get('bevel',0),'bevel')
    if result['bevel'] < 0:
        raise ValueError('bevel must be nonnegative')
    result['smooth']=spec.get('smooth',False)
    if not isinstance(result['smooth'],bool):
        raise ValueError('smooth must be boolean')
    color=spec.get('color',[.65,.68,.72])
    if not isinstance(color,(list,tuple)) or len(color) != 3:
        raise ValueError('color needs three channels')
    result['color']=[number(c,'color') for c in color]
    if any(c < 0 or c > 1 for c in result['color']):
        raise ValueError('color channels must be inside 0..1')
    cuts=spec.get('cuts',[])
    if not isinstance(cuts,list):
        raise ValueError('cuts must be a list')
    result['cuts']=[]
    for i,cut in enumerate(cuts):
        if (not isinstance(cut,dict) or set(cut) != {'plane','outline'}
                or not isinstance(cut['plane'],str) or cut['plane'] not in PLANES):
            raise ValueError(f'cut {i}: expected plane and outline')
        result['cuts'].append({'plane':cut['plane'],'outline':outline(cut['outline'],f'cut {i}')})
    # These are the intersected projection bounds, not a claim that a hull exists.
    bounds=[]
    for axis in range(3):
        spans=[]
        for plane,axes in PLANES.items():
            if axis in axes:
                coords=[p[axes.index(axis)] for p in result[plane]]
                spans.append((min(coords),max(coords)))
        lo=max(s[0] for s in spans);hi=min(s[1] for s in spans)
        if hi-lo <= EPSILON:
            raise ValueError(f'shadows have no overlapping {"XYZ"[axis]} extent')
        bounds.append((lo,hi))
    result['projectionBounds']=bounds
    return result


def preview_svg(spec):
    spec=validate(spec);parts=['<svg xmlns="http://www.w3.org/2000/svg" width="900" height="340" viewBox="0 0 900 340">',
        '<rect width="900" height="340" fill="#1a1a20"/>']
    tint='#'+''.join(f'{round(c*255):02x}' for c in spec['color'])
    parts.append(f'<text x="14" y="22" fill="#eee" font-family="monospace">{html.escape(spec["id"])} | drawn controls; final hull must be evaluated</text>')
    for i,(plane,axes) in enumerate(PLANES.items()):
        points=spec[plane];lo=[min(p[k] for p in points) for k in (0,1)];hi=[max(p[k] for p in points) for k in (0,1)]
        scale=min(250/(hi[0]-lo[0]),230/(hi[1]-lo[1]))
        def path(poly):
            coords=[(i*300+150+(p[0]-(lo[0]+hi[0])/2)*scale,178-(p[1]-(lo[1]+hi[1])/2)*scale) for p in poly]
            return 'M '+' L '.join(f'{x:.3f} {y:.3f}' for x,y in coords)+' Z'
        parts.append(f'<path d="{path(points)}" fill="{tint}" stroke="#eee" stroke-width="1.5"/>')
        for cut in spec['cuts']:
            if cut['plane']==plane:parts.append(f'<path d="{path(cut["outline"])}" fill="#1a1a20" stroke="#ee9977" stroke-width="1.5"/>')
        label=f'{plane}: {"XYZ"[axes[0]]} / {"XYZ"[axes[1]]}'
        parts.append(f'<text x="{i*300+18}" y="320" fill="#ddd" font-family="monospace">{label} | {len(points)} corners</text>')
    return '\n'.join(parts+['</svg>'])+'\n'


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('action',choices=['check','preview','build','inspect-source'])
    parser.add_argument('spec',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args(argv)
    try:
        if args.action=='inspect-source':
            if args.spec.suffix.lower()!='.blend' or args.output is None or args.output.suffix.lower()!='.json':
                raise ValueError('inspect-source needs a saved .blend and --output report.json')
            if args.output.exists():raise ValueError(f'{args.output} exists')
            folder=Path(__file__).resolve().parent
            return subprocess.run([sys.executable,str(folder/'run.py'),str(folder/'shadow_volume_blender.py'),'--','--inspect-source',str(args.spec.resolve()),'--output',str(args.output.resolve())],check=False).returncode
        raw=json.loads(args.spec.read_text(encoding='utf-8'));checked=validate(raw)
        if args.action=='check':
            print(json.dumps({'id':checked['id'],'projectionBounds':checked['projectionBounds'],'cuts':len(checked['cuts']),'hullEvaluated':False}));return 0
        if args.output is None:raise ValueError('--output required')
        if args.output.exists():raise ValueError(f'{args.output} exists; edit saved sources directly')
        if args.action=='preview':
            if args.output.suffix.lower()!='.svg':raise ValueError('preview output must be .svg')
            args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(preview_svg(raw),encoding='utf-8');return 0
        if args.output.suffix.lower()!='.blend' or args.output.stem!=checked['id']:
            raise ValueError('new .blend filename must match id')
        folder=Path(__file__).resolve().parent
        return subprocess.run([sys.executable,str(folder/'run.py'),str(folder/'shadow_volume_blender.py'),'--','--spec',str(args.spec.resolve()),'--output',str(args.output.resolve())],check=False).returncode
    except (ValueError,OSError) as error:
        print(f'SHADOW VOLUME FAILED: {error}',file=sys.stderr);return 1


if __name__=='__main__':
    raise SystemExit(main())
