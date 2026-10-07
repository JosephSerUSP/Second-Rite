"""Read an image silhouette into a thick, UV-bound new-source mesh.

Pixels remain unchanged. Alpha selects geometry; bow and luminance relief are
authored depth controls, not recovered physical depth. The saved .blend is
authority after scaffolding. This module does not import Blender.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


def build_mesh(image_path, *, width=2.0, height=None, grid=48, depth=.12,
               bow=.16, relief=0.0, alpha=240, clip=None):
    from PIL import Image
    for key,value in (('width',width),('depth',depth),('bow',bow),('relief',relief)):
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
            raise ValueError(key+' must be finite')
    if width<=0 or depth<=0 or bow<0 or relief<0:
        raise ValueError('positive width/depth and nonnegative bow/relief required')
    if height is not None and (isinstance(height,bool) or not isinstance(height,(int,float)) or not math.isfinite(height) or height<=0):
        raise ValueError('height must be positive and finite')
    if not isinstance(grid,int) or isinstance(grid,bool) or not 8<=grid<=192:
        raise ValueError('grid must be an integer in 8..192')
    if not isinstance(alpha,int) or isinstance(alpha,bool) or not 1<=alpha<=255:
        raise ValueError('alpha must be an integer in 1..255')
    image_path=Path(image_path); digest=hashlib.sha256(image_path.read_bytes()).hexdigest()
    with Image.open(image_path) as raw:
        if 'A' not in raw.getbands():raise ValueError('an actual alpha channel is required')
        image=raw.convert('RGBA')
    iw,ih=image.size; pixels=image.load()
    if clip is not None:
        if (not isinstance(clip,(list,tuple)) or len(clip)!=4
                or any(isinstance(v,bool) or not isinstance(v,int) for v in clip)
                or not 0<=clip[0]<clip[2]<=iw or not 0<=clip[1]<clip[3]<=ih):
            raise ValueError('clip must be four integer pixel edges inside the original image')
        clip=tuple(clip)
    else:clip=(0,0,iw,ih)
    # Restrict sampling only. UVs still address the original full image and the
    # original file is neither cropped nor rewritten.
    mask=image.getchannel('A').crop(clip); histogram=mask.histogram()
    if not sum(histogram[:alpha]):raise ValueError('image has no transparent silhouette boundary')
    bbox=mask.point(lambda v:255 if v>=alpha else 0).getbbox()
    if bbox is None:raise ValueError('no pixels meet the alpha threshold')
    left,upper,right,lower=(bbox[0]+clip[0],bbox[1]+clip[1],bbox[2]+clip[0],bbox[3]+clip[1])
    # Image-space coordinates are pixel centres. Grid is along the long edge.
    pw=right-left-1;ph=lower-upper-1
    if min(pw,ph)<2:raise ValueError('silhouette too small')
    nx=max(4,round(grid*pw/max(pw,ph))); nz=max(4,round(grid*ph/max(pw,ph)))
    height=height if height is not None else width*ph/pw
    def pixel_at(u,v):
        x=left+u*pw;y=upper+(1-v)*ph
        return pixels[round(x),round(y)]
    # Corners, edge midpoints and centre must all be supported by alpha.
    cells=set()
    for j in range(nz):
        for i in range(nx):
            if all(pixel_at((i+du)/nx,(j+dv)/nz)[3]>=alpha for du,dv in
                   ((0,0),(1,0),(1,1),(0,1),(.5,.5),(.5,0),(1,.5),(.5,1),(0,.5))):
                cells.add((i,j))
    if not cells:raise ValueError('no supported cells; increase grid or lower threshold deliberately')
    # Keep one connected body. Report excluded fragments rather than silently
    # turning detached generated marks into separate geometry.
    groups=[];pending=set(cells)
    while pending:
        seed=min(pending);pending.remove(seed);group={seed};queue=[seed]
        while queue:
            i,j=queue.pop()
            for n in ((i-1,j),(i+1,j),(i,j-1),(i,j+1)):
                if n in pending:pending.remove(n);group.add(n);queue.append(n)
        groups.append(group)
    groups.sort(key=lambda g:(-len(g),min(g))); discarded=sum(len(g) for g in groups[1:]);cells=groups[0]
    # Distinct cell quadrants touching only at a vertex make a nonmanifold
    # extrusion. Split that local vertex into separate edge-connected fans.
    incident={}
    for i,j in sorted(cells):
        for p in ((i,j),(i+1,j),(i+1,j+1),(i,j+1)):incident.setdefault(p,set()).add((i,j))
    vertex_ids={};vertices=[];uv=[]
    for p,adjacent in sorted(incident.items()):
        remaining=set(adjacent)
        while remaining:
            seed=min(remaining);remaining.remove(seed);fan={seed};queue=[seed]
            while queue:
                i,j=queue.pop()
                for n in ((i-1,j),(i+1,j),(i,j-1),(i,j+1)):
                    if n in remaining:remaining.remove(n);fan.add(n);queue.append(n)
            i,j=p;u=i/nx;v=j/nz;x=(u-.5)*width;z=(v-.5)*height
            r2=((u-.5)*2)**2+((v-.5)*2)**2
            red,green,blue,_=pixel_at(u,v);lum=(.2126*red+.7152*green+.0722*blue)/255
            y=-depth/2-bow*max(0,1-r2)-relief*lum
            index=len(vertices);vertices.append((x,y,z));uv.append(((left+u*pw)/(iw-1),1-(upper+(1-v)*ph)/(ih-1)))
            for cell in fan:vertex_ids[(p,cell)]=index
    count=len(vertices)
    # Back follows a gentler matching arch, retaining physical edge thickness.
    vertices += [(x,y+depth+relief*.5,z) for x,y,z in vertices[:count]]
    uv += uv[:count]
    faces=[];materials=[];edges={}
    for cell in sorted(cells):
        i,j=cell;corners=((i,j),(i+1,j),(i+1,j+1),(i,j+1))
        ids=tuple(vertex_ids[(p,cell)] for p in corners)
        faces.append(ids);materials.append(0)
        faces.append(tuple(v+count for v in reversed(ids)));materials.append(1)
        for a,b in zip(ids,ids[1:]+ids[:1]):edges.setdefault(tuple(sorted((a,b))),[]).append((a,b))
    for matches in edges.values():
        if len(matches)==1:
            a,b=matches[0];faces.append((b,a,a+count,b+count));materials.append(1)
        elif len(matches)!=2:raise ValueError('nonmanifold generated edge')
    report={'imageHash':digest,'imageSize':[iw,ih],'sampleClipPixels':list(clip),
            'alphaThreshold':alpha,'alphaBoundsPixels':[left,upper,right,lower],
            'grid':[nx,nz],'acceptedCells':len(cells),'discardedDetachedCells':discarded,
            'depthControls':{'width':width,'height':height,'depth':depth,'bow':bow,'luminanceRelief':relief},
            'vertices':len(vertices),'faces':len(faces),'triangles':sum(len(f)-2 for f in faces),
            'semantics':'alpha constrains silhouette; authored bow and luminance displacement; not recovered depth'}
    return {'vertices':vertices,'faces':faces,'uvs':[[uv[v] for v in f] for f in faces],
            'materials':materials,'report':report}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('image',type=Path);parser.add_argument('--grid',type=int,default=48)
    parser.add_argument('--width',type=float,default=2);parser.add_argument('--height',type=float)
    parser.add_argument('--depth',type=float,default=.12);parser.add_argument('--bow',type=float,default=.16)
    parser.add_argument('--relief',type=float,default=0);parser.add_argument('--alpha',type=int,default=240)
    parser.add_argument('--clip',type=int,nargs=4,metavar=('X0','Y0','X1','Y1'))
    parser.add_argument('--output',type=Path);parser.add_argument('--mesh-output',type=Path)
    args=parser.parse_args(argv)
    try:
        for target in (args.output,args.mesh_output):
            if target and target.exists():raise ValueError('output exists')
        if args.output and args.mesh_output and args.output.resolve()==args.mesh_output.resolve():
            raise ValueError('report and mesh outputs must differ')
        mesh=build_mesh(args.image,grid=args.grid,width=args.width,height=args.height,depth=args.depth,bow=args.bow,relief=args.relief,alpha=args.alpha,clip=args.clip)
        text=json.dumps(mesh['report'],indent=2)+'\n'
        if args.output:
            args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(text,encoding='utf-8')
        if args.mesh_output:
            args.mesh_output.parent.mkdir(parents=True,exist_ok=True)
            args.mesh_output.write_text(json.dumps(mesh,separators=(',',':'))+'\n',encoding='utf-8')
        print(text,end='');return 0
    except (ValueError,OSError) as error:
        print('PAINTED RELIEF FAILED: '+str(error));return 1


if __name__=='__main__':raise SystemExit(main())
