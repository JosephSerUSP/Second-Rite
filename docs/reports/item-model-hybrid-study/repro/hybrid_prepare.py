from pathlib import Path
from PIL import Image
import sys,json,hashlib,shutil
sys.path.insert(0,'tools/blender');from painted_relief import build_mesh
P=Path('out/work/hybrid');OUT=Path('docs/reports/item-model-hybrid-study');OUT.mkdir(exist_ok=True)
PROJECT=OUT/'source-project';SOURCE=PROJECT/'assets/authoring/items';(SOURCE/'_textures').mkdir(parents=True,exist_ok=True);(PROJECT/'data').mkdir(exist_ok=True)
(PROJECT/'data/README.md').write_text('Compile-only study Project marker. No authored gameplay data; review installs candidate items only into disposable canonical stages.\n')
atlas=Image.open(P/'hybrid_surface_atlas.png').convert('RGB');w,h=atlas.size
requested=json.loads((P/'requested-layout.json').read_text());regions={}
def run_bounds(values,center):
    assert values[center];lo=hi=center
    while lo and values[lo-1]:lo-=1
    while hi+1<len(values) and values[hi+1]:hi+=1
    return lo,hi+1
for row,role in enumerate(['outer','core','binding','spine']):
 for col,direction in enumerate(['carved','salvage']):
    cx=int(w*(.25+.5*col));cy=int(h*(row+.5)/4)
    xs=[max(atlas.getpixel((x,cy)))>55 for x in range(w)]
    ys=[max(atlas.getpixel((cx,y)))>55 for y in range(h)]
    x0,x1=run_bounds(xs,cx);y0,y1=run_bounds(ys,cy)
    regions[direction+'_'+role]={'pixels':[x0,y0,x1,y1]}
layout={'imageSize':[w,h],'insetPixels':6,'regions':regions,'requested':requested,'boundary':'Actual contiguous material support measured at panel centres; original RGB unchanged. Texture grain and end seams remain.'}
(P/'actual-layout.json').write_text(json.dumps(layout,indent=2)+'\n')
shutil.copy2(P/'hybrid_surface_atlas.png',SOURCE/'_textures/hybrid_surface_atlas.png')
im=Image.open(P/'panels.png');pw,ph=im.size;panels={}
for row,direction in enumerate(['carved','salvage']):
 for col,side in enumerate(['left','right']):
    clip=[col*pw//2,row*ph//2,(col+1)*pw//2,(row+1)*ph//2]
    mesh=build_mesh(P/'panels.png',clip=clip,width=.92 if side=='left' else .76,height=3.25 if side=='left' else 2.6,grid=28,bow=0,depth=.1)
    panels[direction+'_'+side]=mesh
(P/'panel-meshes.json').write_text(json.dumps(panels,separators=(',',':'))+'\n')
def connected_bounds(image,clip):
    mask=image.getchannel('A');pixels=mask.load();x0,y0,x1,y1=clip
    pending={(x,y) for y in range(y0,y1) for x in range(x0,x1) if pixels[x,y]>=240};largest=set()
    while pending:
        seed=pending.pop();group={seed};queue=[seed]
        while queue:
            x,y=queue.pop()
            for n in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if n in pending:pending.remove(n);group.add(n);queue.append(n)
        if len(group)>len(largest):largest=group
    return [min(x for x,y in largest),min(y for x,y in largest),max(x for x,y in largest)+1,max(y for x,y in largest)+1]
cal={}
for direction in ['carved','salvage']:
    image=Image.open(P/f'reference-{direction}.png');iw,ih=image.size
    clips=[[0,0,iw//2,ih//2],[iw//2,0,iw,ih//2],[0,ih//2,iw//2,ih],[iw//2,ih//2,iw,ih]]
    bounds=[connected_bounds(image,clip) for clip in clips]
    front,right=bounds[:2];width=(front[2]-front[0])/(front[3]-front[1])*3.6;depth=(right[2]-right[0])/(right[3]-right[1])*3.6
    cal[direction]={'clips':clips,'opaqueMainComponentBounds':bounds,'targetDimensions':[width,depth,3.6],
      'boundary':'Independent connected opaque front/right silhouette ratios; includes bindings. Top/back inconsistent; hidden guides, core shape and cheek component outlines authored. Bounds matching is not scan reconstruction.'}
(P/'calibration.json').write_text(json.dumps(cal,indent=2)+'\n')
print('STUDY INPUTS READY',regions,{k:v['targetDimensions'] for k,v in cal.items()})
